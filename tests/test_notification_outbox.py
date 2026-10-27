from concurrent.futures import ThreadPoolExecutor
import os
import subprocess
import sys
from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

from app import store
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_outbox(tmp_path, monkeypatch):
    monkeypatch.setattr(store, '_database_path', tmp_path / 'db.sqlite3')
    monkeypatch.setattr(store, '_database_url', '')
    for key in ('TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'DISCORD_WEBHOOK_URL'):
        monkeypatch.delenv(key, raising=False)
    store.initialize_store()
    store.reset_store()


def headers(role='admin'):
    response = client.post('/auth/login', json={'username': role, 'password': role})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['token']}


def ticket():
    return store.create_ticket('AUD13 synthetic incident', 'Synthetic provider evidence only', 'security', 'urgent', 'user')


def test_escalation_has_durable_delivery_records():
    doc = ticket()
    staff = headers()
    assert client.patch(f"/tickets/{doc['id']}", headers=staff, json={'status': 'in_progress'}).status_code == 200
    assert client.patch(f"/tickets/{doc['id']}", headers=staff, json={'status': 'escalated'}).status_code == 200
    response = client.get('/admin/notifications/deliveries', headers=staff)
    assert response.status_code == 200
    rows = response.json()
    assert sorted((row['event_type'], row['channel']) for row in rows) == [
        ('created', 'telegram'), ('escalated', 'telegram')]
    assert {row['status'] for row in rows} == {'not_configured'}
    assert client.patch(f"/tickets/{doc['id']}", headers=staff, json={'status': 'escalated'}).status_code == 409
    assert len(client.get('/admin/notifications/deliveries', headers=staff).json()) == 2


def configure(monkeypatch):
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'AUD13-fake-token')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', 'AUD13-fake-chat')


def telegram_row():
    from app.notification_outbox import list_deliveries
    return next(row for row in list_deliveries() if row['channel'] == 'telegram')


def test_bounded_retry_backoff_and_no_resend_after_acceptance(monkeypatch):
    from app import notification_outbox as outbox
    configure(monkeypatch)
    clock = [1000.0]
    monkeypatch.setattr(outbox.time, 'time', lambda: clock[0])
    adapter = Mock(side_effect=[False, False, True])
    monkeypatch.setattr('app.notifications.notify_telegram', adapter)
    ticket()
    assert outbox.process_notification_outbox() == 1
    assert telegram_row()['status'] == 'pending' and telegram_row()['next_attempt_at'] == 1005
    assert outbox.process_notification_outbox() == 0
    clock[0] = 1005
    assert outbox.process_notification_outbox() == 1
    clock[0] = 1015
    assert outbox.process_notification_outbox() == 1
    assert telegram_row()['status'] == 'accepted' and telegram_row()['attempts'] == 3
    assert outbox.process_notification_outbox() == 0
    assert len({call.args[0]['notification_event_id'] for call in adapter.call_args_list}) == 1


def test_provider_exception_exhausts_budget_without_persisting_secret(monkeypatch):
    from app import notification_outbox as outbox
    configure(monkeypatch)
    adapter = Mock(side_effect=TimeoutError('https://secret-token.example/private'))
    monkeypatch.setattr('app.notifications.notify_telegram', adapter)
    ticket()
    for _ in range(3):
        with store._connect() as connection:
            connection.execute("UPDATE notification_outbox SET next_attempt_at = 0 WHERE status = 'pending'")
        outbox.process_notification_outbox()
    row = telegram_row()
    assert row['status'] == 'failed' and row['attempts'] == 3
    assert row['last_error'] == 'provider_exception'
    assert 'secret-token' not in str(outbox.list_deliveries())
    assert outbox.process_notification_outbox() == 0
    assert adapter.call_count == 3


def test_claims_are_exclusive_and_stale_acknowledgement_is_fenced(monkeypatch):
    from app import notification_outbox as outbox
    configure(monkeypatch)
    ticket()
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: outbox.claim(100000000000.0), range(2)))
    first = next(item for item in claims if item)
    assert sum(item is not None for item in claims) == 1
    replacement = outbox.claim(100000000000.0 + outbox.LEASE_SECONDS)
    assert replacement['id'] == first['id'] and replacement['lease_token'] != first['lease_token']
    assert not outbox.finish(first, 'accepted', 100000000000.0 + outbox.LEASE_SECONDS + 1)
    assert outbox.finish(replacement, 'accepted', 100000000000.0 + outbox.LEASE_SECONDS + 1)


def test_exhausted_crash_lease_is_terminal_unknown(monkeypatch):
    from app import notification_outbox as outbox
    configure(monkeypatch)
    ticket()
    with store._connect() as connection:
        connection.execute("UPDATE notification_outbox SET status = 'processing', attempts = 3, lease_until = 0 WHERE channel = 'telegram'")
    assert outbox.claim() is None
    assert telegram_row()['status'] == 'failed'
    assert telegram_row()['last_error'] == 'lease_expired_delivery_unknown'


def test_target_rotation_stops_automatic_retargeting(monkeypatch):
    from app import notification_outbox as outbox
    configure(monkeypatch)
    ticket()
    monkeypatch.setenv('TELEGRAM_CHAT_ID', 'new-target')
    adapter = Mock()
    monkeypatch.setattr('app.notifications.notify_telegram', adapter)
    outbox.process_notification_outbox()
    assert telegram_row()['status'] == 'config_changed'
    adapter.assert_not_called()


def test_admin_reconciliation_requeues_only_terminal_rows(monkeypatch):
    ticket()
    row = telegram_row()
    admin = headers()
    url = f"/admin/notifications/deliveries/{row['id']}/retry"
    assert client.get('/admin/notifications/deliveries', headers=headers('user')).status_code == 403
    assert client.post(url, headers=headers('agent')).status_code == 403
    assert client.post(url, headers=admin).status_code == 409
    configure(monkeypatch)
    adapter = Mock(return_value=True)
    monkeypatch.setattr('app.notifications.notify_telegram', adapter)
    assert client.post(url, headers=admin).status_code == 200
    assert telegram_row()['status'] == 'accepted'
    assert client.post(url, headers=admin).status_code == 409
    assert adapter.call_count == 1
    assert client.get('/admin/notifications/deliveries?limit=101', headers=admin).status_code == 422
    assert client.get('/admin/notifications/deliveries?status=unknown', headers=admin).status_code == 422
    assert client.post('/admin/notifications/deliveries/missing/retry', headers=admin).status_code == 404
    with store._connect() as connection:
        assert connection.execute("SELECT COUNT(*) AS n FROM audit_logs WHERE event = 'notification_retry'").fetchone()['n'] == 1


def test_outbox_insert_failure_rolls_back_ticket_and_escalation(monkeypatch):
    from app import notification_outbox as outbox
    doc = ticket()
    store.update_ticket_status(doc['id'], 'in_progress', 'agent')

    def fail(*args, **kwargs):
        raise RuntimeError('AUD13 synthetic enqueue failure')

    monkeypatch.setattr(outbox, 'enqueue', fail)
    with pytest.raises(RuntimeError):
        store.create_ticket('Rolled back', 'Synthetic', 'general', 'low', 'user')
    assert len(store.list_tickets('admin', 'admin')) == 1
    with pytest.raises(RuntimeError):
        store.update_ticket_status(doc['id'], 'escalated', 'agent')
    assert store.get_ticket(doc['id'])['status'] == 'in_progress'
    assert len(outbox.list_deliveries()) == 1


def test_concurrent_escalation_commits_one_event():
    from app import notification_outbox as outbox
    doc = ticket()
    store.update_ticket_status(doc['id'], 'in_progress', 'agent')

    def escalate():
        try:
            store.update_ticket_status(doc['id'], 'escalated', 'agent')
            return 'ok'
        except ValueError:
            return 'conflict'

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: escalate(), range(2))) == ['conflict', 'ok']
    assert len([row for row in outbox.list_deliveries() if row['event_type'] == 'escalated']) == 1


def test_pending_and_claimed_work_survive_new_process(monkeypatch):
    from app import notification_outbox as outbox
    configure(monkeypatch)
    ticket()
    first = outbox.claim()
    with store._connect() as connection:
        connection.execute('UPDATE notification_outbox SET lease_until = 0 WHERE id = ?', (first['id'],))
    environment = {**os.environ, 'DATABASE_URL': '', 'HELPDESK_DB_PATH': str(store._database_path),
                   'DEMO_MODE': 'true', 'SECRET_KEY': 'AUD13-synthetic-secret-more-than-32-characters'}
    code = """
from app import notifications, notification_outbox as outbox
notifications.notify_telegram = lambda payload: True
assert outbox.process_notification_outbox() == 1
row = next(row for row in outbox.list_deliveries() if row['channel'] == 'telegram')
assert row['status'] == 'accepted' and row['attempts'] == 2
"""
    subprocess.run(  # noqa: S603 -- trusted interpreter, fixed synthetic isolated DB script
        [sys.executable, '-c', code], env=environment, check=True, timeout=15,
        capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    assert telegram_row()['status'] == 'accepted'


def test_pagination_and_status_endpoint_expose_persisted_history():
    from app import notification_outbox as outbox
    for _ in range(6):
        ticket()
    first = outbox.list_deliveries(limit=3)
    second = outbox.list_deliveries(limit=3, before_id=first[-1]['id'])
    assert len(first) == len(second) == 3
    assert not {row['id'] for row in first}.intersection(row['id'] for row in second)
    response = client.get('/admin/notifications/status', headers=headers())
    assert response.status_code == 200
    assert len(response.json()['history']) >= 6
    assert all('target_fingerprint' not in row and 'payload' not in row for row in first)


def test_failed_background_wakeup_does_not_change_committed_ticket_response(monkeypatch):
    from app import notification_outbox as outbox
    monkeypatch.setattr(outbox, 'process_notification_outbox', Mock(side_effect=RuntimeError('synthetic worker failure')))
    response = client.post('/tickets', headers=headers('user'), json={
        'title': 'AUD13 worker failure', 'description': 'Synthetic worker wakeup failure',
        'category': 'general', 'priority': 'low'})
    assert response.status_code == 201
    assert store.get_ticket(response.json()['ticket']['id']) is not None
    assert len(outbox.list_deliveries()) == 1


def test_lifespan_worker_drains_existing_pending_work(monkeypatch):
    import time
    configure(monkeypatch)
    adapter = Mock(return_value=True)
    monkeypatch.setattr('app.notifications.notify_telegram', adapter)
    ticket()
    with TestClient(app):
        deadline = time.monotonic() + 5
        while telegram_row()['status'] != 'accepted':
            assert time.monotonic() < deadline
            time.sleep(.02)
    assert adapter.call_count == 1


def test_retry_budget_is_extended_explicitly_and_audited(monkeypatch):
    from app import notification_outbox as outbox
    configure(monkeypatch)
    ticket()
    row = telegram_row()
    with store._connect() as connection:
        connection.execute("UPDATE notification_outbox SET status = 'failed', attempts = 3 WHERE id = ?", (row['id'],))
    outbox.retry_delivery(row['id'], 'admin')
    assert telegram_row()['attempts'] == 3 and telegram_row()['max_attempts'] == 6
    with pytest.raises(ValueError):
        outbox.retry_delivery(row['id'], 'admin')


def test_missing_channel_stops_pending_work_without_send(monkeypatch):
    from app import notification_outbox as outbox
    configure(monkeypatch)
    ticket()
    monkeypatch.delenv('TELEGRAM_BOT_TOKEN')
    adapter = Mock()
    monkeypatch.setattr('app.notifications.notify_telegram', adapter)
    outbox.process_notification_outbox()
    assert telegram_row()['status'] == 'not_configured'
    adapter.assert_not_called()
