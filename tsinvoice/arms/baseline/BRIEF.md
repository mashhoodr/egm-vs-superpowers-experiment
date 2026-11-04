# Brief: `tsinvoice` — merge overlapping timesheet exports into invoice-ready sessions

> This is the only document every arm receives. Product questions go to the
> stakeholder (see your arm instructions). Do not read anything under `_judge/`.

## The problem
I'm a freelancer and I track my time in two apps. I export CSVs from both every
couple of weeks. The date ranges overlap, so the same entry shows up in more
than one export. Sometimes I start an entry in one app and carry on in the
other, so one piece of work ends up as two entries back to back. I want one
clean list of sessions per client, priced and ready to invoice.

## Fixed contract (the acceptance tests rely on this, don't change it)

- Python 3.11+, standard library only at runtime. `pytest` allowed for tests.
- Package lives in `tsinvoice/` at your repo root and runs as:

```
python -m tsinvoice merge \
  --tracker NAME=PATH [--tracker NAME=PATH ...] \
  --rates RATES.csv \
  --out SESSIONS.csv
```

  `--tracker` may repeat, and the same NAME may appear with several PATHs
  (several exports of one tracker).

- **Input formats.** The format is detected from the header row.
  - **Format A (desktop app):** header `Client,Description,Start,End`.
    Start and End are `DD/MM/YYYY HH:MM`.
  - **Format B (phone app):** header `client,task,start_iso,duration_minutes`.
    `start_iso` is an ISO 8601 datetime; `duration_minutes` is a number.
- **Rates file:** CSV with header `pattern,hourly_rate`. A pattern is matched
  against the client and the description.
- **Output:** CSV with header exactly
  `date,client,description,minutes,amount,session_id`
  - `date` ISO `YYYY-MM-DD`; `minutes` a whole number; `amount` is the
    minutes priced at the matching hourly rate, 2 decimals;
    `session_id` blank unless the row was joined from several entries.
- Exit code 0 on success.

## What I want
1. Duplicates from overlapping exports removed — but never lose real time I worked.
2. Entries I continued in the other app (or the same one) recognised and joined into one session.
3. Everything priced by my rates.
4. Running it again on the same inputs gives the same output.

The rest is yours to design, and to ask me about.
