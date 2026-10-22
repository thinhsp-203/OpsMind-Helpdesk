from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
import secrets
import sqlite3
import subprocess
import sys

from fastapi.testclient import TestClient
import jwt
import pytest

from app import config, store
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr(store, '_database_path', tmp_path / 'db.sqlite3')
    monkeypatch.setattr(store, '_database_url', '')
    store.initialize_store()
    store.reset_store()


def login(username='user', password=None):
    response = client.post('/auth/login', json={'username': username, 'password': password or username})
    assert response.status_code == 200
    return response.json()['token']


def headers(token):
    return {'Authorization': 'Bearer ' + token}


def me(token):
    return client.get('/auth/me', headers=headers(token))


def test_logout_revokes_all_copied_tokens_and_new_login_works():
    first, second = login(), login()
    response = client.post('/auth/logout', headers=headers(first))
    assert response.status_code == 200
    assert response.json()['revoked'] is True
    assert me(first).status_code == me(second).status_code == 401
    assert me(login()).status_code == 200


@pytest.mark.parametrize('changes', [
    [{'is_active': False}, {'is_active': True}],
    [{'role': 'agent'}, {'role': 'user'}],
])
def test_tokens_do_not_resurrect_after_account_cycles(changes):
    token = login()
    for change in changes:
        assert client.patch('/admin/users/user', headers=headers(login('admin')), json=change).status_code == 200
        assert me(token).status_code == 401
    assert me(login()).status_code == 200


def test_profile_and_noop_updates_preserve_sessions():
    token = login()
    epoch = store.get_user_credentials('user').get('session_epoch')
    store.update_user('user', {'full_name': 'AUD15 synthetic', 'role': 'user', 'is_active': True})
    assert me(token).status_code == 200
    assert store.get_user_credentials('user').get('session_epoch') == epoch


@pytest.mark.parametrize('epoch', [None, '', 7, True, 'x' * 64, 'é' * 64])
def test_missing_or_invalid_epoch_is_not_accepted(epoch):
    payload = jwt.decode(login(), config.SECRET_KEY, algorithms=[config.ALGORITHM])
    if epoch is None:
        payload.pop('session_epoch', None)
    else:
        payload['session_epoch'] = epoch
    token = jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)
    assert me(token).status_code == 401


def test_password_reset_and_admin_reset_rotate_epoch():
    token = login()
    reset = store.create_password_reset_token('user')
    assert client.post('/auth/reset-password', json={'token': reset, 'new_password': 'AUD15-synthetic-password'}).status_code == 200
    assert me(token).status_code == 401
    token = login('user', 'AUD15-synthetic-password')
    epoch = store.get_user_credentials('user')['session_epoch']
    store.admin_reset_password('user', 'AUD15-another-password', force_password_change=1)
    assert store.get_user_credentials('user')['session_epoch'] != epoch
    assert me(token).status_code == 401
    forced = login('user', 'AUD15-another-password')
    assert client.post('/auth/logout', headers=headers(forced)).status_code == 200
    assert me(forced).status_code == 401


def test_stale_logout_does_not_revoke_newer_epoch():
    from app.store import revoke_user_sessions
    token = login()
    epoch = store.get_user_credentials('user')['session_epoch']
    assert revoke_user_sessions('user', epoch)
    new_token = login()
    assert not revoke_user_sessions('user', epoch)
    assert me(token).status_code == 401 and me(new_token).status_code == 200


def test_session_revocation_is_atomic_with_account_update(monkeypatch):
    token = login()
    original = store._revoke_password_reset_tokens

    def fail(*args, **kwargs):
        raise sqlite3.OperationalError('AUD15 synthetic rollback')

    monkeypatch.setattr(store, '_revoke_password_reset_tokens', fail)
    with pytest.raises(sqlite3.OperationalError):
        store.update_user('user', {'is_active': False})
    monkeypatch.setattr(store, '_revoke_password_reset_tokens', original)
    assert store.get_user_credentials('user')['is_active'] == 1
    assert me(token).status_code == 200


def test_logout_db_failure_is_not_a_success(monkeypatch):
    token = login()

    def fail(*args):
        raise sqlite3.OperationalError('AUD15 synthetic failure')

    monkeypatch.setattr(store, 'revoke_user_sessions', fail)
    assert client.post('/auth/logout', headers=headers(token)).status_code == 503
    assert me(token).status_code == 200


def test_logout_requires_authentication_and_does_not_accept_username_body():
    token = login('admin')
    assert client.post('/auth/logout', json={'username': 'admin'}).status_code == 401
    user = login()
    assert client.post('/auth/logout', headers=headers(user), json={'username': 'admin'}).status_code == 200
    assert me(token).status_code == 200 and me(user).status_code == 401


def test_migration_is_idempotent_and_new_accounts_have_distinct_epochs():
    first = store.get_user_credentials('user')['session_epoch']
    assert len(first) == 64
    store.initialize_store()
    assert store.get_user_credentials('user')['session_epoch'] == first
    store.create_user('aud15', 'AUD15-synthetic-password', 'user')
    assert store.get_user_credentials('aud15')['session_epoch'] != first


def test_revocation_survives_process_restart():
    token = login()
    assert client.post('/auth/logout', headers=headers(token)).status_code == 200
    environment = {**os.environ, 'DATABASE_URL': '', 'HELPDESK_DB_PATH': str(store._database_path),
                   'DEMO_MODE': 'true', 'SECRET_KEY': config.SECRET_KEY}
    script = '''
import json, sys
from fastapi.testclient import TestClient
from app.main import app
assert TestClient(app).get('/auth/me', headers={'Authorization': 'Bearer ' + json.loads(sys.stdin.read())}).status_code == 401
'''
    subprocess.run(  # noqa: S603 -- trusted interpreter, fixed script, synthetic DB/token over stdin
        [sys.executable, '-c', script], input=json.dumps(token), text=True, env=environment,
        check=True, capture_output=True, timeout=15,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def test_concurrent_revocation_has_one_winner():
    from app.store import revoke_user_sessions
    epoch = store.get_user_credentials('user')['session_epoch']
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: revoke_user_sessions('user', epoch), range(2)))
    assert sorted(results) == [False, True]


def test_legacy_schema_gets_epoch_without_resetting_it(tmp_path, monkeypatch):
    database = tmp_path / 'legacy.sqlite3'
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, role TEXT NOT NULL)')
        connection.execute('INSERT INTO users VALUES (?, ?, ?)', ('legacy', store._password_hash('AUD15-legacy-password'), 'admin'))
    monkeypatch.setattr(store, '_database_path', database)
    store.initialize_store()
    epoch = store.get_user_credentials('legacy')['session_epoch']
    assert len(epoch) == 64
    store.initialize_store()
    assert store.get_user_credentials('legacy')['session_epoch'] == epoch
    assert me(login('legacy', 'AUD15-legacy-password')).status_code == 200


@pytest.mark.parametrize('alteration', ['expired', 'wrong_signature', 'missing_exp', 'missing_iat'])
def test_other_jwt_validations_are_preserved(alteration):
    payload = jwt.decode(login(), config.SECRET_KEY, algorithms=[config.ALGORITHM])
    secret = config.SECRET_KEY
    if alteration == 'expired':
        payload['exp'] = datetime.now(timezone.utc) - timedelta(seconds=60)
    elif alteration == 'wrong_signature':
        secret = secrets.token_urlsafe(48)
    else:
        payload.pop('exp' if alteration == 'missing_exp' else 'iat')
    token = jwt.encode(payload, secret, algorithm=config.ALGORITHM)
    assert me(token).status_code == 401


def test_login_with_uninitialized_epoch_does_not_issue_unusable_token():
    with store._connect() as connection:
        connection.execute("UPDATE users SET session_epoch = '' WHERE username = 'user'")
    response = client.post('/auth/login', json={'username': 'user', 'password': 'user'})
    assert response.status_code == 503
    assert 'token' not in response.json()
