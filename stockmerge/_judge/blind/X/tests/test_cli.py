import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
A_HEADER = "Scanned At,SKU,Qty,Unit\n"
B_HEADER = "timestamp,barcode,count,note\n"
RULES = "pattern,category\ncola,Drinks\n123,Cans\n"


def run(tmp_path, locations, rules=RULES, out="out.csv"):
    (tmp_path / "rules.csv").write_text(rules, encoding="utf-8")
    args = [sys.executable, "-m", "stockmerge", "merge"]
    for name, filename, content in locations:
        path = tmp_path / filename
        if content is not None:
            path.write_text(content, encoding="utf-8")
        args += ["--location", f"{name}={path}"]
    args += ["--rules", str(tmp_path / "rules.csv"), "--out", str(tmp_path / out)]
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True)


def output(tmp_path, out="out.csv"):
    return (tmp_path / out).read_text(encoding="utf-8")


def test_full_merge(tmp_path):
    shop_a = A_HEADER + ("05/03/2026 14:30,00123,1,case\n"
                         "05/03/2026 14:35,COLA-1,-6,each\n"
                         "05/03/2026 14:40,TEA,2,each\n"
                         "05/03/2026 14:40,TEA,2,each\n")
    shop_b = B_HEADER + ("2026-03-05T14:30:59,123,12,overlap\n"
                         "2026-03-05T14:40:10,TEA,2,\n")
    back_b = B_HEADER + "2026-03-05T15:10:00,cola-1,6,moved in\n"
    result = run(tmp_path, [("shop floor", "a.csv", shop_a),
                            ("shop floor", "b.csv", shop_b),
                            ("back room", "c.csv", back_b)])
    assert result.returncode == 0, result.stderr
    assert output(tmp_path) == (
        "location,sku,qty_each,category,move_id\n"
        "back room,cola-1,6,Drinks,M1\n"
        "shop floor,00123,12,Cans,\n"
        "shop floor,COLA-1,-6,Drinks,M1\n"
        "shop floor,TEA,2,Uncategorised,\n"
        "shop floor,TEA,2,Uncategorised,\n")


def test_repeat_runs_are_byte_identical(tmp_path):
    locs = [("shop", "a.csv", A_HEADER + "05/03/2026 14:30,X,-1,each\n"),
            ("back", "b.csv", B_HEADER + "2026-03-05T14:31:00,X,1,\n")]
    assert run(tmp_path, locs).returncode == 0
    first = (tmp_path / "out.csv").read_bytes()
    assert run(tmp_path, locs).returncode == 0
    assert (tmp_path / "out.csv").read_bytes() == first


def test_bad_row_warns_and_exits_0(tmp_path):
    result = run(tmp_path, [("shop", "a.csv", A_HEADER + "bad,X,1,each\n05/03/2026 14:30,Y,1,each\n")])
    assert result.returncode == 0
    assert "a.csv:2:" in result.stderr
    assert output(tmp_path).splitlines()[1:] == ["shop,Y,1,Uncategorised,"]


def test_unknown_header_exits_2_and_writes_nothing(tmp_path):
    result = run(tmp_path, [("shop", "a.csv", "what,is,this\n")])
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert not (tmp_path / "out.csv").exists()


def test_missing_input_exits_2(tmp_path):
    result = run(tmp_path, [("shop", "missing.csv", None)])
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "out.csv").exists()


def test_bad_location_argument_exits_2(tmp_path):
    (tmp_path / "rules.csv").write_text(RULES, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "stockmerge", "merge", "--location", "nopath",
         "--rules", str(tmp_path / "rules.csv"), "--out", str(tmp_path / "o.csv")],
        cwd=REPO, capture_output=True, text=True)
    assert result.returncode == 2


def test_missing_output_directory_exits_2(tmp_path):
    result = run(tmp_path, [("shop", "a.csv", A_HEADER)], out="no/such/out.csv")
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


def test_location_name_is_trimmed(tmp_path):
    result = run(tmp_path, [("shop ", "a.csv", A_HEADER + "05/03/2026 14:30,X,1,each\n"),
                            (" shop", "b.csv", A_HEADER + "05/03/2026 14:30,X,1,each\n")])
    assert result.returncode == 0
    assert output(tmp_path).splitlines()[1:] == ["shop,X,1,Uncategorised,"]
