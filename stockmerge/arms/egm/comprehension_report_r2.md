# Comprehension Report (Stage 6, re-audit round 2)

**Target:** `docs/designs/stockmerge.md` (FeatureRange 1-514, DetailedRange 515-762 at the time of review)
**Reviewer:** `egm-comprehension` (direct dispatch) — completed

**What this proposes**
`stockmerge` is a standard-library Python command-line tool. It reads several scanner exports (Format A or Format B, detected from the header row) for named locations and turns each row into a `Scan`. Times are cut to the minute, SKUs are normalised and cases are converted to 12 items each. Copies across exports of the same location are removed by keeping, for each scan key, the first N rows in input order, where N is the largest count of that key in any single export. Next it greedily pairs each negative row, taken in scan order, with the nearest opposite positive row that has the same normalised SKU, a different location and is no more than 120 minutes away. Each pair gets a shared `M0001`-style ID and category `Move`. Every other row gets the first rules-file substring match, or `Uncategorised`. Rows are sorted on a complete key and written to a temporary file that is then moved into place with `os.replace`. Bad rows produce warnings and still exit 0. Bad files or arguments exit 2 and leave `--out` untouched. The detailed plan maps this onto 9 package modules, 6 test files and repo metadata.

**How the existing system works, per this document**
A shop counts stock per location with two barcode scanners, and each exports CSV in its own format: A uses DD/MM/YYYY times with a unit of each or case, and B uses ISO times with a signed count and a free-text note. A location is often exported more than once, so the same scan appears in several files. Stock moving between locations shows up as a negative at one location and a positive at another. Today there is no single count: adding the files together double-counts, and looking at each location alone makes moves look like losses. The document also says, but only in Alternative E, that scanner B drops leading zeros from SKUs.

Every section could be paraphrased and the parts connect. No Blockers.

## Findings
- **comprehension-2-1 (Major)** Overview vs Alternative E, R3.4, glossary. "Scanner B drops leading zeros" is stated only in a rejected alternative; state it in the Problem with its source.
- **comprehension-2-2 (Nit)** Alternative A owner quote appears nowhere else.
- **comprehension-2-3 (Nit)** Glossary "Record number" does not say skipped rows use up a number.
- **comprehension-2-4 (Nit)** R4.3 "only empty fields" vs plan "all fields empty after trim".
- **comprehension-2-5 (Nit)** Whether leading blank lines are skipped before the header.
- **comprehension-2-6 (Nit)** Backstop message PATH source unstated.
- **comprehension-2-7 (Nit)** Worked example lacks the output rows and summary line.

## Resolution (Elephant)
All seven fixed in the target: 2-1 added a paragraph to The Problem; 2-2 to 2-7 as described.
