import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_ablation_script_reproduces_production_ranking():
    # Subprocess: the script points config at its own throwaway DB at import time.
    environment = {k: v for k, v in os.environ.items() if k not in {"HELPDESK_DB_PATH", "DATABASE_URL"}}
    environment["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(  # noqa: S603 -- trusted interpreter and fixed module
        [sys.executable, "-m", "scripts.ablation_rag"], cwd=ROOT, env=environment,
        capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Cấu hình E khớp 100% với app/rag.py" in completed.stdout
    assert "<- đang dùng" in completed.stdout
