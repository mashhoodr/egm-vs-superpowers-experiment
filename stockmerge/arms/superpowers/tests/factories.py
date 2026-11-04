from datetime import datetime

from stockmerge.model import Scan, sku_key


def make_scan(**overrides) -> Scan:
    fields = dict(location="shop", export_index=0, line=2, sku_text="A1",
                  minute=datetime(2026, 3, 5, 14, 30), qty_each=1)
    fields.update(overrides)
    fields.setdefault("sku_key", sku_key(fields["sku_text"]))
    return Scan(**fields)
