# QA Report: P&C Index Milestone 1

Date: 2026-04-19
Mode: CLI/data-pipeline QA adapted from `/qa`
Scope: Review findings from `/review`

## Summary

QA found 2 issues and fixed 2.

Health score: 8/10 -> 10/10

## Fixed Issues

### ISSUE-001: Report page metadata used extracted page count

Severity: Medium
Status: verified

The build pipeline stored `reports.page_count` from reconstructed text pages. The PDF has 707 physical pages, while text reconstruction currently returns 665 extracted pages.

Fix:
- Added `source_pdf_page_count()` to read the physical PDF count from the linearized PDF header, with a `/Type /Page` fallback.
- Updated build metadata to store the source page count.
- Rebuilt `data/pnc_market_share.sqlite`.

Files changed:
- `src/pnc_index/pdf_extract.py`
- `src/pnc_index/build.py`
- `tests/test_pdf_extract.py`
- `tests/test_db_validate_cli.py`

Verification:
- `reports.page_count` is now 707.
- CLI build prints `pages=707`.

### ISSUE-002: Validation checked every market_share_records row

Severity: Medium
Status: verified

Validation expected exactly 10 rows across the full `market_share_records` table. That would fail when additional states, lines, or countrywide rows are added.

Fix:
- Scoped validation to Workers Compensation, `state_by_group`, Texas.
- Added regression coverage proving unrelated state rows do not break the Texas validation slice.

Files changed:
- `src/pnc_index/validate.py`
- `tests/test_db_validate_cli.py`

## Verification

Commands run:

```powershell
$env:PYTHONPATH='src'; py -m unittest discover -s tests -v
$env:PYTHONPATH='src'; py -m pnc_index.cli build
$env:PYTHONPATH='src'; py -m pnc_index.cli validate
```

Results:
- 13 tests passed.
- Build passed with 10 records, 0 warnings, 0 errors.
- Validation passed.
- Working SQLite DB stores `page_count=707`.
