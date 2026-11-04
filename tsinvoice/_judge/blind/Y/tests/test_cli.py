"""End-to-end tests through main() and python -m tsinvoice (Stages 1, 9; CUJs)."""

import os
import sys
from pathlib import Path

import pytest

A = "Client,Description,Start,End\n"
B = "client,task,start_iso,duration_minutes\n"
HEADER = b"date,client,description,minutes,amount,session_id\n"
RATES = "pattern,hourly_rate\nacme,60\nbeta,10.05\n"


def args(trackers, rates, out):
    a = ["merge"]
    for t in trackers:
        a += ["--tracker", t]
    return a + ["--rates", rates, "--out", out]


@pytest.fixture
def rates(write_file):
    return write_file("rates.csv", RATES)


def test_cuj1_overlapping_exports(write_file, run_cli, rates, tmp_path):
    """CUJ 1: overlapping exports of one app."""
    row = "Acme,Design,08/10/2026 09:00,08/10/2026 10:00\n"
    d1 = write_file("d1.csv", A + "Acme,Other,02/10/2026 09:00,02/10/2026 09:30\n" + row)
    d2 = write_file("d2.csv", A + row)
    out = str(tmp_path / "out.csv")
    code, stdout, err, data = run_cli(args([f"desk={d1}", f"desk={d2}"], rates, out), out)
    assert (code, stdout, err) == (0, "", "")
    assert data == HEADER + b"2026-10-02,Acme,Other,30,30.00,\n2026-10-08,Acme,Design,60,60.00,\n"


def test_cuj2_continued_in_other_app(write_file, run_cli, rates, tmp_path):
    """CUJ 2: work continued in the other app."""
    d = write_file("d.csv", A + "Acme,Design,08/10/2026 09:00,08/10/2026 09:07\n")
    p = write_file("p.csv", B + "acme,design ,2026-10-08T09:07,7\n")
    out = str(tmp_path / "out.csv")
    code, _, err, data = run_cli(args([f"desk={d}", f"phone={p}"], rates, out), out)
    assert (code, err) == (0, "")
    assert data == HEADER + b"2026-10-08,Acme,Design,18,18.00,S1\n"


def test_cuj3_real_repeats_kept(write_file, run_cli, rates, tmp_path):
    """CUJ 3: larger per-export count kept, no overlap warning."""
    row = "Acme,Design,08/10/2026 09:00,08/10/2026 10:00\n"
    d1 = write_file("d1.csv", A + row * 2)
    d2 = write_file("d2.csv", A + row * 3)
    out = str(tmp_path / "out.csv")
    code, _, err, data = run_cli(args([f"desk={d1}", f"desk={d2}"], rates, out), out)
    assert (code, err) == (0, "")
    assert data == HEADER + b"2026-10-08,Acme,Design,60,60.00,\n" * 3


def test_cuj4_bad_data_does_not_stop(write_file, run_cli, rates, tmp_path):
    """CUJ 4: bad rows skipped with warnings; unrated kept at 0.00."""
    d = write_file("d.csv", A + "Acme,Design,08/10/2026 09:00,\nZed,Talk,08/10/2026 11:00,08/10/2026 11:30\n")
    p = write_file("p.csv", B + "acme,x,2026-10-08T09:00,29.5\n")
    out = str(tmp_path / "out.csv")
    code, _, err, data = run_cli(args([f"desk={d}", f"phone={p}"], rates, out), out)
    assert code == 0
    assert err.splitlines() == [
        f"tsinvoice: warning: {d}:2: blank end",
        f"tsinvoice: warning: {p}:2: invalid duration_minutes",
        "tsinvoice: warning: no rate for client 'Zed' description 'Talk' on 2026-10-08",
    ]
    assert data == HEADER + b"2026-10-08,Zed,Talk,30,0.00,\n"


@pytest.mark.parametrize("case", ["header", "missing_tracker", "missing_rates", "bad_rates",
                                  "rates_header"])
def test_cuj5_exit2_leaves_out_unchanged(write_file, run_cli, rates, tmp_path, case):
    """CUJ 5 / Exit codes: exit 2, single error line, --out unchanged."""
    out = write_file("out.csv", "previous run\n")
    good = write_file("d.csv", A + "Acme,D,08/10/2026 09:00,08/10/2026 10:00\n")
    trackers, r = [f"desk={good}"], rates
    if case == "header":
        bad = write_file("bad.csv", "foo,bar\n1,2\n")
        trackers.append(f"desk={bad}")
        expect = f"{bad}: unrecognised header"
    elif case == "missing_tracker":
        bad = str(tmp_path / "missing.csv")
        trackers.append(f"phone={bad}")
        expect = f"{bad}: cannot read: "
    elif case == "missing_rates":
        r = str(tmp_path / "norates.csv")
        expect = f"{r}: cannot read: "
    elif case == "bad_rates":
        r = write_file("r2.csv", "pattern,hourly_rate\nacme,-1\n")
        expect = f"{r}:2: invalid rates row: invalid hourly_rate"
    else:
        r = write_file("r2.csv", "pattern;hourly_rate\n")
        expect = f"{r}: unrecognised rates header"
    code, stdout, err, data = run_cli(args(trackers, r, out), out)
    assert code == 2 and stdout == ""
    lines = err.splitlines()
    assert len(lines) == 1 and lines[0].startswith(f"tsinvoice: error: {expect}")
    assert data == b"previous run\n"


def test_cuj6_rerun_byte_identical(write_file, run_cli, rates, tmp_path):
    """CUJ 6 / G5: byte-identical output and identical stderr."""
    d = write_file("d.csv", A + "Acme,D,08/10/2026 09:00,08/10/2026 10:00\n"
                   "Acme,E,08/10/2026 09:30,08/10/2026 10:30\nZed,x,y,z\n")
    out = str(tmp_path / "out.csv")
    first = run_cli(args([f"desk={d}"], rates, out), out)
    second = run_cli(args([f"desk={d}"], rates, out), out)
    assert first == second and first[0] == 0 and first[2]


def test_output_bytes_quoting(write_file, run_cli, rates, tmp_path):
    """Stage 9: \\n endings, no BOM, minimal quoting, line break kept."""
    d = write_file("d.csv", A + 'Acme,"Design, logo",08/10/2026 09:00,08/10/2026 09:06\n'
                   'Acme,"say ""hi""",09/10/2026 09:00,09/10/2026 09:06\n'
                   'Acme,"two\r\nlines",10/10/2026 09:00,10/10/2026 09:06\n')
    out = str(tmp_path / "out.csv")
    code, _, _, data = run_cli(args([f"desk={d}"], rates, out), out)
    assert code == 0
    assert data == HEADER + (b'2026-10-08,Acme,"Design, logo",6,6.00,\n'
                             b'2026-10-09,Acme,"say ""hi""",6,6.00,\n'
                             b'2026-10-10,Acme,"two\r\nlines",6,6.00,\n')


def test_no_valid_entries_header_only(write_file, run_cli, rates, tmp_path):
    """Stage 9: header-only output, exit 0."""
    d = write_file("d.csv", A + "Acme,D,x,y\n")
    out = str(tmp_path / "out.csv")
    code, _, err, data = run_cli(args([f"desk={d}"], rates, out), out)
    assert code == 0 and data == HEADER and "invalid start" in err


@pytest.mark.parametrize("value", ["desk", "=a.csv", "desk="])
def test_bad_tracker_value(run_cli, rates, tmp_path, value):
    """Stage 1: bad --tracker is a usage error."""
    out = str(tmp_path / "out.csv")
    code, stdout, err, data = run_cli(["merge", "--tracker", value, "--rates", rates, "--out", out], out)
    assert code == 2 and "expected NAME=PATH" in err and data is None and stdout == ""


def test_tracker_split_on_first_equals(write_file, run_cli, rates, tmp_path):
    """Stage 1: split on the first '='; paths may contain '='."""
    d = write_file("a=b.csv", A + "Acme,D,08/10/2026 09:00,08/10/2026 10:00\n")
    out = str(tmp_path / "out.csv")
    assert run_cli(args([f"desk={d}"], rates, out), out)[0] == 0


@pytest.mark.parametrize("argv", [
    [],
    ["merge", "--rates", "r.csv", "--out", "o.csv"],
    ["merge", "--tracker", "d=a.csv", "--out", "o.csv"],
    ["merge", "--tracker", "d=a.csv", "--rates", "r.csv"],
    ["merge", "--track", "d=a.csv", "--rates", "r.csv", "--out", "o.csv"],
])
def test_usage_errors(run_cli, argv):
    """Stage 1: missing sub-command/options exit 2 (no abbreviations)."""
    assert run_cli(argv)[0] == 2


def test_help_exit0(run_cli):
    """Stage 9: --help prints to stdout and exits 0."""
    code, stdout, _, _ = run_cli(["merge", "--help"])
    assert code == 0 and "--tracker" in stdout


def test_same_path_two_names_overlap(write_file, run_cli, rates, tmp_path):
    """Stage 1/8: same PATH under two NAMEs gives overlap warnings."""
    d = write_file("d.csv", A + "Acme,D,08/10/2026 09:00,08/10/2026 10:00\n")
    out = str(tmp_path / "out.csv")
    code, _, err, data = run_cli(args([f"desk={d}", f"other={d}"], rates, out), out)
    assert code == 0 and data.count(b"\n") == 3
    assert err == "tsinvoice: warning: overlapping sessions for client 'Acme': row 1 and row 2\n"


def test_same_path_twice_one_name(write_file, run_cli, rates, tmp_path):
    """Glossary/Stage 1: same PATH twice under one NAME adds no rows."""
    d = write_file("d.csv", A + "Acme,D,08/10/2026 09:00,08/10/2026 10:00\n")
    out = str(tmp_path / "out.csv")
    code, _, err, data = run_cli(args([f"desk={d}", f"desk={d}"], rates, out), out)
    assert (code, err) == (0, "") and data.count(b"\n") == 2


def test_out_equal_to_input(write_file, run_cli, rates):
    """Stage 9: --out may equal an input path."""
    d = write_file("d.csv", A + "Acme,D,08/10/2026 09:00,08/10/2026 10:00\n")
    code, _, _, data = run_cli(args([f"desk={d}"], rates, d), d)
    assert code == 0 and data == HEADER + b"2026-10-08,Acme,D,60,60.00,\n"


def test_out_missing_directory(write_file, run_cli, rates, tmp_path):
    """Fatal messages: cannot write; no temp file left."""
    d = write_file("d.csv", A + "Acme,D,08/10/2026 09:00,08/10/2026 10:00\n")
    out = str(tmp_path / "nodir" / "out.csv")
    code, _, err, _ = run_cli(args([f"desk={d}"], rates, out), out)
    assert code == 2 and err.startswith(f"tsinvoice: error: {out}: cannot write: ")
    assert len(err.splitlines()) == 1
    assert not list(tmp_path.rglob(".tsinvoice-*"))


def test_no_temp_file_left_after_success(write_file, run_cli, rates, tmp_path):
    """Stage 9: temp file moved into place."""
    d = write_file("d.csv", A + "Acme,D,08/10/2026 09:00,08/10/2026 10:00\n")
    out = str(tmp_path / "out.csv")
    assert run_cli(args([f"desk={d}"], rates, out), out)[0] == 0
    assert not list(tmp_path.glob(".tsinvoice-*"))


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes and symlinks")
def test_mode_and_symlink(write_file, run_cli, rates, tmp_path):
    """Stage 9: output mode 0o644; a symlinked --out is replaced by a regular file."""
    d = write_file("d.csv", A + "Acme,D,08/10/2026 09:00,08/10/2026 10:00\n")
    target = write_file("target.csv", "keep\n")
    out = tmp_path / "out.csv"
    out.symlink_to(target)
    assert run_cli(args([f"desk={d}"], rates, str(out)), str(out))[0] == 0
    assert not out.is_symlink() and Path(target).read_text() == "keep\n"
    assert (os.stat(out).st_mode & 0o777) == 0o644


def test_stderr_order_three_kinds(write_file, run_cli, rates, tmp_path):
    """Stage 9: bad rows (input order), then unrated (row order), then overlaps."""
    d = write_file("d.csv", A + "Zed,T,08/10/2026 09:00,08/10/2026 10:00\n"
                   "Acme,D,08/10/2026 09:00,08/10/2026 10:00\nAcme,D,x,y\n")
    p = write_file("p.csv", B + "acme,E,2026-10-08T09:30,60\nacme,E,bad,1\nyak,F,2026-10-07T09:00,5\n")
    out = str(tmp_path / "out.csv")
    code, _, err, _ = run_cli(args([f"desk={d}", f"phone={p}"], rates, out), out)
    assert code == 0
    assert err.splitlines() == [
        f"tsinvoice: warning: {d}:4: invalid start",
        f"tsinvoice: warning: {p}:3: invalid start_iso",
        "tsinvoice: warning: no rate for client 'yak' description 'F' on 2026-10-07",
        "tsinvoice: warning: no rate for client 'Zed' description 'T' on 2026-10-08",
        "tsinvoice: warning: overlapping sessions for client 'Acme': row 1 and row 2",
    ]


def test_unterminated_quote_end_to_end(write_file, run_cli, rates, tmp_path):
    """R4.1: unterminated quote is a bad row; exit 0."""
    d = write_file("d.csv", A + "Acme,D,08/10/2026 09:00,08/10/2026 10:00\n"
                   'Acme,"D,08/10/2026 11:00,08/10/2026 12:00\n')
    out = str(tmp_path / "out.csv")
    code, _, err, data = run_cli(args([f"desk={d}"], rates, out), out)
    assert code == 0 and err == f"tsinvoice: warning: {d}:3: unterminated quoted field\n"
    assert data.count(b"\n") == 2


def test_python_m_tsinvoice(write_file, run_module, rates, tmp_path):
    """E2E: the real `python -m tsinvoice merge` command."""
    d = write_file("d.csv", A + "Beta,Call,08/10/2026 09:00,08/10/2026 09:06\n")
    out = str(tmp_path / "out.csv")
    proc = run_module(args([f"desk={d}"], rates, out))
    assert proc.returncode == 0 and proc.stdout == b"" and proc.stderr == b""
    assert Path(out).read_bytes() == HEADER + b"2026-10-08,Beta,Call,6,1.01,\n"
    bad = run_module(["merge"])
    assert bad.returncode == 2
