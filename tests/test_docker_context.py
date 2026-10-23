"""Exercise Docker's real ignore semantics with synthetic secrets, no app startup."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_docker_build_context_excludes_local_secrets_and_runtime(tmp_path: Path) -> None:
    docker = shutil.which("docker")
    if not docker:
        pytest.skip("Docker CLI unavailable; build-context verification requires Docker")
    repository = Path(__file__).resolve().parents[1]
    context = tmp_path / "context"
    context.mkdir()
    shutil.copyfile(repository / ".dockerignore", context / ".dockerignore")
    # FROM scratch avoids network access and COPY uses the actual ignore policy.
    (context / "Dockerfile").write_text("FROM scratch\nCOPY . /\n", encoding="utf-8")
    excluded = [
        ".env", ".env.local", ".env.production", ".env.example",
        "nested/.env", "nested/deeper/.env.production",
        "data/helpdesk.sqlite3", "data/other.sqlite3", "data/other.sqlite3-wal",
        "data/attachments/private.txt", "runtime/private.txt", "nested/server.log",
    ]
    required = [
        "requirements.txt", "app/main.py", "app/static/index.html",
        "data/knowledge/printer_queue.md", "data/rag_dictionary.json",
    ]
    for relative in excluded:
        target = context / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("AUD04-SYNTHETIC-SECRET", encoding="utf-8")
    for relative in required:
        target = context / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repository / relative, target)
    output = tmp_path / "export"
    subprocess.run(  # noqa: S603 -- resolved Docker executable, fixed args, synthetic temp context
        [docker, "build", "--output", f"type=local,dest={output}", str(context)],
        check=True, capture_output=True, text=True, timeout=120,
    )
    for relative in excluded:
        assert not (output / relative).exists(), f"Build leaked {relative}"
    for relative in required:
        assert (output / relative).read_bytes() == (repository / relative).read_bytes()
