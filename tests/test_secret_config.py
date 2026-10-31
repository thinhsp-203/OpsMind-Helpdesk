"""Isolated startup configuration contracts; never print a secret."""
import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("secret", [None, "", " " * 40, "secret", "x" * 31])
def test_non_demo_rejects_missing_or_weak_secret(secret):
    env = {**os.environ, "DEMO_MODE": "false"}
    env.pop("SECRET_KEY", None)
    if secret is not None:
        env["SECRET_KEY"] = secret
    result = subprocess.run(  # noqa: S603 -- fixed script and trusted test interpreter
        [sys.executable, "-c", "import app.config"],
        env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr


@pytest.mark.parametrize("demo,secret", [("true", None), ("false", "synthetic-test-key-with-at-least-32-characters")])
def test_valid_secret_or_explicit_demo_starts(demo, secret):
    env = {**os.environ, "DEMO_MODE": demo}
    env.pop("SECRET_KEY", None)
    if secret is not None:
        env["SECRET_KEY"] = secret
    result = subprocess.run(  # noqa: S603 -- fixed script and trusted test interpreter
        [sys.executable, "-c", "import app.config; assert len(app.config.SECRET_KEY) >= 32"],
        env=env, capture_output=True, check=False,
    )
    assert result.returncode == 0
