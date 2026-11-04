import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

DESKTOP = ("Client,Description,Start,End\n"
           "Acme,Design,02/03/2026 09:00,02/03/2026 09:07\n"
           "Beta,Call,02/03/2026 11:00,02/03/2026 11:30\n")
DESKTOP_2 = ("Client,Description,Start,End\n"
             "Beta,Call,02/03/2026 11:00,02/03/2026 11:30\n"
             "Beta,Call,03/03/2026 11:00,03/03/2026 11:20\n")
PHONE = ("client,task,start_iso,duration_minutes\n"
         "acme,design,2026-03-02T09:07:00Z,7\n"
         "Gamma,Misc,2026-03-02T12:00:00,10\n"
         "Gamma,Misc,2026-03-02T13:00:00,12.5\n")
RATES = "pattern,hourly_rate\nacme,100\nbeta,60\n"


def run(tmp_path, *args):
    return subprocess.run([sys.executable, "-m", "tsinvoice", *args], cwd=REPO,
                          capture_output=True, text=True)


def setup(tmp_path):
    files = {"d1.csv": DESKTOP, "d2.csv": DESKTOP_2, "p.csv": PHONE, "rates.csv": RATES}
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    return [f"--tracker", f"desktop={tmp_path / 'd1.csv'}",
            "--tracker", f"desktop={tmp_path / 'd2.csv'}",
            "--tracker", f"phone={tmp_path / 'p.csv'}",
            "--rates", str(tmp_path / "rates.csv")]


def test_end_to_end(tmp_path):
    out = tmp_path / "out.csv"
    result = run(tmp_path, "merge", *setup(tmp_path), "--out", str(out))
    assert result.returncode == 0, result.stderr
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "date,client,description,minutes,amount,session_id"
    acme, beta1, beta2, gamma = lines[1:]
    assert acme.startswith("2026-03-02,Acme,Design,18,30.00,s-")
    assert beta1 == "2026-03-02,Beta,Call,30,30.00,"
    assert beta2 == "2026-03-03,Beta,Call,24,24.00,"
    assert gamma == "2026-03-02,Gamma,Misc,12,0.00,"
    assert "p.csv:4" in result.stderr                     # bad duration warned
    assert "no rate for client 'Gamma' description 'Misc'" in result.stderr


def test_rerun_is_byte_identical(tmp_path):
    args = setup(tmp_path)
    out1, out2 = tmp_path / "o1.csv", tmp_path / "o2.csv"
    assert run(tmp_path, "merge", *args, "--out", str(out1)).returncode == 0
    assert run(tmp_path, "merge", *args, "--out", str(out2)).returncode == 0
    assert out1.read_bytes() == out2.read_bytes()


def test_same_file_twice_does_not_double(tmp_path):
    (tmp_path / "d.csv").write_text(DESKTOP, encoding="utf-8")
    (tmp_path / "rates.csv").write_text(RATES, encoding="utf-8")
    out = tmp_path / "out.csv"
    result = run(tmp_path, "merge", "--tracker", f"d={tmp_path / 'd.csv'}",
                 "--tracker", f"d={tmp_path / 'd.csv'}",
                 "--rates", str(tmp_path / "rates.csv"), "--out", str(out))
    assert result.returncode == 0, result.stderr
    assert len(out.read_text().splitlines()) == 3


def test_unknown_header_exits_2_without_output(tmp_path):
    (tmp_path / "bad.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "rates.csv").write_text(RATES, encoding="utf-8")
    out = tmp_path / "out.csv"
    result = run(tmp_path, "merge", "--tracker", f"x={tmp_path / 'bad.csv'}",
                 "--rates", str(tmp_path / "rates.csv"), "--out", str(out))
    assert result.returncode == 2
    assert "header" in result.stderr
    assert not out.exists()


def test_fatal_error_leaves_existing_output_untouched(tmp_path):
    (tmp_path / "rates.csv").write_text("nope\n", encoding="utf-8")
    (tmp_path / "d.csv").write_text(DESKTOP, encoding="utf-8")
    out = tmp_path / "out.csv"
    out.write_text("old\n", encoding="utf-8")
    result = run(tmp_path, "merge", "--tracker", f"d={tmp_path / 'd.csv'}",
                 "--rates", str(tmp_path / "rates.csv"), "--out", str(out))
    assert result.returncode == 2
    assert out.read_text() == "old\n"


def test_bad_tracker_argument_exits_2(tmp_path):
    (tmp_path / "rates.csv").write_text(RATES, encoding="utf-8")
    out = tmp_path / "out.csv"
    for bad in ["no-equals-sign", "=path.csv", "name="]:
        result = run(tmp_path, "merge", "--tracker", bad,
                     "--rates", str(tmp_path / "rates.csv"), "--out", str(out))
        assert result.returncode == 2, bad
        assert not out.exists()


def test_missing_tracker_file_exits_2(tmp_path):
    (tmp_path / "rates.csv").write_text(RATES, encoding="utf-8")
    out = tmp_path / "out.csv"
    result = run(tmp_path, "merge", "--tracker", f"d={tmp_path / 'missing.csv'}",
                 "--rates", str(tmp_path / "rates.csv"), "--out", str(out))
    assert result.returncode == 2
    assert not out.exists()


def test_no_rate_warning_uses_single_quotes_even_with_apostrophe(tmp_path):
    (tmp_path / "rates.csv").write_text(RATES, encoding="utf-8")
    (tmp_path / "d.csv").write_text("Client,Description,Start,End\n"
                                    "O'Brien,Call,02/03/2026 09:00,02/03/2026 10:00\n",
                                    encoding="utf-8")
    result = run(tmp_path, "merge", "--tracker", f"d={tmp_path / 'd.csv'}",
                 "--rates", str(tmp_path / "rates.csv"), "--out", str(tmp_path / "o.csv"))
    assert "no rate for client 'O'Brien' description 'Call'" in result.stderr


def test_failed_write_keeps_existing_output_and_leaves_no_temp(tmp_path):
    (tmp_path / "rates.csv").write_text(RATES, encoding="utf-8")
    (tmp_path / "d.csv").write_text(DESKTOP, encoding="utf-8")
    out = tmp_path / "out.csv"
    out.mkdir()  # os.replace of a file onto a directory fails
    result = run(tmp_path, "merge", "--tracker", f"d={tmp_path / 'd.csv'}",
                 "--rates", str(tmp_path / "rates.csv"), "--out", str(out))
    assert result.returncode == 2
    assert "cannot write" in result.stderr
    assert sorted(p.name for p in tmp_path.iterdir()) == ["d.csv", "out.csv", "rates.csv"]
