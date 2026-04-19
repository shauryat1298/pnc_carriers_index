from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from .db import latest_extraction_run_id


@dataclass(frozen=True)
class ValidationIssue:
    check_name: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    issues: list[ValidationIssue]


def validate_database(conn: sqlite3.Connection) -> ValidationResult:
    issues: list[ValidationIssue] = []

    rows = conn.execute(
        """
        SELECT msr.rank, msr.display_name, msr.direct_written_premium_000, msr.source_page
        FROM market_share_records msr
        JOIN lines_of_business lob ON lob.id = msr.line_of_business_id
        JOIN geography_scopes gs ON gs.id = msr.geography_scope_id
        JOIN jurisdictions j ON j.id = msr.jurisdiction_id
        WHERE lob.normalized_name = 'workers compensation'
          AND gs.code = 'state_by_group'
          AND j.normalized_name = 'texas'
        ORDER BY rank
        """
    ).fetchall()

    if not rows:
        issues.append(ValidationIssue("texas_rows_present", "Texas Workers Compensation has zero rows"))
    if len(rows) != 10:
        issues.append(ValidationIssue("texas_row_count", f"Expected 10 Texas rows, found {len(rows)}"))

    ranks = [int(row["rank"]) for row in rows]
    if len(ranks) != len(set(ranks)):
        issues.append(ValidationIssue("unique_ranks", "Duplicate ranks found"))
    if ranks and ranks != list(range(1, len(ranks) + 1)):
        issues.append(ValidationIssue("rank_sequence", f"Ranks are not sequential from 1: {ranks}"))

    missing_premium = [int(row["rank"]) for row in rows if row["direct_written_premium_000"] is None]
    if missing_premium:
        issues.append(
            ValidationIssue("written_premiums_present", f"Rows missing written premium: {missing_premium}")
        )

    missing_source = [int(row["rank"]) for row in rows if not row["source_page"]]
    if missing_source:
        issues.append(ValidationIssue("source_pages_present", f"Rows missing source page: {missing_source}"))

    state_total_rows = conn.execute(
        "SELECT COUNT(*) AS count FROM market_share_records WHERE is_state_total = 1"
    ).fetchone()["count"]
    if state_total_rows:
        issues.append(ValidationIssue("state_total_excluded", "State total rows are loaded as carriers"))

    parser_errors = conn.execute(
        "SELECT COUNT(*) AS count FROM parser_warnings WHERE severity = 'error'"
    ).fetchone()["count"]
    if parser_errors:
        issues.append(ValidationIssue("parser_errors", f"Parser emitted {parser_errors} error warnings"))

    _persist_results(conn, issues)
    return ValidationResult(ok=not issues, issues=issues)


def _persist_results(conn: sqlite3.Connection, issues: list[ValidationIssue]) -> None:
    extraction_run_id = latest_extraction_run_id(conn)
    checks = {
        "texas_rows_present",
        "texas_row_count",
        "unique_ranks",
        "rank_sequence",
        "written_premiums_present",
        "source_pages_present",
        "state_total_excluded",
        "parser_errors",
    }
    issue_map = {issue.check_name: issue.message for issue in issues}
    for check in checks:
        conn.execute(
            """
            INSERT INTO validation_results (
                extraction_run_id, check_name, status, expected_value, actual_value, details
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                extraction_run_id,
                check,
                "fail" if check in issue_map else "pass",
                None,
                None,
                issue_map.get(check, ""),
            ),
        )
    conn.commit()
