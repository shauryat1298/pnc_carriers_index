from __future__ import annotations

from dataclasses import dataclass

from .pdf_extract import ExtractedPage, compact_key


@dataclass(frozen=True)
class SectionPageRange:
    start_index: int
    end_index: int


class SectionNotFoundError(RuntimeError):
    pass


def find_workers_comp_section(pages: list[ExtractedPage]) -> SectionPageRange:
    start: int | None = None
    end: int | None = None

    for idx, page in enumerate(pages):
        key = compact_key(page.text)
        if (
            start is None
            and "propertyandcasualtyinsuranceindustry" in key
            and "16workerscompensation" in key
        ):
            start = idx
            continue
        if (
            start is not None
            and idx > start
            and "propertyandcasualtyinsuranceindustry" in key
            and "171172otherliability" in key
        ):
            end = idx
            break

    if start is None:
        raise SectionNotFoundError("Workers Compensation section not found")

    return SectionPageRange(start_index=start, end_index=end or len(pages))


def workers_comp_pages(pages: list[ExtractedPage]) -> list[ExtractedPage]:
    section = find_workers_comp_section(pages)
    return pages[section.start_index : section.end_index]


def state_by_group_pages(pages: list[ExtractedPage]) -> list[ExtractedPage]:
    return [
        page
        for page in workers_comp_pages(pages)
        if "bystatebygroup" in compact_key(page.text)
        and "excessworkerscompensation" not in compact_key(page.text)
    ]
