import datetime
from decimal import Decimal

from txmerge.dedup import dedup
from txmerge.formats import read_export
from txmerge.model import Record

D = datetime.date(2026, 3, 3)


def rec(export, line, desc="Coffee", amount="-3.50", account="Cur", day=D):
    return Record(account, day, Decimal(amount), desc, export, line)


def test_identical_rows_in_one_export_kept():
    rs = [rec(0, 2), rec(0, 3)]
    assert dedup(rs) == rs


def test_max_count_across_exports():
    rs = [rec(0, 2), rec(0, 3), rec(1, 2, "COFFEE"), rec(1, 3, "coffee"), rec(1, 4, "Coffee")]
    kept = dedup(rs)
    assert kept == rs[:3]
    assert kept[2].description == "COFFEE" and (kept[2].export_index, kept[2].line) == (1, 2)


def test_case_and_whitespace_equal_key_first_text_kept():
    rs = [rec(0, 2, "Coffee  Shop"), rec(1, 2, "coffee shop")]
    kept = dedup(rs)
    assert len(kept) == 1 and kept[0].description == "Coffee  Shop"


def test_differences_stay_separate():
    rs = [
        rec(0, 2),
        rec(1, 2, day=datetime.date(2026, 3, 4)),
        rec(1, 3, amount="-3.51"),
        rec(1, 4, desc="Coffe"),
    ]
    assert dedup(rs) == rs


def test_same_path_twice_adds_no_rows(write):
    # D2
    p = write("a.csv", "Date,Description,Debit,Credit,Balance\n"
                       "01/02/2026,X,1,,\n01/02/2026,X,1,,\n02/02/2026,Y,2,,\n")
    rs = read_export(0, "Cur", p, print)[0] + read_export(1, "Cur", p, print)[0]
    kept = dedup(rs)
    assert len(kept) == 3 and all(r.export_index == 0 for r in kept)


def test_different_names_never_dedup():
    # D3
    rs = [rec(0, 2, account="A"), rec(1, 2, account="B")]
    assert dedup(rs) == rs


def test_format_a_and_b_same_account_dedup(write):
    a = write("a.csv", "Date,Description,Debit,Credit,Balance\n03/03/2026,Coffee,3.50,,\n")
    b = write("b.csv", "Transaction Date,Posting Date,Details,Amount\n2026-03-03,,coffee,-3.50\n")
    rs = read_export(0, "Cur", a, print)[0] + read_export(1, "Cur", b, print)[0]
    kept = dedup(rs)
    assert len(kept) == 1 and kept[0].export_index == 0
