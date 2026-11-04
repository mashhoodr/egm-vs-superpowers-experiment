"""Load categorisation rules and apply them to SKUs."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Callable

from stockmerge.model import FatalError, sku_key
from stockmerge.readers import read_text, split_line, split_lines, strip_empty_tail

UNCATEGORISED = "Uncategorised"


@dataclass(frozen=True)
class Rule:
    pattern: str
    category: str


def load_rules(path: str, warn: Callable[[str], None]) -> list[Rule]:
    lines = list(enumerate(split_lines(read_text(path)), start=1))
    header, start = None, len(lines)
    for position, (_, text) in enumerate(lines):
        try:
            fields = split_line(text)
        except csv.Error:
            break
        if any(f.strip() for f in fields):
            header = [f.strip().casefold() for f in strip_empty_tail(fields, 2)]
            start = position + 1
            break
    if header != ["pattern", "category"]:
        raise FatalError(f"{path}: rules header must be pattern,category")
    rules: list[Rule] = []
    for line, text in lines[start:]:
        try:
            fields = split_line(text)
        except csv.Error as exc:
            warn(f"warning: {path}:{line}: unreadable row ({exc})")
            continue
        if not any(f.strip() for f in fields):
            continue
        fields = strip_empty_tail(fields, 2)
        if len(fields) != 2:
            warn(f"warning: {path}:{line}: expected 2 fields, got {len(fields)}")
            continue
        pattern, category = (f.strip() for f in fields)
        if not pattern or not category:
            warn(f"warning: {path}:{line}: blank pattern or category")
            continue
        rules.append(Rule(pattern.casefold(), category))
    return rules


def categorise(sku_text: str, rules: list[Rule]) -> str:
    """First rule whose pattern is a substring of the normalised or the raw trimmed SKU."""
    normalised = sku_key(sku_text)
    raw = sku_text.strip().casefold()
    for rule in rules:
        if rule.pattern in normalised or rule.pattern in raw:
            return rule.category
    return UNCATEGORISED
