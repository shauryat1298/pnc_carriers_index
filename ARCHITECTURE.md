# Architecture

This project turns a specific NAIC P&C market share PDF into a queryable local SQLite index.

The architecture is deliberately small for Milestone 1. It proves one complete extraction path before expanding to every line of business, state, group, and company.

## Milestone 1 Data Flow

```text
Source PDF
  -> PDF stream extraction
  -> report page reconstruction
  -> Workers Compensation section detection
  -> Texas BY STATE BY GROUP segment parsing
  -> normalized SQLite load
  -> validation checks
  -> CLI retrieval
```

## Components

### `pdf_extract.py`

Reads the source PDF bytes directly and extracts text from Flate-compressed PDF streams. This avoids third-party PDF dependencies for the first milestone.

Responsibilities:

- detect missing PDFs with a clear error
- decompress PDF streams
- decode simple `Tj` and `TJ` text operators
- reconstruct text-bearing report pages
- compute page text hashes for traceability
- read the physical source PDF page count

The extractor is intentionally narrow. It is not a general PDF parser.

### `section_detect.py`

Finds the Workers Compensation section by matching normalized page text. It explicitly avoids confusing `Workers Compensation` with `Excess Workers Compensation`.

### `table_parse.py`

Parses the Texas BY STATE BY GROUP ranked rows from the Workers Compensation section.

It handles current PDF artifacts such as:

- spaced or wrapped carrier names
- comma-formatted premium values
- percent values with spacing artifacts
- `N/A` loss-ratio values

The parser returns structured records plus parser warnings.

### `db.py`

Defines and loads the SQLite schema.

Current tables:

- `reports`
- `lines_of_business`
- `geography_scopes`
- `jurisdictions`
- `extraction_runs`
- `market_share_records`
- `parser_warnings`
- `validation_results`

The schema already has room for multi-line, multi-state data through line, geography, and jurisdiction foreign keys. Group/company affiliation tables are planned but not implemented.

### `build.py`

Coordinates the Milestone 1 build:

```text
extract pages -> parse Texas rows -> initialize DB -> load rows -> record extraction run
```

The generated SQLite database is runtime output and is ignored by git.

### `validate.py`

Runs data-quality checks for the currently implemented slice:

```text
Workers Compensation + state_by_group + Texas
```

Validation checks that Texas rows exist, row count is 10, ranks are unique and sequential, written premiums and source pages are present, state total rows are excluded, and parser errors are absent.

### `cli.py`

Provides the local command interface:

- `build`
- `validate`
- `top-carriers`

## Data Model Notes

The core fact table is `market_share_records`. Its grain is:

```text
report + line_of_business + geography_scope + jurisdiction + rank
```

Each record stores both structured metrics and traceability fields:

- `source_page`
- `source_text_hash`
- `raw_row_text`
- `parse_confidence`

This is important because PDF extraction defects should be auditable row by row.

## Testing Strategy

Tests use Python `unittest` and the real source PDF when present locally.

Coverage currently includes:

- valid and missing PDF extraction paths
- physical PDF page count detection
- Workers Compensation section detection
- guard against Excess Workers Compensation false matches
- Texas top 10 parsing and metric extraction
- wrapped name and `N/A` ratio handling
- DB build/load/query flow
- validation failure for missing source pages
- validation scoping when unrelated jurisdiction rows exist
- CLI build, validate, and query behavior

## Expansion Path

The next architectural step is to generalize the state-level parser within Workers Compensation before parsing every line of business. That keeps the parser risk bounded while preserving the final schema.

Recommended order:

1. Parse all Workers Compensation state/jurisdiction blocks.
2. Add parser warning summaries and state-level row count validation.
3. Parse countrywide Workers Compensation blocks.
4. Extract group/company affiliation index.
5. Add FTS5 search tables.
6. Add carrier retrieval features for later matching.
