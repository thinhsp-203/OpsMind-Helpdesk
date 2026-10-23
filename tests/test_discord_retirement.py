from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app import notifications, notification_outbox as outbox, store
from app.main import app


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(store, '_database_path', tmp_path / 'retirement.sqlite3')
    monkeypatch.setattr(store, '_database_url', '')
    monkeypatch.setenv('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/synthetic/retired')
    monkeypatch.delenv('TELEGRAM_BOT_TOKEN', raising=False)
    monkeypatch.delenv('TELEGRAM_CHAT_ID', raising=False)
    store.initialize_store()
    store.reset_store()


def test_stale_discord_configuration_cannot_send(monkeypatch):
    network = Mock(side_effect=AssertionError('Unexpected provider call'))
    monkeypatch.setattr(notifications, 'urlopen', network)
    assert 'discord' not in notifications.get_notification_channels_status()
    assert notifications.dispatch_ticket_notification({'id': 1}) == {}
    assert notifications.send_test_notification('discord') is False
    network.assert_not_called()


def test_discord_test_endpoint_rejected():
    client = TestClient(app)
    token = client.post('/auth/login', json={'username': 'admin', 'password': 'admin'}).json()['token']
    response = client.post('/admin/notifications/test', headers={'Authorization': f'Bearer {token}'},
                           json={'channel': 'discord'})
    assert response.status_code == 422


def test_new_ticket_only_enqueues_telegram():
    store.create_ticket('Synthetic incident', 'Test only', 'network', 'medium', 'user')
    assert [row['channel'] for row in outbox.list_deliveries()] == ['telegram']


@pytest.mark.parametrize('legacy_status', ['pending', 'processing', 'failed', 'accepted'])
def test_legacy_discord_kept_without_delivery_or_retry(monkeypatch, legacy_status):
    store.create_ticket('Synthetic incident', 'Test only', 'network', 'medium', 'user')
    row = outbox.list_deliveries()[0]
    with store._connect() as connection:
        connection.execute("UPDATE notification_outbox SET channel='discord', status=?, lease_until=0, next_attempt_at=0 WHERE id=?",
                           (legacy_status, row['id']))
    network = Mock(side_effect=AssertionError('Unexpected provider call'))
    monkeypatch.setattr(notifications, 'urlopen', network)
    outbox.process_notification_outbox()
    with pytest.raises(ValueError):
        outbox.retry_delivery(row['id'], 'admin')
    assert outbox.list_deliveries()[0]['id'] == row['id']
    network.assert_not_called()


def test_retired_channel_has_no_target_fingerprint():
    assert outbox.target_fingerprint('discord') == ''
