"""Real HTTP against one Uvicorn process: blocked work must leave health responsive."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import httpx
import pytest


SERVER = r'''
import importlib, json, socket, sys, time
from pathlib import Path
import uvicorn
from app.main import app
import app.main as main

folder = Path(sys.argv[1])
main.KNOWLEDGE_DIR = folder / 'knowledge'
main.KNOWLEDGE_DIR.mkdir()
module, attribute = sys.argv[2].rsplit(':', 1)
target = importlib.import_module(module)
original = getattr(target, attribute)
def slow(*args, **kwargs):
    if (folder / 'armed').exists():
        (folder / 'started').touch()
        deadline = time.monotonic() + 8
        while not (folder / 'release').exists():
            if time.monotonic() > deadline:
                raise RuntimeError('test release deadline exceeded')
            time.sleep(.01)
    return original(*args, **kwargs)
setattr(target, attribute, slow)
sock = socket.socket()
sock.bind(('127.0.0.1', 0))
(folder / 'port').write_text(str(sock.getsockname()[1]))
server = uvicorn.Server(uvicorn.Config(app, log_level='warning', access_log=False))
server.run(sockets=[sock])
'''


@pytest.mark.parametrize('operation,target', [
    ('health_database', 'app.store:check_database'),
    ('rag', 'app.routers.rag:generate_answer'),
    ('database', 'app.store:list_tickets'),
    ('password', 'app.store:verify_password'),
    ('notification', 'app.routers.admin:send_test_notification_result'),
    ('knowledge_import', 'app.routers.knowledge:save_knowledge_document'),
    ('attachment', 'app.store:add_attachment'),
    ('knowledge_auth', 'app.store:get_user_credentials'),
])
def test_health_responds_while_sync_work_is_blocked(tmp_path, operation, target):
    environment = {
        **os.environ, 'DEMO_MODE': 'true', 'ALLOW_DEMO_CREDENTIALS': 'true',
        'SECRET_KEY': 'AUD10-synthetic-test-secret-at-least-32-characters',
        'DATABASE_URL': '', 'HELPDESK_DB_PATH': str(tmp_path / 'db.sqlite3'),
        'HELPDESK_STORAGE_PATH': str(tmp_path / 'storage'),
        'ENABLE_LLM_GENERATION': 'false', 'SMTP_ENABLED': 'false', 'EMAIL_PROVIDER': 'mock',
        'TELEGRAM_BOT_TOKEN': '', 'TELEGRAM_CHAT_ID': '', 'DISCORD_WEBHOOK_URL': '',
        'INITIAL_ADMIN_USERNAME': '', 'INITIAL_ADMIN_PASSWORD': '',
    }
    with (tmp_path / 'server.log').open('w', encoding='utf8') as log:
        process = subprocess.Popen(  # noqa: S603 -- trusted interpreter and fixed isolated server
            [sys.executable, '-c', SERVER, str(tmp_path), target], env=environment,
            cwd=Path(__file__).resolve().parents[1], stdout=log, stderr=log,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        try:
            deadline = time.monotonic() + 15
            with httpx.Client(trust_env=False, timeout=12) as client:
                while True:
                    assert process.poll() is None, 'Uvicorn exited; inspect server.log'
                    try:
                        port = (tmp_path / 'port').read_text()
                        base = f'http://127.0.0.1:{port}'
                        if client.get(base + '/health', timeout=.5).status_code == 200:
                            break
                    except (OSError, httpx.HTTPError):
                        pass
                    assert time.monotonic() < deadline, 'Uvicorn startup timeout'
                    time.sleep(.05)
                login = client.post(base + '/auth/login', json={'username': 'admin', 'password': 'admin'})
                assert login.status_code == 200
                headers = {'Authorization': 'Bearer ' + login.json()['token']}
                ticket = client.post(base + '/tickets', headers=headers, json={
                    'title': 'AUD10 synthetic VPN issue', 'description': 'Synthetic network connection failure',
                    'category': 'network', 'priority': 'medium',
                })
                assert ticket.status_code == 201
                requests = {
                    'health_database': ('GET', '/health', {}),
                    'rag': ('POST', '/rag/ask', {'json': {'question': 'VPN FortiClient'}}),
                    'database': ('GET', '/tickets', {}),
                    'password': ('POST', '/auth/login', {'json': {'username': 'admin', 'password': 'admin'}}),
                    'notification': ('POST', '/admin/notifications/test', {'json': {'channel': 'email'}}),
                    'knowledge_import': ('POST', '/knowledge', {
                        'data': {'title': 'AUD10 synthetic runbook'},
                        'files': {'document': ('aud10-test.md', b'# AUD10\nSynthetic test', 'text/markdown')},
                    }),
                    'attachment': ('POST', f"/tickets/{ticket.json()['ticket']['id']}/attachments", {
                        'files': {'file': ('aud10.log', b'AUD10 synthetic log', 'text/plain')},
                    }),
                    'knowledge_auth': ('POST', '/knowledge', {'json': {
                        'title': 'AUD10 synthetic knowledge', 'content': '# Synthetic\nVPN help',
                        'category': 'network', 'status': 'draft',
                    }}),
                }
                method, path, kwargs = requests[operation]
                (tmp_path / 'armed').touch()
                with ThreadPoolExecutor(max_workers=9) as pool:
                    pending = pool.submit(client.request, method, base + path, headers=headers, **kwargs)
                    try:
                        deadline = time.monotonic() + 5
                        while not (tmp_path / 'started').exists():
                            assert not pending.done(), 'Request missed blocking probe'
                            assert time.monotonic() < deadline, 'Blocking probe not reached'
                            time.sleep(.01)

                        def health_probe():
                            start = time.monotonic()
                            probe_path = '/config' if operation == 'health_database' else '/health'
                            response = client.get(base + probe_path, timeout=1.5)
                            assert response.status_code == 200
                            return time.monotonic() - start

                        durations = sorted(pool.map(lambda _: health_probe(), range(8)))
                        assert not pending.done(), 'Slow work must still be blocked when health responds'
                        print(json.dumps({'operation': operation, 'health_samples': 8,
                                          'health_p95_seconds': durations[-1], 'workers': 1}))
                    finally:
                        (tmp_path / 'release').touch()
                    response = pending.result(timeout=10)
                    assert response.status_code in {200, 201}, response.text
        finally:
            (tmp_path / 'release').touch()
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
