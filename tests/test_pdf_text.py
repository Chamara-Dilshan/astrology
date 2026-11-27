"""Sinhala copied or searched in the PDFs is the real text (found scrambled 2026-11-27: "r,දෝෂ" for "දෝෂ").
Checked with PDFium, the engine of Chrome, Edge and Android's PDF viewer."""
import pytest

import jyotisha_pdftext
import jyotisha_report as jr

pytest.importorskip("weasyprint")
pdfium = pytest.importorskip("pypdfium2")
pymupdf = pytest.importorskip("pymupdf")

WORDS = ["දෝෂ", "ග්‍රහ", "වර්තමාන", "කේන්ද්‍රය", "ජ්‍යොතිෂ", "පොරොන්දම්", "සිකුරාදා", "මුහූර්ත", "ශ්‍රී ලංකා",
         "ස්වක්ෂේත්‍ර", "ශුක්‍ර", "බ්‍රහස්පතින්දා", "Sample 1990-05-15"]


def render(words):
    from weasyprint import HTML
    css = jr.CSS.replace("FONTDIR", jr.font_uri()).replace("BRANDNAME", "x")
    page = f"<html><head><style>{css}</style></head><body>" + "".join(f"<p>{w}</p>" for w in words) + "</body></html>"
    return HTML(string=page, base_url=jr.HERE).write_pdf()


def copied_lines(pdf_bytes):
    text = pdfium.PdfDocument(pdf_bytes)[0].get_textpage().get_text_range()
    return [ln.strip() for ln in text.replace("\r", "").split("\n") if ln.strip()]


def test_the_fix_is_in_place_for_the_locked_weasyprint():
    # fails when WeasyPrint is upgraded: re-adapt draw_first_line from the new version, then update the hash
    assert jyotisha_pdftext.install()


def test_copied_sinhala_is_the_real_text():
    jyotisha_pdftext.install()
    assert copied_lines(render(WORDS))[:len(WORDS)] == WORDS


def test_the_pages_look_exactly_the_same(monkeypatch):
    from weasyprint.draw import text as wt
    jyotisha_pdftext.install()
    fixed = render(WORDS)
    monkeypatch.setattr(wt, "draw_first_line", jyotisha_pdftext.ORIGINAL)
    plain = render(WORDS)
    a, b = pymupdf.open(stream=fixed, filetype="pdf"), pymupdf.open(stream=plain, filetype="pdf")
    assert a[0].get_pixmap(dpi=100).samples == b[0].get_pixmap(dpi=100).samples
    assert copied_lines(plain)[0] != "දෝෂ"     # and without the fix it was scrambled
