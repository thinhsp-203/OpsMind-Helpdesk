"""KB imports and deletion use committed DB state, never a second mutable file copy."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest

from app import store
from app.main import app
from app.rag import build_retrieval_index, load_knowledge_base

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_knowledge(tmp_path, monkeypatch):
    monkeypatch.setattr(store, '_database_url', '')
    monkeypatch.setattr(store, '_database_path', tmp_path / 'db.sqlite3')
    store.initialize_store()
    store.reset_store()
    builtin = tmp_path / 'builtin'
    runtime = tmp_path / 'runtime-knowledge'
    builtin.mkdir()
    runtime.mkdir()
    monkeypatch.setattr('app.main.KNOWLEDGE_DIR', builtin)
    monkeypatch.setattr('app.routers.knowledge.BASE_KNOWLEDGE_DIR', builtin, raising=False)
    monkeypatch.setattr('app.routers.knowledge.STORAGE_KNOWLEDGE_DIR', runtime, raising=False)
    load_knowledge_base.cache_clear()
    yield builtin, runtime
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()


def login(username='admin', password=None):
    response = client.post('/auth/login', json={'username': username, 'password': password or username})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['token']}


def test_builtin_reviewed_edit_survives_fresh_process(isolated_knowledge):
    original = store.get_knowledge_document('wifi_network.md')
    store.update_knowledge_document(original['id'], {
        'content': '# Reviewed WiFi\nReviewed configuration from the publication database.',
        'status': 'pending_review',
    }, 'admin', change_summary='Restart regression')
    before = store.get_knowledge_document(original['id'])
    versions = store.list_knowledge_versions(original['id'])
    script = """
import json
from app import store
doc = store.get_knowledge_document('wifi_network.md')
print(json.dumps({'document': doc, 'versions': store.list_knowledge_versions(doc['id'])}))
"""
    environment = {**os.environ, 'DATABASE_URL': '', 'DEMO_MODE': 'true',
                   'HELPDESK_DB_PATH': str(store._database_path), 'PYTHONDONTWRITEBYTECODE': '1'}
    output = subprocess.check_output(  # noqa: S603 -- fixed script, interpreter and isolated DB
        [sys.executable, '-c', script], env=environment,
        cwd=Path(__file__).resolve().parents[1], timeout=15,
    )
    restored = json.loads(output)
    assert restored == {'document': before, 'versions': versions}


def upload(headers, filename='aud11-import.md', title='AUD11 imported knowledge'):
    return client.post('/knowledge', headers=headers, data={'title': title},
                       files={'document': (filename, b'# AUD11\n\nSynthetic quasar runbook.', 'text/markdown')})


def test_upload_db_outage_is_failure_without_files_or_rows(isolated_knowledge, monkeypatch):
    headers = login()
    original = store.create_knowledge_document

    def unavailable(*args, **kwargs):
        raise sqlite3.OperationalError('AUD11 synthetic DB outage')

    monkeypatch.setattr(store, 'create_knowledge_document', unavailable)
    response = upload(headers)
    assert response.status_code == 503
    assert 'AUD11 synthetic' not in response.text
    assert store.get_knowledge_document('aud11-import.md') is None
    assert all(not list(root.iterdir()) for root in isolated_knowledge)
    monkeypatch.setattr(store, 'create_knowledge_document', original)
    assert upload(headers).status_code == 201


def test_upload_version_insert_failure_rolls_back_document_and_creates_no_file(isolated_knowledge):
    headers = login()
    with store._connect() as connection:
        connection.execute("""CREATE TRIGGER aud11_fail_version BEFORE INSERT ON knowledge_versions
            WHEN NEW.title = 'AUD11 imported knowledge'
            BEGIN SELECT RAISE(ABORT, 'AUD11 synthetic version failure'); END""")
    response = upload(headers)
    assert response.status_code == 503
    assert store.get_knowledge_document('aud11-import.md') is None
    assert all(not list(root.iterdir()) for root in isolated_knowledge)


def test_upload_duplicate_db_slug_preserves_content_and_versions(isolated_knowledge):
    headers = login()
    doc = store.create_knowledge_document('Existing', 'general', '# Original', custom_slug='aud11-import.md')
    response = upload(headers)
    assert response.status_code == 409
    assert store.get_knowledge_document(doc['id'])['content'] == '# Original'
    assert len(store.list_knowledge_versions(doc['id'])) == 1
    assert all(not list(root.iterdir()) for root in isolated_knowledge)


def test_upload_succeeds_without_filesystem_write_permission(isolated_knowledge, monkeypatch):
    headers = login()
    original_open = Path.open

    def read_only(path, mode='r', *args, **kwargs):
        if any(path.is_relative_to(root) for root in isolated_knowledge) and any(flag in mode for flag in 'wax+'):
            raise PermissionError('AUD11 synthetic immutable image')
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', read_only)
    response = upload(headers)
    assert response.status_code == 201
    source = response.json()['source']
    doc = store.get_knowledge_document(source)
    assert doc['content'] == '# AUD11\n\nSynthetic quasar runbook.'
    assert doc['status'] == 'published' and not doc['is_builtin']
    assert client.get('/knowledge/' + source, headers=headers).json()['content'] == doc['content']
    assert source in {item['source'] for item in load_knowledge_base()}
    assert all(not list(root.iterdir()) for root in isolated_knowledge)


def test_upload_preserves_actor_and_provenance_after_process_restart(isolated_knowledge):
    store.create_user('aud11admin', 'AUD11-synthetic-password', 'admin')
    response = upload(login('aud11admin', 'AUD11-synthetic-password'))
    assert response.status_code == 201
    source = response.json()['source']
    environment = {**os.environ, 'DATABASE_URL': '', 'HELPDESK_DB_PATH': str(store._database_path),
                   'DEMO_MODE': 'true', 'SECRET_KEY': 'AUD11-synthetic-secret-more-than-32-characters'}
    script = '''
import json, sys
from app import store
store.initialize_store()
doc = store.get_knowledge_document(sys.argv[1])
print(json.dumps({'doc': doc, 'versions': store.list_knowledge_versions(doc['id'])}))
'''
    result = subprocess.run(  # noqa: S603 -- trusted interpreter, fixed script and synthetic database
        [sys.executable, '-c', script, source], env=environment,
        capture_output=True, text=True, encoding='utf8', timeout=15, check=True,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )
    state = json.loads(result.stdout)
    assert state['doc']['author'] == 'aud11admin'
    assert state['doc']['reviewer'] == 'aud11admin'
    assert not state['doc']['is_builtin']
    assert len(state['versions']) == 1 and state['versions'][0]['author'] == 'aud11admin'
    assert all(not list(root.iterdir()) for root in isolated_knowledge)


def test_concurrent_duplicate_uploads_have_one_document_and_one_version(isolated_knowledge):
    headers = login()
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: upload(headers), range(2)))
    assert sorted(response.status_code for response in responses) == [201, 409]
    doc = store.get_knowledge_document('aud11-import.md')
    assert len(store.list_knowledge_versions(doc['id'])) == 1
    assert all(not list(root.iterdir()) for root in isolated_knowledge)


@pytest.mark.parametrize('operation', ['list', 'get', 'reindex', 'delete'])
def test_legacy_file_without_db_record_is_not_served_or_mutated(isolated_knowledge, monkeypatch, operation):
    builtin, _ = isolated_knowledge
    legacy = builtin / 'aud11-orphan.md'
    legacy.write_text('# AUD11 orphan\nUnreviewed legacy file', encoding='utf8')
    monkeypatch.setattr('app.rag.KNOWLEDGE_DIR', builtin)
    with store._connect() as connection:
        connection.execute("UPDATE knowledge_documents SET status = 'archived'")
    headers = login()
    if operation == 'list':
        assert client.get('/knowledge', headers=login('user', 'user')).json() == []
    else:
        method = {'get': 'GET', 'reindex': 'POST', 'delete': 'DELETE'}[operation]
        suffix = '/reindex' if operation == 'reindex' else ''
        assert client.request(method, '/knowledge/aud11-orphan.md' + suffix, headers=headers).status_code == 404
    assert legacy.read_text(encoding='utf8') == '# AUD11 orphan\nUnreviewed legacy file'


def test_delete_rejects_builtin_collision_before_mutating_db(isolated_knowledge):
    builtin, _ = isolated_knowledge
    (builtin / 'aud11-shadow.md').write_text('# Packaged sentinel', encoding='utf8')
    doc = store.create_knowledge_document('Legacy shadow', 'general', '# Custom', custom_slug='aud11-shadow.md')
    response = client.delete('/knowledge/aud11-shadow.md', headers=login())
    assert response.status_code == 403
    assert store.get_knowledge_document(doc['id']) is not None
    assert len(store.list_knowledge_versions(doc['id'])) == 1


def test_delete_failure_preserves_db_and_legacy_file(isolated_knowledge, monkeypatch):
    builtin, _ = isolated_knowledge
    legacy = builtin / 'aud11-import.md'
    legacy.write_text('# Legacy copy', encoding='utf8')
    doc = store.create_knowledge_document('Existing', 'general', '# Original', custom_slug='aud11-import.md')
    # A custom runtime copy must not be part of the API transaction.
    monkeypatch.setattr('app.routers.knowledge.BASE_KNOWLEDGE_DIR', builtin / 'packaged', raising=False)

    def unavailable(*args, **kwargs):
        raise sqlite3.OperationalError('AUD11 synthetic delete failure')

    monkeypatch.setattr(store, 'delete_knowledge_document', unavailable)
    response = client.delete('/knowledge/aud11-import.md', headers=login())
    assert response.status_code == 503
    assert store.get_knowledge_document(doc['id']) is not None
    assert legacy.read_text(encoding='utf8') == '# Legacy copy'


def test_delete_success_removes_db_versions_without_resurrecting_legacy_file(isolated_knowledge, monkeypatch):
    builtin, runtime = isolated_knowledge
    monkeypatch.setattr('app.routers.knowledge.BASE_KNOWLEDGE_DIR', builtin / 'packaged', raising=False)
    for root in (builtin, runtime):
        (root / 'aud11-import.md').write_text('# Legacy copy', encoding='utf8')
    headers = login()
    assert upload(headers).status_code == 201
    doc = store.get_knowledge_document('aud11-import.md')
    assert client.delete('/knowledge/aud11-import.md', headers=headers).status_code == 200
    assert store.get_knowledge_document(doc['id']) is None
    assert store.list_knowledge_versions(doc['id']) == []
    assert client.get('/knowledge/aud11-import.md', headers=headers).status_code == 404
    assert all((root / 'aud11-import.md').read_text(encoding='utf8') == '# Legacy copy' for root in (builtin, runtime))
