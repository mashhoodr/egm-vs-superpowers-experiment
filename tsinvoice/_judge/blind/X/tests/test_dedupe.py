from tests.factories import entry
from tsinvoice.dedupe import dedupe


def e(arg_index, line, tracker="desktop", client="Acme", description="Design",
      start="2026-03-02T09:00", minutes=30):
    return entry(start, minutes, client=client, description=description,
                 tracker=tracker, arg_index=arg_index, line=line)


def test_same_entry_twice_in_one_file_is_kept_twice():
    assert len(dedupe([e(0, 2), e(0, 3)])) == 2


def test_across_exports_of_one_tracker_keep_max_count():
    entries = [e(0, 2), e(0, 3), e(1, 2), e(1, 3), e(1, 4)]
    kept = dedupe(entries)
    assert len(kept) == 3
    assert [x.order for x in kept] == [(0, 2), (0, 3), (1, 4)]


def test_max_count_when_larger_export_comes_first():
    assert len(dedupe([e(0, 2), e(0, 3), e(0, 4), e(1, 2)])) == 3


def test_match_uses_normalised_text():
    kept = dedupe([e(0, 2, client="Acme", description="Design  work"),
                   e(1, 2, client=" ACME ", description="design work")])
    assert len(kept) == 1
    assert kept[0].order == (0, 2)


def test_different_trackers_never_dedupe():
    assert len(dedupe([e(0, 2, tracker="desktop"), e(1, 2, tracker="phone")])) == 2


def test_different_times_are_not_duplicates():
    assert len(dedupe([e(0, 2), e(1, 2, minutes=31)])) == 2
    assert len(dedupe([e(0, 2), e(1, 2, start="2026-03-02T09:01")])) == 2


def test_output_is_in_input_order_regardless_of_given_order():
    kept = dedupe([e(1, 5, start="2026-03-02T08:00"), e(0, 9, start="2026-03-02T10:00")])
    assert [x.order for x in kept] == [(0, 9), (1, 5)]
