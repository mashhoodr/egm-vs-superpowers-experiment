# Brief: `txmerge` — merge overlapping bank exports into one ledger

> This is the only document every arm receives. Product questions go to the
> stakeholder (see your arm instructions). Do not read anything under `_judge/`.

## The problem
I download CSV exports from my bank accounts every few weeks. The date ranges
overlap, so the same transaction shows up in more than one export. I also move
money between my own accounts, which looks like spending in one account and
income in another. I want one clean, categorised ledger.

## Fixed contract (the acceptance tests rely on this, don't change it)

- Python 3.11+, standard library only at runtime. `pytest` allowed for tests.
- Package lives in `txmerge/` at your repo root and runs as:

```
python -m txmerge merge \
  --account NAME=PATH [--account NAME=PATH ...] \
  --rules RULES.csv \
  --out LEDGER.csv
```

  `--account` may repeat, and the same NAME may appear with several PATHs
  (several exports of one account).

- **Input formats.** The format is detected from the header row.
  - **Format A (current account):** header `Date,Description,Debit,Credit,Balance`.
    Date is `DD/MM/YYYY`. Debit/Credit are positive numbers or blank and may
    contain thousands separators (`1,250.00`).
  - **Format B (credit card):** header `Transaction Date,Posting Date,Details,Amount`.
    Dates are `YYYY-MM-DD`. Amount is signed: negative = spend, positive = refund/payment.
- **Rules file:** CSV with header `pattern,category`.
- **Output:** CSV with header exactly
  `date,account,description,amount,category,transfer_id`
  - `date` ISO `YYYY-MM-DD`; `amount` signed (outflow negative), 2 decimals;
    `transfer_id` blank unless the row is part of a transfer.
- Exit code 0 on success.

## What I want
1. Duplicates from overlapping exports removed — but never lose a real transaction.
2. Transfers between my own accounts recognised and linked, not counted as spending.
3. Everything else categorised by my rules.
4. Running it again on the same inputs gives the same output.

The rest is yours to design, and to ask me about.
