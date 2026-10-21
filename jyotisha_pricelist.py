#!/usr/bin/env python3
"""jyotisha_pricelist.py — Jyothisha Insight සේවා මෙනුව / මිල ලැයිස්තුව

මිල වෙනස් කරන්න: prices.json එකේ අගයන් වෙනස් කර නැවත run කරන්න.
  python3 jyotisha_pricelist.py --prices prices.json --out pricelist.pdf
  python3 jyotisha_pricelist.py --dump-prices prices.json      # පෙරනිමි මිල file එකක් ලියයි
"""
import argparse
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BRAND = "Jyothisha Insight"
BRAND_TAGLINE = "පාරම්පරික ජ්‍යොතිෂය · නවීන නිරවද්‍යතාව"
BRAND_CONTACT = ""

# ---------------------------------------------------------------- default catalogue
# price = රු. (market-based placeholder — ඔබේ තීරණය අනුව වෙනස් කරන්න)
CATALOG = [
    ("ජන්ම කේන්දර වාර්තා", [
        dict(code="A1", name="කේන්දර සාර", desc="ලග්නය, ග්‍රහ ස්ථාන, නවාංශකය, ප්‍රධාන යෝග, විම්ශෝත්තරී දශා, ගෝචරය සහ ඉදිරි වසර 3ේ ප්‍රවණතා",
             pages=8, days="2–3", price=2500),
        dict(code="A2", name="සම්පූර්ණ කේන්දර විග්‍රහය", desc="A1 සියල්ල + D10, අෂ්ටකවර්ග, ජීවන ක්ෂේත්‍ර 5ක් (රැකියාව, විවාහය, ධනය, අධ්‍යාපනය, පවුල), නාරායණ දශා, සඩේ සති කාල රේඛාව, ඉදිරි වසර 5",
             pages=12, days="3–4", price=5000, extra="ප්‍රශ්න 2ක්"),
        dict(code="A3", name="ගැඹුරු කේන්දර විග්‍රහය", desc="A2 සියල්ල + වර්ග කේන්දර 8ක් (D2, D4, D7, D9, D10, D12, D24, D60), සම්පූර්ණ යෝග ලැයිස්තුව, අර්ගල, උපග්‍රහ, කාලචක්‍ර දශා, ඉදිරි වසර 10",
             pages=16, days="5–7", price=9500, extra="ප්‍රශ්න 5ක් + විනාඩි 20 ඇමතුමක්"),
    ]),
    ("එක් ක්ෂේත්‍රයක් පමණක්", [
        dict(code="B1", name="විවාහ විග්‍රහය", desc="7 වන භාවය, උපපදය, දාරාකාරක, නවාංශකය සහ විවාහ කාල කවුළු", pages=6, days="3–4", price=3000),
        dict(code="B2", name="වෘත්තීය විග්‍රහය", desc="10 වන භාවය, දශාංශකය (D10), අමාත්‍යකාරක සහ රැකියා වෙනස්කම් කාල", pages=6, days="3–4", price=3000),
        dict(code="B3", name="අධ්‍යාපන විග්‍රහය", desc="4/5/9 භාව, චතුර්විංශාංශකය (D24), විෂය ප්‍රවණතාව සහ විභාග කාල", pages=6, days="3–4", price=3000),
        dict(code="B4", name="ධන විග්‍රහය", desc="2/11 භාව, හෝරා කේන්දරය (D2), ධන යෝග සහ ආදායම් රටාව", pages=6, days="3–4", price=3000),
        dict(code="B5", name="සන්තාන විග්‍රහය", desc="5 වන භාවය, සප්තාංශකය (D7), පුත්‍රකාරක", pages=6, days="3–4", price=3000),
        dict(code="B6", name="විදේශ විග්‍රහය", desc="12/9/3 භාව, චතුර්ථාංශකය (D4), රාහු සහ විදේශ කාල කවුළු", pages=6, days="3–4", price=3000),
        dict(code="B7", name="දේපල විග්‍රහය", desc="4 වන භාවය, D4, කුජ සහ ශුක්‍ර — නිවස, ඉඩම්, වාහන", pages=6, days="3–4", price=3000),
        dict(code="B8", name="මාතෘ–පිතෘ විග්‍රහය", desc="4/9 භාව, ද්වාදශාංශකය (D12) — දෙමව්පියන් සමඟ සම්බන්ධතාව", pages=5, days="3–4", price=3000),
    ], "ක්ෂේත්‍ර 3ක් එකට ගත්තොත්: රු. {bundle3}"),
    ("වාර්ෂික සහ කාල වාර්තා", [
        dict(code="C1", name="වාර්ෂික ඵල", desc="තාජක වර්ෂ කුණ්ඩලිය, මුන්ථා, වර්ෂේශ, තාජක යෝග, සහම් සහ මුද්දා දශා", pages=5, days="2–3", price=2500),
        dict(code="C2", name="වාර්ෂික ඵල + ගෝචර දින දර්ශනය", desc="C1 සියල්ල + වර්ෂය තුළ ගෝචරය සහ මාසික සම්මුඛ දින දර්ශනය (මාසයකට දශා + ගෝචරය එකට)",
             pages=7, days="3–4", price=4000),
        dict(code="C3", name="සඩේ සති වාර්තාව", desc="අවධි 3ේ කාල රේඛාව, ජන්ම ශනිගේ තත්ත්වය, අෂ්ටකවර්ග බින්දු සහ ප්‍රායෝගික ආකල්ප", pages=5, days="2–3", price=2500),
        dict(code="C4", name="දශා සන්ධි වාර්තාව", desc="මහා දශා මාරුව වටා අවුරුදු 1 ± — කුමක් වෙනස් වේද, කෙසේ සූදානම් වේද", pages=4, days="2–3", price=2500),
        dict(code="C6", name="මාස ඵල", desc="තාජක මාසික කුණ්ඩලිය සහ මාසේශ (වාර්ෂික වාර්තාවට අතිරේකයක්)", pages=3, days="1–2", price=1200),
    ]),
    ("පොරොන්දම්", [
        dict(code="D1", name="පොරොන්දම් සාර", desc="අෂ්ටකූට 8 (ලකුණු 36), භකූට/නාඩි දෝෂ සහ නිෂ්ප්‍රභ වීම්, කුජ දෝෂය", pages=5, days="2–3", price=2500),
        dict(code="D2", name="සම්පූර්ණ පොරොන්දම්", desc="D1 සියල්ල + කේන්දර දෙකේ සංයෝජනය (synastry), 7 වන භාවය/උපපදය/දාරාකාරක සංසන්දනය, නවාංශක දෙක සහ විවාහ දශා කවුළු ගැලපීම",
             pages=6, days="5–7", price=6500),
        dict(code="D3", name="යෝජනා සංසන්දනය", desc="යෝජනා කිහිපයක් එකම වගුවක — අෂ්ටකූට, දෝෂ, සංයෝජනය අනුව පෙළගැස්වීම", pages=4, days="3–4", price=3500,
             extra="යෝජනා 3ක් දක්වා; ඉන් පසු එකකට රු. {extra_match}"),
    ]),
    ("විශේෂ වාර්තා", [
        dict(code="E1", name="උපන් වේලාව නිවැරදි කිරීම", desc="පසුගිය සිදුවීම් අනුව උපන් වේලාව scan කර වඩාත් ගැලපෙන කාල කවුළු යෝජනා කිරීම",
             pages=6, days="5–7", price=5500, extra="සිදුවීම් 5ක් වත් අවශ්‍යයි"),
        dict(code="M1", name="නැකත් (මුහූර්ත)", desc="විවාහය, ගෘහ ප්‍රවේශය, ව්‍යාපාර ආරම්භය ආදී කාර්යයන්ට සුබ කවුළු — දින පරාසයක් තුළ",
             pages=5, days="2–3", price=3000, extra="ලිත් නැකතට දෙවන මතයක්"),
        dict(code="N", name="නාම නක්ෂත්‍රය", desc="දරුවාගේ නම පටන් ගත යුතු අකුර සහ නැකතේ පාද 4ේ අකුරු", pages=3, days="1", price=1000),
        dict(code="P1", name="ප්‍රශ්න වාර්තාව", desc="ප්‍රශ්නය අසන මොහොතේ කේන්දරය — තාජක යෝග, කාරක විග්‍රහය", pages=5, days="1–2", price=2000),
        dict(code="P2", name="ප්‍රශ්න + ෂට්පංචාශිකා", desc="P1 සියල්ල + ෂට්පංචාශිකා ශ්ලෝක නියම (නැතිවූ දේ, ගමන්, ආරවුල්, සුවතාව ආදිය)", pages=5, days="2–3", price=3000),
    ]),
]
ADDONS = [
    dict(name="අමතර ප්‍රශ්න 3ක් (WhatsApp)", price=800),
    dict(name="දුරකථන/වීඩියෝ ඇමතුම — විනාඩි 30", price=2500),
    dict(name="ප්‍රතිකර්ම කොටස (මන්ත්‍ර, දාන, ආකල්ප)", price=800),
    dict(name="ඉංග්‍රීසි පිටපත", price=1500),
    dict(name="ගණන් කළ දත්ත (JSON + SVG) — ඉගෙන ගන්නා අයට", price=1000),
]
DEFAULTS = dict(bundle3=7500, extra_match=1200, subscription=2000)

FREE_BLURB = ("<b>නොමිලේ:</b> ලග්නය, චන්ද්‍ර රාශිය, ජන්ම නැකත, නාම අකුර සහ වත්මන් මහා දශාව — එක් පිටුවක්. "
              "Facebook පිටුවේ පෝරමය පුරවා ඉල්ලන්න.")


def build_html(prices):
    def P(code, default):
        return prices.get(code, default)
    css = """
@page { size: A4; margin: 14mm 12mm 16mm 12mm;
  @bottom-left { content: "BRANDNAME"; font-family: "Noto Sans"; font-size: 7.5pt; color: #a08c6a; letter-spacing: .5px; }
  @bottom-right { content: "පිටුව " counter(page) " / " counter(pages); font-family: "Noto Sans Sinhala"; font-size: 8pt; color: #7a6f6f; } }
@font-face { font-family: "Noto Sans Sinhala"; src: url("file://FONTDIR/NotoSansSinhala.ttf"); }
@font-face { font-family: "Noto Sans"; src: url("file://FONTDIR/NotoSans.ttf"); }
body { font-family: "Noto Sans Sinhala", "Noto Sans", sans-serif; font-size: 9.4pt; color: #1e1a1a; line-height: 1.45; }
.brandmark { font-family: "Noto Sans", sans-serif; font-size: 16pt; letter-spacing: 2.5px; color: #6b1010; font-weight: 700; text-transform: uppercase; text-align:center; }
.brandline { width: 46mm; height: 2px; background: #c9a24d; margin: 6pt auto 4pt auto; }
.brandtag { font-size: 9pt; color: #8a7f7f; text-align:center; letter-spacing:.5px; }
h1 { font-size: 15pt; color: #6b1010; text-align:center; margin: 10pt 0 2pt 0; }
h2 { font-size: 11.5pt; color: #6b1010; border-bottom: 1.5px solid #c9a24d; padding-bottom: 2pt; margin: 12pt 0 5pt 0; page-break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 3pt 0 6pt 0; font-size: 8.9pt; }
thead { display: table-header-group; }
th { background: #6b1010; color: #fff; padding: 3pt 4pt; text-align: left; font-weight: 600; }
td { padding: 3pt 4pt; border-bottom: 1px solid #e4dccb; vertical-align: top; }
tr:nth-child(even) td { background: #faf6ee; }
tr { page-break-inside: avoid; }
.price { text-align: right; white-space: nowrap; font-weight: 700; }
.code { font-family: "Noto Sans", sans-serif; font-weight: 700; color: #6b1010; }
.box { border: 1px solid #d9cfa8; background: #fbf7ea; padding: 6pt 8pt; border-radius: 4pt; margin: 6pt 0; }
.muted { color: #7a6f6f; font-size: 8.2pt; }
.note { border-left: 4px solid #c9a24d; background: #fbf7ea; padding: 5pt 8pt; margin: 6pt 0; font-size: 8.6pt; }
ul { margin: 3pt 0 5pt 15pt; padding: 0; } li { margin: 1.5pt 0; }
.pb { page-break-before: always; }
"""
    H = [f'<div class="brandmark">{BRAND}</div><div class="brandline"></div><div class="brandtag">{BRAND_TAGLINE}</div>',
         '<h1>සේවා මෙනුව සහ මිල ලැයිස්තුව</h1>',
         f'<div class="box">{FREE_BLURB}</div>']
    for block in CATALOG:
        title, items = block[0], block[1]
        foot = block[2] if len(block) > 2 else None
        H.append(f"<h2>{title}</h2>")
        H.append("<table><tr><th style='width:7%'>කේතය</th><th style='width:22%'>වාර්තාව</th><th>අන්තර්ගතය</th>"
                 "<th style='width:7%'>පිටු</th><th style='width:9%'>වැඩ දින</th><th style='width:11%'>මිල (රු.)</th></tr>")
        for it in items:
            pr = P(it["code"], it["price"])
            extra = it.get("extra", "")
            if extra:
                extra = extra.format(extra_match=P("extra_match", DEFAULTS["extra_match"]))
                extra = f'<br><span class="muted">ඇතුළත්: {extra}</span>'
            H.append(f"<tr><td class='code'>{it['code']}</td><td><b>{html.escape(it['name'])}</b></td>"
                     f"<td>{html.escape(it['desc'])}{extra}</td><td>{it['pages']}</td><td>{it['days']}</td>"
                     f"<td class='price'>{pr:,}</td></tr>")
        H.append("</table>")
        if foot:
            H.append(f'<p class="muted">{foot.format(bundle3=P("bundle3", DEFAULTS["bundle3"]))}</p>')
    H.append('<div class="pb"></div><h2>අමතර සේවා</h2>')
    H.append("<table><tr><th>සේවාව</th><th style='width:16%'>මිල (රු.)</th></tr>"
             + "".join(f"<tr><td>{html.escape(x['name'])}</td><td class='price'>{P(x['name'], x['price']):,}</td></tr>" for x in ADDONS)
             + f"<tr><td>වාර්ෂික දායකත්වය — හැම උපන් දිනයකටම වාර්ෂික ඵල වාර්තාව</td>"
               f"<td class='price'>{P('subscription', DEFAULTS['subscription']):,}/වසර</td></tr></table>")
    H.append("<h2>කෙසේ ඇණවුම් කරන්නද?</h2><ul>"
             "<li>Facebook පිටුවේ ඇති පෝරමය පුරවන්න (හෝ WhatsApp හරහා ලියන්න)</li>"
             "<li>පැය 24ක් ඇතුළත වාර්තා වර්ගය, මිල සහ ලබාදෙන දිනය WhatsApp හරහා තහවුරු කරමු</li>"
             "<li>ගෙවීමෙන් පසු වැඩ ආරම්භ වේ; වාර්තාව PDF ලෙස WhatsApp/Email හරහා ලැබේ</li></ul>")
    H.append('<div class="note"><b>උපන් වේලාව:</b> හැකි නම් රෝහල් උපන් සහතිකයේ වේලාව දෙන්න. '
             'වේලාව ආසන්න නම් ඒ බව කියන්න — වාර්තාවේ අදාළ කොටස් ප්‍රවේශමෙන් ලියනවා, '
             'අවශ්‍ය නම් උපන් වේලාව නිවැරදි කිරීමේ වාර්තාව (E1) යෝජනා කරනවා.</div>')
    H.append('<h2>ක්‍රමවේදය</h2><p class="muted">ගණනය Swiss Ephemeris මත; ලාහිරි අයනාංශය, සම්පූර්ණ රාශි භාව ක්‍රමය, මධ්‍යම රාහු–කේතු. '
             'පරාශර සහ ජෛමිනි සම්ප්‍රදාය; ප්‍රධාන යොමුව P.V.R. Narasimha Rao ගේ <i>Vedic Astrology: An Integrated Approach</i>. '
             'සෑම වාර්තාවක්ම මිනිසෙකු විසින් පරීක්ෂා කර, අර්ථකථනය ලියා ලබාදේ.</p>')
    H.append('<div class="note"><b>අප නොකරන දේ:</b> ආයුෂ හෝ මරණය පිළිබඳ අනාවැකි · රෝග විනිශ්චය හෝ වෛද්‍ය උපදෙස් · '
             'මූල්‍ය ආයෝජන හෝ නීතිමය උපදෙස් · නූපන් දරුවෙකුගේ ලිංගය · අනෙකෙකුගේ අනුදැනුමකින් තොරව ඔවුන්ගේ පෞද්ගලික කාරණා. '
             'වාර්තා ප්‍රවණතා පෙන්වන අතර, තීරණය සැමවිටම ඔබේ.</div>')
    H.append(f'<div style="text-align:center; margin-top:12pt; padding-top:8pt; border-top:1px solid #e4dccb">'
             f'<div class="brandmark" style="font-size:11pt">{BRAND}</div><div class="brandtag" style="font-size:8pt">{BRAND_TAGLINE}</div>'
             + (f'<div class="muted">{html.escape(BRAND_CONTACT)}</div>' if BRAND_CONTACT else "") + "</div>")
    fontdir = os.path.join(HERE, "fonts")
    return (f'<!DOCTYPE html><html lang="si"><head><meta charset="utf-8"><title>{BRAND} — මිල ලැයිස්තුව</title>'
            f'<style>{css.replace("FONTDIR", fontdir).replace("BRANDNAME", BRAND)}</style></head><body>'
            + "\n".join(H) + "</body></html>")


def default_prices():
    p = {}
    for block in CATALOG:
        for it in block[1]:
            p[it["code"]] = it["price"]
    for x in ADDONS:
        p[x["name"]] = x["price"]
    p.update(DEFAULTS)
    return p


def main():
    global BRAND, BRAND_CONTACT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prices", help="JSON file with {code: price}")
    ap.add_argument("--dump-prices", help="write the default price file and exit")
    ap.add_argument("--brand", default=BRAND)
    ap.add_argument("--brand-contact", default="")
    ap.add_argument("--out", default="pricelist.pdf")
    ap.add_argument("--html", help="also save the HTML")
    a = ap.parse_args()
    if a.dump_prices:
        with open(a.dump_prices, "w", encoding="utf-8") as f:
            json.dump(default_prices(), f, ensure_ascii=False, indent=1)
        print(f"default prices written: {a.dump_prices} — අගයන් වෙනස් කර --prices සමඟ නැවත run කරන්න")
        return
    BRAND, BRAND_CONTACT = a.brand, a.brand_contact
    prices = json.load(open(a.prices, encoding="utf-8")) if a.prices else {}
    page = build_html(prices)
    if a.html:
        open(a.html, "w", encoding="utf-8").write(page)
    from weasyprint import HTML
    HTML(string=page, base_url=HERE).write_pdf(a.out)
    print(f"PDF written: {a.out}")


if __name__ == "__main__":
    main()
