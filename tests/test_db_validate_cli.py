from pathlib import Path
import tempfile
import unittest

from pnc_index.build import build_milestone1_index
from pnc_index.cli import main
from pnc_index.db import connect, top_carriers
from pnc_index.validate import validate_database


PDF_PATH = "artifacts/publication-msr-pb-property-casualty.pdf"


class DbValidateCliTests(unittest.TestCase):
    def test_build_loads_queryable_texas_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "pnc.sqlite"
            result = build_milestone1_index(PDF_PATH, db_path)
            self.assertEqual("success", result["status"])
            self.assertEqual(10, result["records"])

            conn = connect(db_path)
            try:
                report_page_count = conn.execute("SELECT page_count FROM reports").fetchone()["page_count"]
                self.assertEqual(707, report_page_count)
                rows = top_carriers(conn, state="Texas", line="Workers Compensation")
                self.assertEqual(10, len(rows))
                self.assertEqual("TEXAS MUT GRP", rows[0]["display_name"])
                self.assertTrue(validate_database(conn).ok)
            finally:
                conn.close()

    def test_validation_fails_for_missing_source_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "pnc.sqlite"
            build_milestone1_index(PDF_PATH, db_path)

            conn = connect(db_path)
            try:
                conn.execute("UPDATE market_share_records SET source_page = NULL WHERE rank = 2")
                conn.commit()
                result = validate_database(conn)
            finally:
                conn.close()

            self.assertFalse(result.ok)
            self.assertIn("source_pages_present", {issue.check_name for issue in result.issues})

    def test_validation_scopes_checks_to_texas_workers_comp(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "pnc.sqlite"
            build_milestone1_index(PDF_PATH, db_path)

            conn = connect(db_path)
            try:
                conn.execute(
                    """
                    INSERT INTO jurisdictions (name, normalized_name, type, abbreviation)
                    VALUES (?, ?, ?, ?)
                    """,
                    ("Oklahoma", "oklahoma", "state", "OK"),
                )
                report_id = conn.execute("SELECT id FROM reports").fetchone()["id"]
                line_id = conn.execute(
                    "SELECT id FROM lines_of_business WHERE normalized_name = 'workers compensation'"
                ).fetchone()["id"]
                scope_id = conn.execute(
                    "SELECT id FROM geography_scopes WHERE code = 'state_by_group'"
                ).fetchone()["id"]
                jurisdiction_id = conn.execute(
                    "SELECT id FROM jurisdictions WHERE normalized_name = 'oklahoma'"
                ).fetchone()["id"]
                conn.execute(
                    """
                    INSERT INTO market_share_records (
                        report_id, line_of_business_id, geography_scope_id, jurisdiction_id,
                        rank, display_name, source_text_hash, raw_row_text, parse_confidence
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (report_id, line_id, scope_id, jurisdiction_id, 1, "OTHER CARRIER", "hash", "raw", "test"),
                )
                conn.commit()

                result = validate_database(conn)
            finally:
                conn.close()

            self.assertTrue(result.ok)

    def test_cli_build_validate_and_top_carriers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "pnc.sqlite")
            self.assertEqual(0, main(["--db", db_path, "build", "--pdf", PDF_PATH]))
            self.assertEqual(0, main(["--db", db_path, "validate"]))
            self.assertEqual(
                0,
                main(
                    [
                        "--db",
                        db_path,
                        "top-carriers",
                        "--state",
                        "Texas",
                        "--line",
                        "Workers Compensation",
                    ]
                ),
            )

    def test_cli_unknown_state_returns_empty_state_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "pnc.sqlite")
            build_milestone1_index(PDF_PATH, db_path)
            self.assertEqual(
                1,
                main(
                    [
                        "--db",
                        db_path,
                        "top-carriers",
                        "--state",
                        "Atlantis",
                        "--line",
                        "Workers Compensation",
                    ]
                ),
            )


if __name__ == "__main__":
    unittest.main()
