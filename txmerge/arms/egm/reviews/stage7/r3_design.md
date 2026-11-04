# Stage 7 R3 egm-design (completed): 0 Blocker, 1 Major, 4 Nit
M1 unterminated quote with default strict=False swallows rest of file into one field -> one warning, rows lost, exit 0. Verified in scratchpad (Python 3.13): strict=False returns the field; strict=True raises "unexpected end of data".
N2 whole-file fatal on encoding/csv error not logged as decision; field_size_limit. N3 bisect window; memory estimate basis. N4 G4 depends on Python Unicode tables. N5 same file under two names can create false transfers; add risk or warn.
