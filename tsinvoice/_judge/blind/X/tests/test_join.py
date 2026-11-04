from datetime import date

from tests.factories import entry
from tsinvoice.join import join


def orders(sessions):
    return [[x.order for x in s.entries] for s in sessions]


def test_back_to_back_entries_join_across_trackers():
    a = entry("2026-03-02T09:00", 7, tracker="desktop", arg_index=0, line=2)
    b = entry("2026-03-02T09:07", 7, tracker="phone", arg_index=1, line=2)
    (s,) = join([a, b])
    assert s.entries == [a, b]
    assert s.raw_minutes == 14 and s.minutes == 18


def test_gap_of_two_minutes_joins_three_does_not():
    a = entry("2026-03-02T09:00", 30, line=2)
    b = entry("2026-03-02T09:32", 30, line=3)   # gap 2 -> joins
    c = entry("2026-03-02T10:05", 30, line=4)   # gap 3 -> separate
    assert orders(join([a, b, c])) == [[(0, 2), (0, 3)], [(0, 4)]]


def test_gap_measured_in_seconds():
    a = entry("2026-03-02T09:00:00", 30, line=2)
    b = entry("2026-03-02T09:32:01", 30, line=3)  # gap 2m01s -> separate
    assert len(join([a, b])) == 2


def test_overlap_never_joins():
    a = entry("2026-03-02T09:00", 60, line=2)
    b = entry("2026-03-02T09:59", 30, line=3)
    assert len(join([a, b])) == 2


def test_client_and_description_must_match_normalised():
    a = entry("2026-03-02T09:00", 30, client="Acme", description="Design", line=2)
    b = entry("2026-03-02T09:30", 30, client=" ACME", description="design", line=3)
    c = entry("2026-03-02T10:00", 30, client="Acme", description="Review", line=4)
    assert orders(join([a, b, c])) == [[(0, 2), (0, 3)], [(0, 4)]]


def test_long_chain_is_one_session():
    es = [entry(f"2026-03-02T{9 + i:02d}:00", 60, line=2 + i) for i in range(4)]
    (s,) = join(list(reversed(es)))
    assert s.entries == es
    assert s.minutes == 240


def test_smallest_gap_wins_then_input_order():
    p = entry("2026-03-02T09:00", 60, arg_index=0, line=2)
    far = entry("2026-03-02T10:02", 10, arg_index=0, line=3)
    near_late = entry("2026-03-02T10:01", 10, arg_index=1, line=2)
    near_early = entry("2026-03-02T10:01", 10, arg_index=0, line=4)
    sessions = join([p, far, near_late, near_early])
    assert sessions[0].entries == [p, near_early]
    # the losers stay separate sessions
    assert sorted(len(s.entries) for s in sessions) == [1, 1, 2]


def test_earlier_session_gets_first_pick():
    p1 = entry("2026-03-02T08:00", 120, arg_index=0, line=2)  # ends 10:00
    p2 = entry("2026-03-02T09:00", 60, arg_index=1, line=2)   # ends 10:00
    q = entry("2026-03-02T10:00", 30, arg_index=0, line=3)
    sessions = join([q, p2, p1])
    assert sessions[0].entries == [p1, q]
    assert sessions[1].entries == [p2]


def test_same_start_tie_broken_by_input_order():
    p1 = entry("2026-03-02T09:00", 60, arg_index=1, line=2)
    p2 = entry("2026-03-02T09:00", 60, arg_index=0, line=5)
    q = entry("2026-03-02T10:00", 30, arg_index=0, line=9)
    sessions = join([p1, p2, q])
    assert sessions[0].entries == [p2, q]


def test_join_across_midnight_keeps_start_date():
    a = entry("2026-03-02T23:50", 10, line=2)
    b = entry("2026-03-03T00:01", 9, line=3)
    (s,) = join([a, b])
    assert s.date == date(2026, 3, 2)
    assert s.minutes == 24  # 19 rounded up to 24


def test_empty_input():
    assert join([]) == []
