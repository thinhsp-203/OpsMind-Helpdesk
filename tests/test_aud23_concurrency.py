"""Real independent DB connections with a controlled read/write interleaving."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import threading
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(store, '_database_path', tmp_path / 'aud23.sqlite3')
    monkeypatch.setattr(store, '_database_url', '')
    store.initialize_store()


def ticket(status='in_progress'):
    item = store.create_ticket('AUD23 sandbox', 'Concurrency regression', 'software', 'medium', 'user')
    store.update_ticket_status(item['id'], 'in_progress', 'agent')
    if status == 'resolved':
        store.update_ticket_status(item['id'], 'resolved', 'agent')
    return item['id']


def interleave(monkeypatch, table, first, second):
    """Pause first after its DB read. A competing writer must wait on the DB lock.

    The pause is outside any application mutex. SQL, transactions and constraints
    are real; only the cursor's already-read result is delayed.
    """
    connect = store._connect
    read, release, started = threading.Event(), threading.Event(), threading.Event()
    paused = False

    class PausedConnection:
        def __init__(self):
            self.real = connect()

        def __enter__(self):
            self.real.__enter__()
            return self

        def __exit__(self, *args):
            return self.real.__exit__(*args)

        def execute(self, sql, parameters=()):
            nonlocal paused
            cursor = self.real.execute(sql, parameters)
            if not paused and sql.lstrip().startswith('SELECT') and f'FROM {table}' in sql:
                paused = True
                snapshot = cursor.fetchone()
                cursor.close()
                read.set()
                assert release.wait(10), 'read release timed out'
                return SimpleNamespace(fetchone=lambda: snapshot)
            return cursor

    monkeypatch.setattr(store, '_connect', lambda: PausedConnection()
                        if threading.current_thread().name.startswith('AUD23first') else connect())

    def run(operation, mark=False):
        if mark:
            started.set()
        try:
            return 'accepted', operation()
        except ValueError as exc:
            return 'conflict', str(exc)

    with ThreadPoolExecutor(max_workers=1, thread_name_prefix='AUD23first') as a, ThreadPoolExecutor(max_workers=1) as b:
        one = a.submit(run, first)
        try:
            assert read.wait(10), 'first transaction did not read'
            two = b.submit(run, second, True)
            assert started.wait(5)
            try:
                two.result(timeout=.25)
                blocked = False
            except TimeoutError:
                blocked = True
        finally:
            release.set()
        results = one.result(timeout=15), two.result(timeout=15)
    return blocked, results


def assert_csat_one_winner(monkeypatch):
    identifier = ticket('resolved')
    blocked, results = interleave(monkeypatch, 'tickets',
        lambda: store.rate_ticket(identifier, 4, 'first', 'user'),
        lambda: store.rate_ticket(identifier, 1, 'second', 'user'))
    assert [r[0] for r in results] == ['accepted', 'conflict'], results
    assert blocked
    assert store.get_ticket(identifier)['rating'] == 4
    assert len([r for r in store.get_ticket_audit(identifier) if r['event'] == 'rated']) == 1


def test_csat_two_connections_one_winner(monkeypatch):
    assert_csat_one_winner(monkeypatch)


def assert_comment_does_not_undo_resolution(monkeypatch):
    identifier = ticket()
    blocked, results = interleave(monkeypatch, 'tickets',
        lambda: store.add_comment(identifier, 'user', 'More information'),
        lambda: store.update_ticket_status(identifier, 'resolved', 'agent'))
    assert all(r[0] == 'accepted' for r in results)
    assert store.get_ticket(identifier)['status'] == 'resolved'
    assert store.get_ticket(identifier)['resolved_at']
    assert blocked


def test_comment_cannot_restore_stale_status(monkeypatch):
    assert_comment_does_not_undo_resolution(monkeypatch)


def assert_kb_partial_updates_preserved(monkeypatch):
    doc = store.create_knowledge_document('AUD23 KB', 'general', 'original', tags='old')
    blocked, results = interleave(monkeypatch, 'knowledge_documents',
        lambda: store.update_knowledge_document(doc['id'], {'title': 'Title A'}, 'agent'),
        lambda: store.update_knowledge_document(doc['id'], {'tags': 'Tags B'}, 'admin'))
    assert all(r[0] == 'accepted' for r in results)
    current = store.get_knowledge_document(doc['id'])
    assert (current['title'], current['tags']) == ('Title A', 'Tags B')
    versions = store.list_knowledge_versions(doc['id'])
    assert [v['version_number'] for v in versions] == [3, 2, 1]
    assert versions[0]['title'] == current['title'] and versions[0]['tags'] == current['tags']
    assert blocked


def test_kb_partial_updates_do_not_erase_each_other(monkeypatch):
    assert_kb_partial_updates_preserved(monkeypatch)


@pytest.mark.parametrize('operation', ['review', 'restore'])
def test_kb_all_version_writers_lock_current_document(monkeypatch, operation):
    doc = store.create_knowledge_document('AUD23 review', 'general', 'v1')
    store.update_knowledge_document(doc['id'], {'content': 'v2'}, 'agent')
    first = (lambda: store.review_knowledge_document(doc['id'], 'approve', 'admin')) if operation == 'review' else (
        lambda: store.restore_knowledge_version(doc['id'], 1, 'admin'))
    blocked, results = interleave(monkeypatch, 'knowledge_documents', first,
        lambda: store.update_knowledge_document(doc['id'], {'tags': 'latest'}, 'agent'))
    assert all(r[0] == 'accepted' for r in results)
    current = store.get_knowledge_document(doc['id'])
    versions = store.list_knowledge_versions(doc['id'])
    assert [v['version_number'] for v in versions] == [4, 3, 2, 1]
    for field in ('title', 'content', 'tags', 'category'):
        assert versions[0][field] == current[field]
    assert blocked


def test_database_rejects_duplicate_kb_version():
    doc = store.create_knowledge_document('AUD23 unique', 'general', 'text')
    with pytest.raises(store.DatabaseIntegrityError):
        with store._connect() as connection:
            connection.execute('''INSERT INTO knowledge_versions
                (document_id, version_number, title, category, tags, content, change_summary, author, created_at)
                SELECT document_id, version_number, title, category, tags, content, change_summary, author, created_at
                FROM knowledge_versions WHERE document_id = ?''', (doc['id'],))
    assert len(store.list_knowledge_versions(doc['id'])) == 1


def test_stale_expected_status_returns_409_without_audit():
    identifier = ticket()
    client = TestClient(app)
    token = client.post('/auth/login', json={'username': 'agent', 'password': 'agent'}).json()['token']
    before = store.get_ticket_audit(identifier)
    response = client.patch(f'/tickets/{identifier}', headers={'Authorization': f'Bearer {token}'},
        json={'status': 'resolved', 'expected_status': 'new'})
    assert response.status_code == 409
    assert store.get_ticket(identifier)['status'] == 'in_progress'
    assert store.get_ticket_audit(identifier) == before


def test_api_visibility_snapshot_is_checked_in_write_transaction(monkeypatch):
    from app.routers import tickets
    identifier = ticket()
    client = TestClient(app)
    token = client.post('/auth/login', json={'username': 'agent', 'password': 'agent'}).json()['token']
    visible = tickets.visible_ticket

    def stale(*args):
        snapshot = visible(*args)
        store.update_ticket_status(identifier, 'in_progress', 'agent')
        store.update_ticket_status(identifier, 'resolved', 'agent')
        # in_progress is valid from both waiting and resolved; FSM validation alone is insufficient.
        return snapshot

    store.update_ticket_status(identifier, 'pending_waiting_user', 'agent')
    monkeypatch.setattr(tickets, 'visible_ticket', stale)
    response = client.patch(f'/tickets/{identifier}', headers={'Authorization': f'Bearer {token}'},
        json={'status': 'in_progress'})
    assert response.status_code == 409
    assert store.get_ticket(identifier)['status'] == 'resolved'


def assert_status_one_winner(monkeypatch):
    identifier = ticket()
    blocked, results = interleave(monkeypatch, 'tickets',
        lambda: store.update_ticket_status(identifier, 'resolved', 'agent', expected_status='in_progress'),
        lambda: store.update_ticket_status(identifier, 'pending_waiting_user', 'agent', expected_status='in_progress'))
    assert [r[0] for r in results] == ['accepted', 'conflict']
    assert blocked
    assert store.get_ticket(identifier)['status'] == 'resolved'
    assert len([r for r in store.get_ticket_audit(identifier) if r['event'] == 'status_changed']) == 2


def test_competing_status_requests_one_winner(monkeypatch):
    assert_status_one_winner(monkeypatch)


def test_priority_writer_rechecks_completed_status_after_lock(monkeypatch):
    identifier = ticket()
    blocked, results = interleave(monkeypatch, 'tickets',
        lambda: store.update_ticket_status(identifier, 'resolved', 'agent'),
        lambda: store.update_ticket_fields(identifier, 'agent', {'priority': 'urgent'}))
    assert [r[0] for r in results] == ['accepted', 'conflict']
    assert blocked
    assert store.get_ticket(identifier)['priority'] == 'medium'


def test_csat_audit_failure_rolls_back_rating(monkeypatch):
    identifier = ticket('resolved')
    before = store.get_ticket(identifier)

    def fail(*args):
        raise RuntimeError('AUD23 synthetic audit failure')

    monkeypatch.setattr(store, '_record_audit', fail)
    with pytest.raises(RuntimeError, match='AUD23'):
        store.rate_ticket(identifier, 5, 'test', 'user')
    assert store.get_ticket(identifier) == before


@pytest.mark.parametrize('operation', ['update', 'review', 'restore'])
def test_version_insert_failure_rolls_back_document(operation):
    doc = store.create_knowledge_document('AUD23 rollback', 'general', 'original')
    before = store.get_knowledge_document(doc['id'])
    versions = store.list_knowledge_versions(doc['id'])
    with store._connect() as connection:
        connection.execute("CREATE TRIGGER aud23_fail BEFORE INSERT ON knowledge_versions "
                           "BEGIN SELECT RAISE(ABORT, 'AUD23 synthetic version failure'); END;")
    actions = {
        'update': lambda: store.update_knowledge_document(doc['id'], {'content': 'changed'}, 'agent'),
        'review': lambda: store.review_knowledge_document(doc['id'], 'approve', 'admin'),
        'restore': lambda: store.restore_knowledge_version(doc['id'], 1, 'admin'),
    }
    with pytest.raises(store.DatabaseIntegrityError):
        actions[operation]()
    assert store.get_knowledge_document(doc['id']) == before
    assert store.list_knowledge_versions(doc['id']) == versions


def test_legacy_duplicate_versions_abort_migration_without_repair():
    doc = store.create_knowledge_document('AUD23 legacy duplicate', 'general', 'text')
    with store._connect() as connection:
        connection.execute('DROP INDEX uq_knowledge_document_version')
        connection.execute('''INSERT INTO knowledge_versions
            (document_id, version_number, title, category, tags, content, change_summary, author, created_at)
            SELECT document_id, version_number, title, category, tags, content, change_summary, author, created_at
            FROM knowledge_versions WHERE document_id = ?''', (doc['id'],))
    before = store.list_knowledge_versions(doc['id'])
    with pytest.raises(RuntimeError, match='AUD-23: duplicate KB version'):
        store.initialize_store()
    assert store.list_knowledge_versions(doc['id']) == before


def test_clean_migration_is_idempotent():
    doc = store.create_knowledge_document('AUD23 migration', 'general', 'text')
    before = store.list_knowledge_versions(doc['id'])
    store.initialize_store()
    store.initialize_store()
    assert store.list_knowledge_versions(doc['id']) == before
    test_database_rejects_duplicate_kb_version()


def test_closed_during_comment_visibility_check_returns_409(monkeypatch):
    from app.routers import tickets
    identifier = ticket('resolved')
    client = TestClient(app)
    token = client.post('/auth/login', json={'username': 'user', 'password': 'user'}).json()['token']
    visible = tickets.visible_ticket

    def stale(*args):
        snapshot = visible(*args)
        store.update_ticket_status(identifier, 'closed', 'user')
        return snapshot

    monkeypatch.setattr(tickets, 'visible_ticket', stale)
    response = client.post(f'/tickets/{identifier}/comments', headers={'Authorization': f'Bearer {token}'},
                           json={'comment': 'stale request'})
    assert response.status_code == 409
    assert store.get_ticket(identifier)['comments'] == []


def test_client_expected_status_cannot_override_authorized_snapshot(monkeypatch):
    from app.routers import tickets
    identifier = ticket('resolved')
    client = TestClient(app)
    token = client.post('/auth/login', json={'username': 'user', 'password': 'user'}).json()['token']
    visible = tickets.visible_ticket

    def stale(*args):
        snapshot = visible(*args)
        store.update_ticket_status(identifier, 'in_progress', 'agent')
        store.update_ticket_status(identifier, 'pending_waiting_user', 'agent')
        return snapshot

    monkeypatch.setattr(tickets, 'visible_ticket', stale)
    response = client.patch(f'/tickets/{identifier}', headers={'Authorization': f'Bearer {token}'},
        json={'status': 'in_progress', 'expected_status': 'pending_waiting_user'})
    assert response.status_code == 409
    assert store.get_ticket(identifier)['status'] == 'pending_waiting_user'
