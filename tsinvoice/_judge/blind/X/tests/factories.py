from datetime import datetime, timedelta

from tsinvoice.model import Entry


def entry(start, minutes, client="Acme", description="Design",
          tracker="desktop", arg_index=0, line=2):
    st = datetime.fromisoformat(start)
    return Entry(tracker=tracker, arg_index=arg_index, line=line,
                 client=client, description=description,
                 start=st, end=st + timedelta(minutes=minutes),
                 minutes=minutes)
