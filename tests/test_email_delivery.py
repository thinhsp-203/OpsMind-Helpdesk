"""AUD16 acceptance: no password in email, fail closed, durable safe delivery."""
from concurrent.futures import ThreadPoolExecutor
import secrets
import time

import pytest
from fastapi.testclient import TestClient

from app import config, email_sender, store
from app.main import app, _forgot_password_attempts, _forgot_password_target_cooldown


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(store, '_database_path', tmp_path/'email.sqlite3')
    monkeypatch.setattr(store, '_database_url', '')
    monkeypatch.setattr(config, 'DEMO_MODE', True)
    monkeypatch.setattr(config, 'EMAIL_PROVIDER', 'console')
    monkeypatch.setattr(config, 'PUBLIC_BASE_URL', '')
    store.initialize_store()
    email_sender.clear_outbox()
    _forgot_password_attempts.clear()
    _forgot_password_target_cooldown.clear()
    yield
    email_sender.clear_outbox()
    _forgot_password_attempts.clear()
    _forgot_password_target_cooldown.clear()


def admin(client):
    token=client.post('/auth/login', json={'username':'admin','password':'admin'}).json()['token']
    return {'Authorization':'Bearer '+token}


def test_welcome_uses_one_use_link_never_account_password():
    client=TestClient(app)
    sensitive=secrets.token_urlsafe(24)
    assert client.post('/admin/users',headers=admin(client),json={
        'username':'invitee','password':sensitive,'role':'user','email':'invitee@example.invalid'}).status_code==201
    message=email_sender.get_outbox()[-1]
    assert sensitive not in message['body']
    assert 'temp_password' not in message
    token=message['token']
    assert token in message['link']
    response=client.post('/auth/reset-password',json={'token':token,'new_password':secrets.token_urlsafe(24)})
    assert response.status_code==200
    assert client.post('/auth/reset-password',json={'token':token,'new_password':secrets.token_urlsafe(24)}).status_code==400


def test_disabled_smtp_cannot_report_send_success(monkeypatch):
    monkeypatch.setattr(config,'EMAIL_PROVIDER','smtp')
    monkeypatch.setattr(config,'SMTP_ENABLED',False)
    monkeypatch.setattr(config,'DEMO_MODE',False)
    assert email_sender.dispatch_email('fake@example.invalid','subject','body') is False
    assert email_sender.get_outbox()==[]


@pytest.mark.parametrize('provider',['console','mock','smtp','resend','brevo','webhook'])
def test_non_demo_startup_refuses_unconfigured_provider(monkeypatch,provider):
    monkeypatch.setattr(config,'DEMO_MODE',False)
    monkeypatch.setattr(config,'EMAIL_PROVIDER',provider)
    monkeypatch.setattr(config,'PUBLIC_BASE_URL','https://helpdesk.example.invalid')
    for name in ['RESEND_API_KEY','BREVO_API_KEY','EMAIL_WEBHOOK_URL']:
        monkeypatch.setattr(config,name,'')
    monkeypatch.setattr(config,'SMTP_ENABLED',False)
    with pytest.raises(ValueError):
        with TestClient(app):
            pass


def test_failed_reset_delivery_survives_lifespan_restart(monkeypatch):
    store.update_user('user',{'email':'user@example.invalid'})
    calls=[]
    def send(**kwargs):
        calls.append(kwargs)
        return len(calls)>1
    monkeypatch.setattr(email_sender,'send_password_reset_email',send)
    with TestClient(app) as client:
        assert client.post('/auth/forgot-password',json={'identifier':'user'}).status_code==200
    assert len(calls)==1
    with TestClient(app):
        deadline=time.monotonic()+9
        while len(calls)<2 and time.monotonic()<deadline:
            time.sleep(.05)
    assert len(calls)==2
    assert calls[0]['reset_token']==calls[1]['reset_token']


def make_job():
    from app import email_outbox
    store.update_user('user',{'email':'user@example.invalid'})
    identifier=email_outbox.request_password_email('user','reset','http://testserver')
    assert identifier
    return identifier


def test_failed_delivery_is_persisted_and_bounded(monkeypatch):
    from app import email_outbox
    identifier=make_job()
    monkeypatch.setattr(email_sender,'send_password_reset_email',lambda **kwargs:False)
    for attempt in range(3):
        assert email_outbox.process_email_outbox()==1
        with store._connect() as connection:
            row=dict(connection.execute('SELECT * FROM email_deliveries WHERE id=?',(identifier,)).fetchone())
            assert row['attempts']==attempt+1
            assert row['last_error']=='provider_rejected'
            connection.execute('UPDATE email_deliveries SET next_attempt_at=0 WHERE id=?',(identifier,))
    assert row['status']=='failed'
    assert email_outbox.process_email_outbox()==0


def test_job_storage_and_admin_api_contain_no_raw_token():
    from app import email_outbox
    identifier=make_job()
    email_outbox.process_email_outbox()
    token=email_sender.get_outbox()[-1]['token']
    with store._connect() as connection:
        row=dict(connection.execute('SELECT * FROM email_deliveries WHERE id=?',(identifier,)).fetchone())
        assert all(token not in str(value) for value in row.values())
    client=TestClient(app)
    result=client.get('/admin/email-deliveries',headers=admin(client))
    assert result.status_code==200
    assert token not in result.text
    assert 'fingerprint' not in result.text and 'session_epoch' not in result.text
    assert result.json()[0]['status']=='mocked'
    user_token=client.post('/auth/login',json={'username':'user','password':'user'}).json()['token']
    assert client.get('/admin/email-deliveries',headers={'Authorization':'Bearer '+user_token}).status_code==403


def test_exclusive_claim_and_stale_lease_cannot_acknowledge():
    from app import email_outbox
    identifier=make_job()
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims=list(pool.map(lambda _:email_outbox.claim(),range(2)))
    first=next(x for x in claims if x is not None)
    assert sum(x is not None for x in claims)==1
    with store._connect() as connection:
        connection.execute('UPDATE email_deliveries SET lease_until=0 WHERE id=?',(identifier,))
    second=email_outbox.claim()
    assert second and second['lease_token']!=first['lease_token']
    assert email_outbox.finish(first,'accepted') is False
    assert email_outbox.finish(second,'accepted') is True


@pytest.mark.parametrize('change',[{'email':'other@example.invalid'},{'is_active':False},{'role':'agent'}])
def test_changed_account_cancels_unsent_job(monkeypatch,change):
    from app import email_outbox
    identifier=make_job()
    store.update_user('user',change)
    monkeypatch.setattr(email_sender,'send_password_reset_email',lambda **kwargs:pytest.fail('Must not send stale job'))
    email_outbox.process_email_outbox()
    assert email_outbox.list_deliveries()[0]['id']==identifier
    assert email_outbox.list_deliveries()[0]['status']=='cancelled'


def test_changed_provider_cancels_without_retargeting(monkeypatch):
    from app import email_outbox
    make_job()
    monkeypatch.setattr(config,'EMAIL_PROVIDER','mock')
    email_outbox.process_email_outbox()
    assert email_outbox.list_deliveries()[0]['status']=='config_changed'
    assert email_sender.get_outbox()==[]


def test_expired_job_does_not_send(monkeypatch):
    from app import email_outbox
    identifier=make_job()
    with store._connect() as connection:
        connection.execute('UPDATE email_deliveries SET expires_at=0 WHERE id=?',(identifier,))
    monkeypatch.setattr(email_sender,'send_password_reset_email',lambda **kwargs:pytest.fail('Must not send expired job'))
    email_outbox.process_email_outbox()
    assert email_outbox.list_deliveries()[0]['status']=='expired'


def test_account_invitation_is_atomic_on_enqueue_failure():
    with store._connect() as connection:
        connection.execute("CREATE TRIGGER email_fail BEFORE INSERT ON email_deliveries "
                           "BEGIN SELECT RAISE(ABORT, 'synthetic enqueue failure'); END;")
    client=TestClient(app)
    response=client.post('/admin/users',headers=admin(client),json={
        'username':'rollbackuser','password':secrets.token_urlsafe(24),'role':'user','email':'user@example.invalid'})
    assert response.status_code==503
    assert store.get_user_credentials('rollbackuser') is None
    assert email_sender.get_outbox()==[]
    with store._connect() as connection:
        assert connection.execute('SELECT COUNT(*) AS n FROM password_reset_tokens').fetchone()['n']==0


def test_enqueue_failure_rolls_back_link_revocation():
    from app import email_outbox
    store.update_user('user',{'email':'user@example.invalid'})
    previous=store.create_password_reset_token('user')
    with store._connect() as connection:
        connection.execute("CREATE TRIGGER email_fail BEFORE INSERT ON email_deliveries "
                           "BEGIN SELECT RAISE(ABORT, 'synthetic enqueue failure'); END;")
    with pytest.raises(store.DatabaseIntegrityError):
        email_outbox.request_password_email('user','reset','http://testserver')
    assert store.verify_and_consume_reset_token(previous)=='user'
    assert email_outbox.list_deliveries()==[]


def test_new_link_supersedes_prior_job_and_token():
    from app import email_outbox
    make_job()
    email_outbox.process_email_outbox()
    old=email_sender.get_outbox()[-1]['token']
    email_outbox.request_password_email('user','reset','http://testserver')
    email_outbox.process_email_outbox()
    latest=email_sender.get_outbox()[-1]['token']
    assert old!=latest
    assert store.verify_and_consume_reset_token(old) is None
    assert store.verify_and_consume_reset_token(latest)=='user'


def test_provider_acceptance_is_terminal_and_not_a_read_receipt(monkeypatch):
    from app import email_outbox
    monkeypatch.setattr(config,'EMAIL_PROVIDER','smtp')
    monkeypatch.setattr(config,'SMTP_ENABLED',True)
    calls=[]
    monkeypatch.setattr(email_sender,'_send_via_smtp',lambda *args:calls.append(True) or True)
    make_job()
    email_outbox.process_email_outbox()
    store.initialize_store()
    assert email_outbox.process_email_outbox()==0
    row=email_outbox.list_deliveries()[0]
    assert row['status']=='accepted' and row['accepted_at']
    assert row['attempts']==1 and len(calls)==1


def test_claim_budget_survives_crash_and_exhaustion():
    from app import email_outbox
    identifier=make_job()
    for attempt in range(3):
        item=email_outbox.claim()
        assert item['attempts']==attempt+1
        with store._connect() as connection:
            connection.execute('UPDATE email_deliveries SET lease_until=0 WHERE id=?',(identifier,))
    assert email_outbox.claim() is None
    row=email_outbox.list_deliveries()[0]
    assert row['status']=='failed' and row['last_error']=='lease_expired_delivery_unknown'


def test_worker_exception_never_persists_provider_secrets(monkeypatch):
    from app import email_outbox
    sensitive=secrets.token_urlsafe(24)
    def explode(**kwargs):
        raise RuntimeError(sensitive)
    monkeypatch.setattr(email_sender,'send_password_reset_email',explode)
    make_job()
    email_outbox.process_email_outbox()
    row=email_outbox.list_deliveries()[0]
    assert row['last_error']=='provider_exception'
    assert sensitive not in str(row)


def test_new_process_can_deliver_pending_job_without_raw_token_storage():
    from app import email_outbox
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    make_job()
    script="""
import hashlib,json
from app import email_outbox,email_sender,store
assert email_outbox.process_email_outbox()==1
row=email_outbox.list_deliveries()[0]
with store._connect() as connection:
    secret_hash=connection.execute('SELECT token_hash FROM email_deliveries WHERE id=?',(row['id'],)).fetchone()['token_hash']
token=email_sender.get_outbox()[0]['token']
print(json.dumps({'status':row['status'],'hash_matches':hashlib.sha256(token.encode()).hexdigest()==secret_hash}))
"""
    env={**os.environ,'DEMO_MODE':'true','DATABASE_URL':'','HELPDESK_DB_PATH':str(store._database_path),
         'EMAIL_PROVIDER':'console','PUBLIC_BASE_URL':'','SECRET_KEY':config.SECRET_KEY,'PYTHONIOENCODING':'utf-8'}
    result=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parents[1],env=env,  # noqa: S603 -- fixed script, sandbox DB
        capture_output=True,text=True,encoding='utf8',timeout=20,check=True)
    assert json.loads(result.stdout)=={'status':'mocked','hash_matches':True}
    assert email_outbox.process_email_outbox()==0


def test_non_demo_valid_provider_requires_trusted_base_and_tls(monkeypatch):
    monkeypatch.setattr(config,'DEMO_MODE',False)
    monkeypatch.setattr(config,'EMAIL_PROVIDER','smtp')
    monkeypatch.setattr(config,'SMTP_ENABLED',True)
    monkeypatch.setattr(config,'PUBLIC_BASE_URL','https://helpdesk.example.invalid')
    monkeypatch.setattr(config,'SMTP_SSL_VERIFY',True)
    monkeypatch.setattr(config,'SMTP_USE_TLS',True)
    assert email_sender.validate_email_configuration()['is_mock'] is False
    for bad in ['http://helpdesk.example.invalid','https://helpdesk.example.invalid/?token=value','https://[bad']:
        monkeypatch.setattr(config,'PUBLIC_BASE_URL',bad)
        with pytest.raises(email_sender.EmailConfigurationError):
            email_sender.validate_email_configuration()


def test_smtp_refused_recipient_is_not_success(monkeypatch):
    from unittest.mock import MagicMock
    monkeypatch.setattr(config,'EMAIL_PROVIDER','smtp')
    monkeypatch.setattr(config,'SMTP_ENABLED',True)
    server=MagicMock()
    server.__enter__.return_value=server
    server.send_message.return_value={'user@example.invalid':(550,b'refused')}
    monkeypatch.setattr(email_sender.smtplib,'SMTP',lambda *args,**kwargs:server)
    monkeypatch.setattr(email_sender.smtplib,'SMTP_SSL',lambda *args,**kwargs:server)
    assert email_sender.dispatch_email('user@example.invalid','test','test') is False
