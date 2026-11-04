import glob
import os
import subprocess
import sys
from pathlib import Path

import pytest

A = "Date,Description,Debit,Credit,Balance\n"
B = "Transaction Date,Posting Date,Details,Amount\n"
EXPECTED_HEADERS = (
    'expected "Date,Description,Debit,Credit,Balance" or '
    '"Transaction Date,Posting Date,Details,Amount"'
)
OLD = b"old ledger\n"


def read_bytes(p):
    with open(p, "rb") as f:
        return f.read()


def test_cuj1_merge(write, run):
    mar = write("mar.csv", A
                + "01/03/2026,Salary,,3000.00,\n"
                + "03/03/2026,Coffee,3.50,,\n"
                + "03/03/2026,Coffee,3.50,,\n"
                + '16/03/2026,Card payment,"1,200.00",,\n'
                + "31/02/2026,Bad,1.00,,\n")
    apr = write("apr.csv", A
                + '16/03/2026,CARD  PAYMENT,"1,200.00",,\n'
                + "02/04/2026,Rent,950.00,,\n"
                + "05/04/2026,Gym,30.00,,\n")
    card = write("card.csv", B
                 + "2026-03-10,2026-03-11,Coffee House,-4.20\n"
                 + "2026-03-17,2026-03-18,Payment received,1200.00\n"
                 + "2026-03-20,2026-03-21,Mystery shop,-15.00\n")
    rules = write("rules.csv", "pattern,category\ncoffee,Food\nsalary,Income\nrent\n"
                               "mystery,Uncategorised\nrent,Housing\n")
    out = str(Path(mar).parent / "ledger.csv")
    code, stdout, err = run(["merge", "--account", f"Current={mar}", "--account",
                             f"Current={apr}", "--account", f"Card={card}",
                             "--rules", rules, "--out", out])
    assert code == 0 and stdout == ""
    expected = (
        "date,account,description,amount,category,transfer_id\n"
        "2026-03-01,Current,Salary,3000.00,Income,\n"
        "2026-03-03,Current,Coffee,-3.50,Food,\n"
        "2026-03-03,Current,Coffee,-3.50,Food,\n"
        "2026-03-10,Card,Coffee House,-4.20,Food,\n"
        "2026-03-16,Current,Card payment,-1200.00,Transfer,T0001\n"
        "2026-03-17,Card,Payment received,1200.00,Transfer,T0001\n"
        "2026-03-20,Card,Mystery shop,-15.00,Uncategorised,\n"
        "2026-04-02,Current,Rent,-950.00,Housing,\n"
        "2026-04-05,Current,Gym,-30.00,Uncategorised,\n"
    )
    assert read_bytes(out) == expected.encode("utf-8")
    assert err.splitlines() == [
        f"txmerge: warning: {mar}:6: invalid date '31/02/2026'",
        f"txmerge: warning: {rules}:4: expected 2 fields, found 1",
        f"txmerge: wrote 9 rows to {out} (parsed 10, skipped 1 malformed, removed 1 "
        "duplicates, linked 1 transfer pairs, 2 uncategorised)",
    ]


@pytest.fixture
def basic(write, tmp_path):
    a = write("a.csv", A + "01/02/2026,Coffee,3.50,,\n02/02/2026,Rent,900.00,,\n")
    rules = write("rules.csv", "pattern,category\ncoffee,Food\n")
    return a, rules, str(tmp_path / "out.csv")


def test_cuj3_invalid_date_warning(write, run, read_ledger, basic):
    _, rules, out = basic
    a = write("x.csv", A + "01/02/2026,Ok,1.00,,\n31/02/2026,Bad,1.00,,\n")
    code, _, err = run(["merge", "--account", f"C={a}", "--rules", rules, "--out", out])
    assert code == 0
    assert f"txmerge: warning: {a}:3: invalid date '31/02/2026'\n" in err
    assert [r[2] for r in read_ledger(out)[1:]] == ["Ok"]


def test_embedded_newlines_quoted(write, run, basic):
    _, rules, out = basic
    a = write("x.csv", A + '01/02/2026,"two\nlines",1.00,,\n02/02/2026,"lone\rcr",1.00,,\n')
    assert run(["merge", "--account", f"C={a}", "--rules", rules, "--out", out])[0] == 0
    data = read_bytes(out)
    assert b'"two\nlines"' in data and b'"lone\rcr"' in data


def test_deterministic(run, basic, tmp_path):
    # D14
    a, rules, _ = basic
    o1, o2 = str(tmp_path / "1.csv"), str(tmp_path / "2.csv")
    for o in (o1, o2):
        assert run(["merge", "--account", f"C={a}", "--account", f"D={a}",
                    "--rules", rules, "--out", o])[0] == 0
    assert read_bytes(o1) == read_bytes(o2)


def test_subprocess(basic):
    # D13
    a, rules, out = basic
    proc = subprocess.run(
        [sys.executable, "-m", "txmerge", "merge", "--account", f"Cur={a}",
         "--rules", rules, "--out", out],
        cwd=Path(__file__).resolve().parent.parent, capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert proc.stdout == ""
    assert proc.stderr == (
        f"txmerge: wrote 2 rows to {out} (parsed 2, skipped 0 malformed, removed 0 "
        "duplicates, linked 0 transfer pairs, 1 uncategorised)\n"
    )


# ---- exit 2 cases -------------------------------------------------------

def _app_case(name, write, tmp_path, basic):
    """Return (argv-without-out, exact message or None). Out added by caller."""
    a, rules, _ = basic
    if name == "unrecognised header":
        p = write("bad.csv", "Foo, Bar\n1,2\n")
        return ["--account", f"C={p}", "--rules", rules], \
            f'txmerge: error: {p}: unrecognised header "Foo,Bar"; {EXPECTED_HEADERS}\n'
    if name == "empty input":
        p = write("empty.csv", "")
        return ["--account", f"C={p}", "--rules", rules], \
            f"txmerge: error: {p}: unrecognised header (empty file); {EXPECTED_HEADERS}\n"
    if name == "missing input":  # D10
        return ["--account", f"C={tmp_path / 'nope.csv'}", "--rules", rules], None
    if name == "missing rules":  # D9
        return ["--account", f"C={a}", "--rules", str(tmp_path / "nope.csv")], None
    if name == "wrong rules header":  # D9
        r = write("r2.csv", "pattern;category\n")
        return ["--account", f"C={a}", "--rules", r], None
    if name == "non-utf8":
        p = write("latin.csv", b"Date,Description,Debit,Credit,Balance\n01/02/2026,Caf\xa3,1.00,,\n")
        return ["--account", f"C={p}", "--rules", rules], None
    if name == "unclosed quote":  # D24
        p = write("q.csv", A + '01/02/2026,"Open,1.00,,\n02/02/2026,Later,2.00,,\n')
        return ["--account", f"C={p}", "--rules", rules], None
    raise AssertionError(name)


APP_CASES = ["unrecognised header", "empty input", "missing input", "missing rules",
             "wrong rules header", "non-utf8", "unclosed quote"]


@pytest.mark.parametrize("preexisting", [True, False])
@pytest.mark.parametrize("name", APP_CASES)
def test_app_errors_exit_2(name, preexisting, write, run, tmp_path, basic):
    argv, message = _app_case(name, write, tmp_path, basic)
    out = tmp_path / "ledger.csv"
    if preexisting:
        out.write_bytes(OLD)
    code, stdout, err = run(["merge", *argv, "--out", str(out)])
    assert code == 2 and stdout == ""
    assert err.startswith("txmerge: error:")
    if name in ("missing input", "missing rules", "non-utf8", "unclosed quote"):
        assert "cannot read" in err
    if message is not None:
        assert err == message
    if preexisting:
        assert out.read_bytes() == OLD
    else:
        assert not out.exists()
    assert glob.glob(str(tmp_path / "*.txmerge-tmp")) == []


def test_missing_output_directory(run, basic, tmp_path):
    a, rules, _ = basic
    out = str(tmp_path / "nodir" / "out.csv")
    code, _, err = run(["merge", "--account", f"C={a}", "--rules", rules, "--out", out])
    assert code == 2 and err.startswith(f"txmerge: error: cannot write {out}:")
    assert not os.path.exists(out)


@pytest.mark.parametrize("which", ["export", "rules"])
def test_out_is_an_input(which, run, basic):
    # D18
    a, rules, _ = basic
    target = a if which == "export" else rules
    before = read_bytes(target)
    code, _, err = run(["merge", "--account", f"C={a}", "--rules", rules, "--out", target])
    assert code == 2
    assert err == f"txmerge: error: --out {target} is also an input file\n"
    assert read_bytes(target) == before


@pytest.mark.parametrize("preexisting", [True, False])
@pytest.mark.parametrize(
    "argv",
    [
        ["merge", "--account", "noequals"],          # D25
        ["merge", "--account", "=x.csv"],
        [],
        ["merge", "--acc", "C=x.csv"],
    ],
    ids=["no-equals", "empty-name", "no-subcommand", "abbreviated"],
)
def test_argument_errors(argv, preexisting, run, basic, tmp_path):
    a, rules, _ = basic
    out = tmp_path / "ledger.csv"
    if preexisting:
        out.write_bytes(OLD)
    full = argv + (["--rules", rules, "--out", str(out)] if argv else [])
    code, stdout, err = run(full)
    assert code == 2
    assert err.startswith("usage: txmerge") and "error:" in err
    if preexisting:
        assert out.read_bytes() == OLD
    else:
        assert not out.exists()


@pytest.mark.parametrize("preexisting", [True, False])
def test_replace_failure_leaves_no_temp(preexisting, run, basic, monkeypatch, tmp_path):
    # D15
    a, rules, out = basic
    if preexisting:
        Path(out).write_bytes(OLD)

    def boom(src, dst):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "replace", boom)
    code, _, err = run(["merge", "--account", f"C={a}", "--rules", rules, "--out", out])
    assert code == 2
    assert err == f"txmerge: error: cannot write {out}: No space left on device\n"
    assert glob.glob(str(tmp_path / "*.txmerge-tmp")) == []
    if preexisting:
        assert read_bytes(out) == OLD
    else:
        assert not os.path.exists(out)


def test_equals_in_path_and_repeated_out(write, run, read_ledger, monkeypatch, tmp_path):
    # D25
    write("dir/a=b.csv", A + "01/02/2026,X,1.00,,\n")
    write("rules.csv", "pattern,category\n")
    monkeypatch.chdir(tmp_path)
    code, _, err = run(["merge", "--account", "Name=dir/a=b.csv", "--rules", "rules.csv",
                        "--out", "first.csv", "--out", "second.csv"])
    assert code == 0
    assert not (tmp_path / "first.csv").exists()
    assert read_ledger("second.csv")[1][:3] == ["2026-02-01", "Name", "X"]
    assert "wrote 1 rows to second.csv" in err


def test_symlink_out_replaced(run, basic, tmp_path, read_ledger):
    # D21
    a, rules, _ = basic
    target = tmp_path / "other.csv"
    target.write_bytes(OLD)
    link = tmp_path / "link.csv"
    os.symlink(target, link)
    code, _, _ = run(["merge", "--account", f"C={a}", "--rules", rules, "--out", str(link)])
    assert code == 0
    assert not link.is_symlink()
    assert read_ledger(str(link))[0][0] == "date"
    assert target.read_bytes() == OLD


def test_format_b_posting_date_ignored(write, run, read_ledger, basic):
    _, rules, out = basic
    b = write("b.csv", B + "2026-02-01,xyz,Shop,-2.00\n")
    assert run(["merge", "--account", f"Card={b}", "--rules", rules, "--out", out])[0] == 0
    assert read_ledger(out)[1] == ["2026-02-01", "Card", "Shop", "-2.00", "Uncategorised", ""]


def test_help(run):
    code, stdout, _ = run(["merge", "--help"])
    assert code == 0 and stdout.strip()


def test_all_rows_malformed(write, run, basic):
    _, rules, out = basic
    a = write("x.csv", A + "bad,X,1,,\n01/02/2026,X,,,\n")
    code, _, err = run(["merge", "--account", f"C={a}", "--rules", rules, "--out", out])
    assert code == 0
    assert read_bytes(out) == b"date,account,description,amount,category,transfer_id\n"
    assert "skipped 2 malformed" in err
