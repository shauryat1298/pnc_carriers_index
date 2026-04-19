import unittest

from pnc_index.pdf_extract import extract_pages
from pnc_index.table_parse import parse_workers_comp_texas_rows


class WorkersCompTableParseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pages = extract_pages("artifacts/publication-msr-pb-property-casualty.pdf")

    def test_parses_texas_top_10(self) -> None:
        result = parse_workers_comp_texas_rows(self.pages)
        self.assertEqual(10, len(result.records))
        self.assertEqual([], result.warnings)
        self.assertEqual(list(range(1, 11)), [record.rank for record in result.records])

    def test_parses_first_ranked_carrier_metrics(self) -> None:
        first = parse_workers_comp_texas_rows(self.pages).records[0]
        self.assertEqual("5067", first.display_code)
        self.assertEqual("TEXAS MUT GRP", first.display_name)
        self.assertEqual(1027243, first.direct_written_premium_000)
        self.assertEqual(1031140, first.direct_earned_premium_000)
        self.assertEqual(39.40, first.market_share_pct)
        self.assertEqual(39.40, first.cumulative_market_share_pct)
        self.assertEqual(37.21, first.loss_ratio_pct)
        self.assertEqual(42.21, first.loss_cost_containment_ratio_pct)
        self.assertEqual("321", first.source_page)
        self.assertIn("TEXAS MUT GRP", first.raw_row_text)

    def test_parses_wrapped_name_and_na_ratios(self) -> None:
        fifth = parse_workers_comp_texas_rows(self.pages).records[4]
        self.assertEqual(5, fifth.rank)
        self.assertEqual("111", fifth.display_code)
        self.assertEqual("LIBERTY MUT GRP", fifth.display_name)
        self.assertIsNone(fifth.loss_ratio_pct)
        self.assertIsNone(fifth.loss_cost_containment_ratio_pct)


if __name__ == "__main__":
    unittest.main()
