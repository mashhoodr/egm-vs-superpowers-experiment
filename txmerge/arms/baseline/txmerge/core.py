"""Parse bank exports, dedupe overlaps, link transfers, categorise."""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

HEADER_A = ["Date", "Description", "Debit", "Credit", "Balance"]
HEADER_B = ["Transaction Date", "Posting Date", "Details", "Amount"]
RULES_HEADER = ["pattern", "category"]
OUTPUT_HEADER = ["date", "account", "description", "amount", "category", "transfer_id"]
TRANSFER_WINDOW_DAYS = 3
TRANSFER_CATEGORY = "Transfer"
UNCATEGORISED = "Uncategorised"
CENT = Decimal("0.01")


class InputError(Exception):
    """Fatal input problem: the run must stop with exit code 2."""


class RowError(ValueError):
    """A single malformed row: skipped with a warning."""


@dataclass
class Txn:
    date: date
    account: str
    description: str
    amount: Decimal
    arg_index: int  # position of the --account argument it came from
    line_no: int  # 1-based line number in its file
    category: str = ""
    transfer_id: str = ""

    def dedupe_key(self) -> tuple:
        return (self.date, self.amount, normalise_description(self.description))

    def sort_key(self) -> tuple:
        return (self.date, self.account, self.line_no, self.arg_index)


@dataclass
class Rule:
    pattern: str
    category: str
    _needle: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._needle = self.pattern.casefold()

    def matches(self, description: str) -> bool:
        return self._needle in description.casefold()


def normalise_description(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).casefold()


def parse_amount(raw: str) -> Decimal:
    cleaned = raw.strip().replace(",", "").replace(" ", "")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise RowError(f"bad amount {raw!r}") from None
    if not value.is_finite():
        raise RowError(f"bad amount {raw!r}")
    value = value.quantize(CENT, rounding=ROUND_HALF_UP)
    return value if value != 0 else Decimal("0.00")


def parse_date(raw: str, fmt: str) -> date:
    try:
        return datetime.strptime(raw.strip(), fmt).date()
    except ValueError:
        raise RowError(f"bad date {raw!r}") from None


def _row_format_a(row: list[str]) -> tuple[date, str, Decimal]:
    if len(row) != len(HEADER_A):
        raise RowError(f"expected {len(HEADER_A)} fields, got {len(row)}")
    raw_date, desc, debit, credit, _balance = row
    d = parse_date(raw_date, "%d/%m/%Y")
    has_debit, has_credit = bool(debit.strip()), bool(credit.strip())
    if has_debit and has_credit:
        raise RowError("both Debit and Credit filled")
    if not has_debit and not has_credit:
        raise RowError("both Debit and Credit blank")
    if has_debit:
        amount = -abs(parse_amount(debit))
    else:
        amount = abs(parse_amount(credit))
    return d, desc, amount if amount != 0 else Decimal("0.00")


def _row_format_b(row: list[str]) -> tuple[date, str, Decimal]:
    if len(row) != len(HEADER_B):
        raise RowError(f"expected {len(HEADER_B)} fields, got {len(row)}")
    raw_date, _posting, desc, raw_amount = row
    d = parse_date(raw_date, "%Y-%m-%d")
    if not raw_amount.strip():
        raise RowError("blank Amount")
    return d, desc, parse_amount(raw_amount)


def _clean_header(header: list[str]) -> list[str]:
    return [h.strip().lstrip("﻿").strip() for h in header]


def read_export(path: str, account: str, arg_index: int, warn=None) -> list[Txn]:
    """Read one export file. Malformed rows are skipped with a warning."""
    warn = warn or (lambda msg: print(msg, file=sys.stderr))
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.reader(fh))
    except FileNotFoundError:
        raise InputError(f"{path}: file not found") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise InputError(f"{path}: cannot read file ({exc})") from None

    header_idx = next((i for i, r in enumerate(rows) if any(c.strip() for c in r)), None)
    if header_idx is None:
        raise InputError(f"{path}: empty file, no header row")
    header = _clean_header(rows[header_idx])
    if header == HEADER_A:
        parse_row = _row_format_a
    elif header == HEADER_B:
        parse_row = _row_format_b
    else:
        raise InputError(f"{path}: unrecognised header {','.join(header)!r}")

    txns: list[Txn] = []
    for i in range(header_idx + 1, len(rows)):
        row = rows[i]
        line_no = i + 1
        if not any(c.strip() for c in row):
            continue
        try:
            d, desc, amount = parse_row(row)
        except RowError as exc:
            warn(f"warning: {path}:{line_no}: skipped malformed row: {exc}")
            continue
        txns.append(Txn(d, account, desc.strip(), amount, arg_index, line_no))
    return txns


def read_rules(path: str) -> list[Rule]:
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.reader(fh))
    except FileNotFoundError:
        raise InputError(f"{path}: rules file not found") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise InputError(f"{path}: cannot read rules file ({exc})") from None
    if not rows or _clean_header(rows[0]) != RULES_HEADER:
        raise InputError(f"{path}: rules file must have header 'pattern,category'")
    rules = []
    for row in rows[1:]:
        if len(row) < 2 or not row[0].strip():
            continue  # blank or patternless lines would match everything; ignore
        rules.append(Rule(row[0].strip(), row[1].strip()))
    return rules


def dedupe(exports: list[list[Txn]]) -> list[Txn]:
    """Merge exports (in --account argument order).

    Within one account, a key (date, amount, normalised description) is kept
    as many times as the maximum count seen in any single export. The earliest
    occurrences by argument order are the ones kept.
    """
    kept_counts: dict[str, Counter] = defaultdict(Counter)
    result: list[Txn] = []
    for txns in exports:
        seen_in_file: Counter = Counter()
        for t in txns:
            key = t.dedupe_key()
            seen_in_file[key] += 1
            already = kept_counts[t.account]
            if seen_in_file[key] > already[key]:
                already[key] = seen_in_file[key]
                result.append(t)
    return result


def link_transfers(txns: list[Txn]) -> None:
    """Pair outflows with inflows in other accounts. `txns` must be in output order."""
    inflows: dict[Decimal, list[tuple[int, Txn]]] = defaultdict(list)
    for idx, t in enumerate(txns):
        if t.amount > 0:
            inflows[t.amount].append((idx, t))
    used: set[int] = set()
    counter = 0
    for out in txns:
        if out.amount >= 0:
            continue
        best = None
        best_score = None
        for idx, inn in inflows.get(-out.amount, ()):
            if idx in used or inn.account == out.account:
                continue
            gap = abs((inn.date - out.date).days)
            if gap > TRANSFER_WINDOW_DAYS:
                continue
            score = (gap, idx)
            if best_score is None or score < best_score:
                best, best_score = inn, score
        if best is not None:
            counter += 1
            tid = f"T{counter:04d}"
            used.add(best_score[1])
            for leg in (out, best):
                leg.transfer_id = tid
                leg.category = TRANSFER_CATEGORY


def categorise(txns: list[Txn], rules: list[Rule]) -> None:
    for t in txns:
        if t.transfer_id:
            continue
        t.category = next((r.category for r in rules if r.matches(t.description)), UNCATEGORISED)


def build_ledger(exports: list[list[Txn]], rules: list[Rule]) -> list[Txn]:
    txns = sorted(dedupe(exports), key=Txn.sort_key)
    link_transfers(txns)
    categorise(txns, rules)
    return txns


def ledger_rows(txns: list[Txn]) -> list[list[str]]:
    return [
        [t.date.isoformat(), t.account, t.description, f"{t.amount:.2f}", t.category, t.transfer_id]
        for t in txns
    ]
