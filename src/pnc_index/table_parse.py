from __future__ import annotations

from dataclasses import dataclass
import re

from .pdf_extract import ExtractedPage, compact_key
from .section_detect import state_by_group_pages


@dataclass(frozen=True)
class ParserWarning:
    warning_code: str
    message: str
    source_page: str | None = None
    raw_text: str = ""
    severity: str = "warning"


@dataclass(frozen=True)
class MarketShareRecord:
    line_number: str
    line_name: str
    geography_scope: str
    jurisdiction: str
    rank: int
    display_code: str | None
    display_name: str
    direct_written_premium_000: int | None
    direct_earned_premium_000: int | None
    market_share_pct: float | None
    cumulative_market_share_pct: float | None
    loss_ratio_pct: float | None
    loss_cost_containment_ratio_pct: float | None
    is_state_total: bool
    source_page: str | None
    source_text_hash: str
    raw_row_text: str
    parse_confidence: str = "high"


@dataclass(frozen=True)
class ParseResult:
    records: list[MarketShareRecord]
    warnings: list[ParserWarning]


class TableParseError(RuntimeError):
    pass


def parse_workers_comp_texas_rows(pages: list[ExtractedPage]) -> ParseResult:
    for page in state_by_group_pages(pages):
        if "texas" not in compact_key(page.text):
            continue
        segment = _extract_texas_segment(page.text)
        if segment:
            return _parse_texas_segment(segment, page)

    raise TableParseError("Texas Workers Compensation block not found")


def _extract_texas_segment(text: str) -> str | None:
    state_match = re.search(r"T\s*e\s*x\s*a\s*s", text)
    if not state_match:
        return None

    start = text.rfind("\n% % 1 ", 0, state_match.start())
    if start < 0:
        start = text.rfind("\n1 ", 0, state_match.start())
    if start < 0:
        return None

    end = text.find("* * S TAT E T O TA L * *", state_match.end())
    if end < 0:
        return None
    return text[start:end]


def _parse_texas_segment(segment: str, page: ExtractedPage) -> ParseResult:
    normalized = re.sub(r"\s+", " ", segment).strip()
    starts = list(_row_start_matches(normalized))
    records: list[MarketShareRecord] = []
    warnings: list[ParserWarning] = []

    for idx, match in enumerate(starts):
        row_start = match.start("rank")
        row_end = starts[idx + 1].start() if idx + 1 < len(starts) else len(normalized)
        raw = normalized[row_start:row_end].strip()
        try:
            records.append(_parse_ranked_row(raw, page))
        except ValueError as exc:
            warnings.append(
                ParserWarning(
                    warning_code="ROW_PARSE_FAILED",
                    message=str(exc),
                    source_page=page.report_page_label,
                    raw_text=raw,
                    severity="error",
                )
            )

    if len(records) != 10:
        warnings.append(
            ParserWarning(
                warning_code="RANK_GAP",
                message=f"Expected 10 Texas ranked rows, parsed {len(records)}",
                source_page=page.report_page_label,
                raw_text=segment,
                severity="error",
            )
        )

    return ParseResult(records=records, warnings=warnings)


def _row_start_matches(text: str) -> list[re.Match[str]]:
    pattern = re.compile(r"(?:(?:^)|(?:%\s+%\s+)|(?:N\s*/A\s+N\s*/A\s+))(?P<rank>10|[1-9])\s+")
    matches = list(pattern.finditer(text))
    return [m for m in matches if _is_plausible_rank_start(text, m)]


def _is_plausible_rank_start(text: str, match: re.Match[str]) -> bool:
    after = text[match.end() : match.end() + 20]
    return bool(re.match(r"(?:\d{1,5}\s+){0,2}[A-Z]", after))


def _parse_ranked_row(raw: str, page: ExtractedPage) -> MarketShareRecord:
    rank_match = re.match(r"(?P<rank>10|[1-9])\s+(?P<body>.+)$", raw)
    if not rank_match:
        raise ValueError("missing rank")
    rank = int(rank_match.group("rank"))
    body = rank_match.group("body")

    first_percent = body.find("%")
    if first_percent < 0:
        raise ValueError("missing market share fields")

    identity = body[:first_percent].strip()
    metrics = body[first_percent:].strip()
    code_match = re.match(r"(?P<code>(?:\d+\s+){0,2}\d+)\s+(?P<name>[A-Z].*)$", identity)
    if code_match:
        display_code = re.sub(r"\s+", "", code_match.group("code"))
        display_name = _clean_name(code_match.group("name"))
    else:
        display_code = None
        display_name = _clean_name(identity)

    percentages = list(_percent_matches(metrics))
    if len(percentages) < 2:
        raise ValueError("missing cumulative/market share percentages")

    cumulative_market_share_pct = _parse_decimal(percentages[0])
    market_share_pct = _parse_decimal(percentages[1])
    after_second_pct = metrics[metrics.find(percentages[1]) + len(percentages[1]) :]

    premiums = re.findall(r"\d{1,3}(?:,\d{3})+", after_second_pct)
    if len(premiums) < 2:
        raise ValueError("missing written/earned premium values")
    written = _parse_int(premiums[0])
    earned = _parse_int(premiums[1])
    after_premiums = after_second_pct[after_second_pct.find(premiums[1]) + len(premiums[1]) :]

    ratio_values = _ratio_values(after_premiums)
    loss_ratio = ratio_values[0] if len(ratio_values) > 0 else None
    loss_cost = ratio_values[1] if len(ratio_values) > 1 else None

    return MarketShareRecord(
        line_number="16",
        line_name="Workers Compensation",
        geography_scope="state_by_group",
        jurisdiction="Texas",
        rank=rank,
        display_code=display_code,
        display_name=display_name,
        direct_written_premium_000=written,
        direct_earned_premium_000=earned,
        market_share_pct=market_share_pct,
        cumulative_market_share_pct=cumulative_market_share_pct,
        loss_ratio_pct=loss_ratio,
        loss_cost_containment_ratio_pct=loss_cost,
        is_state_total=False,
        source_page=page.report_page_label,
        source_text_hash=page.text_hash,
        raw_row_text=raw,
    )


def _percent_matches(text: str) -> list[str]:
    return re.findall(r"%\s*\d+\.\s*\d+", text)


def _ratio_values(text: str) -> list[float | None]:
    values: list[float | None] = []
    for token in re.findall(r"N\s*/A|\d+\.\s*\d+", text):
        if re.search(r"N\s*/A", token):
            values.append(None)
        else:
            values.append(_parse_decimal(token))
    return values


def _parse_decimal(value: str) -> float:
    clean = value.replace("%", "")
    clean = re.sub(r"\s+", "", clean)
    return float(clean)


def _parse_int(value: str) -> int:
    return int(value.replace(",", ""))


def _clean_name(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    replacements = {
        "LIBER TY": "LIBERTY",
        "C H UBB": "CHUBB",
        "CHUBB L T D": "CHUBB LTD",
        "Z URI C H": "ZURICH",
        "TRA V EL ER S": "TRAVELERS",
        "H ARTF O R D": "HARTFORD",
        "FI RE": "FIRE",
        "C A S": "CAS",
        "C N A": "CNA",
        "S T ARR": "STARR",
        "ARC H": "ARCH",
        "OL D REP U BL I C": "OLD REPUBLIC",
        "I N S": "INS",
        "GRP": "GRP",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value
