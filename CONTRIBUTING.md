# Contributing

This is a small Python data-extraction project. Keep changes scoped and preserve row-level traceability back to the PDF.

## Local Setup

Use Python 3.11 or newer.

No third-party packages are required for Milestone 1.

Set `PYTHONPATH` before running commands from the repo root:

```powershell
$env:PYTHONPATH='src'
```

The source PDF should be available locally at:

```text
artifacts/publication-msr-pb-property-casualty.pdf
```

The PDF is ignored by git. Markdown notes under `artifacts/` are intended to be tracked.

## Test Commands

Run the full suite:

```powershell
$env:PYTHONPATH='src'
py -m unittest discover -s tests -v
```

Build and validate the generated SQLite database:

```powershell
$env:PYTHONPATH='src'
py -m pnc_index.cli build
py -m pnc_index.cli validate
```

Query the implemented slice:

```powershell
$env:PYTHONPATH='src'
py -m pnc_index.cli top-carriers --state Texas --line "Workers Compensation"
```

## Development Rules

- Keep generated files out of git. `data/`, SQLite files, Python caches, and source PDFs are ignored.
- Preserve `source_page`, `source_text_hash`, and `raw_row_text` for parsed records.
- Add regression tests for parser or validation changes.
- Do not broaden parsing scope and data model scope in the same change unless the tests cover the new grain.
- Prefer deterministic parsing and validation before fuzzy search or embeddings.

## Current Milestone Boundary

Milestone 1 supports only:

```text
Workers Compensation + Texas + BY STATE BY GROUP
```

If you expand beyond this, update:

- `README.md`
- `ARCHITECTURE.md`
- `artifacts/pnc_carrier_index_plan.md`
- `artifacts/pnc_carrier_index_test_plan.md`

## Useful Docs

- `README.md`: user-facing setup, CLI usage, current limitations
- `ARCHITECTURE.md`: data flow, module responsibilities, data model notes
- `artifacts/pnc_market_share_report_structure.md`: PDF structure notes
- `artifacts/pnc_carrier_index_plan.md`: implementation plan
- `artifacts/pnc_carrier_index_test_plan.md`: test plan
