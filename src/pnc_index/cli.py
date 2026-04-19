from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .build import DEFAULT_PDF_PATH, build_milestone1_index
from .db import DEFAULT_DB_PATH, connect, top_carriers
from .validate import validate_database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pnc-index")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite database path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build the Milestone 1 index")
    build_parser.add_argument("--pdf", default=str(DEFAULT_PDF_PATH), help="Source PDF path")

    top_parser = subparsers.add_parser("top-carriers", help="Show top carriers for a state and line")
    top_parser.add_argument("--state", required=True)
    top_parser.add_argument("--line", required=True)
    top_parser.add_argument("--limit", type=int, default=10)

    subparsers.add_parser("validate", help="Validate the SQLite index")

    args = parser.parse_args(argv)

    if args.command == "build":
        result = build_milestone1_index(args.pdf, args.db)
        print(
            "build {status}: pages={pages} records={records} warnings={warnings} errors={errors}".format(
                **result
            )
        )
        return 0 if result["status"] == "success" else 1

    if args.command == "top-carriers":
        return _top_carriers(args.db, args.state, args.line, args.limit)

    if args.command == "validate":
        return _validate(args.db)

    parser.error(f"Unknown command: {args.command}")
    return 2


def _top_carriers(db_path: str, state: str, line: str, limit: int) -> int:
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}. Run `python -m pnc_index.cli build` first.", file=sys.stderr)
        return 1

    conn = connect(db_path)
    try:
        rows = top_carriers(conn, state=state, line=line, limit=limit)
    finally:
        conn.close()

    if not rows:
        print(f"No rows found for state={state!r}, line={line!r}.")
        return 1

    print(f"Top carriers for {line} in {state}")
    print("rank | code | carrier | written_000 | earned_000 | share | cumulative | loss | loss_cc | page")
    for row in rows:
        print(
            " | ".join(
                [
                    str(row["rank"]),
                    row["display_code"] or "",
                    row["display_name"],
                    _fmt(row["direct_written_premium_000"]),
                    _fmt(row["direct_earned_premium_000"]),
                    _fmt_pct(row["market_share_pct"]),
                    _fmt_pct(row["cumulative_market_share_pct"]),
                    _fmt_pct(row["loss_ratio_pct"]),
                    _fmt_pct(row["loss_cost_containment_ratio_pct"]),
                    row["source_page"] or "",
                ]
            )
        )
    return 0


def _validate(db_path: str) -> int:
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}. Run `python -m pnc_index.cli build` first.", file=sys.stderr)
        return 1

    conn = connect(db_path)
    try:
        result = validate_database(conn)
    finally:
        conn.close()

    if result.ok:
        print("validation passed")
        return 0

    print("validation failed")
    for issue in result.issues:
        print(f"- {issue.check_name}: {issue.message}")
    return 1


def _fmt(value: object) -> str:
    if value is None:
        return "N/A"
    return str(value)


def _fmt_pct(value: object) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.2f}%"


if __name__ == "__main__":
    raise SystemExit(main())
