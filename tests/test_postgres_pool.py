"""PostgreSQL connection reuse and transaction boundaries on an isolated DB."""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from psycopg.conninfo import make_conninfo

from app import store

pytestmark = pytest.mark.skipif(not os.getenv('DATABASE_URL'), reason='DATABASE_URL is not configured')


@pytest.fixture(autouse=True)
def isolated_pool(monkeypatch):
    store.close_database_pool()
    monkeypatch.setattr(store, '_database_url', os.environ['DATABASE_URL'])
    yield
    store.close_database_pool()


def test_postgres_reuses_physical_connection_between_store_operations():
    with store._connect() as first:
        first_pid = first.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid']
    with store._connect() as second:
        second_pid = second.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid']
    assert first_pid == second_pid, 'Sequential store operations must reuse a healthy physical connection'


def test_failed_transaction_is_rolled_back_before_reuse():
    with store._connect() as connection:
        connection.execute('CREATE TEMP TABLE pool_rollback_probe (value INTEGER)')
    with pytest.raises(store.DatabaseError):
        with store._connect() as connection:
            connection.execute('INSERT INTO pool_rollback_probe VALUES (7)')
            connection.execute('SELECT 1 / 0')
    with store._connect() as connection:
        assert connection.execute('SELECT count(*) AS n FROM pool_rollback_probe').fetchone()['n'] == 0
        connection.execute('DROP TABLE pool_rollback_probe')


def test_successful_transaction_commits_before_reuse():
    with store._connect() as connection:
        connection.execute('CREATE TEMP TABLE pool_commit_probe (value INTEGER)')
    with store._connect() as connection:
        connection.execute('INSERT INTO pool_commit_probe VALUES (7)')
    with store._connect() as connection:
        assert connection.execute('SELECT value FROM pool_commit_probe').fetchone()['value'] == 7
        connection.execute('DROP TABLE pool_commit_probe')


def test_concurrent_leases_do_not_share_an_active_transaction():
    barrier = Barrier(2)
    def transaction():
        with store._connect() as connection:
            pid = connection.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid']
            barrier.wait(timeout=10)
            return pid
    with ThreadPoolExecutor(max_workers=2) as threads:
        first, second = list(threads.map(lambda _: transaction(), range(2)))
    assert first != second


def test_closed_connection_is_replaced_without_replaying_statements():
    with store._connect() as connection:
        old_pid = connection.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid']
        connection._connection.close()
    with store._connect() as connection:
        new_pid = connection.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid']
    assert old_pid != new_pid


@pytest.mark.parametrize('existing_application_name', [None, 'pool-first'])
def test_database_url_change_does_not_reuse_previous_pool(monkeypatch, existing_application_name):
    original_url = os.environ['DATABASE_URL']
    if existing_application_name is not None:
        original_url = make_conninfo(original_url, application_name=existing_application_name)
    monkeypatch.setattr(store, '_database_url', original_url)
    with store._connect() as connection:
        initial = connection.execute("SELECT pg_backend_pid() AS pid, current_setting('application_name') AS name").fetchone()
    if existing_application_name is not None:
        assert initial['name'] == existing_application_name
    updated_url = make_conninfo(original_url, application_name='pool-second')
    monkeypatch.setattr(store, '_database_url', updated_url)
    with store._connect() as connection:
        row = connection.execute("SELECT pg_backend_pid() AS pid, current_setting('application_name') AS name").fetchone()
    assert row['pid'] != initial['pid']
    assert row['name'] == 'pool-second'


def test_shutdown_releases_connections_and_next_use_reopens():
    with store._connect() as connection:
        first_pid = connection.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid']
    store.close_database_pool()
    with store._connect() as connection:
        assert connection.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid'] != first_pid
