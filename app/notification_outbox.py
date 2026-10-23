"""Transactional ticket events and bounded, leased, at-least-once delivery.

Provider acceptance is not human acknowledgement. A crash after a remote send
but before its DB acknowledgement can cause a duplicate when a lease expires.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid

MAX_ATTEMPTS = 3
LEASE_SECONDS = 120
logger = logging.getLogger(__name__)


def initialize(connection) -> None:
    connection.execute("""CREATE TABLE IF NOT EXISTS notification_outbox (
        id TEXT PRIMARY KEY,
        event_id TEXT NOT NULL,
        ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
        event_type TEXT NOT NULL CHECK (event_type IN ('created', 'escalated')),
        channel TEXT NOT NULL CHECK (channel IN ('telegram', 'discord')),
        payload TEXT NOT NULL,
        target_fingerprint TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN
            ('pending', 'processing', 'accepted', 'failed', 'not_configured', 'config_changed')),
        attempts INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL DEFAULT 3,
        next_attempt_at DOUBLE PRECISION NOT NULL,
        lease_until DOUBLE PRECISION NOT NULL DEFAULT 0,
        lease_token TEXT NOT NULL DEFAULT '',
        last_error TEXT NOT NULL DEFAULT '',
        created_at DOUBLE PRECISION NOT NULL,
        updated_at DOUBLE PRECISION NOT NULL,
        accepted_at DOUBLE PRECISION,
        UNIQUE (event_id, channel)
    )""")
    connection.execute('CREATE INDEX IF NOT EXISTS idx_notification_due ON notification_outbox(status, next_attempt_at)')
    connection.execute('CREATE INDEX IF NOT EXISTS idx_notification_history ON notification_outbox(created_at, id)')


def target_fingerprint(channel: str) -> str:
    def setting(key):
        return os.getenv(key, '').strip().strip("'\"")
    if channel == 'telegram':
        token, chat = setting('TELEGRAM_BOT_TOKEN'), setting('TELEGRAM_CHAT_ID')
        target = token + '\0' + chat if token and chat else ''
    else:
        return ''  # Retired/unknown channels must never resolve a target.
    return hashlib.sha256(target.encode()).hexdigest() if target else ''


def enqueue(connection, ticket: dict, event_type: str) -> None:
    """Caller owns the ticket transaction. No network or independent commit."""
    now = time.time()
    event_id = uuid.uuid4().hex
    payload = {key: ticket.get(key) for key in (
        'id', 'title', 'description', 'category', 'priority', 'requester',
        'created_at', 'sla_deadline', 'status',
    )}
    payload.update(notification_event=event_type, notification_event_id=event_id)
    for channel in ('telegram',):
        fingerprint = target_fingerprint(channel)
        connection.execute("""INSERT INTO notification_outbox
            (id, event_id, ticket_id, event_type, channel, payload, target_fingerprint,
             status, next_attempt_at, created_at, updated_at, last_error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (uuid.uuid4().hex, event_id, ticket['id'], event_type, channel,
             json.dumps(payload, ensure_ascii=False), fingerprint,
             'pending' if fingerprint else 'not_configured', now, now, now,
             '' if fingerprint else 'not_configured'))


def claim(now: float | None = None) -> dict | None:
    from app import store
    now = time.time() if now is None else now
    with store._connect() as connection:
        # Serialize SQLite writers; PG skips a row already claimed by another worker.
        if not store._database_url:
            connection.execute('BEGIN IMMEDIATE')
        connection.execute("""UPDATE notification_outbox SET status = 'failed',
            last_error = 'lease_expired_delivery_unknown', updated_at = ?, lease_token = '', lease_until = 0
            WHERE status = 'processing' AND lease_until <= ? AND attempts >= max_attempts""", (now, now))
        # Keep legacy Discord history, but never claim it for delivery.
        query = """SELECT * FROM notification_outbox WHERE channel = 'telegram' AND attempts < max_attempts AND
            ((status = 'pending' AND next_attempt_at <= ?) OR (status = 'processing' AND lease_until <= ?))
            ORDER BY next_attempt_at, id LIMIT 1"""
        if store._database_url:
            query += ' FOR UPDATE SKIP LOCKED'
        row = connection.execute(query, (now, now)).fetchone()
        if row is None:
            return None
        token = uuid.uuid4().hex
        connection.execute("""UPDATE notification_outbox SET status = 'processing',
            attempts = attempts + 1, lease_token = ?, lease_until = ?, updated_at = ? WHERE id = ?""",
            (token, now + LEASE_SECONDS, now, row['id']))
        claimed = dict(row)
        claimed.update(lease_token=token, attempts=row['attempts'] + 1)
        return claimed


def finish(item: dict, outcome: str, now: float | None = None) -> bool:
    from app import store
    now = time.time() if now is None else now
    accepted = outcome == 'accepted'
    if accepted:
        status = 'accepted'
    elif outcome in {'not_configured', 'config_changed'}:
        status = outcome
    else:
        status = 'failed' if item['attempts'] >= item['max_attempts'] else 'pending'
    attempt_in_cycle = MAX_ATTEMPTS - item['max_attempts'] + item['attempts']
    with store._connect() as connection:
        result = connection.execute("""UPDATE notification_outbox SET status = ?, last_error = ?,
            next_attempt_at = ?, lease_until = 0, lease_token = '', updated_at = ?, accepted_at = ?
            WHERE id = ? AND status = 'processing' AND lease_token = ? AND lease_until > ?""",
            (status, '' if accepted else outcome, now + min(300, 5 * 2 ** max(0, min(6, attempt_in_cycle - 1))),
             now, now if accepted else None, item['id'], item['lease_token'], now))
        return result.rowcount == 1


def process_notification_outbox(limit: int = 10) -> int:
    """Short bounded batches; never hold a DB connection while calling a provider."""
    from app.notifications import notify_telegram

    processed = 0
    for _ in range(limit):
        item = claim()
        if item is None:
            break
        fingerprint = target_fingerprint(item['channel'])
        if not fingerprint:
            outcome = 'not_configured'
        elif fingerprint != item['target_fingerprint']:
            outcome = 'config_changed'
        else:
            try:
                payload = json.loads(item['payload'])
                outcome = 'accepted' if notify_telegram(payload) else 'provider_rejected'
            except Exception:
                # Persist only an enum, never exception messages containing URLs/tokens.
                outcome = 'provider_exception'
        finish(item, outcome)
        processed += 1
    return processed


def wake_notification_worker() -> None:
    """A failed post-commit wake-up must not change the ticket's successful response."""
    try:
        process_notification_outbox()
    except Exception as exc:
        logger.warning('Notification wake-up failed: %s', type(exc).__name__)


PUBLIC_COLUMNS = ('id, event_id, ticket_id, event_type, channel, status, attempts, max_attempts, '
                  'next_attempt_at, last_error, created_at, updated_at, accepted_at')


def list_deliveries(status: str | None = None, limit: int = 50, before_id: str | None = None) -> list[dict]:
    from app import store
    if not 1 <= limit <= 100:
        raise ValueError('Invalid delivery limit')
    with store._connect() as connection:
        conditions, parameters = [], []
        if status:
            conditions.append('status = ?')
            parameters.append(status)
        if before_id:
            cursor = connection.execute('SELECT created_at, id FROM notification_outbox WHERE id = ?', (before_id,)).fetchone()
            if cursor is None:
                raise ValueError('Unknown delivery cursor')
            conditions.append('(created_at < ? OR (created_at = ? AND id < ?))')
            parameters.extend((cursor['created_at'], cursor['created_at'], cursor['id']))
        where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
        rows = connection.execute(
            f'SELECT {PUBLIC_COLUMNS} FROM notification_outbox{where} ORDER BY created_at DESC, id DESC LIMIT ?',  # noqa: S608 -- fixed columns/clause; values are bound
            (*parameters, limit)).fetchall()
        return [dict(row) for row in rows]


def retry_delivery(delivery_id: str, actor: str) -> None:
    from app import store
    with store._connect() as connection:
        if not store._database_url:
            connection.execute('BEGIN IMMEDIATE')
        query = 'SELECT * FROM notification_outbox WHERE id = ?'
        if store._database_url:
            query += ' FOR UPDATE'
        row = connection.execute(query, (delivery_id,)).fetchone()
        if row is None:
            raise LookupError('Delivery not found')
        if row['status'] not in {'failed', 'not_configured', 'config_changed'}:
            raise ValueError('Only terminal failed or unconfigured deliveries can be retried')
        fingerprint = target_fingerprint(row['channel'])
        if not fingerprint:
            raise ValueError('Channel is not configured')
        now = time.time()
        connection.execute("""UPDATE notification_outbox SET status = 'pending',
            target_fingerprint = ?, max_attempts = attempts + ?, next_attempt_at = ?,
            updated_at = ?, lease_until = 0, lease_token = '', last_error = '' WHERE id = ?""",
            (fingerprint, MAX_ATTEMPTS, now, now, delivery_id))
        store._record_audit(connection, row['ticket_id'], actor, 'notification_retry', None, None, delivery_id)
