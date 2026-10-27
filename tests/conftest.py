from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

# Ensure test suite runs with demo mode enabled and a predictable secret key
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("SECRET_KEY", "pytest-test-secret-key-32chars-minimum-safe")


@contextmanager
def _knowledge_reader_process():
    from app import store

    script = """
import json, os, sys
from app import store
from app.rag import generate_answer
print(json.dumps({'ready': True, 'pid': os.getpid()}), flush=True)
for line in sys.stdin:
    question = json.loads(line)['question']
    result = generate_answer(question)
    result['pid'] = os.getpid()
    print(json.dumps(result), flush=True)
"""
    environment = {
        **os.environ,
        "HELPDESK_DB_PATH": str(store._database_path.resolve()), "DATABASE_URL": store._database_url,
        "DEMO_MODE": "true", "ENABLE_LLM_GENERATION": "false", "SMTP_ENABLED": "false",
        "SECRET_KEY": "AUD08-synthetic-process-secret-more-than-32-characters",
        "PYTHONIOENCODING": "utf-8",
    }
    with subprocess.Popen(  # noqa: S603 -- trusted interpreter, fixed script, isolated test DB
        [sys.executable, "-u", "-c", script], cwd=Path(__file__).resolve().parents[1],
        env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    ) as process:
        reader = ThreadPoolExecutor(max_workers=1)

        def read():
            line = reader.submit(process.stdout.readline).result(timeout=15)
            assert line, f"Reader exited unexpectedly: {process.poll()}"
            return json.loads(line)

        def ask(question):
            process.stdin.write(json.dumps({"question": question}) + "\n")
            process.stdin.flush()
            return read()

        try:
            ready = read()
            assert ready["ready"] and ready["pid"] != os.getpid()
            yield ask
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            reader.shutdown(wait=True, cancel_futures=True)


@pytest.fixture
def knowledge_reader_process():
    return _knowledge_reader_process
