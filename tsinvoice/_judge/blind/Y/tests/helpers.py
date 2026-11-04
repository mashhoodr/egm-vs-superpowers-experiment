from datetime import datetime

from tsinvoice.model import Entry, normalise


def dt(hm, day="2026-10-08"):
    return datetime.fromisoformat(f"{day} {hm}")


def entry(start, end, client="Acme", description="Design", tracker="desk",
          order=(0, 2), day="2026-10-08"):
    s, e = dt(start, day), dt(end, day)
    return Entry(
        tracker=tracker, order=order, path=f"{tracker}.csv", line=order[1],
        client=client, description=description,
        client_key=normalise(client), desc_key=normalise(description),
        start=s, end=e, minutes=int((e - s).total_seconds()) // 60,
    )
