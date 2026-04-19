from pathlib import Path
import unittest

from pnc_index.pdf_extract import PdfExtractionError, compact_key, extract_pages, source_pdf_page_count


PDF_PATH = Path("artifacts/publication-msr-pb-property-casualty.pdf")


class PdfExtractTests(unittest.TestCase):
    def test_extract_pages_finds_workers_comp_text(self) -> None:
        pages = extract_pages(PDF_PATH)
        self.assertGreater(len(pages), 600)
        self.assertTrue(any("16workerscompensation" in compact_key(page.text) for page in pages))

    def test_missing_pdf_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(PdfExtractionError, "PDF not found"):
            extract_pages("artifacts/does-not-exist.pdf")

    def test_source_pdf_page_count_reads_physical_page_count(self) -> None:
        self.assertEqual(707, source_pdf_page_count(PDF_PATH))


if __name__ == "__main__":
    unittest.main()
