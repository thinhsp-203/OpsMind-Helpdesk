"""Durable credential mail; bounded at-least-once delivery, never a read receipt.

Only job metadata and token hashes are stored. HMAC-SHA256 derives a stable,
scoped reset token from a random job ID and the server secret across retries.
Send/ack crashes may duplicate a message; the underlying reset token is one-use.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import time
import uuid

from app import config, email_sender

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3
LEASE_SECONDS = 120


def initialize(connection) -> None:
    connection.execute('''CREATE TABLE IF NOT EXISTS email_deliveries (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
        recipient TEXT NOT NULL,
        kind TEXT NOT NULL CHECK (kind IN ('reset', 'invitation')),
        base_url TEXT NOT NULL,
        session_epoch TEXT NOT NULL,
        fingerprint TEXT NOT NULL,
        token_hash TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN
            ('pending','processing','accepted','mocked','failed','cancelled','config_changed','expired')),
        attempts INTEGER NOT NULL DEFAULT 0,
        next_attempt_at DOUBLE PRECISION NOT NULL,
        lease_until DOUBLE PRECISION NOT NULL DEFAULT 0,
        lease_token TEXT NOT NULL DEFAULT '',
        last_error TEXT NOT NULL DEFAULT '',
        created_at DOUBLE PRECISION NOT NULL,
        updated_at DOUBLE PRECISION NOT NULL,
        expires_at DOUBLE PRECISION NOT NULL,
        accepted_at DOUBLE PRECISION
    )''')
    connection.execute('CREATE INDEX IF NOT EXISTS idx_email_due ON email_deliveries(status, next_attempt_at)')
    connection.execute('CREATE INDEX IF NOT EXISTS idx_email_history ON email_deliveries(created_at, id)')


def fingerprint() -> str:
    fields = ('EMAIL_PROVIDER', 'EMAIL_FROM', 'RESEND_API_KEY', 'BREVO_API_KEY', 'EMAIL_WEBHOOK_URL',
              'SMTP_ENABLED', 'SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD',
              'SMTP_USE_TLS', 'SMTP_SSL_VERIFY', 'PUBLIC_BASE_URL', 'DEMO_MODE', 'SECRET_KEY',
              'RESET_TOKEN_EXPIRE_MINUTES')
    return hashlib.sha256(json.dumps([getattr(config, name) for name in fields]).encode()).hexdigest()


def _raw_token(item: dict) -> str:
    message = f"OpsMind-email-link:v1:{item['id']}:{item['kind']}:{item['username']}:{item['session_epoch']}"
    return hmac.new(config.SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()


def enqueue(connection, username: str, kind: str, base_url: str) -> str | None:
    """Caller owns the user-write transaction. No independent commit or I/O."""
    from app import store
    email_sender.validate_email_configuration()
    if kind not in {'reset', 'invitation'}:
        raise ValueError('Invalid email kind')
    store._lock_credential_user(connection, username)
    user = connection.execute('SELECT email, session_epoch, is_active FROM users WHERE username=?', (username,)).fetchone()
    if not user or not user['is_active'] or not user['email']:
        return None
    now = time.time()
    item = {'id': uuid.uuid4().hex, 'kind': kind, 'username': username, 'session_epoch': user['session_epoch']}
    token_hash = hashlib.sha256(_raw_token(item).encode()).hexdigest()
    deadline = now + config.RESET_TOKEN_EXPIRE_MINUTES * 60
    # Issuing a new link supersedes earlier jobs/links for this account atomically.
    connection.execute("UPDATE email_deliveries SET status='cancelled', last_error='superseded', "
                       "lease_token='', lease_until=0, updated_at=? WHERE username=? AND status IN ('pending','processing')",
                       (now, username))
    store._revoke_password_reset_tokens(connection, username)
    connection.execute('''INSERT INTO password_reset_tokens (username, token_hash, expires_at, used, created_at)
        VALUES (?, ?, ?, 0, ?)''', (username, token_hash,
        datetime.fromtimestamp(deadline, timezone.utc).isoformat(), datetime.fromtimestamp(now, timezone.utc).isoformat()))
    connection.execute('''INSERT INTO email_deliveries
        (id,username,recipient,kind,base_url,session_epoch,fingerprint,token_hash,status,next_attempt_at,
         created_at,updated_at,expires_at) VALUES (?,?,?,?,?,?,?,?,'pending',?,?,?,?)''',
        (item['id'], username, user['email'], kind, (config.PUBLIC_BASE_URL or base_url).rstrip('/'),
         user['session_epoch'], fingerprint(), token_hash, now, now, now, deadline))
    return item['id']


def request_password_email(username: str, kind: str, base_url: str) -> str | None:
    from app import store
    with store._connect() as connection:
        store._begin_credential_write(connection)
        return enqueue(connection, username, kind, base_url)


def claim(now: float | None = None) -> dict | None:
    from app import store
    now = time.time() if now is None else now
    with store._connect() as connection:
        if not store._database_url:
            connection.execute('BEGIN IMMEDIATE')
        connection.execute("UPDATE email_deliveries SET status='expired', last_error='link_expired', "
                           "lease_token='', lease_until=0, updated_at=? WHERE expires_at<=? "
                           "AND status IN ('pending','processing')", (now, now))
        connection.execute("UPDATE email_deliveries SET status='failed', last_error='lease_expired_delivery_unknown', "
                           "lease_token='', lease_until=0, updated_at=? WHERE status='processing' "
                           "AND lease_until<=? AND attempts>=?", (now, now, MAX_ATTEMPTS))
        query = "SELECT * FROM email_deliveries WHERE attempts<? AND ((status='pending' AND next_attempt_at<=?) "
        query += "OR (status='processing' AND lease_until<=?)) ORDER BY next_attempt_at,id LIMIT 1"
        if store._database_url:
            query += ' FOR UPDATE SKIP LOCKED'
        row = connection.execute(query, (MAX_ATTEMPTS, now, now)).fetchone()
        if not row:
            return None
        token = uuid.uuid4().hex
        connection.execute("UPDATE email_deliveries SET status='processing', attempts=attempts+1, "
                           "lease_token=?, lease_until=?, updated_at=? WHERE id=?", (token, now+LEASE_SECONDS, now, row['id']))
        item = dict(row)
        item.update(lease_token=token, attempts=row['attempts']+1)
        return item


def finish(item: dict, outcome: str, now: float | None = None) -> bool:
    from app import store
    now = time.time() if now is None else now
    terminal = {'accepted', 'mocked', 'cancelled', 'config_changed', 'expired'}
    if outcome not in terminal | {'provider_rejected', 'provider_exception'}:
        raise ValueError('Invalid email outcome')
    status = outcome if outcome in terminal else ('failed' if item['attempts']>=MAX_ATTEMPTS else 'pending')
    with store._connect() as connection:
        result = connection.execute('''UPDATE email_deliveries SET status=?, last_error=?, next_attempt_at=?,
            lease_token='', lease_until=0, updated_at=?, accepted_at=?
            WHERE id=? AND status='processing' AND lease_token=? AND lease_until>?''',
            (status, '' if outcome in {'accepted','mocked'} else outcome,
             now+5*2**(item['attempts']-1), now, now if outcome=='accepted' else None,
             item['id'], item['lease_token'], now))
        return result.rowcount==1


def _still_valid(item: dict) -> bool:
    from app import store
    with store._connect() as connection:
        row = connection.execute('''SELECT t.expires_at FROM password_reset_tokens t JOIN users u ON u.username=t.username
            WHERE t.username=? AND t.token_hash=? AND t.used=0 AND u.is_active=1
            AND u.email=? AND u.session_epoch=?''',
            (item['username'],item['token_hash'],item['recipient'],item['session_epoch'])).fetchone()
        return bool(row and datetime.fromisoformat(row['expires_at']).timestamp()>time.time())


def process_email_outbox(limit: int = 10) -> int:
    """No DB connection held during provider I/O. Provider acceptance is not delivery."""
    processed = 0
    for _ in range(limit):
        item = claim()
        if not item:
            break
        if item['fingerprint']!=fingerprint():
            outcome = 'config_changed'
        elif not _still_valid(item):
            outcome = 'cancelled'
        else:
            try:
                email_sender.validate_email_configuration()
                token = _raw_token(item)
                if not hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(), item['token_hash']):
                    outcome = 'cancelled'
                else:
                    send = email_sender.send_account_created_email if item['kind']=='invitation' else email_sender.send_password_reset_email
                    ok = send(to_email=item['recipient'], username=item['username'], reset_token=token, base_url=item['base_url'])
                    outcome = ('mocked' if email_sender.get_email_status()['is_mock'] else 'accepted') if ok else 'provider_rejected'
            except email_sender.EmailConfigurationError:
                outcome = 'config_changed'
            except Exception:
                outcome = 'provider_exception'
        finish(item, outcome)
        processed += 1
    return processed


def wake_email_worker() -> None:
    try:
        process_email_outbox()
    except Exception as exc:
        # Once business data commits, wake-up failure must not change the response.
        logger.warning('Email worker wake-up failed: %s', type(exc).__name__)


def list_deliveries(limit: int = 50) -> list[dict]:
    from app import store
    if not 1<=limit<=100:
        raise ValueError('limit must be between 1 and 100')
    with store._connect() as connection:
        rows = connection.execute('''SELECT id,username,kind,status,attempts,next_attempt_at,last_error,
            created_at,updated_at,expires_at,accepted_at FROM email_deliveries ORDER BY created_at DESC,id DESC LIMIT ?''',
            (limit,)).fetchall()
    return [dict(row) for row in rows]
