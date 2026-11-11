"""Real API regressions for account deletion, runbook identifiers and attachment races."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import threading

from fastapi.testclient import TestClient
import pytest

from app import store
from app.main import app
from app.rag import build_retrieval_index, load_knowledge_base


@pytest.fixture(params=['sqlite', 'postgres'])
def audit_api(request, tmp_path, monkeypatch):
    database_url = os.getenv('DATABASE_URL', '') if request.param == 'postgres' else ''
    if request.param == 'postgres' and not database_url:
        pytest.skip('DATABASE_URL is not configured for PostgreSQL audit regressions')
    monkeypatch.setattr(store, '_database_url', database_url)
    monkeypatch.setattr(store, '_database_path', tmp_path / 'audit.sqlite3')
    monkeypatch.setattr(store, 'DEMO_MODE', True)
    attachments = tmp_path / 'attachments'
    monkeypatch.setattr('app.routers.tickets._get_attachments_dir', lambda: attachments)
    store.initialize_store()
    store.reset_store()
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    client = TestClient(app, raise_server_exceptions=False)
    yield client, attachments
    client.close()
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()


def _auth(client, role):
    response = client.post('/auth/login', json={'username': role, 'password': role})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['token']}


@pytest.mark.parametrize('actor', ['admin', 'self'])
def test_account_deletion_cleans_credentials_and_preserves_history(audit_api, monkeypatch, actor):
    from app import config, email_outbox

    client, _ = audit_api
    monkeypatch.setattr(config, 'DEMO_MODE', True)
    monkeypatch.setattr(config, 'EMAIL_PROVIDER', 'console')
    monkeypatch.setattr(config, 'PUBLIC_BASE_URL', '')
    username = 'delete-regression'
    store.create_user(username, 'SyntheticPassword123!', 'user', email='delete@example.invalid')
    login = client.post('/auth/login', json={'username': username, 'password': 'SyntheticPassword123!'})
    assert login.status_code == 200
    user_headers = {'Authorization': 'Bearer ' + login.json()['token']}
    ticket = store.create_ticket('Synthetic account deletion', 'Preserve this history.', 'hardware', 'medium', username)
    store.add_comment(ticket['id'], username, 'Synthetic comment')
    store.save_chat_exchange(username, None, 'Synthetic question', 'Synthetic answer', [])
    job = email_outbox.request_password_email(username, 'reset', 'https://helpdesk.example.invalid')
    assert job is not None
    with store._connect() as connection:
        connection.execute('INSERT INTO rate_limit_attempts (key, attempt_time) VALUES (?, ?)',
                           ('login:' + username, 1.0))
        assert connection.execute('SELECT id FROM email_deliveries WHERE username = ?', (username,)).fetchone()

    if actor == 'admin':
        response = client.request('DELETE', f'/admin/users/{username}', headers=_auth(client, 'admin'),
                                  json={'confirm_username': username})
    else:
        response = client.delete('/auth/me', headers=user_headers)
    assert response.status_code == 200, response.text
    assert store.get_user_credentials(username) is None
    assert client.get('/auth/me', headers=user_headers).status_code == 401
    preserved = store.get_ticket(ticket['id'])
    assert preserved['requester'] == store.ANONYMIZED_USER
    assert preserved['comments'][0]['author'] == store.ANONYMIZED_USER
    with store._connect() as connection:
        for query in ('SELECT COUNT(*) AS n FROM email_deliveries WHERE username = ?',
                      'SELECT COUNT(*) AS n FROM password_reset_tokens WHERE username = ?',
                      'SELECT COUNT(*) AS n FROM chat_sessions WHERE user_id = ?'):
            assert connection.execute(query, (username,)).fetchone()['n'] == 0
        assert connection.execute('SELECT COUNT(*) AS n FROM rate_limit_attempts WHERE key = ?',
                                  ('login:' + username,)).fetchone()['n'] == 0
        payloads = connection.execute('SELECT payload FROM notification_outbox WHERE ticket_id = ?',
                                     (ticket['id'],)).fetchall()
        assert payloads
        assert all(json.loads(row['payload'])['requester'] == store.ANONYMIZED_USER for row in payloads)


def test_admin_deletion_of_missing_account_returns_404(audit_api):
    client, _ = audit_api
    response = client.request('DELETE', '/admin/users/missing-account', headers=_auth(client, 'admin'),
                              json={'confirm_username': 'missing-account'})
    assert response.status_code == 404


def test_account_deletion_rolls_back_if_snapshot_anonymization_fails(audit_api):
    client, _ = audit_api
    store.create_user('delete-rollback', 'SyntheticPassword123!', 'user')
    ticket = store.create_ticket('Synthetic rollback', 'Preserve the owner on failure.', 'hardware', 'medium',
                                 'delete-rollback')
    with store._connect() as connection:
        connection.execute('UPDATE notification_outbox SET payload = ? WHERE ticket_id = ?',
                           ('invalid-json', ticket['id']))
    response = client.request('DELETE', '/admin/users/delete-rollback', headers=_auth(client, 'admin'),
                              json={'confirm_username': 'delete-rollback'})
    assert response.status_code == 409
    assert store.get_user_credentials('delete-rollback') is not None
    assert store.get_ticket(ticket['id'])['requester'] == 'delete-rollback'


def test_account_deletion_preserves_authorization_and_last_admin_guards(audit_api):
    client, _ = audit_api
    store.create_user('protected-target', 'SyntheticPassword123!', 'user')
    for role in ('user', 'agent'):
        response = client.request('DELETE', '/admin/users/protected-target', headers=_auth(client, role),
                                  json={'confirm_username': 'protected-target'})
        assert response.status_code == 403
    admin = _auth(client, 'admin')
    assert client.request('DELETE', '/admin/users/admin', headers=admin,
                          json={'confirm_username': 'admin'}).status_code == 409
    assert client.delete('/auth/me', headers=admin).status_code == 400
    assert client.request('DELETE', '/admin/users/protected-target', headers=admin,
                          json={'confirm_username': 'wrong-target'}).status_code == 422
    assert store.get_user_credentials('admin') is not None
    assert store.get_user_credentials('protected-target') is not None


def test_long_duplicate_runbooks_remain_manageable(audit_api):
    client, _ = audit_api
    headers = _auth(client, 'admin')
    sources = []
    for _ in range(12):
        response = client.post('/knowledge', headers=headers, json={
            'title': 'a' * 64, 'category': 'general',
            'content': '# Synthetic runbook\nSynthetic regression content.', 'status': 'draft',
        })
        assert response.status_code == 201
        sources.append(response.json()['source'])
    assert len(set(sources)) == len(sources)
    assert all(len(source.removesuffix('.md')) <= 64 for source in sources)
    for source in (sources[1], sources[-1]):
        assert client.post(f'/knowledge/{source}/reindex', headers=headers).status_code == 200
        assert client.delete(f'/knowledge/{source}', headers=headers).status_code == 200
        assert client.get(f'/knowledge/{source}', headers=headers).status_code == 404


@pytest.mark.parametrize('action', ['delete', 'reindex'])
def test_existing_long_collision_source_remains_manageable(audit_api, action):
    client, _ = audit_api
    # Preserve a source generated by earlier releases; no rename or data migration.
    source = 'a' * 64 + '_1.md'
    store.create_knowledge_document(
        'Legacy collision source', 'general', '# Synthetic legacy runbook',
        custom_slug=source, author='admin',
    )
    headers = _auth(client, 'admin')
    if action == 'delete':
        response = client.delete(f'/knowledge/{source}', headers=headers)
        assert response.status_code == 200
        assert client.get(f'/knowledge/{source}', headers=headers).status_code == 404
    else:
        response = client.post(f'/knowledge/{source}/reindex', headers=headers)
        assert response.status_code == 200


@pytest.mark.parametrize(('transition', 'expected_status'), [('close', 409), ('archive', 404)])
def test_upload_rechecks_lifecycle_after_file_write(audit_api, monkeypatch, transition, expected_status):
    client, attachments = audit_api
    user = _auth(client, 'user')
    agent = _auth(client, 'agent')
    admin = _auth(client, 'admin')
    created = client.post('/tickets', headers=user, json={
        'title': 'Synthetic attachment race', 'description': 'Synthetic lifecycle regression.',
        'category': 'hardware', 'priority': 'medium',
    })
    assert created.status_code == 201
    ticket_id = created.json()['ticket']['id']
    for status in ('in_progress', 'resolved'):
        assert client.patch(f'/tickets/{ticket_id}', headers=agent,
                            json={'status': status}).status_code == 200
    reached = threading.Event()
    release = threading.Event()
    original_add = store.add_attachment

    def paused_add(*args, **kwargs):
        reached.set()
        assert release.wait(10), 'Test did not release attachment persistence'
        return original_add(*args, **kwargs)

    monkeypatch.setattr(store, 'add_attachment', paused_add)
    with ThreadPoolExecutor(max_workers=1) as pool:
        upload = pool.submit(
            client.post, f'/tickets/{ticket_id}/attachments', headers=user,
            files={'file': ('race.log', b'Synthetic attachment content.', 'text/plain')},
        )
        try:
            assert reached.wait(10), 'Upload did not reach persistence'
            assert len(list(attachments.iterdir())) == 1
            if transition == 'close':
                changed = client.patch(f'/tickets/{ticket_id}', headers=user,
                                       json={'status': 'closed'})
            else:
                changed = client.delete(f'/tickets/{ticket_id}', headers=admin)
            assert changed.status_code == 200
        finally:
            release.set()
        response = upload.result(timeout=15)
    assert response.status_code == expected_status
    assert list(attachments.iterdir()) == []
    with store._connect() as connection:
        count = connection.execute(
            'SELECT COUNT(*) AS count FROM ticket_attachments WHERE ticket_id = ?', (ticket_id,),
        ).fetchone()['count']
    assert count == 0


def test_normal_attachment_stays_readable(audit_api):
    client, attachments = audit_api
    user = _auth(client, 'user')
    ticket_id = client.post('/tickets', headers=user, json={
        'title': 'Synthetic normal attachment', 'description': 'Synthetic control case.',
    }).json()['ticket']['id']
    response = client.post(f'/tickets/{ticket_id}/attachments', headers=user,
                           files={'file': ('control.log', b'Synthetic control.', 'text/plain')})
    assert response.status_code == 201
    attachment_id = response.json()['id']
    downloaded = client.get(f'/tickets/{ticket_id}/attachments/{attachment_id}', headers=user)
    assert downloaded.status_code == 200
    assert downloaded.content == b'Synthetic control.'
    assert len(list(attachments.iterdir())) == 1
