"""Jyothisha Insight logo and the images made from it.

The mark is the South Indian chart frame (the 12 houses around an empty centre, as on every report)
with the Sun in the middle, in the reports' maroon and gold. Chosen by the owner on 2026-11-28.

    python tools/brand_assets.py [out_dir]

Writes into web/static/ (served by the site) and brand/ (to upload to Facebook):
  web/static/favicon.svg, favicon.ico (16/32/48), apple-touch-icon.png (180), og-image.png (1200x630)
  brand/logo.svg, logo_1024.png          the mark on its own
  brand/fb_profile_1080.png              Facebook profile picture (Facebook shows it as a circle)
  brand/fb_cover_1640x624.png            Facebook Page cover photo
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

MAROON, GOLD, GOLD_SOFT, CREAM = "#6b1010", "#c9a24d", "#8c5a2b", "#fbf7ea"
SITE = "jyotisha-insight.onrender.com"


def mark_svg(rounded=True, background=True, stroke=20):
    """The logo mark, 512x512. rounded: app-icon corners (off for Facebook, which crops to a circle)."""
    bg = (f'<rect width="512" height="512" rx="{104 if rounded else 0}" fill="{MAROON}"/>' if background else "")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">{bg}'
            f'<g fill="none" stroke="{GOLD}" stroke-width="{stroke}" stroke-linecap="square">'
            '<rect x="76" y="76" width="360" height="360"/><rect x="166" y="166" width="180" height="180"/>'
            '<path d="M166 76V166M256 76V166M346 76V166M166 346V436M256 346V436M346 346V436'
            'M76 166H166M76 256H166M76 346H166M346 166H436M346 256H436M346 346H436"/></g>'
            f'<circle cx="256" cy="256" r="34" fill="{GOLD}"/></svg>')


def small_mark_svg():
    """For 16-32 px: the frame and centre only, with heavier lines (the 12 small boxes blur at that size)."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" rx="96" fill="{MAROON}"/>'
            f'<g fill="none" stroke="{GOLD}" stroke-width="44"><rect x="78" y="78" width="356" height="356"/>'
            '<rect x="186" y="186" width="140" height="140"/>'
            '<path d="M256 78V186M256 326V434M78 256H186M326 256H434"/></g></svg>')


def _css(w, h, extra=""):
    from jyotisha_report import font_uri
    f = font_uri()
    return (f'@page {{ size: {w}px {h}px; margin: 0; }}'
            f'@font-face {{ font-family: NS; src: url("{f}/NotoSans-Bold.ttf"); font-weight: 700; }}'
            f'@font-face {{ font-family: NS; src: url("{f}/NotoSans.ttf"); }}'
            f'@font-face {{ font-family: NSS; src: url("{f}/NotoSansSinhala-Bold.ttf"); font-weight: 700; }}'
            f'@font-face {{ font-family: NSS; src: url("{f}/NotoSansSinhala.ttf"); }}'
            f'html, body {{ margin: 0; width: {w}px; height: {h}px; overflow: hidden; }}' + extra)


def render_png(body, w, h, extra_css="", transparent=False):
    """HTML -> PNG bytes at exactly w x h pixels (WeasyPrint, then PyMuPDF at 96 dpi = 1 px per CSS px)."""
    import pymupdf
    from weasyprint import HTML
    from jyotisha_report import HERE
    pdf = HTML(string=f"<html><head><style>{_css(w, h, extra_css)}</style></head><body>{body}</body></html>",
               base_url=HERE).write_pdf()
    pix = pymupdf.open(stream=pdf, filetype="pdf")[0].get_pixmap(dpi=96, alpha=transparent)
    assert (pix.width, pix.height) == (w, h), (pix.width, pix.height)
    return pix.tobytes("png")


def svg_png(svg, size, transparent=False):
    return render_png(svg.replace("<svg ", f'<svg width="{size}" height="{size}" '), size, size, transparent=transparent)


def wordmark(scale=1.0, align="left"):
    """JYOTHISHA INSIGHT, the gold rule, the Sinhala name and both taglines (the reports' cover style)."""
    s = scale
    return (f'<div style="text-align:{align}">'
            f'<div style="font:700 {round(64 * s)}px NS; letter-spacing:{round(11 * s)}px; color:{GOLD}">JYOTHISHA INSIGHT</div>'
            f'<div style="width:{round(300 * s)}px; height:{max(2, round(4 * s))}px; background:{GOLD}; margin:{round(18 * s)}px '
            f'{"auto" if align == "center" else "0"} {round(16 * s)}px {"auto" if align == "center" else "0"}"></div>'
            f'<div style="font:700 {round(46 * s)}px NSS; color:{CREAM}">ජ්‍යොතිෂ ඉන්සයිට්</div>'
            f'<div style="font:400 {round(27 * s)}px NSS; color:{CREAM}; opacity:.85; margin-top:{round(8 * s)}px">'
            'පාරම්පරික ජ්‍යොතිෂය · නවීන නිරවද්‍යතාව</div>'
            f'<div style="font:400 {round(22 * s)}px NS; color:{GOLD}; letter-spacing:{round(1.5 * s, 1)}px; margin-top:{round(6 * s)}px">'
            'Traditional astrology · modern precision</div></div>')


def fb_cover():
    """1640x624. Facebook shows the middle 1640x624 on desktop and crops the sides on phones,
    so the text stays in the middle ~1100 px and the faint chart frames sit at the edges, clear of it."""
    w, h = 1640, 624
    motif = mark_svg(rounded=False, background=False, stroke=12).replace("<svg ", '<svg width="560" height="560" ')
    body = (f'<div style="position:absolute; inset:0; background:{MAROON}"></div>'
            f'<div style="position:absolute; right:-217px; top:32px; opacity:.16">{motif}</div>'
            f'<div style="position:absolute; left:-230px; top:120px; opacity:.10">{motif}</div>'
            f'<div style="position:absolute; left:0; right:0; top:150px">{wordmark(1.0, "center")}'
            f'<div style="text-align:center; margin-top:34px; font:400 24px NSS; color:{CREAM}">'
            f'නොමිලේ ජන්ම පත්‍ර සාරාංශය · Free birth chart summary — <b style="color:{GOLD}; font-family:NS">{SITE}</b></div></div>')
    return render_png(body, w, h)


def og_image():
    """1200x630 link preview (Facebook, WhatsApp): the mark beside the wordmark."""
    w, h = 1200, 630
    body = (f'<div style="position:absolute; inset:0; background:{MAROON}"></div>'
            f'<div style="position:absolute; left:80px; top:165px">{mark_svg(rounded=True).replace("<svg ", "<svg width=300 height=300 ")}</div>'
            f'<div style="position:absolute; left:440px; top:178px; width:720px">{wordmark(0.86)}</div>'
            f'<div style="position:absolute; left:0; right:0; bottom:40px; text-align:center; font:400 24px NSS; color:{CREAM}">'
            f'නොමිලේ ජන්ම පත්‍ර සාරාංශය · Free birth chart summary — <b style="color:{GOLD}; font-family:NS">{SITE}</b></div>')
    return render_png(body, w, h)


def fb_profile():
    """1080x1080, full-bleed maroon. The frame spans 63 % of the width, so its corners stay inside
    the circle Facebook crops to (half-diagonal 477 px < radius 540 px)."""
    size, m = 1080, 960
    body = (f'<div style="position:absolute; inset:0; background:{MAROON}"></div>'
            f'<div style="position:absolute; left:{(size - m) // 2}px; top:{(size - m) // 2}px">'
            f'{mark_svg(rounded=False, background=False).replace("<svg ", f"<svg width={m} height={m} ")}</div>')
    return render_png(body, size, size)


def favicon_ico():
    """16/32/48 px in one .ico: the simple mark at 16 and 32, the full one at 48."""
    from PIL import Image
    imgs = {s: Image.open(io.BytesIO(svg_png(small_mark_svg() if s < 48 else mark_svg(), s, transparent=True))) for s in (16, 32, 48)}
    out = io.BytesIO()
    imgs[48].save(out, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)], append_images=[imgs[16], imgs[32]])
    return out.getvalue()


def main():
    web = os.path.join(ROOT, "web", "static")
    brand = os.path.join(ROOT, "brand")
    os.makedirs(web, exist_ok=True)
    os.makedirs(brand, exist_ok=True)
    files = {
        os.path.join(web, "favicon.svg"): mark_svg().encode(),
        os.path.join(web, "favicon.ico"): favicon_ico(),
        # iOS rounds the corners itself, so the home-screen icon is square
        os.path.join(web, "apple-touch-icon.png"): svg_png(mark_svg(rounded=False), 180),
        os.path.join(web, "og-image.png"): og_image(),
        os.path.join(brand, "logo.svg"): mark_svg().encode(),
        os.path.join(brand, "logo_1024.png"): svg_png(mark_svg(), 1024, transparent=True),
        os.path.join(brand, "fb_profile_1080.png"): fb_profile(),
        os.path.join(brand, "fb_cover_1640x624.png"): fb_cover(),
    }
    for path, data in files.items():
        with open(path, "wb") as f:
            f.write(data)
        print(f"{len(data) // 1024:5} KB  {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
