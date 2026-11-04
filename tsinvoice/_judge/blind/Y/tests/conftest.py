import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def write_file(tmp_path):
    def write(name, content):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            with open(p, "w", encoding="utf-8", newline="") as fh:
                fh.write(content)
        return str(p)

    return write


@pytest.fixture
def run_cli(capsys):
    def run(args, out_path=None):
        from tsinvoice import cli

        try:
            code = cli.main(args)
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 2
        captured = capsys.readouterr()
        out_bytes = None
        if out_path is not None and Path(out_path).exists():
            out_bytes = Path(out_path).read_bytes()
        return code, captured.out, captured.err, out_bytes

    return run


@pytest.fixture
def run_module():
    def run(args):
        return subprocess.run(
            [sys.executable, "-m", "tsinvoice", *args],
            cwd=REPO_ROOT,
            capture_output=True,
        )

    return run
