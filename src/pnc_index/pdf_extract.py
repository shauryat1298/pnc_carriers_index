from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from pathlib import Path
import zlib


@dataclass(frozen=True)
class ExtractedPage:
    pdf_page_index: int
    report_page_label: str | None
    text: str
    text_hash: str
    extraction_method: str = "stdlib-pdf-streams"


class PdfExtractionError(RuntimeError):
    pass


def extract_pages(pdf_path: str | Path) -> list[ExtractedPage]:
    """Extract text-like page records from the NAIC PDF.

    Pipeline:
        Source PDF
          -> Flate stream decompression
          -> text operator extraction
          -> content/footer stream pairing
          -> ExtractedPage records

    This is intentionally narrow. It handles the machine-generated NAIC report
    well enough for Milestone 1 without adding an external PDF dependency.
    """

    path = Path(pdf_path)
    if not path.exists():
        raise PdfExtractionError(f"PDF not found: {path}")

    data = path.read_bytes()
    streams = _decode_streams(data)
    text_chunks: list[tuple[int, str]] = []
    for obj_num, stream_text in streams:
        text = _extract_text_ops(stream_text)
        if len(text) >= 20:
            text_chunks.append((obj_num, _clean_text(text)))

    if not text_chunks:
        raise PdfExtractionError(f"No extractable text found in PDF: {path}")

    pages: list[ExtractedPage] = []
    pending_text: str | None = None
    pending_label: str | None = None
    pdf_page_index = 0

    for _obj_num, text in text_chunks:
        footer_label = _extract_footer_label(text)
        if footer_label and pending_text:
            pages.append(_make_page(pdf_page_index, footer_label, pending_text))
            pdf_page_index += 1
            pending_text = None
            pending_label = None
            continue

        if _looks_like_report_content(text):
            if pending_text:
                pages.append(_make_page(pdf_page_index, pending_label, pending_text))
                pdf_page_index += 1
            pending_text = text
            pending_label = footer_label

    if pending_text:
        pages.append(_make_page(pdf_page_index, pending_label, pending_text))

    if not pages:
        raise PdfExtractionError(f"No report pages could be reconstructed from PDF: {path}")

    return pages


def source_pdf_page_count(pdf_path: str | Path) -> int:
    """Return the physical page count from the source PDF metadata."""

    path = Path(pdf_path)
    if not path.exists():
        raise PdfExtractionError(f"PDF not found: {path}")

    data = path.read_bytes()
    linearized_count = re.search(rb"/Linearized\b(?:(?!endobj).)*/N\s+(\d+)", data[:4096], re.DOTALL)
    if linearized_count:
        return int(linearized_count.group(1))

    page_objects = re.findall(rb"/Type\s*/Page\b", data)
    if page_objects:
        return len(page_objects)

    raise PdfExtractionError(f"No PDF page count found in PDF: {path}")


def _make_page(pdf_page_index: int, label: str | None, text: str) -> ExtractedPage:
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
    return ExtractedPage(
        pdf_page_index=pdf_page_index,
        report_page_label=label,
        text=text,
        text_hash=digest,
    )


def _decode_streams(data: bytes) -> list[tuple[int, str]]:
    streams: list[tuple[int, str]] = []
    pos = 0
    stream_marker = b"stream"
    end_marker = b"endstream"

    while True:
        marker_pos = data.find(stream_marker, pos)
        if marker_pos < 0:
            break
        header_start = data.rfind(b"obj", 0, marker_pos)
        if header_start < 0:
            pos = marker_pos + len(stream_marker)
            continue
        obj_start = data.rfind(b"\n", 0, header_start)
        obj_header = data[obj_start + 1 : header_start + 3]
        obj_match = re.search(rb"(\d+)\s+\d+\s+obj", obj_header)
        if not obj_match:
            pos = marker_pos + len(stream_marker)
            continue
        obj_num = int(obj_match.group(1))
        header = data[header_start + 3 : marker_pos].decode("latin1", errors="ignore")
        start = marker_pos + len(stream_marker)
        if data[start : start + 2] == b"\r\n":
            start += 2
        elif data[start : start + 1] in (b"\n", b"\r"):
            start += 1
        end = data.find(end_marker, start)
        if end < 0:
            break
        raw = data[start:end]
        decoded = raw
        if "/FlateDecode" in header:
            try:
                decoded = zlib.decompress(raw)
            except zlib.error:
                try:
                    decoded = zlib.decompress(raw.rstrip(b"\r\n"))
                except zlib.error:
                    continue
        streams.append((obj_num, decoded.decode("latin1", errors="ignore")))
        pos = end + len(end_marker)

    return streams


def _extract_text_ops(stream_text: str) -> str:
    if "Tj" not in stream_text and "TJ" not in stream_text:
        return ""
    pieces: list[str] = []
    token_re = re.compile(r"\((?:\\.|[^\\)])*\)\s*Tj|<([0-9A-Fa-f\s]+)>\s*Tj|\[([^\]]*)\]\s*TJ")
    for match in token_re.finditer(stream_text):
        token = match.group(0)
        if token.startswith("("):
            pieces.append(_decode_pdf_string(token[1 : token.rfind(")")]))
        elif token.startswith("<"):
            pieces.append(_decode_hex_string(match.group(1) or ""))
        else:
            array_body = match.group(2) or ""
            for item in re.finditer(r"\((?:\\.|[^\\)])*\)|<([0-9A-Fa-f\s]+)>", array_body):
                item_text = item.group(0)
                if item_text.startswith("("):
                    pieces.append(_decode_pdf_string(item_text[1:-1]))
                else:
                    pieces.append(_decode_hex_string(item.group(1) or ""))
            pieces.append("\n")

    return " ".join(pieces)


def _decode_pdf_string(value: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        i += 1
        if i >= len(value):
            break
        nxt = value[i]
        escapes = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f"}
        if nxt in escapes:
            out.append(escapes[nxt])
        elif nxt in "()\\":
            out.append(nxt)
        elif nxt in "\r\n":
            if nxt == "\r" and i + 1 < len(value) and value[i + 1] == "\n":
                i += 1
        elif nxt in "01234567":
            octal = nxt
            for _ in range(2):
                if i + 1 < len(value) and value[i + 1] in "01234567":
                    i += 1
                    octal += value[i]
            out.append(chr(int(octal, 8)))
        else:
            out.append(nxt)
        i += 1
    return "".join(out)


def _decode_hex_string(value: str) -> str:
    clean = re.sub(r"\s+", "", value)
    chars: list[str] = []
    for i in range(0, len(clean) - 1, 2):
        try:
            chars.append(chr(int(clean[i : i + 2], 16)))
        except ValueError:
            continue
    return "".join(chars)


def _clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[^\x09\x0a\x0d\x20-\x7e]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def _extract_footer_label(text: str) -> str | None:
    match = re.search(r"rights reserved\.?\s+(\d{1,3})\s*$", text, re.IGNORECASE)
    return match.group(1) if match else None


def _looks_like_report_content(text: str) -> bool:
    compact = compact_key(text)
    markers = (
        "propertyandcasualtyinsuranceindustry",
        "marketsharereport",
        "introduction",
        "tableofcontents",
        "indexofcompanies",
        "directwrittenpremiumtrend",
    )
    return any(marker in compact for marker in markers)


def compact_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())
