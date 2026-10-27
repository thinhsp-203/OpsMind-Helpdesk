"""Password strings are opaque: no trimming or Unicode normalization."""
import secrets
import unicodedata

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import store
from app.main import app, _failed_logins
from app.schemas import ResetPasswordRequest


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(store, '_database_url', '')
    monkeypatch.setattr(store, '_database_path', tmp_path / 'aud24.sqlite3')
    store.initialize_store()
    _failed_logins.clear()
    yield
    _failed_logins.clear()


@pytest.mark.parametrize('flow', ['create', 'change', 'reset', 'admin_reset'])
@pytest.mark.parametrize('sample', ['ascii_spaces', 'unicode_spaces', 'composed', 'decomposed'])
def test_password_roundtrip_across_credential_flows(flow, sample):
    suffix = secrets.token_urlsafe(16)
    candidates = {
        'ascii_spaces': '  ' + suffix + '  ',
        'unicode_spaces': '\u00a0\t' + suffix + '\t\u2003',
        'composed': '  Mật-khẩu-Đặng-' + suffix + '  ',
        'decomposed': '  ' + unicodedata.normalize('NFD', 'Mật-khẩu-Đặng-') + suffix + '  ',
    }
    candidate = candidates[sample]
    initial = '\tInitial-' + secrets.token_urlsafe(16) + '  '
    username = 'aud24user'
    client = TestClient(app)

    def login(value, user=username):
        return client.post('/auth/login', json={'username': user, 'password': value})

    def admin_headers():
        token = login('admin', 'admin').json()['token']
        return {'Authorization': 'Bearer ' + token}

    if flow == 'create':
        response = client.post('/admin/users', headers=admin_headers(), json={
            'username': username, 'password': candidate, 'role': 'user'})
        assert response.status_code == 201
    else:
        store.create_user(username, initial, 'user')
        if flow == 'change':
            token = login(initial).json()['token']
            response = client.post('/auth/change-password', headers={'Authorization': 'Bearer ' + token},
                json={'old_password': initial, 'new_password': candidate})
        elif flow == 'reset':
            token = store.create_password_reset_token(username)
            response = client.post('/auth/reset-password',
                json={'token': '  ' + token + '\n', 'new_password': candidate})
            assert store.verify_and_consume_reset_token(token) is None
        else:
            response = client.post(f'/admin/users/{username}/reset-password', headers=admin_headers(),
                json={'new_password': candidate})
        assert response.status_code == 200
        assert login(initial).status_code == 401

    credentials = store.get_user_credentials(username)
    assert store.verify_password(candidate, credentials['password_hash'])
    assert login(candidate).status_code == 200
    assert login(candidate.strip()).status_code == 401
    if sample in {'composed', 'decomposed'}:
        other_form = unicodedata.normalize('NFD' if sample == 'composed' else 'NFC', candidate)
        assert other_form != candidate
        assert login(other_form).status_code == 401


@pytest.mark.parametrize('length', [11, 12, 200, 201])
def test_reset_length_checks_use_exact_input(length):
    # Boundary whitespace counts exactly as it does for create/change/admin reset.
    candidate = ' ' + 'x' * (length - 2) + ' '
    token = secrets.token_urlsafe(32)
    if length in {12, 200}:
        payload = ResetPasswordRequest(token='  ' + token + ' ', new_password=candidate)
        assert payload.new_password == candidate
        assert payload.token == token
    else:
        with pytest.raises(ValidationError):
            ResetPasswordRequest(token=token, new_password=candidate)
