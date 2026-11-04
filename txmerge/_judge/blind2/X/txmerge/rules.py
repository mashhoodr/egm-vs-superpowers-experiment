"""Category rules (D10, D11)."""

from __future__ import annotations

from .model import TxmergeError, warn
from .readers import read_csv

UNCATEGORISED = "Uncategorised"


def load_rules(path: str) -> list[tuple[str, str]]:
    """Return (casefolded pattern, category) pairs in file order."""
    lines = read_csv(path)
    header = [c.strip() for c in lines[0][1]]
    if header != ["pattern", "category"]:
        raise TxmergeError(f"{path}: header must be pattern,category")
    rules: list[tuple[str, str]] = []
    for line_no, cells in lines[1:]:
        if len(cells) != 2:
            warn(path, line_no, f"expected 2 cells, got {len(cells)}", what="rule")
            continue
        pattern, category = cells[0].strip(), cells[1].strip()
        if not pattern:
            warn(path, line_no, "blank pattern", what="rule")
            continue
        if not category:
            warn(path, line_no, "blank category", what="rule")
            continue
        rules.append((pattern.casefold(), category))
    return rules


def categorise(description: str, rules: list[tuple[str, str]]) -> str:
    folded = description.casefold()
    for pattern, category in rules:
        if pattern in folded:
            return category
    return UNCATEGORISED
