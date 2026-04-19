# P&C Carrier Market Share Index Plan

Source PDF: `artifacts/publication-msr-pb-property-casualty.pdf`

Related structure notes: `artifacts/pnc_market_share_report_structure.md`

Status: Milestone 1 implemented

Engineering review status: Reviewed by `/plan-eng-review`; see `GSTACK REVIEW REPORT` at the end.

Implementation status:

- Milestone 1 locked scope implemented.
- Build command works: `python -m pnc_index.cli build`.
- Validation command works: `python -m pnc_index.cli validate`.
- Query command works: `python -m pnc_index.cli top-carriers --state Texas --line "Workers Compensation"`.
- Test suite passes with `python -m unittest discover -s tests -v`.

## Goal

Build a Python-based searchable index from the NAIC P&C market share PDF.

The first version should answer factual retrieval questions, not make carrier recommendations yet. It should let you retrieve carriers, insurer groups, daughter companies, unaffiliated companies, and their meaningful market-share metrics by line of business and geography.

Example first-class queries:

- `Top carriers for workers compensation in Texas`
- `Top carriers for commercial auto liability in California`
- `Show every state and line where Travelers appears`
- `Resolve this daughter company to its parent group`
- `Given state + requested policy lines, return carriers with rank, premium, share, and loss metrics`

## Core Premises

1. The PDF is a market-presence source, not a carrier-appetite source.
2. The first index should preserve factual metrics before inventing any matching score.
3. The market-share rows are mostly group-level records.
4. The end index must connect group-level rows to daughter companies and unaffiliated companies.
5. State and line-of-business filtering is the highest-value retrieval path for the first version.
6. Search should be deterministic first. Fuzzy search and embeddings can come later.

## Recommended Approach

Use the ideal architecture, but ship it in minimal milestones:

1. Python extraction pipeline.
2. Normalized SQLite database.
3. SQLite FTS5 search index.
4. CLI query interface.
5. Later, a FastAPI service or UI can sit on top of the same database.

SQLite is enough for the first version because the dataset is small, local, inspectable, and easy to validate. If analysis grows later, DuckDB can be added for analytical queries without changing the extraction model much.

## Locked Milestone 1 Scope

Milestone 1 is the only implementation scope approved by this plan.

Build only enough system to prove this workflow:

```text
Input: Workers Compensation + Texas
Output: top state-level carrier rows with rank, market share, premiums, loss ratio, and source page
```

Milestone 1 should not implement every module in the final file layout. It should create the smallest version of the pipeline that preserves the final data model and can grow without a rewrite:

```text
PDF pages
  -> page text/layout extraction
  -> Workers Compensation section detection
  -> Texas BY STATE BY GROUP row parsing
  -> SQLite load
  -> top-carriers CLI query
  -> validation report
```

Implementation gates:

1. Do not parse all lines until Workers Compensation/Texas is validated against the PDF.
2. Do not parse the full group/company index until at least one market-share section parses reliably.
3. Do not build API/UI until the CLI and database are validated.
4. Do not add recommendation scoring in this phase.

ASCII data-flow diagram to keep in the implementation docs:

```text
        +------------------+
        |  Source PDF      |
        +---------+--------+
                  |
                  v
        +------------------+
        | Page extraction  |
        | text + coords    |
        +---------+--------+
                  |
                  v
        +------------------+
        | Section detector |
        | Workers Comp     |
        +---------+--------+
                  |
                  v
        +------------------+
        | Row parser       |
        | TX top 10        |
        +---------+--------+
                  |
                  v
        +------------------+
        | SQLite facts     |
        +---------+--------+
                  |
                  v
        +------------------+
        | CLI retrieval    |
        +------------------+
```

## Data Model

### `reports`

One row per PDF/report.

Fields:

- `id`
- `report_year`
- `title`
- `source_pdf_path`
- `page_count`
- `created_at`
- `source_hash`

### `lines_of_business`

Canonical line definitions.

Fields:

- `id`
- `line_number`
- `name`
- `normalized_name`
- `section_start_page`
- `is_derived_total`

Examples:

- `16`, `Workers Compensation`
- `19.3, 19.4`, `Commercial Auto Liability`
- `21.2`, `Commercial Auto Physical Damage`
- `Derived total`, `Total Commercial Auto`

### `geography_scopes`

The report has repeated geographic blocks.

Fields:

- `id`
- `code`
- `name`

Initial values:

- `countrywide_with_canada_alien`: States, U.S. territories, Canada, Aggregate Other Alien
- `countrywide_us_territories`: States and U.S. territories
- `state_by_group`: By state by group

### `jurisdictions`

States, territories, Canada, Aggregate Other Alien, and report-level totals.

Fields:

- `id`
- `name`
- `normalized_name`
- `type`
- `abbreviation`

Types:

- `state`
- `territory`
- `country`
- `aggregate_other_alien`
- `countrywide`

### `carrier_groups`

Group-level carrier entities.

Fields:

- `id`
- `group_code`
- `group_name`
- `normalized_group_name`

### `companies`

Individual insurance companies, including daughter companies and unaffiliated companies.

Fields:

- `id`
- `company_code`
- `company_name`
- `normalized_company_name`
- `is_unaffiliated`

### `group_memberships`

Maps daughter companies to carrier groups.

Fields:

- `id`
- `group_id`
- `company_id`
- `source_page`

### `market_share_records`

The main fact table.

Fields:

- `id`
- `report_id`
- `line_of_business_id`
- `geography_scope_id`
- `jurisdiction_id`
- `rank`
- `carrier_group_id`
- `company_id`
- `display_code`
- `display_name`
- `direct_written_premium_000`
- `direct_earned_premium_000`
- `market_share_pct`
- `cumulative_market_share_pct`
- `loss_ratio_pct`
- `loss_cost_containment_ratio_pct`
- `is_state_total`
- `source_page`
- `source_text_hash`
- `raw_row_text`
- `parse_confidence`

Notes:

- Most ranked rows will populate `carrier_group_id`.
- Unaffiliated company rows should populate `company_id`.
- `display_code` and `display_name` preserve exactly what the report row used.
- `is_state_total` marks the state total rows so they can be excluded from carrier search.
- `raw_row_text` preserves the row text that produced the structured fields.
- `parse_confidence` starts as a simple enum: `high`, `medium`, `low`.

### `source_pages`

Traceability layer for debugging extraction.

Fields:

- `id`
- `report_id`
- `pdf_page_index`
- `report_page_label`
- `text`
- `extraction_method`
- `text_hash`

### `extraction_runs`

One row per attempt to parse the PDF.

Fields:

- `id`
- `report_id`
- `started_at`
- `finished_at`
- `extractor_name`
- `extractor_version`
- `status`
- `warnings_count`
- `errors_count`

### `parser_warnings`

Warnings are part of the data product. Silent parser failure is the main risk.

Fields:

- `id`
- `extraction_run_id`
- `source_page`
- `line_of_business_id`
- `geography_scope_id`
- `jurisdiction_id`
- `severity`
- `warning_code`
- `message`
- `raw_text`

Initial warning codes:

- `ROW_PARSE_FAILED`
- `RANK_GAP`
- `MISSING_STATE_TOTAL`
- `UNRESOLVED_CARRIER_CODE`
- `DUPLICATE_RANK`
- `UNEXPECTED_COLUMN_COUNT`
- `PREMIUM_PARSE_FAILED`
- `PERCENT_PARSE_FAILED`

### `validation_results`

Stores validation outcomes so every build can be compared.

Fields:

- `id`
- `extraction_run_id`
- `check_name`
- `status`
- `expected_value`
- `actual_value`
- `details`

## Search Index

Use SQLite FTS5 virtual tables for text lookup.

### `carrier_search`

Searchable carrier identity table.

Indexed text:

- group name
- group code
- company name
- company code
- aliases, if later added

Returned entity:

- `carrier_group_id` or `company_id`

### `market_record_search`

Searchable market records.

Indexed text:

- carrier display name
- line of business
- jurisdiction
- geography scope

Returned entity:

- `market_share_record_id`

## Extraction Pipeline

### Stage 1: PDF Text and Page Extraction

Try in this order:

1. `pymupdf` for page text, layout blocks, coordinates.
2. `pdfplumber` for table extraction and coordinate-based rows.
3. Custom fallback parser for specific table patterns if needed.

Output:

- one text artifact per page
- page metadata
- extraction diagnostics

Important: preserve page boundaries. The same table headers repeat across many pages, and page context is needed to know the current line of business and geography scope.

### Stage 2: Section Detection

Detect:

- line-of-business section starts
- geography scope block starts
- state/jurisdiction boundaries
- index section starts
- technical notes boundary

Use the known table of contents from `pnc_market_share_report_structure.md` as the seed map, then verify each page header during parsing.

### Stage 3: Market Share Table Parsing

For each line-of-business section:

1. Identify countrywide block including Canada and Other Alien.
2. Extract top 125 ranked rows.
3. Identify countrywide U.S./territories-only block.
4. Extract top 125 ranked rows.
5. Identify `BY STATE BY GROUP`.
6. Extract top 10 rows per jurisdiction plus state total rows.

Expected table columns:

- rank
- group/company code
- group/company name
- direct written premium
- direct earned premium
- market share
- cumulative market share
- loss ratio
- loss and cost containment ratio

Parsing risk:

- PDF text extraction may split names and numbers awkwardly.
- Some values can be `N/A`.
- Some names wrap across lines.
- Some sections may have fewer than 10 rows for small jurisdictions or niche lines.

Mitigation:

- Use coordinates when possible, not only raw text.
- Keep raw source page text for every parsed row.
- Add validation checks before accepting the dataset.

### Stage 4: Index Section Parsing

Parse two index structures:

1. Companies affiliated with a group by group name.
2. Companies not affiliated with a group by company name.

Output:

- `carrier_groups`
- `companies`
- `group_memberships`

Important behavior:

- If a market-share row uses a group code, connect it to all member companies through `group_memberships`.
- If a market-share row uses an individual unaffiliated company code, connect it directly to `companies`.

### Stage 5: Normalization

Normalize:

- names
- line numbers
- state/jurisdiction names
- percentages
- premium values
- `N/A` values

Do not throw away original text. Store raw display names and source page pointers.

### Stage 6: Validation

Validation should be treated as part of extraction, not an afterthought.

Checks:

- Every known line of business has records.
- Every line has expected geography blocks unless the PDF section genuinely omits one.
- Countrywide top-125 blocks have up to 125 ranked rows.
- State blocks have up to 10 ranked rows per jurisdiction.
- State total rows exist where expected.
- Ranks are increasing within each section/block/jurisdiction.
- Market share and cumulative market share are numeric or `N/A`.
- Premium values are numeric where present.
- Group codes in market rows resolve to `carrier_groups` where possible.
- Unaffiliated company codes resolve to `companies` where possible.
- Parsed row counts by page are logged.
- Extraction warnings are saved, not hidden.

## Query Layer

Start with a CLI.

### Query 1: Top Carriers by State and Line

Input:

- state
- line of business
- optional limit

Output:

- rank
- carrier/group name
- group code
- direct written premium
- market share
- cumulative market share
- loss ratio
- source page

### Query 2: Carrier Footprint

Input:

- group/company search string

Output:

- matched group/company
- affiliated companies, if group
- all market-share records where carrier appears
- filterable by state and line

### Query 3: Policy Request Candidate Set

Input:

- company state
- requested policy lines

Output:

- candidate carrier groups appearing in any requested line/state
- metrics per line
- aggregate facts, not a recommendation score yet

Example response shape:

```json
{
  "state": "Texas",
  "requested_lines": ["Workers Compensation", "Commercial Auto Liability"],
  "candidates": [
    {
      "carrier_group": "Example Group",
      "group_code": "123",
      "lines": [
        {
          "line": "Workers Compensation",
          "rank": 3,
          "market_share_pct": 7.2,
          "direct_written_premium_000": 123456,
          "loss_ratio_pct": 58.1,
          "source_page": 312
        }
      ]
    }
  ]
}
```

## Milestones

### Milestone 1: Prove Extraction on One Line

Target line:

- Workers Compensation, because it is commercially useful and likely relevant for P&C matching.

Deliverables:

- parse the Workers Compensation section
- load records into SQLite
- query top carriers by state
- save extraction warnings
- generate a validation report

Acceptance criteria:

- Texas Workers Compensation top 10 can be queried.
- Countrywide top 125 can be queried.
- Each parsed record has source page and source text hash.
- Every parsed row stores `raw_row_text`.
- Parser warnings are written to `parser_warnings`, not just printed.
- The validation command exits non-zero if Texas has zero rows, duplicate ranks, missing premiums, or missing source pages.

Milestone 1 implementation should target these modules only:

```text
src/pnc_index/
  __init__.py
  pdf_extract.py
  section_detect.py
  table_parse.py
  db.py
  validate.py
  cli.py
tests/
  fixtures/
  test_section_detect.py
  test_table_parse_workers_comp.py
  test_db_load_workers_comp.py
  test_cli_top_carriers.py
```

Defer `index_parse.py`, `normalize.py`, and `search.py` until Milestones 2-4 unless Milestone 1 needs a small helper.

### Milestone 2: Parse All Market Share Sections

Deliverables:

- all line-of-business sections loaded
- all geography blocks loaded
- validation report generated

Acceptance criteria:

- every line listed in the structure doc has records
- row counts are plausible
- malformed rows are visible in an exceptions table

### Milestone 3: Parse Group and Company Index

Deliverables:

- group table
- company table
- group membership table
- unaffiliated company table

Acceptance criteria:

- group-level rows can list daughter companies
- daughter company search resolves to parent group
- unaffiliated company search resolves directly

### Milestone 4: Search and Retrieval CLI

Deliverables:

- `search-carrier`
- `top-carriers`
- `carrier-footprint`
- `policy-candidates`

Acceptance criteria:

- fuzzy name search works for common carrier names
- state + line lookup works
- policy request returns factual candidate set

### Milestone 5: API or UI

Only after the database and CLI are validated.

Options:

- FastAPI service for programmatic access.
- Streamlit app for internal exploration.
- Lightweight web UI for broker-style carrier lookup.

## File Layout

Recommended Python project structure:

```text
src/
  pnc_index/
    __init__.py
    config.py
    pdf_extract.py
    section_detect.py
    table_parse.py
    index_parse.py
    normalize.py
    db.py
    validate.py
    search.py
    cli.py
tests/
  fixtures/
  test_section_detect.py
  test_table_parse_workers_comp.py
  test_normalize.py
  test_validation.py
artifacts/
  publication-msr-pb-property-casualty.pdf
  pnc_market_share_report_structure.md
  pnc_carrier_index_plan.md
  extracted/
  validation/
data/
  pnc_market_share.sqlite
```

## Key Risks

### PDF Table Extraction Quality

The biggest risk is not database design. It is reliable row extraction from a 707-page PDF.

Mitigation:

- start with one line
- compare parsed output against visible PDF pages
- keep source page references
- log every skipped or suspicious row

### Group vs Company Ambiguity

Market share records may be group-level, while users may search daughter-company names.

Mitigation:

- parse the index section early
- make group/company resolution a first-class feature
- preserve both group and company identities

### Recommendation Pressure Too Early

It will be tempting to turn market share into "best carrier."

Mitigation:

- first product returns facts only
- later scoring must label assumptions clearly
- appetite, class code fit, underwriting constraints, admitted/non-admitted status, and broker relationships are separate datasets

## Open Questions

1. Should the first parser target all states and territories, or only U.S. states?
2. Should Canada and Aggregate Other Alien be included in the first index?
3. Should derived totals like Total Commercial Auto be indexed as separate lines, or computed later from component lines?
4. Should the first CLI accept natural language, or only structured flags?
5. Which 3 to 5 lines of business matter most for the first carrier-matching workflow?

## The Assignment

Before implementation, pick the first policy workflow to test against the index.

Recommended first workflow:

```text
A business in one U.S. state needs Workers Compensation and Commercial Auto.
Return carriers with top-10 state presence in either line, plus countrywide rank and market-share metrics.
```

This gives the extraction work a concrete test without forcing premature recommendation logic.

## Engineering Review Addendum

Generated by `/plan-eng-review`.

### Step 0: Scope Challenge

Scope accepted with one reduction: Milestone 1 is now locked to Workers Compensation + Texas retrieval. The full module layout remains the destination, but implementation should not build all modules at once.

Reason: the riskiest part is PDF row extraction. A small validated slice lowers blast radius and prevents building a search layer on untrusted data.

### Architecture Review

Issue 1, fixed in this plan: extraction diagnostics were not first-class data.

Resolution:

- Added `extraction_runs`.
- Added `parser_warnings`.
- Added `validation_results`.
- Added `raw_row_text` and `parse_confidence` to `market_share_records`.

Why this matters: PDF parsing failures are often partial. A parser that silently drops five rows can still look successful unless warnings are queryable.

Issue 2, fixed in this plan: Milestone 1 originally inherited the full future file layout.

Resolution:

- Added `Locked Milestone 1 Scope`.
- Limited Milestone 1 modules to extraction, section detection, row parsing, DB load, validation, and CLI.
- Deferred index parsing, broad normalization, search abstraction, API, and UI.

### Code Quality Review

No code exists yet, so this review focused on planned module boundaries.

Rules for implementation:

- Keep parsing rules explicit and data-driven.
- Do not hide PDF-specific heuristics in generic helper names.
- Prefer small pure functions for parsing numbers, percentages, ranks, and row text.
- Store raw inputs beside parsed outputs for every market row.
- Avoid global mutable parser state. Pass section/page context explicitly.

Suggested pipeline comments:

- `table_parse.py` should include the ASCII pipeline from `Locked Milestone 1 Scope`.
- `db.py` should include a small relationship diagram for reports, source pages, market records, and parser warnings.

### Test Review

Test plan artifact saved to:

```text
artifacts/pnc_carrier_index_test_plan.md
```

Coverage target:

```text
PDF extraction
  -> section detection
  -> Workers Compensation Texas row parsing
  -> SQLite load
  -> CLI retrieval
  -> validation failure modes
```

Required test gaps added:

- Missing PDF error.
- Empty/no-text page warning.
- Workers Compensation vs Excess Workers Compensation disambiguation.
- Wrapped carrier names.
- Numeric premium parsing.
- Percent and `N/A` parsing.
- Duplicate rank validation.
- Missing source page validation.
- Unknown state and unknown line CLI behavior.

### Performance Review

No production-scale concern for Milestone 1. The PDF is small enough to parse locally.

Implementation constraints:

- Parse page-by-page rather than loading derived artifacts into memory repeatedly.
- Cache extracted page text/layout to `artifacts/extracted/` during development.
- Keep SQLite indexes on `line_of_business_id`, `jurisdiction_id`, `rank`, `carrier_group_id`, and `company_id`.
- Do not introduce DuckDB, FastAPI, background jobs, or embeddings in Milestone 1.

### Failure Modes

| Failure mode | Covered by plan? | Required behavior |
|---|---:|---|
| PDF dependency cannot parse the file | Yes | fail clearly, no empty database marked successful |
| Workers Compensation section not found | Yes | validation failure with clear message |
| Parser matches Excess Workers Compensation instead | Yes | section detection test must prevent this |
| Row parse fails for wrapped carrier name | Yes | warning row plus failed validation if target row count is wrong |
| Duplicate ranks inserted | Yes | DB or validation failure |
| State total returned as carrier | Yes | `is_state_total` excluded from carrier query |
| Source page missing | Yes | validation failure |
| Unknown state/line queried | Yes | useful empty-state CLI message |

No silent-failure critical gaps remain in the plan.

### NOT In Scope

- All-line extraction: deferred until Workers Compensation/Texas proves parser reliability.
- Full group/company index parsing: deferred until at least one market-share section parses cleanly.
- Carrier recommendation scoring: deferred because market share is not underwriting appetite.
- Natural-language query parsing: deferred; structured CLI flags are enough for validation.
- API or UI: deferred until database and CLI are correct.
- Embeddings: deferred; deterministic retrieval should work first.
- Canada and Aggregate Other Alien matching: deferred for Milestone 1 unless needed for countrywide validation.

### What Already Exists

- `artifacts/publication-msr-pb-property-casualty.pdf`: source PDF.
- `artifacts/pnc_market_share_report_structure.md`: extracted report structure, line list, repeated table pattern, and index notes.
- `artifacts/pnc_carrier_index_plan.md`: this implementation plan.
- `artifacts/pnc_carrier_index_test_plan.md`: engineering review test plan.

No application code exists yet, so there is no existing parser, DB schema, CLI, or test framework to reuse.

### Parallelization Strategy

Sequential implementation for Milestone 1. The steps touch the same parser and schema surface, so parallel worktrees would create coordination overhead.

Recommended order:

```text
1. Project skeleton + dependency setup
2. Page extraction
3. Section detection
4. Workers Compensation Texas row parser
5. SQLite schema/load
6. Validation
7. CLI query
8. Tests and fixture cleanup
```

### Completion Summary

- Step 0: Scope Challenge: scope reduced to locked Milestone 1.
- Architecture Review: 2 issues found, 2 fixed in plan.
- Code Quality Review: 0 code findings, implementation rules added.
- Test Review: diagram produced, 9 required test gaps captured.
- Performance Review: 0 blocking issues, constraints added.
- NOT in scope: written.
- What already exists: written.
- TODO updates: 0 separate TODOs proposed; deferred work is captured in NOT in scope and milestones.
- Failure modes: 0 critical silent-failure gaps remain.
- Outside voice: skipped.
- Parallelization: 1 sequential lane.
- Lake Score: 3/3 recommendations chose the complete option.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | - | - |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | - | - |
| Eng Review | `/plan-eng-review` | Architecture & tests | 1 | CLEAR | 2 architecture issues fixed, 9 test gaps captured, 0 critical silent-failure gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | - | Not applicable for backend/CLI Milestone 1 |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | - | Not needed before first CLI exists |

**VERDICT:** ENG CLEARED for Milestone 1 implementation.
