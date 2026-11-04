"""Rules file loading and categorisation (R3.1 to R3.5, R7.1)."""

from __future__ import annotations

from dataclasses import dataclass

from stockmerge.model import (
    MOVE_CATEGORY,
    UNCATEGORISED,
    StockmergeError,
    Warnings,
)
from stockmerge.readers import has_bad_bytes, iter_records

RULES_HEADER = ("pattern", "category")


@dataclass(frozen=True)
class Rule:
    pattern: str
    category: str


def load_rules(path: str, warnings: Warnings) -> list[Rule]:
    header, records = iter_records(path)
    if tuple(header) != RULES_HEADER:
        raise StockmergeError(
            f"{path}: rules header must be pattern,category, found: {','.join(header)}"
        )
    rules: list[Rule] = []
    for line_no, raw in records:
        fields = [f.strip() for f in raw]
        if len(fields) != 2:
            warnings.add(path, line_no, f"expected 2 fields, found {len(fields)}")
            continue
        if has_bad_bytes(fields):
            warnings.add(path, line_no, "not valid UTF-8")
            continue
        pattern, category = fields
        if not pattern:
            warnings.add(path, line_no, "blank pattern")
            continue
        if not category:
            warnings.add(path, line_no, "blank category")
            continue
        if pattern.startswith("0"):
            warnings.add(
                path, line_no,
                "pattern starts with 0 and cannot match leading zeros of a SKU",
            )
        if category in (MOVE_CATEGORY, UNCATEGORISED):
            warnings.add(
                path, line_no, f"category {category} is also used by stockmerge itself"
            )
        rules.append(Rule(pattern=pattern.lower(), category=category))
    return rules


def categorise(sku_norm: str, rules: list[Rule]) -> str:
    for rule in rules:
        if rule.pattern in sku_norm:
            return rule.category
    return UNCATEGORISED
