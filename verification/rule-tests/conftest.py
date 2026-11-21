"""Lets these rule-derived tests import the engine without touching backend/.
Run from the repo root:  python -m pytest verification/rule-tests -q
(needs backend deps installed: cd backend && pip install -e ".[dev]")"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
os.environ.setdefault("ONE822_DB_PATH", os.path.join(tempfile.mkdtemp(prefix="1822-rule-tests-"), "t.db"))
