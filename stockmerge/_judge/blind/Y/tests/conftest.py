import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from stockmerge.model import Scan, normalise_sku

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def write_file(tmp_path):
    def _write(name, content):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(content)
        return str(p)

    return _write


@pytest.fixture
def run_cli():
    def _run(*args):
        r = subprocess.run(
            [sys.executable, "-m", "stockmerge", *args],
            cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8",
        )
        return r.returncode, r.stdout, r.stderr

    return _run


def make_scan(**overrides):
    values = dict(
        location="shop", arg_index=0, record_no=0, path="t.csv", line=2,
        minute=datetime(2026, 3, 5, 10, 0), sku="ABC", qty_each=1,
    )
    values.update(overrides)
    if "sku_norm" not in values:
        values["sku_norm"] = normalise_sku(values["sku"])
    return Scan(**values)


@pytest.fixture
def scan_factory():
    return make_scan


@pytest.fixture
def read_out():
    def _read(path):
        with open(path, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    return _read
