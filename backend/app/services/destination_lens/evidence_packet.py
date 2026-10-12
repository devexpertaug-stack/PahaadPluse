"""Evidence Packet PDF generator (Req 14.4-14.8).

A destination_official selects a Hotspot + theme and gets a PDF (built with
reportlab) within 30s containing: a title, the Destination, the date range, a
monthly trend chart, the total mention count, the count of distinct Properties
whose guests mention the issue, a map excerpt and >=5 representative quotes with
platform + date + source URL. A Hindi option renders the headings/summary in
Devanagari with a Hindi translation beneath each original-language quote.
Pseudonyms + guest PII are excluded (only the public review quote, platform,
date and source URL are shown). Each generated packet is recorded as an issue
surfaced to authorities (issues-surfaced metric).
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.services.destination_lens.service import DestinationLensService, Mention
from app.services.destination_lens.translate import (
    label_hi,
    theme_hi,
    translate_quote_hi,
)

MIN_QUOTES = 5
_FONT_PATH = (
    Path(__file__).resolve().parents[2] / "assets" / "fonts" / "NotoSansDevanagari-Regular.ttf"
)
_DEVA_FONT = "NotoDeva"
_FONT_REGISTERED = False


def _ensure_font() -> bool:
    """Register the bundled Devanagari font once; return True if available."""
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return True
    if _FONT_PATH.exists():
        try:
            pdfmetrics.registerFont(TTFont(_DEVA_FONT, str(_FONT_PATH)))
            _FONT_REGISTERED = True
            return True
        except Exception:  # pragma: no cover - defensive
            return False
    return False


@dataclass
class EvidencePacketResult:
    """Result of generating an Evidence Packet."""

    pdf_bytes: bytes
    quote_count: int
    distinct_properties: int
    total_mentions: int
    language: str
    issues_surfaced: int


class EvidencePacketGenerator:
    """Build the Evidence Packet PDF for a hotspot + theme."""

    def __init__(self, service: DestinationLensService) -> None:
        self._service = service

    def generate(
        self,
        canonical: str,
        theme: str | None,
        start: date | None,
        end: date | None,
        *,
        language: str = "en",
    ) -> EvidencePacketResult:
        hindi = language.lower() in {"hi", "hindi"}
        has_deva = _ensure_font() if hindi else False

        hotspots = {h.canonical: h for h in self._service.hotspots(theme, start, end)}
        hotspot = hotspots.get(canonical)
        quotes = self._service.quotes_for(canonical, theme, start, end)
        trend = self._service.monthly_trend(canonical, theme, start, end)

        distinct_properties = len({q.property_id for q in quotes})
        total_mentions = hotspot.negative_count if hotspot else len(quotes)
        label = canonical.title()

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        width, height = A4

        base_font = "Helvetica"

        def L(key: str) -> str:
            """Resolve a label in the chosen language."""
            return label_hi(key) if (hindi and has_deva) else key

        def set_heading_font(size: int) -> None:
            if hindi and has_deva:
                c.setFont(_DEVA_FONT, size)
            else:
                c.setFont("Helvetica-Bold", size)

        y = height - 20 * mm

        # ---- Title ----
        set_heading_font(18)
        c.setFillColor(colors.HexColor("#275233"))
        title = f"{L('Evidence Packet')}: {label}"
        c.drawString(20 * mm, y, title)
        y -= 10 * mm

        c.setFillColor(colors.black)
        theme_text = (
            theme_hi(theme)
            if (hindi and has_deva and theme)
            else (theme or "all themes")
        )

        def meta_line(key: str, value: str) -> None:
            nonlocal y
            if hindi and has_deva:
                c.setFont(_DEVA_FONT, 11)
            else:
                c.setFont("Helvetica-Bold", 11)
            c.drawString(20 * mm, y, f"{L(key)}: ")
            c.setFont(base_font if not (hindi and has_deva) else _DEVA_FONT, 11)
            c.drawString(70 * mm, y, value)
            y -= 7 * mm

        meta_line("Destination", "Mussoorie, Uttarakhand")
        date_range = (
            f"{start.isoformat() if start else '—'} → {end.isoformat() if end else '—'}"
        )
        meta_line("Date range", date_range)
        meta_line("Issue theme", theme_text)
        meta_line("Total mentions", str(total_mentions))
        meta_line("Distinct properties", str(distinct_properties))

        y -= 3 * mm

        # ---- Monthly trend chart (simple bar chart) ----
        set_heading_font(13)
        c.drawString(20 * mm, y, L("Monthly trend"))
        y -= 6 * mm
        y = self._draw_trend(c, trend, 20 * mm, y, width - 40 * mm, 30 * mm)
        y -= 6 * mm

        # ---- Map excerpt ----
        set_heading_font(13)
        c.drawString(20 * mm, y, L("Map excerpt"))
        y -= 6 * mm
        y = self._draw_map(c, hotspot, canonical, 20 * mm, y)
        y -= 6 * mm

        # ---- Representative quotes (>=5) ----
        set_heading_font(13)
        c.drawString(20 * mm, y, L("Representative quotes"))
        y -= 7 * mm

        shown = quotes[:MIN_QUOTES] if len(quotes) >= MIN_QUOTES else quotes
        for q in shown:
            if y < 35 * mm:
                c.showPage()
                y = height - 20 * mm
            y = self._draw_quote(c, q, hindi and has_deva, 20 * mm, y, width - 40 * mm)
            y -= 4 * mm

        # Footer note on surfacing to authorities.
        if y < 20 * mm:
            c.showPage()
            y = height - 20 * mm
        c.setFont(base_font, 8)
        c.setFillColor(colors.grey)
        c.drawString(
            20 * mm,
            15 * mm,
            "Guest pseudonyms and PII are excluded. Quotes are public review text only.",
        )

        c.showPage()
        c.save()
        pdf_bytes = buf.getvalue()

        issues = self._service.record_issue_surfaced()
        return EvidencePacketResult(
            pdf_bytes=pdf_bytes,
            quote_count=len(shown),
            distinct_properties=distinct_properties,
            total_mentions=total_mentions,
            language="hi" if hindi else "en",
            issues_surfaced=issues,
        )

    # ---- drawing helpers ----
    def _draw_trend(
        self, c: canvas.Canvas, trend: list[tuple[str, int]], x: float, y: float, w: float, h: float
    ) -> float:
        bottom = y - h
        c.setStrokeColor(colors.HexColor("#c9ddcc"))
        c.line(x, bottom, x + w, bottom)
        if not trend:
            c.setFont("Helvetica-Oblique", 9)
            c.setFillColor(colors.grey)
            c.drawString(x, bottom - 5 * mm, "No mentions in the selected window.")
            return bottom - 8 * mm
        max_count = max(v for _, v in trend) or 1
        n = len(trend)
        bar_w = min(12 * mm, (w / n) * 0.6)
        gap = (w - bar_w * n) / (n + 1)
        c.setFillColor(colors.HexColor("#3f8150"))
        for i, (month, count) in enumerate(trend):
            bx = x + gap + i * (bar_w + gap)
            bh = (count / max_count) * (h - 6 * mm)
            c.setFillColor(colors.HexColor("#3f8150"))
            c.rect(bx, bottom, bar_w, bh, fill=1, stroke=0)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 6)
            c.drawCentredString(bx + bar_w / 2, bottom + bh + 1 * mm, str(count))
            c.setFillColor(colors.grey)
            c.drawCentredString(bx + bar_w / 2, bottom - 4 * mm, month[2:])
        return bottom - 7 * mm

    def _draw_map(
        self, c: canvas.Canvas, hotspot, canonical: str, x: float, y: float
    ) -> float:
        box_h = 28 * mm
        box_w = 70 * mm
        bottom = y - box_h
        c.setStrokeColor(colors.HexColor("#275233"))
        c.setFillColor(colors.HexColor("#eef5ef"))
        c.rect(x, bottom, box_w, box_h, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#275233"))
        c.setFont("Helvetica-Bold", 9)
        if hotspot:
            c.drawString(x + 3 * mm, bottom + box_h - 6 * mm, "Mussoorie hotspot")
            c.setFillColor(colors.HexColor("#b3261e"))
            # marker in the centre of the excerpt box
            c.circle(x + box_w / 2, bottom + box_h / 2, 2.2 * mm, fill=1, stroke=0)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 8)
            c.drawString(
                x + 3 * mm,
                bottom + 3 * mm,
                f"{canonical.title()}  ({hotspot.latitude:.4f}, {hotspot.longitude:.4f})",
            )
        else:
            c.setFillColor(colors.grey)
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(x + 3 * mm, bottom + box_h / 2, "Location not geocoded.")
        return bottom

    def _draw_quote(
        self, c: canvas.Canvas, q: Mention, hindi: bool, x: float, y: float, w: float
    ) -> float:
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Oblique", 9)
        text = q.text if len(q.text) <= 110 else q.text[:107] + "..."
        # Original-language quote. If Devanagari and we have the font use it.
        if any("\u0900" <= ch <= "\u097f" for ch in text) and _FONT_REGISTERED:
            c.setFont(_DEVA_FONT, 9)
        c.drawString(x, y, f"\u201c{text}\u201d")
        y -= 5 * mm
        if hindi:
            c.setFont(_DEVA_FONT, 9)
            c.setFillColor(colors.HexColor("#2f663e"))
            gloss = translate_quote_hi(q.text)
            gloss = gloss if len(gloss) <= 110 else gloss[:107] + "..."
            c.drawString(x + 4 * mm, y, gloss)
            y -= 5 * mm
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.grey)
        url = q.source_url or "source URL unavailable"
        c.drawString(x, y, f"{q.platform} · {q.date.isoformat()} · {url}")
        y -= 2 * mm
        return y
