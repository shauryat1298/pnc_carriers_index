from __future__ import annotations

from pathlib import Path
import sqlite3

from .table_parse import MarketShareRecord, ParserWarning


DEFAULT_DB_PATH = Path("data/pnc_market_share.sqlite")


def connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY,
            report_year INTEGER NOT NULL,
            title TEXT NOT NULL,
            source_pdf_path TEXT NOT NULL,
            page_count INTEGER NOT NULL,
            source_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS lines_of_business (
            id INTEGER PRIMARY KEY,
            line_number TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            section_start_page INTEGER,
            is_derived_total INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS geography_scopes (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jurisdictions (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            normalized_name TEXT NOT NULL,
            type TEXT NOT NULL,
            abbreviation TEXT
        );

        CREATE TABLE IF NOT EXISTS extraction_runs (
            id INTEGER PRIMARY KEY,
            report_id INTEGER NOT NULL,
            started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            finished_at TEXT,
            extractor_name TEXT NOT NULL,
            extractor_version TEXT NOT NULL,
            status TEXT NOT NULL,
            warnings_count INTEGER NOT NULL DEFAULT 0,
            errors_count INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(report_id) REFERENCES reports(id)
        );

        CREATE TABLE IF NOT EXISTS market_share_records (
            id INTEGER PRIMARY KEY,
            report_id INTEGER NOT NULL,
            line_of_business_id INTEGER NOT NULL,
            geography_scope_id INTEGER NOT NULL,
            jurisdiction_id INTEGER NOT NULL,
            rank INTEGER NOT NULL,
            carrier_group_id INTEGER,
            company_id INTEGER,
            display_code TEXT,
            display_name TEXT NOT NULL,
            direct_written_premium_000 INTEGER,
            direct_earned_premium_000 INTEGER,
            market_share_pct REAL,
            cumulative_market_share_pct REAL,
            loss_ratio_pct REAL,
            loss_cost_containment_ratio_pct REAL,
            is_state_total INTEGER NOT NULL DEFAULT 0,
            source_page TEXT,
            source_text_hash TEXT NOT NULL,
            raw_row_text TEXT NOT NULL,
            parse_confidence TEXT NOT NULL,
            UNIQUE(report_id, line_of_business_id, geography_scope_id, jurisdiction_id, rank),
            FOREIGN KEY(report_id) REFERENCES reports(id),
            FOREIGN KEY(line_of_business_id) REFERENCES lines_of_business(id),
            FOREIGN KEY(geography_scope_id) REFERENCES geography_scopes(id),
            FOREIGN KEY(jurisdiction_id) REFERENCES jurisdictions(id)
        );

        CREATE TABLE IF NOT EXISTS parser_warnings (
            id INTEGER PRIMARY KEY,
            extraction_run_id INTEGER NOT NULL,
            source_page TEXT,
            line_of_business_id INTEGER,
            geography_scope_id INTEGER,
            jurisdiction_id INTEGER,
            severity TEXT NOT NULL,
            warning_code TEXT NOT NULL,
            message TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            FOREIGN KEY(extraction_run_id) REFERENCES extraction_runs(id)
        );

        CREATE TABLE IF NOT EXISTS validation_results (
            id INTEGER PRIMARY KEY,
            extraction_run_id INTEGER,
            check_name TEXT NOT NULL,
            status TEXT NOT NULL,
            expected_value TEXT,
            actual_value TEXT,
            details TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(extraction_run_id) REFERENCES extraction_runs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_market_line_jurisdiction_rank
            ON market_share_records(line_of_business_id, jurisdiction_id, rank);
        CREATE INDEX IF NOT EXISTS idx_market_display_name
            ON market_share_records(display_name);
        """
    )
    conn.commit()


def seed_reference_data(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO lines_of_business
            (line_number, name, normalized_name, section_start_page, is_derived_total)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("16", "Workers Compensation", "workers compensation", 306, 0),
    )
    conn.execute(
        "INSERT OR IGNORE INTO geography_scopes (code, name) VALUES (?, ?)",
        ("state_by_group", "By State By Group"),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO jurisdictions (name, normalized_name, type, abbreviation)
        VALUES (?, ?, ?, ?)
        """,
        ("Texas", "texas", "state", "TX"),
    )
    conn.commit()


def reset_milestone1_data(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM validation_results")
    conn.execute("DELETE FROM parser_warnings")
    conn.execute("DELETE FROM market_share_records")
    conn.execute("DELETE FROM extraction_runs")
    conn.execute("DELETE FROM reports")
    conn.commit()


def create_report(
    conn: sqlite3.Connection,
    *,
    source_pdf_path: str,
    page_count: int,
    source_hash: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO reports (report_year, title, source_pdf_path, page_count, source_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            2024,
            "2024 Market Share Reports for Property/Casualty Groups and Companies by State and Countrywide",
            source_pdf_path,
            page_count,
            source_hash,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def create_extraction_run(
    conn: sqlite3.Connection,
    *,
    report_id: int,
    status: str = "running",
) -> int:
    cur = conn.execute(
        """
        INSERT INTO extraction_runs (report_id, extractor_name, extractor_version, status)
        VALUES (?, ?, ?, ?)
        """,
        (report_id, "stdlib-pdf-streams", "0.1.0", status),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_extraction_run(
    conn: sqlite3.Connection,
    *,
    extraction_run_id: int,
    status: str,
    warnings_count: int,
    errors_count: int,
) -> None:
    conn.execute(
        """
        UPDATE extraction_runs
        SET finished_at = CURRENT_TIMESTAMP,
            status = ?,
            warnings_count = ?,
            errors_count = ?
        WHERE id = ?
        """,
        (status, warnings_count, errors_count, extraction_run_id),
    )
    conn.commit()


def load_market_share_records(
    conn: sqlite3.Connection,
    *,
    report_id: int,
    records: list[MarketShareRecord],
) -> None:
    line_id = _id_for(conn, "lines_of_business", "line_number", "16")
    scope_id = _id_for(conn, "geography_scopes", "code", "state_by_group")
    jurisdiction_id = _id_for(conn, "jurisdictions", "name", "Texas")

    for record in records:
        conn.execute(
            """
            INSERT INTO market_share_records (
                report_id, line_of_business_id, geography_scope_id, jurisdiction_id,
                rank, display_code, display_name, direct_written_premium_000,
                direct_earned_premium_000, market_share_pct, cumulative_market_share_pct,
                loss_ratio_pct, loss_cost_containment_ratio_pct, is_state_total,
                source_page, source_text_hash, raw_row_text, parse_confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                line_id,
                scope_id,
                jurisdiction_id,
                record.rank,
                record.display_code,
                record.display_name,
                record.direct_written_premium_000,
                record.direct_earned_premium_000,
                record.market_share_pct,
                record.cumulative_market_share_pct,
                record.loss_ratio_pct,
                record.loss_cost_containment_ratio_pct,
                int(record.is_state_total),
                record.source_page,
                record.source_text_hash,
                record.raw_row_text,
                record.parse_confidence,
            ),
        )
    conn.commit()


def load_parser_warnings(
    conn: sqlite3.Connection,
    *,
    extraction_run_id: int,
    warnings: list[ParserWarning],
) -> None:
    for warning in warnings:
        conn.execute(
            """
            INSERT INTO parser_warnings (
                extraction_run_id, source_page, severity, warning_code, message, raw_text
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                extraction_run_id,
                warning.source_page,
                warning.severity,
                warning.warning_code,
                warning.message,
                warning.raw_text,
            ),
        )
    conn.commit()


def top_carriers(
    conn: sqlite3.Connection,
    *,
    state: str,
    line: str,
    limit: int = 10,
) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            msr.rank,
            msr.display_code,
            msr.display_name,
            msr.direct_written_premium_000,
            msr.direct_earned_premium_000,
            msr.market_share_pct,
            msr.cumulative_market_share_pct,
            msr.loss_ratio_pct,
            msr.loss_cost_containment_ratio_pct,
            msr.source_page
        FROM market_share_records msr
        JOIN lines_of_business lob ON lob.id = msr.line_of_business_id
        JOIN jurisdictions j ON j.id = msr.jurisdiction_id
        WHERE j.normalized_name = ?
          AND lob.normalized_name = ?
          AND msr.is_state_total = 0
        ORDER BY msr.rank
        LIMIT ?
        """,
        (_normalize(state), _normalize(line), limit),
    ).fetchall()


def latest_extraction_run_id(conn: sqlite3.Connection) -> int | None:
    row = conn.execute("SELECT id FROM extraction_runs ORDER BY id DESC LIMIT 1").fetchone()
    return int(row["id"]) if row else None


def _id_for(conn: sqlite3.Connection, table: str, field: str, value: str) -> int:
    row = conn.execute(f"SELECT id FROM {table} WHERE {field} = ?", (value,)).fetchone()
    if row is None:
        raise RuntimeError(f"Missing reference data: {table}.{field}={value}")
    return int(row["id"])


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())
