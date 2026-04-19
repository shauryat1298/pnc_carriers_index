# P&C Market Share Index

Python prototype for extracting and indexing carrier market-share data from the NAIC property/casualty market share PDF.

Milestone 1 is implemented for one validated slice:

```text
Line:  Workers Compensation
State: Texas
Scope: BY STATE BY GROUP
Rows:  Top 10 ranked carrier groups
```

The current index is factual retrieval only. It does not yet recommend carriers or infer underwriting appetite.

## What Is Included

- Source PDF structure notes in `artifacts/pnc_market_share_report_structure.md`
- Product and extraction plan in `artifacts/pnc_carrier_index_plan.md`
- Milestone 1 test plan in `artifacts/pnc_carrier_index_test_plan.md`
- Stdlib-only PDF text extraction for this NAIC PDF
- Workers Compensation section detection
- Texas BY STATE BY GROUP row parsing
- SQLite schema and loader
- CLI commands to build, validate, and query the local index
- Unittest coverage for extraction, section detection, parsing, DB loading, validation, and CLI behavior

## Repository Layout

```text
src/pnc_index/
  build.py          Build the Milestone 1 SQLite index
  cli.py            Command-line interface
  db.py             SQLite schema, seed data, load/query helpers
  pdf_extract.py    Narrow PDF stream extractor for the NAIC source PDF
  section_detect.py Workers Compensation section detection
  table_parse.py    Texas Workers Compensation row parser
  validate.py       Milestone 1 validation checks

tests/              Unittest suite
artifacts/          Markdown plans/structure notes; source PDF is gitignored
data/               Generated SQLite DB; gitignored
```

## Setup

Use Python 3.11 or newer. No third-party packages are required for Milestone 1.

On this Windows workspace, `py` is the working Python launcher:

```powershell
$env:PYTHONPATH='src'
py -m unittest discover -s tests -v
```

The source PDF is expected at:

```text
artifacts/publication-msr-pb-property-casualty.pdf
```

The PDF is intentionally ignored by git because it is a large source artifact.

## CLI Usage

Build the local SQLite index:

```powershell
$env:PYTHONPATH='src'
py -m pnc_index.cli build
```

Validate the index:

```powershell
$env:PYTHONPATH='src'
py -m pnc_index.cli validate
```

Query top carriers:

```powershell
$env:PYTHONPATH='src'
py -m pnc_index.cli top-carriers --state Texas --line "Workers Compensation"
```

The default database path is:

```text
data/pnc_market_share.sqlite
```

## Current Output

The Texas Workers Compensation query returns ranked rows with:

- rank
- carrier/group code
- carrier/group display name
- direct written premium, in thousands
- direct earned premium, in thousands
- market share percentage
- cumulative market share percentage
- loss ratio percentage
- loss and cost containment ratio percentage
- source report page

The current source PDF has 707 physical pages. The custom extractor reconstructs text-bearing report pages separately, so the database stores the physical PDF page count in `reports.page_count` and row-level source page labels in `market_share_records.source_page`.

## Limitations

- Only Texas Workers Compensation BY STATE BY GROUP rows are loaded.
- Group/company affiliation index extraction is not implemented yet.
- No FTS search index is implemented yet.
- No carrier recommendation or appetite scoring exists yet.
- The PDF extractor is intentionally narrow and tuned for this NAIC report, not a general-purpose PDF parser.

## Next Milestones

1. Expand Workers Compensation parsing from Texas to all state/jurisdiction blocks.
2. Add validation for jurisdiction counts, state totals, and parser warnings.
3. Parse the group/company index section.
4. Add SQLite FTS5 search over carriers, groups, companies, lines, and jurisdictions.
5. Design retrieval features for later carrier suitability ranking.
