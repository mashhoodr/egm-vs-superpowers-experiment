"""Rule-based categorisation: case-insensitive substring, first match wins."""
import csv

from txmerge.model import InputError

UNCATEGORISED = "Uncategorised"
TRANSFER = "Transfer"


def load_rules(path: str) -> list[tuple[str, str]]:
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh, strict=True)
            header = [c.strip() for c in next(reader, [])]
            if header != ["pattern", "category"]:
                raise InputError(f"{path}: rules header must be 'pattern,category'")
            rules = []
            for row in reader:
                if len(row) < 2 or not row[0].strip() or not row[1].strip():
                    continue
                rules.append((row[0].strip(), row[1].strip()))
            return rules
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc.strerror or exc}") from None
    except csv.Error as exc:
        raise InputError(f"{path}: malformed rules CSV ({exc})") from None
    except UnicodeDecodeError:
        raise InputError(f"cannot read {path}: not UTF-8 text") from None


def categorise(description: str, rules: list[tuple[str, str]]) -> str:
    text = description.casefold()
    for pattern, category in rules:
        if pattern.casefold() in text:
            return category
    return UNCATEGORISED
