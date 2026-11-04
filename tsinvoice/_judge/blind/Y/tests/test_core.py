"""Stages 4-8 with hand-built entries."""

from datetime import datetime
from decimal import Decimal

from tsinvoice.core import dedupe, find_rate, join, merge, price
from tsinvoice.model import Entry, Rule, normalise
from tests.helpers import entry

RULES = [Rule("acme", Decimal("60"))]


def chains(sessions):
    return sorted([[e.order for e in s.entries] for s in sessions])


# ---- Stage 4 dedupe ----------------------------------------------------------

def test_dedupe_identical_across_exports_kept_once():
    """Stage 4 / CUJ 1."""
    a = entry("09:00", "10:00", order=(0, 2))
    b = entry("09:00", "10:00", order=(1, 5))
    assert dedupe([a, b]) == [a]


def test_dedupe_max_count():
    """Stage 4 / worked example Max count: 2 and 3 give 3; export 1's two + export 2's first."""
    e1 = [entry("09:00", "10:00", order=(0, n)) for n in (2, 3)]
    e2 = [entry("09:00", "10:00", order=(1, n)) for n in (2, 3, 4)]
    assert dedupe(e2 + e1) == e1 + [e2[0]]


def test_dedupe_within_one_export_all_kept():
    """Stage 4: real repeats in one export are kept."""
    es = [entry("09:00", "10:00", order=(0, n)) for n in (2, 3)]
    assert dedupe(es) == es


def test_dedupe_case_and_space_insensitive():
    """Stage 4: duplicate key uses normalised text; first copy supplies text."""
    a = entry("09:00", "10:00", client="Acme", description="Design", order=(0, 2))
    b = entry("09:00", "10:00", client=" ACME ", description="design ", order=(1, 2))
    assert dedupe([b, a]) == [a]


def test_dedupe_one_minute_difference_kept():
    """Stage 4: overlaps without exact match are not duplicates."""
    a = entry("09:00", "10:00", order=(0, 2))
    b = entry("09:00", "10:01", order=(1, 2))
    assert dedupe([a, b]) == [a, b]


def test_dedupe_different_trackers_never():
    """Stage 4: different trackers never compared."""
    a = entry("09:00", "10:00", tracker="desk", order=(0, 2))
    b = entry("09:00", "10:00", tracker="phone", order=(1, 2))
    assert dedupe([a, b]) == [a, b]


def test_dedupe_same_path_twice_one_name():
    """Stage 1/4: same PATH twice under one NAME adds no rows."""
    a = [entry("09:00", "10:00", order=(0, 2)), entry("11:00", "12:00", order=(0, 3))]
    b = [entry("09:00", "10:00", order=(1, 2)), entry("11:00", "12:00", order=(1, 3))]
    assert dedupe(a + b) == a


# ---- Stage 5 join --------------------------------------------------------------

def test_join_gap_zero_and_two():
    """Stage 5 / worked example Gap limit."""
    a = entry("09:00", "10:00", order=(0, 2))
    b = entry("10:00", "10:30", order=(0, 3))
    c = entry("10:32", "11:00", order=(0, 4))
    assert chains(join([a, b, c])) == [[(0, 2), (0, 3), (0, 4)]]


def test_join_gap_three_and_negative_not_joined():
    """Stage 5: gap 3 or negative not joined."""
    a = entry("09:00", "10:00", order=(0, 2))
    b = entry("10:03", "10:30", order=(0, 3))
    c = entry("10:29", "10:45", order=(0, 4))
    assert len(join([a, b, c])) == 3


def test_join_chain_across_trackers():
    """Stage 5: chains of 3 across trackers."""
    a = entry("09:00", "09:10", tracker="desk", order=(0, 2))
    b = entry("09:11", "09:20", tracker="phone", description=" design", order=(1, 2))
    c = entry("09:20", "09:30", tracker="desk", order=(0, 3))
    (s,) = join([c, b, a])
    assert [e.order for e in s.entries] == [(0, 2), (1, 2), (0, 3)]


def test_join_smallest_gap_wins():
    """Stage 5: P takes the candidate with the smallest gap."""
    p = entry("09:00", "10:00", order=(0, 2))
    q2 = entry("10:02", "10:30", order=(0, 3))
    q1 = entry("10:01", "10:20", order=(0, 4))
    got = chains(join([p, q2, q1]))
    assert [(0, 2), (0, 4)] in got and [(0, 3)] in got


def test_join_gap_tie_input_order():
    """Stage 5: gap tie broken by input order."""
    p = entry("09:00", "10:00", order=(1, 2))
    q_late = entry("10:01", "10:20", order=(1, 9))
    q_early = entry("10:01", "10:30", order=(0, 7))
    assert chains(join([p, q_late, q_early])) == [[(1, 2), (0, 7)], [(1, 9)]]


def test_join_claimed_successor():
    """Worked example Claimed successor: A takes C; B alone."""
    a = entry("09:00", "10:00", order=(0, 2))
    b = entry("09:30", "10:01", order=(0, 3))
    c = entry("10:01", "10:30", order=(0, 4))
    assert chains(join([a, b, c])) == [[(0, 2), (0, 4)], [(0, 3)]]


def test_join_same_start_predecessors_input_order():
    """Stage 5: sort by (start, input order); the earlier input picks first."""
    p1 = entry("09:00", "10:00", order=(1, 2))
    p2 = entry("09:00", "10:00", order=(0, 2), tracker="phone")
    q = entry("10:00", "10:30", order=(1, 3))
    got = chains(join([p1, p2, q]))
    assert [(0, 2), (1, 3)] in got and [(1, 2)] in got


def test_join_different_descriptions_not_joined():
    """Stage 5: grouped by client and description."""
    a = entry("09:00", "10:00", description="Design")
    b = entry("10:00", "10:30", description="Build", order=(0, 3))
    assert len(join([a, b])) == 2


def test_join_phone_seconds_handoff():
    """Worked example App handoff with seconds (truncated in reader)."""
    a = entry("09:00", "09:07", tracker="phone", order=(1, 2))
    b = entry("09:07", "09:14", tracker="desk", order=(0, 2))
    rows, _ = merge([a, b], RULES)
    assert [(r.minutes, r.session_id) for r in rows] == [(18, "S1")]


# ---- Stage 6 price / rate --------------------------------------------------------

def test_price_half_up():
    """Worked example Half-up: 6 minutes at 10.05 -> 1.01."""
    assert price(6, Decimal("10.05")) == "1.01"


def test_price_zero_and_large():
    """Stage 6/9: zero rate 0.00; no exponent notation."""
    assert price(60, Decimal("0")) == "0.00"
    assert price(600, Decimal("1000000")) == "10000000.00"
    assert price(6, Decimal("100")) == "10.00"


def test_find_rate_first_rule_wins_and_description_match():
    """Stage 6: first rule matching client or description."""
    rules = [Rule("logo", Decimal("90")), Rule("acme", Decimal("60")), Rule("ac", Decimal("1"))]
    assert find_rate(rules, entry("09:00", "10:00", description="Logo work")) == Decimal("90")
    assert find_rate(rules, entry("09:00", "10:00")) == Decimal("60")
    assert find_rate(rules, entry("09:00", "10:00", client="Beta", description="call ACME")) == Decimal("60")
    assert find_rate(rules, entry("09:00", "10:00", client="Zed", description="x")) is None


def test_find_rate_normalised_pattern():
    """Stage 2/6: whitespace-normalised, case-insensitive pattern."""
    rules = [Rule(normalise("  ACME   corp "), Decimal("5"))]
    assert find_rate(rules, entry("09:00", "10:00", client="Acme Corp")) == Decimal("5")


def test_unrated_session_warning():
    """Stage 6 / worked example Unrated."""
    rows, warns = merge([entry("09:00", "10:00", client="Zed", description="Talk")], RULES)
    assert rows[0].amount == "0.00"
    assert warns == ["tsinvoice: warning: no rate for client 'Zed' description 'Talk' on 2026-10-08"]


def test_zero_rate_no_warning():
    """Stage 2: zero rate allowed, no warning."""
    rows, warns = merge([entry("09:00", "10:00")], [Rule("acme", Decimal("0"))])
    assert rows[0].amount == "0.00" and warns == []


def test_exact_multiple_and_amount():
    """Worked example Exact multiple: 12 worked minutes stays 12."""
    rows, _ = merge([entry("09:00", "09:12")], RULES)
    assert (rows[0].minutes, rows[0].amount) == (12, "12.00")


def test_join_and_round():
    """Worked example Join and round / CUJ 2."""
    a = entry("09:00", "09:07", order=(0, 2))
    b = entry("09:07", "09:14", client="acme", description="design ", tracker="phone", order=(1, 2))
    (r,), warns = merge([a, b], RULES)
    assert (r.date, r.client, r.description, r.minutes, r.amount, r.session_id) == (
        "2026-10-08", "Acme", "Design", 18, "18.00", "S1")
    assert warns == []


# ---- Stage 7 sort / ids ------------------------------------------------------------

def test_case_of_client_printed_per_session():
    """Worked example Case of client."""
    a = entry("09:00", "10:00", client="Acme", order=(0, 2))
    b = entry("11:00", "12:00", client="ACME", order=(0, 3))
    c = entry("08:00", "08:30", client="Beta", order=(0, 4))
    rows, _ = merge([b, c, a], RULES)
    assert [r.client for r in rows] == ["Acme", "ACME", "Beta"]


def test_sort_order_tie_break_input_order():
    """Stage 7: sort by (client key, start, input order)."""
    a = entry("09:00", "10:00", description="X", tracker="t1", order=(1, 2))
    b = entry("09:00", "09:30", description="Y", tracker="t2", order=(0, 2))
    c = entry("08:00", "08:30", client="beta", order=(0, 3))
    d = entry("07:00", "07:30", day="2026-10-09", order=(0, 4))
    rows, _ = merge([a, b, c, d], RULES)
    assert [r.session.first.order for r in rows] == [(0, 2), (1, 2), (0, 4), (0, 3)]


def test_session_ids_only_on_joined_sequential():
    """Stage 7: S1, S2 on joined rows in output order; blank otherwise."""
    es = [
        entry("09:00", "09:10", order=(0, 2)), entry("09:10", "09:20", order=(0, 3)),
        entry("11:00", "11:10", order=(0, 4)),
        entry("13:00", "13:10", order=(0, 5)), entry("13:11", "13:20", order=(0, 6)),
    ]
    rows, _ = merge(es, RULES)
    assert [r.session_id for r in rows] == ["S1", "", "S2"]


def test_date_from_first_entry_no_midnight_split():
    """Stage 6: date is the first entry's start date."""
    e = Entry("d", (0, 2), "d.csv", 2, "Acme", "D", "acme", "d",
              datetime(2026, 10, 8, 23, 30), datetime(2026, 10, 9, 0, 30), 60)
    (r,), _ = merge([e], RULES)
    assert r.date == "2026-10-08" and r.minutes == 60


# ---- Stage 8 overlaps --------------------------------------------------------------

OVERLAP = "tsinvoice: warning: overlapping sessions for client '{}': row {} and row {}"


def test_overlap_warned():
    """Worked example Overlap is not a join."""
    a = entry("09:00", "10:00", order=(0, 2))
    b = entry("09:59", "10:30", order=(0, 3))
    rows, warns = merge([a, b], RULES)
    assert len(rows) == 2 and warns == [OVERLAP.format("Acme", 1, 2)]


def test_overlap_touching_not_warned_and_other_client():
    """Stage 8: touching not an overlap; different clients not compared."""
    a = entry("09:00", "10:00", description="X", order=(0, 2))
    b = entry("10:00", "10:30", description="Y", order=(0, 3))
    c = entry("09:00", "10:00", client="Beta", order=(0, 4))
    assert merge([a, b, c], RULES + [Rule("beta", Decimal("1"))])[1] == []


def test_overlap_exact_repeats_not_warned():
    """Stage 8 / CUJ 3: exact repeats (one export or across exports) not warned."""
    e1 = [entry("09:00", "10:00", order=(0, n)) for n in (2, 3)]
    e2 = [entry("09:00", "10:00", order=(1, n)) for n in (2, 3, 4)]
    rows, warns = merge(e1 + e2, RULES)
    assert len(rows) == 3 and warns == []


def test_overlap_same_entry_two_trackers_warned():
    """Stage 8: the same entry in two trackers is warned."""
    a = entry("09:00", "10:00", tracker="desk", order=(0, 2))
    b = entry("09:00", "10:00", tracker="phone", order=(1, 2))
    rows, warns = merge([a, b], RULES)
    assert warns == [OVERLAP.format("Acme", 1, 2)]


def test_overlap_claimed_successor_and_order():
    """Worked example Claimed successor + Stage 8 (i, j) order; client from row i."""
    a = entry("09:00", "10:00", order=(0, 2))
    b = entry("09:30", "10:01", client="ACME", order=(0, 3))
    c = entry("10:01", "10:30", order=(0, 4))
    d = entry("09:45", "09:50", client="acme", description="Other", order=(0, 5))
    rows, warns = merge([a, b, c, d], RULES)
    assert [r.session_id for r in rows] == ["S1", "", ""]
    assert warns == [OVERLAP.format("Acme", 1, 2), OVERLAP.format("Acme", 1, 3),
                     OVERLAP.format("ACME", 2, 3)]


def test_merge_warning_order_unrated_then_overlap():
    """Stage 9: unrated warnings before overlap warnings."""
    a = entry("09:00", "10:00", client="Zed", order=(0, 2))
    b = entry("09:30", "10:30", client="Zed", description="X", order=(0, 3))
    _, warns = merge([a, b], RULES)
    assert [w.split(": ")[2][:7] for w in warns] == ["no rate", "no rate", "overlap"]
