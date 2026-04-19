import unittest

from pnc_index.pdf_extract import ExtractedPage, extract_pages
from pnc_index.section_detect import (
    SectionNotFoundError,
    find_workers_comp_section,
    state_by_group_pages,
)


class SectionDetectTests(unittest.TestCase):
    def test_finds_workers_comp_section_in_real_pdf(self) -> None:
        pages = extract_pages("artifacts/publication-msr-pb-property-casualty.pdf")
        section = find_workers_comp_section(pages)
        self.assertGreater(section.start_index, 250)
        self.assertGreater(section.end_index, section.start_index)
        self.assertGreaterEqual(len(state_by_group_pages(pages)), 1)

    def test_does_not_confuse_excess_workers_comp_for_workers_comp_start(self) -> None:
        pages = [
            ExtractedPage(
                pdf_page_index=0,
                report_page_label="1",
                text="Property and Casualty Insurance Industry\n17.3 Excess Workers Compensation",
                text_hash="a",
            )
        ]
        with self.assertRaises(SectionNotFoundError):
            find_workers_comp_section(pages)


if __name__ == "__main__":
    unittest.main()
