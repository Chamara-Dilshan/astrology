#!/usr/bin/env python3
"""jyotisha_gfx.py — Jyothisha Insight Facebook post වලට ඕනෑ රූප හදන script එක.

  python3 jyotisha_gfx.py --out gfx

හදන දේ (FB_POSTS_01-16.md අනුව):
  post02_lagna_chart.png        ලග්නය + භාව 12 කේන්දර රාමුව
  post05_houses.png             භාව 12 කාරණා සමඟ
  post08_time_compare.png       මිනිත්තු 20ක වෙනසකින් D9/D10 වෙනස් වීම (Reel එකට)
  post11_timezone.png           1996–2006 කාල කලාප වැරැද්ද
  post12_d9_split.png           රාශියක් අංශක 30 → නවාංශක 9
  post13_transit_<mm>.png       මාසික ගෝචරය — ලග්න 12ට වගුවක්
  post14_report_pages_*.png     වාර්තාවේ පිටු — පෞද්ගලික තොරතුරු blur කරලා
  post06_ayanamsa.png           සායන vs නිරයන — අංශක 24ක වෙනස
  chart_blank.png               හිස් දකුණු ඉන්දීය රාමුව (ඕනෑම post එකකට)

සටහන: රූප 1200×1200 (FB/IG square). Reel එකට 1080×1920 වෙනම හදනවා.
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jyotisha_calc as jc  # noqa: E402

SIGN_SI = ["මේෂ", "වෘෂභ", "මිථුන", "කටක", "සිංහ", "කන්‍යා", "තුලා", "වෘශ්චික", "ධනු", "මකර", "කුම්භ", "මීන"]
PL_SI = {"Su": "රවි", "Mo": "චන්ද්‍ර", "Ma": "කුජ", "Me": "බුධ", "Ju": "ගුරු", "Ve": "ශුක්‍ර", "Sa": "ශනි", "Ra": "රාහු", "Ke": "කේතු"}
HOUSE_SI = {1: "ශරීරය, පෞරුෂය", 2: "ධනය, කථනය, පවුල", 3: "සහෝදරයන්, ධෛර්යය", 4: "මව, නිවස, වාහන",
            5: "දරුවන්, බුද්ධිය", 6: "රෝග, ණය, තරඟ", 7: "විවාහය, සහකරු", 8: "හදිසි වෙනස්, උරුම",
            9: "පියා, වාසනාව, ධර්මය", 10: "රැකියාව, කීර්තිය", 11: "ලාභ, මිතුරන්", 12: "වියදම්, විදේශ"}
GRID = {11: (0, 0), 0: (1, 0), 1: (2, 0), 2: (3, 0), 10: (0, 1), 3: (3, 1), 9: (0, 2), 4: (3, 2),
        8: (0, 3), 7: (1, 3), 6: (2, 3), 5: (3, 3)}

BASE_CSS = """
@page { size: 1200px 1200px; margin: 0; }
@font-face { font-family: "NSS"; src: url("file://FONTDIR/NotoSansSinhala.ttf"); }
@font-face { font-family: "NS"; src: url("file://FONTDIR/NotoSans.ttf"); }
* { box-sizing: border-box; }
body { margin: 0; width: 1200px; height: 1200px; background: #fbf7ea; font-family: "NSS","NS",sans-serif; color: #1e1a1a;
       padding: 54px 54px 90px 54px; position: relative; }
.title { font-size: 46px; font-weight: 700; color: #6b1010; line-height: 1.25; }
.sub { font-size: 25px; color: #7a6f6f; margin-top: 10px; line-height: 1.4; }
.rule { width: 150px; height: 4px; background: #c9a24d; margin: 20px 0 26px 0; }
.wm { position: absolute; right: 54px; bottom: 40px; font-family: "NS",sans-serif; font-size: 17px; letter-spacing: 2.2px;
      color: #a08c6a; text-transform: uppercase; }
.note { font-size: 21px; color: #5a5050; line-height: 1.5; }
table { border-collapse: collapse; width: 100%; font-size: 22px; }
th { background: #6b1010; color: #fff; padding: 9px 11px; text-align: left; }
td { padding: 8px 11px; border-bottom: 1px solid #e0d6bf; }
tr:nth-child(even) td { background: #f6f0e0; }
.sic { position: relative; border: 3px solid #3b2f2f; background: #fffdf7; }
.sic .c { position: absolute; width: 25%; height: 25%; border: 1.5px solid #3b2f2f; padding: 7px 9px; overflow: hidden; }
.sic .c .sn { font-size: 17px; color: #8a7f7f; }
.sic .c .pl { font-size: 23px; line-height: 1.3; }
.sic .c .pl b { color: #8b1a1a; }
.sic .c .hn { font-size: 34px; font-weight: 700; color: #c9a24d; }
.sic .mid { position: absolute; left: 25%; top: 25%; width: 50%; height: 50%; display: flex; flex-direction: column;
            align-items: center; justify-content: center; text-align: center; }
.sic .mid .t { font-size: 30px; font-weight: 700; color: #3b2f2f; }
.sic .mid .s { font-size: 18px; color: #8a7f7f; margin-top: 8px; }
.hl { background: #f7e3c8 !important; }
.bad { color: #8b1a1a; font-weight: 700; }
.ok { color: #2f6b2f; font-weight: 700; }
.two { display: flex; gap: 30px; }
.two > div { flex: 1; }
"""


def chart_html(labels, title, sub="", size=760, house_numbers_from=None):
    cells = []
    for si, (cx, cy) in GRID.items():
        labs = labels.get(si, [])
        inner = ""
        if house_numbers_from is not None:
            inner += f'<div class="hn">{jc.house_from(house_numbers_from, si)}</div>'
        inner += "<div class='pl'>" + "<br>".join(f"<b>{x}</b>" if x.startswith("ලග්න") else x for x in labs[:5]) + "</div>"
        cells.append(f'<div class="c" style="left:{cx * 25}%;top:{cy * 25}%"><div class="sn">{SIGN_SI[si]}</div>{inner}</div>')
    mid = f'<div class="mid"><div class="t">{title}</div>' + (f'<div class="s">{sub}</div>' if sub else "") + "</div>"
    return f'<div class="sic" style="width:{size}px;height:{size}px;margin:0 auto">' + "".join(cells) + mid + "</div>"


def render(body, path, w=1200, h=1200, extra_css=""):
    css = BASE_CSS.replace("FONTDIR", os.path.join(HERE, "fonts")).replace("1200px 1200px", f"{w}px {h}px")
    css = css.replace("width: 1200px; height: 1200px;", f"width: {w}px; height: {h}px;")
    html = (f'<!DOCTYPE html><html lang="si"><head><meta charset="utf-8">'
            f'<style>{css}{extra_css}</style></head><body>{body}<div class="wm">Jyothisha Insight</div></body></html>')
    from weasyprint import HTML
    pdf = path.replace(".png", ".pdf")
    HTML(string=html, base_url=HERE).write_pdf(pdf)
    subprocess.run(["pdftoppm", "-r", "96", "-png", "-singlefile", pdf, path[:-4]], check=True)
    os.remove(pdf)
    print("  " + os.path.basename(path))


def sample_chart(date="1999-10-28", time="08:11", lat=7.9403, lon=81.0188, tz="Asia/Colombo"):
    jd, _ = jc.to_jd_ut(datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M"), tz)
    pos, _ = jc.compute_positions(jd)
    lag = jc.compute_lagna(jd, lat, lon)
    return pos, lag, jc.sign_of(lag)


def g_blank(out):
    labels = {}
    render(f'<div class="title">දකුණු ඉන්දීය කේන්දර රාමුව</div><div class="rule"></div>'
           + chart_html(labels, "රාශි චක්‍රය", "රාශි 12 ස්ථානය ස්ථිරයි", 800),
           os.path.join(out, "chart_blank.png"))


def g_post02(out):
    pos, lag, ls = sample_chart()
    labels = {ls: ["ලග්නය"]}
    render(f'<div class="title">ලග්නය කියන්නේ මොකක්ද?</div>'
           f'<div class="sub">ඔබ උපන් මොහොතේ නැගෙනහිර උදා වෙමින් තිබුණු රාශිය</div><div class="rule"></div>'
           + chart_html(labels, "ලග්නය = 1 වන භාවය", "අනිත් භාව 11 මෙතැනින් ගණන් වෙනවා", 760, house_numbers_from=ls),
           os.path.join(out, "post02_lagna_chart.png"))


def g_post05(out):
    pos, lag, ls = sample_chart()
    labels = {(ls + h - 1) % 12: [HOUSE_SI[h]] for h in range(1, 13)}
    render('<div class="title">කේන්දරයේ භාව 12</div>'
           '<div class="sub">එක් එක් කොටුව ජීවිතයේ වෙන වෙන පැත්තක්</div><div class="rule"></div>'
           + chart_html(labels, "භාව 12", "ලග්නයෙන් ගණන් වෙනවා", 780, house_numbers_from=ls),
           os.path.join(out, "post05_houses.png"))


def g_post08(out):
    """Two births 20 minutes apart — D9/D10 lagna differ."""
    rows = []
    for t in ("08:11", "08:31"):
        pos, lag, ls = sample_chart(time=t)
        rows.append((t, ls, jc.varga_sign(lag, 9), jc.varga_sign(lag, 10), jc.varga_sign(lag, 60)))
    (t1, l1, d9a, d10a, d60a), (t2, l2, d9b, d10b, d60b) = rows
    def cell(a, b):
        same = a == b
        return f'<td class="{"ok" if same else "bad"}">{SIGN_SI[a]}</td>', f'<td class="{"ok" if same else "bad"}">{SIGN_SI[b]}</td>'
    body = ('<div class="title">උපන් වේලාව මිනිත්තු 20කින් වැරදුනොත්?</div>'
            f'<div class="sub">එකම දිනය, එකම ස්ථානය — වෙනස මිනිත්තු 20යි</div><div class="rule"></div>'
            '<table style="font-size:30px"><tr><th>කේන්දරය</th><th>වේලාව</th><th>ලග්නය</th>'
            '<th>D9 (විවාහය)</th><th>D10 (රැකියාව)</th><th>D60</th></tr>')
    for label, (t, ls, d9, d10, d60) in zip(("පළමු", "දෙවන"), rows):
        body += (f'<tr><td><b>{label}</b></td><td>{t}</td><td>{SIGN_SI[ls]}</td>'
                 f'<td class="{"ok" if d9a == d9b else "bad"}">{SIGN_SI[d9]}</td>'
                 f'<td class="{"ok" if d10a == d10b else "bad"}">{SIGN_SI[d10]}</td>'
                 f'<td class="{"ok" if d60a == d60b else "bad"}">{SIGN_SI[d60]}</td></tr>')
    body += ('</table><div class="note" style="margin-top:34px">'
             'ලග්නය <b>එකමයි</b> — ඒත් විවාහය බලන නවාංශකයත් (D9), රැකියාව බලන දශාංශකයත් (D10) '
             '<span class="bad">වෙනස්</span>.<br><br>'
             'ඒ කියන්නේ විවාහය සහ රැකියාව ගැන පිළිතුරු දෙකක්ම වෙනස් වෙන්න පුළුවන්. '
             'ඒකයි අපි වාර්තාවේ <b>“උපන් වේලාව නිශ්චිතද ආසන්නද”</b> කියලා ලියන්නේ.</div>')
    render(body, os.path.join(out, "post08_time_compare.png"))
    # vertical version for the reel
    render(body, os.path.join(out, "post08_time_compare_reel.png"), 1080, 1920)


def g_post11(out):
    body = ('<div class="title">1996–2006 අතර උපන් අයට<br>වැදගත් දෙයක්</div>'
            '<div class="sub">ලංකාවේ කාල කලාපය හැම විටම +5:30 නෙවෙයි</div><div class="rule"></div>'
            '<table style="font-size:28px"><tr><th>කාලය</th><th>UTC offset</th></tr>'
            '<tr><td>1996 මැයි 25 – ඔක්තෝබර් 26</td><td class="bad">+6:30</td></tr>'
            '<tr><td>1996 ඔක්තෝබර් 26 – 2006 අප්‍රේල් 15</td><td class="bad">+6:00</td></tr>'
            '<tr><td>2006 අප්‍රේල් 15 සිට අද දක්වා</td><td class="ok">+5:30</td></tr></table>'
            '<div class="note" style="margin-top:36px">'
            'ඒ කාලයේ උපන් අයෙකුගේ කේන්දරය <b>+5:30</b> පාවිච්චි කරලා ගණන් කළොත් — වෙනස <b class="bad">විනාඩි 30ක්</b>.<br><br>'
            'විනාඩි 30කින් ලග්නය සමහර විට වෙනස්ම රාශියක්. නවාංශකය සහ දශාංශකය <b class="bad">නිසැකවම</b> වෙනස්.<br><br>'
            'පරණ කේන්දරයක් තියෙනවා නම් — ආපහු පරීක්ෂා කරගන්න වටිනවා.</div>')
    render(body, os.path.join(out, "post11_timezone.png"))


def g_post12(out):
    cells = "".join(f'<div style="flex:1;border:2px solid #3b2f2f;background:#fffdf7;padding:10px 6px;text-align:center">'
                    f'<div style="font-size:19px;color:#8a7f7f">නවාංශක {i + 1}</div>'
                    f'<div style="font-size:22px;margin-top:6px">{i * 3}°20′</div></div>' for i in range(9))
    body = ('<div class="title">නවාංශකය (D9) ඇයි වැදගත්?</div>'
            '<div class="sub">රාශියක් අංශක 30යි — ඒක කොටස් 9කට බෙදුවම නවාංශකය</div><div class="rule"></div>'
            '<div style="border:3px solid #6b1010;padding:16px;text-align:center;font-size:30px;background:#fff">'
            'රාශියක් = අංශක 30</div>'
            '<div style="text-align:center;font-size:40px;color:#c9a24d;margin:14px 0">↓ කොටස් 9කට ↓</div>'
            f'<div style="display:flex;gap:6px">{cells}</div>'
            '<div class="note" style="margin-top:34px">'
            'D9 බලන්නේ <b>විවාහය</b>, අභ්‍යන්තර ශක්තිය සහ ග්‍රහයාගේ ඇත්ත බලය.<br>'
            'රාශි කේන්දරයේ ශක්තිමත් පෙනෙන ග්‍රහයෙක් D9 එකේ දුර්වල නම් — ප්‍රතිඵල අඩුවෙන්.<br><br>'
            'රැකියාවට <b>D10</b> · දරුවන්ට <b>D7</b> · අධ්‍යාපනයට <b>D24</b> · පූර්ව කර්මයට <b>D60</b>.</div>')
    render(body, os.path.join(out, "post12_d9_split.png"))


def g_post06(out):
    body = ('<div class="title">ලාහිරි අයනාංශය කියන්නේ?</div>'
            '<div class="sub">බටහිර සහ වෛදික ජ්‍යොතිෂයේ රාශි වෙනස් වෙන්නේ ඇයි</div><div class="rule"></div>'
            '<div class="two" style="margin-top:20px">'
            '<div style="border:3px solid #8a7f7f;padding:22px;background:#fff">'
            '<div style="font-size:28px;font-weight:700;color:#5a5050">සායන (බටහිර)</div>'
            '<div style="font-size:22px;margin-top:12px;line-height:1.5">සෘතු අනුව.<br>වසන්ත විෂුවය = මේෂ 0°</div></div>'
            '<div style="border:3px solid #6b1010;padding:22px;background:#fff">'
            '<div style="font-size:28px;font-weight:700;color:#6b1010">නිරයන (වෛදික)</div>'
            '<div style="font-size:22px;margin-top:12px;line-height:1.5">ඇත්ත තාරකා අනුව.<br>අපි පාවිච්චි කරන ක්‍රමය</div></div>'
            '</div>'
            '<div style="text-align:center;margin-top:30px;font-size:46px;font-weight:700;color:#c9a24d">වෙනස ≈ 24°</div>'
            '<div class="note" style="margin-top:26px">'
            'පෘථිවියේ අක්ෂය හෙමින් කැරකෙන නිසා (precession), වසර 72කට වරක් විතර මේ පරතරය අංශක 1කින් වැඩි වෙනවා.<br><br>'
            'අපි පාවිච්චි කරන්නේ <b>ලාහිරි</b> — ඉන්දියානු රජය 1955දී නිල ලෙස පිළිගත් ක්‍රමය. '
            'වෙනත් ක්‍රම (රාමන්, KP) අංශක 1කින් විතර වෙනස්.<br><br>'
            '<b>අපේ හැම වාර්තාවකම කුමන අයනාංශය කියලා ලියලා තියෙනවා.</b></div>')
    render(body, os.path.join(out, "post06_ayanamsa.png"))


def g_post13(out, date=None):
    """Monthly transit table for all 12 lagnas."""
    d = date or datetime.now().strftime("%Y-%m-%d")
    jd, _ = jc.to_jd_ut(datetime.strptime(d + " 12:00", "%Y-%m-%d %H:%M"), "Asia/Colombo")
    pos, _ = jc.compute_positions(jd)
    sa, ju, ra = (jc.sign_of(pos[p]["lon"]) for p in ("Sa", "Ju", "Ra"))
    rows = "".join(
        f'<tr><td><b>{SIGN_SI[ls]}</b></td><td>{jc.house_from(ls, sa)}</td><td>{jc.house_from(ls, ju)}</td>'
        f'<td>{jc.house_from(ls, ra)}</td><td>{HOUSE_SI[jc.house_from(ls, ju)]}</td></tr>' for ls in range(12))
    body = (f'<div class="title">{d[:7]} — ලග්න 12ට</div>'
            f'<div class="sub">ශනි {SIGN_SI[sa]} · ගුරු {SIGN_SI[ju]} · රාහු {SIGN_SI[ra]}</div><div class="rule"></div>'
            '<table style="font-size:23px"><tr><th>ලග්නය</th><th>ශනි</th><th>ගුරු</th><th>රාහු</th>'
            '<th>ගුරු ගෝචරයේ ක්ෂේත්‍රය</th></tr>' + rows + '</table>'
            '<div class="note" style="margin-top:24px;font-size:19px">'
            'අංක = ඔබේ ලග්නයෙන් ගණන් කරන භාවය. මේවා <b>පොදු</b> ප්‍රවණතා — '
            'ඔබේ දශාව සමඟ ගැලපුණාම තමයි සිදුවීම් එන්නේ.</div>')
    render(body, os.path.join(out, f"post13_transit_{d[:7].replace('-', '')}.png"))


def g_post14(out, report_pdf):
    """Blur personal fields on the first pages of a sample report."""
    if not os.path.exists(report_pdf):
        print(f"  (skip post14 — {report_pdf} නැත)")
        return
    from PIL import Image, ImageFilter
    tmp = os.path.join(out, "_rp")
    subprocess.run(["pdftoppm", "-r", "110", "-f", "1", "-l", "6", "-png", report_pdf, tmp], check=True)
    # blur the personal fields: cover name/birth line, and the birth-data table values on page 2
    boxes = {1: [(0.15, 0.235, 0.85, 0.325)],
             2: [(0.33, 0.395, 0.96, 0.58)]}
    for i in range(1, 7):
        p = f"{tmp}-{i:02d}.png" if os.path.exists(f"{tmp}-{i:02d}.png") else f"{tmp}-{i}.png"
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGB")
        W, H = im.size
        for (x0, y0, x1, y1) in boxes.get(i, []):
            box = (int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))
            im.paste(im.crop(box).filter(ImageFilter.GaussianBlur(14)), box)
        im.save(os.path.join(out, f"post14_report_page{i}.png"))
        os.remove(p)
    print("  post14_report_page1..6.png")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="gfx")
    ap.add_argument("--report", default="sample_A1_natal.pdf", help="post 14 සඳහා සාම්පල් වාර්තාව")
    ap.add_argument("--transit-date", help="post 13 සඳහා දිනය (YYYY-MM-DD)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    print("හදනවා:")
    g_blank(a.out)
    g_post02(a.out)
    g_post05(a.out)
    g_post06(a.out)
    g_post08(a.out)
    g_post11(a.out)
    g_post12(a.out)
    g_post13(a.out, a.transit_date)
    g_post14(a.out, a.report)
    print(f"\nඉවරයි → {a.out}/")


if __name__ == "__main__":
    main()
