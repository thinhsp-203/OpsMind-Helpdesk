from concurrent.futures import ThreadPoolExecutor
import threading
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from app import store
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_assignment(tmp_path, monkeypatch):
    monkeypatch.setattr(store, '_database_path', tmp_path / 'db.sqlite3')
    monkeypatch.setattr(store, '_database_url', '')
    for key in ('TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'DISCORD_WEBHOOK_URL'):
        monkeypatch.delenv(key, raising=False)
    store.initialize_store()
    store.reset_store()


def make_ticket(status='in_progress'):
    doc = store.create_ticket('AUD14 synthetic ticket', 'Synthetic assignment attribution test', 'general', 'medium', 'user')
    store.assign_ticket(doc['id'], 'agent', 'admin')
    if status != 'new':
        store.update_ticket_status(doc['id'], 'in_progress', 'agent')
    if status in {'resolved', 'closed'}:
        store.update_ticket_status(doc['id'], 'resolved', 'agent')
    if status == 'closed':
        store.update_ticket_status(doc['id'], 'closed', 'user')
    if status in {'pending_waiting_user', 'escalated'}:
        store.update_ticket_status(doc['id'], status, 'agent')
    return doc


def auth(role='admin'):
    result = client.post('/auth/login', json={'username': role, 'password': role})
    assert result.status_code == 200
    return {'Authorization': 'Bearer ' + result.json()['token']}


@pytest.mark.parametrize('status', ['resolved', 'closed'])
@pytest.mark.parametrize('role', ['agent', 'admin'])
def test_completed_assignment_api_rejects_without_changing_attribution(status, role):
    doc = make_ticket(status)
    before = store.get_ticket(doc['id'])
    audit = store.get_ticket_audit(doc['id'])
    performance = store.get_analytics()['agent_performance']
    agent = store.get_agent_analytics('agent')
    response = client.put(f"/tickets/{doc['id']}/assignment", headers=auth(role), json={'assignee': 'admin'})
    assert response.status_code == 409
    assert store.get_ticket(doc['id']) == before
    assert store.get_ticket_audit(doc['id']) == audit
    assert store.get_analytics()['agent_performance'] == performance
    assert store.get_agent_analytics('agent') == agent


@pytest.mark.parametrize('status', ['resolved', 'closed'])
def test_store_enforces_completed_assignment_even_without_router(status):
    doc = make_ticket(status)
    with pytest.raises(ValueError):
        store.assign_ticket(doc['id'], 'admin', 'admin')
    assert store.get_ticket(doc['id'])['assignee'] == 'agent'


@pytest.mark.parametrize('status', ['new', 'in_progress', 'pending_waiting_user', 'escalated'])
def test_active_assignment_still_works(status):
    doc = make_ticket(status)
    result = client.put(f"/tickets/{doc['id']}/assignment", headers=auth(), json={'assignee': 'admin'})
    assert result.status_code == 200
    assert result.json()['ticket']['assignee'] == 'admin'
    assert store.get_ticket_audit(doc['id'])[0]['event'] == 'assigned'


def test_reopen_allows_assignment_and_next_resolution_uses_new_owner():
    doc = make_ticket('resolved')
    assert client.patch(f"/tickets/{doc['id']}", headers=auth('user'), json={'status': 'in_progress'}).status_code == 200
    assert client.put(f"/tickets/{doc['id']}/assignment", headers=auth(), json={'assignee': 'admin'}).status_code == 200
    store.update_ticket_status(doc['id'], 'resolved', 'admin')
    assert store.get_agent_analytics('admin')['resolved_tickets'] == 1
    assert store.get_agent_analytics('agent')['resolved_tickets'] == 0


def test_archived_and_missing_assignment_remain_not_found():
    doc = make_ticket()
    store.archive_ticket(doc['id'], 'admin')
    for identifier in (doc['id'], 999999):
        assert client.put(f'/tickets/{identifier}/assignment', headers=auth(), json={'assignee': 'admin'}).status_code == 404
        with pytest.raises(LookupError):
            store.assign_ticket(identifier, 'admin', 'admin')


def assert_assignment_serializes_with_resolution(monkeypatch):
    """Pause after assignment's read; the resolving writer must wait for its transaction."""
    doc = make_ticket()
    read = threading.Event()
    release = threading.Event()
    resolving = threading.Event()
    connect = store._connect

    class PausedConnection:
        def __init__(self):
            self.real = connect()

        def __enter__(self):
            self.real.__enter__()
            return self

        def __exit__(self, *args):
            return self.real.__exit__(*args)

        def execute(self, sql, parameters=()):
            cursor = self.real.execute(sql, parameters)
            if sql.startswith('SELECT * FROM tickets WHERE id = ? AND archived_at IS NULL'):
                snapshot = cursor.fetchone()
                cursor.close()
                read.set()
                assert release.wait(5), 'assignment read release timeout'
                return SimpleNamespace(fetchone=lambda: snapshot)
            return cursor

    def connection():
        return PausedConnection() if threading.current_thread().name.startswith('AUD14assign') else connect()

    def resolve():
        resolving.set()
        return store.update_ticket_status(doc['id'], 'resolved', 'agent')

    monkeypatch.setattr(store, '_connect', connection)
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix='AUD14assign') as assigner, ThreadPoolExecutor(max_workers=1) as resolver:
        assignment = assigner.submit(store.assign_ticket, doc['id'], 'admin', 'admin')
        try:
            assert read.wait(5)
            resolution = resolver.submit(resolve)
            assert resolving.wait(5)
            with pytest.raises(TimeoutError):
                resolution.result(timeout=.2)
        finally:
            release.set()
        assert assignment.result(timeout=10)['assignee'] == 'admin'
        assert resolution.result(timeout=10)['status'] == 'resolved'
    assert store.get_ticket(doc['id'])['assignee'] == 'admin'
    assert store.get_agent_analytics('admin')['resolved_tickets'] == 1
    with pytest.raises(ValueError):
        store.assign_ticket(doc['id'], 'agent', 'admin')


def test_assignment_transaction_serializes_with_resolution(monkeypatch):
    assert_assignment_serializes_with_resolution(monkeypatch)


def test_missing_ticket_after_api_visibility_check_maps_to_not_found(monkeypatch):
    doc = make_ticket()

    def missing(*args):
        raise LookupError('Synthetic archive race')

    monkeypatch.setattr(store, 'assign_ticket', missing)
    assert client.put(f"/tickets/{doc['id']}/assignment", headers=auth(), json={'assignee': 'admin'}).status_code == 404


def test_completed_assignment_cannot_be_bypassed_by_requester_or_same_assignee():
    doc = make_ticket('closed')
    url = f"/tickets/{doc['id']}/assignment"
    assert client.put(url, headers=auth('user'), json={'assignee': 'admin'}).status_code == 403
    assert client.put(url, headers=auth('admin'), json={'assignee': 'agent'}).status_code == 409
