# Goldfish Review Report

**Target:** `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers/arms/egm2/docs/designs/txmerge.md` (`1-701`)

Stage 8, Intermediate Zoom Out Review. Two independent instances (A and B) of `egm-zoom-out` were run against `zoom-out-standard.md`. The prior Stage 5 report (`zoom_out_report_r2.md`) was given as context. Both instances judged the design **pass with changes**. The core pipeline (read, dedup, sort, pair, categorise, write) is still the simplest design that meets the brief. Almost all of the new complexity sits in D23.

Severity breakdown: 0 Blocker, 1 Major, 5 Nit.

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-zoom-out` (instance A) | completed |
| `egm-zoom-out` (instance B) | completed |

## Prioritized Findings (Blockers -> Major -> Nits)

### zoom-out-3-1: D23 atomic write has grown extra machinery, and Alternative J is rejected for a circular reason - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (A and B agree)
* **Affected Scope:** Lines 126 (last sentence of D13), 136 (D23), 222-226, 425-435 (Alternative J), 443, 457 (R7), 554-565 (`write_ledger`), 663-669 (test_cli D23 tests)
* **Discrepancy Description**:
  * Neither instance re-argues zoom-out-2-1. The temp-file-plus-`os.replace` core is accepted as a designer (E) choice.
  * What is new since Stage 5: the design dealt with the two side effects Stage 5 named by adding code to undo each one, instead of accepting them. It added:
    * `realpath` to follow a symlink at `--out` and keep the link;
    * mode preservation through `shutil.copymode`, or `0o666 & ~umask`, with the umask read by changing process-global state (`os.umask(0); os.umask(old)`);
    * a `BaseException` handler that cleans up on Ctrl-C;
    * a paragraph explaining the `fsync` decision;
    * dedicated mid-write-failure and symlink end-to-end tests.
  * Neither BRIEF.md nor any (S) ruling asks for symlink behaviour or mode preservation on a single-user personal ledger.
  * **Circular justification:** Alternative J is rejected because "D13 promises every exit-2 run leaves an existing ledger unchanged" (432-433). That D13 clause (126, marked "E (rest)") is itself a designer choice, written together with D23. The stakeholder ruling only requires that a file-level input error writes no output file. Lines 222-223 already meet that, because every check runs before anything is written. The ledger can always be rebuilt (D20; 445, "Rollback: None needed").
  * **A design rule shaped by a test:** line 559 ("`ledger.py` does `import csv`") exists only so the test at 663-665 can monkeypatch `ledger.csv.writer`.
* **Rationale & Recommendation**:
  * Reduce D23 to one sentence: "write to a temp file in the same directory, `os.replace` onto `--out`, remove the temp file on any failure (`OSError`)".
  * Accept the side effects in one line each:
    * a new ledger gets mode 0600, a reasonable default for bank data;
    * a symlink at `--out` is replaced by a regular file.
  * Drop the following: `realpath`, copymode and umask steps, the `BaseException`/Ctrl-C clause, the `fsync` paragraph, and the symlink test (668-669).
  * Mark D13's write-failure sentence plainly as an E choice. Restate Alternative J's rejection with its real reason ("designer prefers that a disk-full or kill mid-write does not destroy the previous ledger"), without citing D13 as if it were a requirement.
  * Remove the "`ledger.py` does `import csv`" sentence. Describe the failure test by behaviour: the old ledger is intact and no temp file is left. Let the implementer choose the injection point (for example an unwritable directory or a read-only target).
  * Update R7 (457) to match.
  * Instance A notes that writing `--out` directly after all checks (the Stage 5 recommendation) is still acceptable too. The middle layer of extra machinery is the part to remove.

### zoom-out-3-2: Library-level detail grew in `write_ledger` (zoom-out-2-3 got worse) - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:** Lines 554-565 (`write_ledger`), 239 (`csv.reader.line_num`), 249 (`strptime`), 543 (no set iteration)
* **Discrepancy Description**: Stage 5 asked for library calls to move out of the design. Lines 239, 249 and 543 are unchanged. The `write_ledger` entry has grown into pseudocode that spells out `mkstemp` arguments, the umask trick, the try/except structure and the re-raise policy.
* **Rationale & Recommendation**: Describe `write_ledger` by its contract: signature, "implements D21 and D23", "raises `TxmergeError` on `OSError`". Leave the call sequence to the code. Cleaning up 239, 249 and 543 is optional. The test-coupling part is covered in zoom-out-3-1.

### zoom-out-3-3: D20 same-file check spells out edge-case mechanics, and its pipeline position is stated two ways - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B agree)
* **Affected Scope:** Lines 133 (D20), 212 (data-flow diagram), 638-641 (`cli.main` order)
* **Discrepancy Description**: Both instances judge the guard itself proportionate. It is cheap, and it stops a `--out cur.csv` typo from destroying an export (brief want 1).
  * D20 spends most of its length on mechanics: the "if `--out` does not exist it cannot be an input" note, and a rule for `os.path.samefile` raising `OSError`. That rule covers a near-impossible race, since every input has just been read successfully.
  * The diagram puts the check after `categorise`, just before `write_ledger` (212). `cli.main` runs it right after reading, before dedup (639-640). Both satisfy D20's wording, but a reader cannot tell which order is intended.
* **Rationale & Recommendation**:
  * Cut the clause to "if `--out` is the same file as any input or the rules file, exit 2 ('--out is also an input')". Drop the `OSError` sentence, or reduce it to "any `OSError` is a cannot-read error".
  * Pick one position. Right after reading is simplest. Make the diagram match `cli.main`.

### zoom-out-3-4: D24 trims whitespace from PATH, which nobody asked for - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (instance A; instance B judged D24 proportionate overall)
* **Affected Scope:** Lines 137 (D24), 325 (Messages qualifier), 671-672 (` cur = x.csv ` test)
* **Discrepancy Description**: Splitting on the first `=` is the minimal rule the brief's `NAME=PATH` syntax needs. Trimming outer whitespace from PATH is invented: a real file name can start or end with a space. It also forces the "after the trimming in D24" qualifier at 325 and an extra test.
* **Rationale & Recommendation**: Split on the first `=` and trim only NAME, or trim neither. Then drop the qualifier at 325 and the ` cur = x.csv ` test case.

### zoom-out-3-5: Summary still shapes the `read_export` interface and CUJ 1 (zoom-out-2-5 still open); Messages precedence rule - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B on 2-5; B only on the precedence rule)
* **Affected Scope:** Lines 506-507 (`read_export` return type), 150-151 (CUJ 1 "Then"), 337-343 (Counts paragraph), 311-315 (Messages preamble)
* **Discrepancy Description**:
  * `read_export` still returns `tuple[list[Row], int]` only to feed the skip count `S`.
  * CUJ 1 still uses the summary line as an acceptance criterion, although the stakeholder left success output as "your call".
  * Instance B adds a point: the Messages preamble rule "if any quote elsewhere differs, this section wins" is only needed because message text is quoted in several places. Instance A judged the same rule sensible. Both judge the Messages table itself proportionate.
* **Rationale & Recommendation**:
  * Count skips where warnings are already emitted, and return `list[Row]` from `read_export`.
  * Remove the summary from CUJ 1's "Then".
  * Optionally, replace quoted message text elsewhere with references to table rows, which makes the precedence rule unnecessary.

### zoom-out-3-6: Amount index in pairing still present (zoom-out-2-6 still open) - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (instance A; instance B noted it unchanged and chose not to raise it again)
* **Affected Scope:** Lines 276-278
* **Discrepancy Description**: Pairing still builds an index from amount to inflows. For personal-scale inputs this is premature optimisation.
* **Rationale & Recommendation**: Optional. Accept or decline it explicitly in the review record so it is not raised again.

## Additions Judged Proportionate (no finding)

* **Fixed-formats table (101-108):** restates the BRIEF contract in one place, as the Overview (27-30) promises. Adds no behaviour.
* **D24 core rule (137, 633-637):** splitting on the first `=` with argparse `type=` is the minimal parse rule. Only the PATH trim is flagged (zoom-out-3-4).
* **Messages section (309-343):** exact wording supports byte-exact and stderr tests.
* **Risks & Mitigations R1-R8 (447-458):** documentation only. It records accepted consequences of settled rulings and builds nothing. R7 should follow any change to D23.
* **D14 check order (127):** needed so a warning's `REASON` is deterministic.
* **Alternative J (425-435):** belongs in the document. Only its rationale needs rewording (zoom-out-3-1).
* **D20 guard itself:** proportionate (zoom-out-3-3 covers the wording only).

## Stage 5 Findings Status

| Stage 5 id | Status |
| --- | --- |
| zoom-out-2-1 (atomic write) | Reversed for a stated reason. The extra machinery is now excessive (zoom-out-3-1). |
| zoom-out-2-2 (date rule) | Addressed in D14. |
| zoom-out-2-3 (library detail) | Not addressed, and worse at 554-565 (zoom-out-3-2). |
| zoom-out-2-4 (T10000 test) | Addressed (612-613). |
| zoom-out-2-5 (summary in reader signature and CUJ 1) | Not addressed (zoom-out-3-5). |
| zoom-out-2-6 (amount index) | Not addressed (zoom-out-3-6). |

No finding asks to change BRIEF.md or reopen a stakeholder (S) ruling.
