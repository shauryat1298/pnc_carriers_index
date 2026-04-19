from __future__ import annotations

import hashlib
from pathlib import Path

from .db import (
    connect,
    create_extraction_run,
    create_report,
    finish_extraction_run,
    init_db,
    load_market_share_records,
    load_parser_warnings,
    reset_milestone1_data,
    seed_reference_data,
)
from .pdf_extract import extract_pages, source_pdf_page_count
from .table_parse import parse_workers_comp_texas_rows


DEFAULT_PDF_PATH = Path("artifacts/publication-msr-pb-property-casualty.pdf")


def build_milestone1_index(pdf_path: str | Path, db_path: str | Path) -> dict[str, int | str]:
    pdf = Path(pdf_path)
    pages = extract_pages(pdf)
    page_count = source_pdf_page_count(pdf)
    parse_result = parse_workers_comp_texas_rows(pages)

    conn = connect(db_path)
    try:
        init_db(conn)
        reset_milestone1_data(conn)
        seed_reference_data(conn)
        report_id = create_report(
            conn,
            source_pdf_path=str(pdf),
            page_count=page_count,
            source_hash=_file_hash(pdf),
        )
        extraction_run_id = create_extraction_run(conn, report_id=report_id)
        load_market_share_records(conn, report_id=report_id, records=parse_result.records)
        load_parser_warnings(conn, extraction_run_id=extraction_run_id, warnings=parse_result.warnings)
        error_count = sum(1 for warning in parse_result.warnings if warning.severity == "error")
        status = "failed" if error_count else "success"
        finish_extraction_run(
            conn,
            extraction_run_id=extraction_run_id,
            status=status,
            warnings_count=len(parse_result.warnings),
            errors_count=error_count,
        )
    finally:
        conn.close()

    return {
        "status": status,
        "pages": page_count,
        "extracted_pages": len(pages),
        "records": len(parse_result.records),
        "warnings": len(parse_result.warnings),
        "errors": error_count,
    }


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
