import csv
import os

import pytest


@pytest.fixture
def write(tmp_path):
    def _write(name, content):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(content)
        return str(path)

    return _write


@pytest.fixture
def run(capsys):
    def _run(argv):
        import txmerge.cli

        try:
            code = txmerge.cli.main(argv)
        except SystemExit as e:
            code = e.code
        out, err = capsys.readouterr()
        return code, out, err

    return _run


@pytest.fixture
def read_ledger():
    def _read(path):
        with open(path, encoding="utf-8", newline="") as f:
            return list(csv.reader(f))

    return _read
