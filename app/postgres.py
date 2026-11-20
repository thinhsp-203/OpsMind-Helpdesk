"""Process-local PostgreSQL leases; each lease keeps its own transaction."""
import atexit
from contextlib import AbstractContextManager
from threading import Lock

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_lock = Lock()
_pool: ConnectionPool | None = None
_url: str | None = None


def connection(url: str) -> AbstractContextManager[psycopg.Connection]:
    global _pool, _url
    with _lock:
        if _pool is None or _pool.closed or _url != url:
            if _pool is not None:
                _pool.close()
            _pool = ConnectionPool(
                conninfo=url,
                kwargs={'row_factory': dict_row, 'prepare_threshold': None, 'connect_timeout': 5},
                min_size=1,
                max_size=4,
                timeout=10,
                max_idle=60,
                max_lifetime=600,
                check=ConnectionPool.check_connection,
                name='opsmind-postgres',
                open=False,
            )
            _url = url
            _pool.open(wait=True, timeout=10)
        pool = _pool
    return pool.connection()


def close_pool() -> None:
    global _pool, _url
    with _lock:
        pool, _pool = _pool, None
        _url = None
    if pool is not None:
        pool.close()


atexit.register(close_pool)
