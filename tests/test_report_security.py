"""The PDF renderer must not load anything except the bundled fonts, even from hostile HTML.

Report HTML contains client input. If markup ever got through unescaped, WeasyPrint would
otherwise attach server files to the PDF (<a rel=attachment href=file:///...>) or fetch URLs
from the server (<img src=http://...>, SSRF). jyotisha_report.safe_url_fetcher prevents both.
"""
import pathlib
import subprocess
import sys

import pytest

pymupdf = pytest.importorskip("pymupdf")
weasyprint = pytest.importorskip("weasyprint")

import jyotisha_report as jr  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SECRET = ROOT / "requirements.txt"          # any real file outside fonts/


def attachments(pdf_bytes):
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    found = list(doc.embfile_names())
    for page in doc:
        found += [a.file_info.get("filename") for a in page.annots() or []
                  if a.type[0] == pymupdf.PDF_ANNOT_FILE_ATTACHMENT]
    return doc, found


def render(body):
    css = jr.CSS.replace("FONTDIR", jr.font_uri()).replace("BRANDNAME", "T")
    page = f"<html><head><style>{css}</style></head><body>{body}</body></html>"
    return weasyprint.HTML(string=page, base_url=jr.HERE, url_fetcher=jr.safe_url_fetcher()).write_pdf()


def test_fetcher_allows_only_fonts_and_data():
    f = jr.safe_url_fetcher()
    ok = pathlib.Path(jr.fontdir_global(), "NotoSansSinhala.ttf").resolve().as_uri()
    f.fetch(ok)                                           # bundled font: allowed
    f.fetch("data:text/plain,hello")                      # inline data: allowed
    for bad in (SECRET.resolve().as_uri(),
                pathlib.Path(jr.fontdir_global(), "..", "requirements.txt").resolve().as_uri(),
                jr.font_uri() + "/../requirements.txt",   # path traversal out of fonts/
                "file://evil-host/share/x",
                "http://169.254.169.254/latest/meta-data/",
                "https://example.com/x.png",
                "ftp://example.com/x"):
        with pytest.raises(ValueError):
            f.fetch(bad)


def test_hostile_markup_attaches_nothing_and_fonts_still_load():
    body = (f'<p>Test සිංහල</p><a rel="attachment" href="{SECRET.resolve().as_uri()}">x</a>'
            '<img src="http://127.0.0.1:9/x.png"><link rel="attachment" href="file:///etc/passwd">')
    doc, found = attachments(render(body))
    assert found == []
    fonts = {s["font"] for b in doc[0].get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"]}
    assert any(f.startswith("Noto-Sans-Sinhala") for f in fonts)


def test_a1_report_escapes_name_and_place(tmp_path):
    """End to end through the CLI (bypassing the web app's own input checks)."""
    payload = f'<a rel=attachment href="{SECRET.resolve().as_uri()}">x</a>'
    out = tmp_path / "a1.pdf"
    r = subprocess.run([sys.executable, str(ROOT / "jyotisha_report.py"), "--report=A1", f"--name={payload}",
                        "--date=1990-05-15", "--time=10:30", "--lat=6.93", "--lon=79.85", f"--place={payload}",
                        f"--out={out}"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-500:]
    doc, found = attachments(out.read_bytes())
    assert found == []
    assert "<a rel=attachment" in "".join(p.get_text() for p in doc)   # shown as text, not markup
