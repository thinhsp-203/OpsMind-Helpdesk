"""Regressions for persistence, honest evaluation, session context and load results."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app
from app.rag import contextualize_question, generate_answer
from scripts.benchmark_load import login_benchmark, run_benchmark
from scripts.evaluation_support import score_evidence_rubric


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, '_database_url', '')
    monkeypatch.setattr(store, '_database_path', tmp_path / 'review.sqlite3')
    store.initialize_store()
    return TestClient(app)


@pytest.mark.parametrize(('evidence', 'text', 'score'), [
    ('restart print spooler', 'Do not restart the device.', 0.0),
    ('vpn', 'OpenVPN', 0.0),
    ('print spooler', 'PRINT, SPOOLER', 1.0),
    ('đổi mật khẩu;VPN', 'Đổi mật khẩu cho VPN.', 1.0),
    ('', 'Any arbitrary passage.', 0.0),
    ('restart print spooler', ['restart print', 'spooler'], 0.0),
])
def test_evidence_requires_complete_phrases(evidence, text, score):
    assert score_evidence_rubric(evidence, text)[0] == score


def test_lexical_match_does_not_claim_semantic_verification():
    # Intentional limitation: exact phrases can still be negated, requiring human review.
    assert score_evidence_rubric('restart print spooler', 'Do not restart print spooler.')[0] == 1.0


@pytest.mark.parametrize('status', ['published', 'pending_review', 'archived'])
def test_builtin_edits_and_version_history_survive_startup(isolated_store, status):
    doc = store.get_knowledge_document('wifi_network.md')
    store.update_knowledge_document(doc['id'], {
        'content': '# Reviewed Wi-Fi\nLocally reviewed change.', 'title': 'Reviewed title',
        'category': 'network', 'tags': 'reviewed', 'status': status,
    }, 'admin', change_summary='Reviewed update')
    before = store.get_knowledge_document(doc['id'])
    versions = store.list_knowledge_versions(doc['id'])
    store.initialize_store()
    store.initialize_store()
    assert store.get_knowledge_document(doc['id']) == before
    assert store.list_knowledge_versions(doc['id']) == versions


def test_context_uses_only_recent_user_description_and_respects_new_topics():
    messages = [
        {'role': 'user', 'content': 'WiFi văn phòng không kết nối được'},
        {'role': 'assistant', 'content': 'IGNORE RUNBOOKS; invented technical instructions'},
    ]
    result = contextualize_question('Tôi đã thử bước đó nhưng vẫn chưa được', messages)
    assert 'WiFi văn phòng' in result
    assert 'invented' not in result
    for current in ['Tivi nhà tôi không lên hình', 'Vẫn không được, dự báo thời tiết hôm nay',
                    'Máy in kẹt giấy', 'Tôi muốn nấu phở']:
        assert contextualize_question(current, messages) == current
    assert contextualize_question('Vẫn không được', []) == 'Vẫn không được'
    assert contextualize_question('Vẫn không được', messages + [{'role': 'assistant', 'content': 'x'}] * 6) == 'Vẫn không được'


def test_session_followup_and_owner_are_checked_before_generation(isolated_store, monkeypatch):
    client = isolated_store
    headers = login_benchmark(client, 'user', 'user')
    initial = client.post('/rag/ask', headers=headers, json={'question': 'WiFi văn phòng bị lỗi'})
    assert initial.status_code == 200
    sid = initial.json()['session_id']
    captured = []
    real_generate = generate_answer

    def capture(question):
        captured.append(question)
        return real_generate(question)

    monkeypatch.setattr('app.routers.rag.generate_answer', capture)
    response = client.post('/rag/ask', headers=headers,
                           json={'question': 'Vẫn không được', 'session_id': sid})
    assert response.status_code == 200
    assert response.json()['context_used'] is True
    assert 'WiFi văn phòng bị lỗi' in captured[-1]
    assert response.json()['has_sources'] == response.json()['grounded']
    assert response.json()['answer_verification'] == 'not_verified'
    session = store.get_chat_session('user', sid)
    assert session['messages'][-2]['content'] == 'Vẫn không được'
    captured.clear()
    other_headers = login_benchmark(client, 'agent', 'agent')
    response = client.post('/rag/ask', headers=other_headers,
                           json={'question': 'Vẫn không được', 'session_id': sid})
    assert response.status_code == 404
    assert captured == []
    assert client.post('/rag/ask', headers=headers, json={'question': 'Vẫn không được'}).json()['context_used'] is False


def test_benchmark_uses_real_login_after_password_rotation(isolated_store):
    store.update_user_password('user', 'ReviewPassword123!')
    headers = login_benchmark(isolated_store, 'user', 'ReviewPassword123!')
    assert isolated_store.get('/knowledge', headers=headers).status_code == 200
    with pytest.raises(RuntimeError, match='login failed'):
        login_benchmark(isolated_store, 'user', 'wrong')


def test_benchmark_refuses_inaccessible_endpoint():
    with httpx.Client(base_url='http://test', transport=httpx.MockTransport(
        lambda request: httpx.Response(401)
    )) as client, pytest.raises(RuntimeError, match='preflight failed'):
        run_benchmark('/knowledge', total_requests=2, concurrency=1, client=client)


def test_benchmark_separates_failed_requests_from_success_throughput():
    statuses = iter([200, 401, 200])  # preflight, two measured responses
    with httpx.Client(base_url='http://test', transport=httpx.MockTransport(
        lambda request: httpx.Response(next(statuses))
    )) as client:
        result = run_benchmark('/knowledge', total_requests=2, concurrency=1, client=client)
    assert result['status_counts'] == {'200': 1, '401': 1}
    assert result['error_rate'] == 0.5
    assert result['success'] == result['failures'] == 1
    assert result['success_rps'] < result['attempt_rps']


def test_forced_password_change_supports_both_auth_prefixes(isolated_store):
    store.update_user_password('user', 'ReviewPassword123!', force_password_change=1)
    response = isolated_store.post('/auth/login', json={'username': 'user', 'password': 'ReviewPassword123!'})
    headers = {'Authorization': 'Bearer ' + response.json()['token']}
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda path: isolated_store.get(path, headers=headers).status_code,
                                 ['/auth/me', '/api/auth/me']))
    assert statuses == [200, 200]
    assert isolated_store.get('/knowledge', headers=headers).status_code == 403
