"""Copyable Sinhala in the PDFs.

WeasyPrint 70.0 tells PDF readers which letters each glyph stands for in one table (ToUnicode), filled
from the first time it draws each glyph. Sinhala often draws one syllable with two or more glyphs (the
kombuva of "දෝ" comes first, then the consonant), and WeasyPrint gives every glyph but the last of such
a syllable an empty string. A glyph like ද that first appears at the start of "දා" is then empty for the
whole document, so copying or searching gives "r,දෝෂ" for "දෝෂ" and "සිකු7ා,ා" for "සිකුරාදා".

No glyph table can be right anyway: the kombuva is drawn before the consonant but written after it. So
this module wraps every multi-glyph syllable in a PDF ActualText span carrying its real text, which
Acrobat, Chrome (PDFium), pdf.js and MuPDF use for copying and search. As a fallback for readers that
ignore ActualText, a glyph drawn alone records its exact text, and one inside a longer syllable gets its
own letter from the font.

`draw_first_line` below is WeasyPrint 70.0's (weasyprint/draw/text.py, BSD-3-Clause, © Kozea) with
those changes, marked "Jyothisha:". install() swaps it in only if WeasyPrint's own function is still the
one it was adapted from (requirements.lock pins 70.0); otherwise it warns and leaves WeasyPrint alone,
so the PDFs still render correctly, just with WeasyPrint's text map.
"""
import collections
import hashlib
import inspect
import sys
from io import BytesIO
from xml.etree import ElementTree

ADAPTED_FROM = "70.0"
ORIGINAL_SHA256 = "1bb8eae6d88e71b17096a034656f3be17da8f1f513c78536c1c38d971927638b"
ORIGINAL = None         # WeasyPrint's own draw_first_line, once install() has replaced it (tests compare)
_REVERSE_CMAPS = {}     # font hash -> {glyph id: the character the font maps to it}


def install():
    """Use the ActualText-aware draw_first_line. Returns True if it is in place."""
    import weasyprint
    from weasyprint.draw import text as wt
    if getattr(wt.draw_first_line, "_jyotisha", False):
        return True
    source = inspect.getsource(wt.draw_first_line)
    if weasyprint.__version__ != ADAPTED_FROM or hashlib.sha256(source.encode()).hexdigest() != ORIGINAL_SHA256:
        print(f"jyotisha_pdftext: WeasyPrint {weasyprint.__version__} is not the {ADAPTED_FROM} this was adapted "
              "from; Sinhala copy/paste from the PDF may be scrambled (the PDF itself is fine).", file=sys.stderr)
        return False
    global ORIGINAL
    ORIGINAL = wt.draw_first_line
    wt.draw_first_line = draw_first_line
    return True


def _reverse_cmap(font):
    rev = _REVERSE_CMAPS.get(font.hash)
    if rev is None:
        rev = {}
        try:
            from fontTools.ttLib import TTFont
            tt = TTFont(BytesIO(font.file_content), fontNumber=font.index, lazy=True)
            for codepoint, name in sorted(tt.getBestCmap().items()):
                rev.setdefault(tt.getGlyphID(name), chr(codepoint))
        except Exception:   # noqa: BLE001 — bitmap or odd fonts: no fallback letters, ActualText still works
            pass
        _REVERSE_CMAPS[font.hash] = rev
    return rev


def _actual_text(text):
    return b"<< /ActualText <FEFF" + text.encode("utf-16-be").hex().upper().encode() + b"> >>"


def _sinhala_words(run_utf8, starts, cluster_end, rtl=False):
    """{cluster start: (word start, word text)} for the clusters of words that contain Sinhala.
    A word is a stretch of clusters without white space. Other text is left as it was."""
    if rtl:
        return {}
    words, current = [], None
    for s in starts:
        text = run_utf8[s:cluster_end[s]].decode()
        if not text.strip():
            # a space goes with the word before it: between two spans, PDFium drops it
            if current is not None:
                current[1].append(s)
            current = None
            continue
        if current is None:
            current = [s, []]
            words.append(current)
        current[1].append(s)
    out = {}
    for w0, members in words:
        text = run_utf8[w0:cluster_end[members[-1]]].decode()
        if any("඀" <= ch <= "෿" for ch in text):
            for s in members:
                out[s] = (w0, text)
    return out


def _flush(stream, string):
    """Show the glyphs gathered so far; return an open glyph list."""
    if string.endswith("<"):
        string = string[:-1]
    elif string:
        string += ">"
    if string:
        stream.show_text(string)
    return "<"


def draw_first_line(stream, textbox, text_overflow, block_ellipsis, matrix):
    """Draw the given ``textbox`` line to the document ``stream``."""
    from PIL import Image
    from weasyprint.images import RasterImage, SVGImage
    from weasyprint.logger import LOGGER
    from weasyprint.text.ffi import FROM_UNITS, TO_UNITS, ffi, pango
    from weasyprint.text.fonts import get_hb_object_data
    from weasyprint.text.line_break import get_last_word_end

    # Don’t draw lines with only invisible characters.
    if not textbox.text.strip():
        return []

    if textbox.style['font_size'] < 1e-6:  # default float precision used by pydyf
        return []

    pango.pango_layout_set_single_paragraph_mode(textbox.pango_layout.layout, True)

    if text_overflow == 'ellipsis' or block_ellipsis != 'none':
        assert textbox.pango_layout.max_width is not None
        max_width = textbox.pango_layout.max_width
        pango.pango_layout_set_width(
            textbox.pango_layout.layout, int(max_width * TO_UNITS))
        if text_overflow == 'ellipsis':
            pango.pango_layout_set_ellipsize(
                textbox.pango_layout.layout, pango.PANGO_ELLIPSIZE_END)
        else:
            if block_ellipsis == 'auto':
                ellipsis = '…'
            else:
                assert block_ellipsis[0] == 'string'
                ellipsis = block_ellipsis[1]

            # Remove last word if hyphenated.
            new_text = textbox.pango_layout.text
            if new_text.endswith(textbox.style['hyphenate_character']):
                last_word_end = get_last_word_end(
                    new_text[:-len(textbox.style['hyphenate_character'])],
                    textbox.style['lang'])
                if last_word_end:
                    new_text = new_text[:last_word_end]

            textbox.pango_layout.set_text(new_text + ellipsis)

    first_line, index = textbox.pango_layout.get_first_line()

    if block_ellipsis != 'none':
        while index:
            last_word_end = get_last_word_end(
                textbox.pango_layout.text[:-len(ellipsis)],
                textbox.style['lang'])
            if last_word_end is None:
                break
            new_text = textbox.pango_layout.text[:last_word_end]
            textbox.pango_layout.set_text(new_text + ellipsis)
            first_line, index = textbox.pango_layout.get_first_line()

    stream.set_text_matrix(*matrix.values)
    previous_pango_font = None
    string = ''
    x_advance = 0
    emojis = []
    run = first_line.runs[0]
    while run != ffi.NULL:
        # Get Pango objects.
        glyph_item = run.data
        run = run.next
        glyph_string = glyph_item.glyphs
        glyphs_info = glyph_string.glyphs
        num_glyphs = glyph_string.num_glyphs
        clusters = glyph_string.log_clusters
        utf8_text = None

        pango_font = glyph_item.item.analysis.font
        if pango_font != previous_pango_font:
            # Add font file content and get font size.
            previous_pango_font = pango_font
            font, font_size = stream.add_font(pango_font)

            # Workaround for https://gitlab.gnome.org/GNOME/pango/-/issues/530.
            # This is also needed by raster emoji fonts, see #2800.
            if pango.pango_version() < 14802 or font.png:
                font_size = textbox.style['font_size']

            # Go through the run glyphs.
            if string:
                stream.show_text(string)
            string = ''
            stream.set_font_size(font.hash, 1 if font.bitmap else font_size)
        string += '<'

        # Jyothisha: the clusters of this run — where each one's text ends and how many glyphs draw
        # it — and the Sinhala words they make up. Each word goes in one ActualText span: per syllable,
        # readers still guess a word break where a vowel sign (ි, ්) is drawn back over its consonant.
        item_offset, item_length = glyph_item.item.offset, glyph_item.item.length
        cluster_of = [clusters[k] for k in range(num_glyphs)]
        starts = sorted(set(cluster_of))
        cluster_end = {s: (starts[j + 1] if j + 1 < len(starts) else item_length) for j, s in enumerate(starts)}
        cluster_size = collections.Counter(cluster_of)
        utf8_text = textbox.pango_layout.text.encode()
        word_of = _sinhala_words(utf8_text[item_offset:item_offset + item_length], starts, cluster_end,
                                 rtl=glyph_item.item.analysis.level % 2)
        reverse_cmap = _reverse_cmap(font)
        # glyphs of this document's font whose text map came from inside a longer syllable
        weak = font.__dict__.setdefault('_jyotisha_weak', set())
        span_open = None   # the word whose span is open

        for i, glyph_info in enumerate(glyphs_info[0:num_glyphs]):
            glyph_id = glyph_info.glyph
            width = glyph_info.geometry.width

            # Jyothisha: a Sinhala word goes in an ActualText span with its text.
            c0 = cluster_of[i]
            last_of_cluster = i == num_glyphs - 1 or cluster_of[i + 1] != c0
            cluster_text = utf8_text[item_offset + c0:item_offset + cluster_end[c0]].decode()
            multi = cluster_size[c0] > 1
            word = word_of.get(c0)
            if span_open is not None and (word is None or word[0] != span_open):
                string = _flush(stream, string)
                stream.end_marked_content()
                span_open = None
            if word is not None and span_open is None:
                string = _flush(stream, string)
                stream.begin_marked_content('Span', _actual_text(word[1]))
                span_open = word[0]

            # Display zero-width empty glyph.
            if glyph_id == pango.PANGO_GLYPH_EMPTY:
                string += f'>{-width / font_size}<'
                continue

            # Display .notdef and log warning for missing glyphs.
            if glyph_id & pango.PANGO_GLYPH_UNKNOWN_FLAG:
                codepoint = glyph_id - pango.PANGO_GLYPH_UNKNOWN_FLAG
                LOGGER.warning(
                    '.notdef glyph rendered for Unicode string unsupported by fonts: '
                    '"%s" (U+%04X)', chr(codepoint), codepoint)
                glyph_id = font.get_unused_glyph_id(codepoint)
                font.widths[glyph_id] = round(width * 1000 * FROM_UNITS / font_size)
                if 0 not in font.widths:
                    # "width" is actually Pango’s get_approximate_char_width. Force
                    # .notdef’s to use this width, even if it’s not the right, as we
                    # want to keep Pango’s layout for next glyphs.
                    font.widths[0] = font.widths[glyph_id]

            # Create mapping between glyphs and Unicode codepoints.
            # Jyothisha: a glyph drawn alone maps to exactly its text, and that wins over a map made
            # inside a longer syllable; inside one, a glyph maps to its own letter from the font, or
            # (a ligature with none) the last glyph carries the syllable's text. Every drawn glyph
            # needs an entry: the font subset keeps only glyphs in to_unicode.
            if not multi:
                if glyph_id not in font.to_unicode or glyph_id in weak:
                    font.to_unicode[glyph_id] = cluster_text
                    weak.discard(glyph_id)
            elif glyph_id not in font.to_unicode:
                font.to_unicode[glyph_id] = reverse_cmap.get(glyph_id) or (cluster_text if last_of_cluster else '')
                weak.add(glyph_id)

            # Set horizontal and vertical offsets.
            offset = glyph_info.geometry.x_offset / font_size
            rise = glyph_info.geometry.y_offset / 1000
            if rise:
                if string[-1] == '<':
                    string = string[:-1]
                else:
                    string += '>'
                if string:
                    stream.show_text(string)
                stream.set_text_rise(-rise)
                string = ''
                if offset:
                    string = f'{-offset}'
                string += f'<{glyph_id:02x}>' if font.bitmap else f'<{glyph_id:04x}>'
                stream.show_text(string)
                stream.set_text_rise(0)
                string = '<'
            else:
                if offset:
                    string += f'>{-offset}<'
                string += f'{glyph_id:02x}' if font.bitmap else f'{glyph_id:04x}'

            # Get glyph logical widths.
            if glyph_id in font.widths:
                logical_width = font.widths[glyph_id]
            else:
                pango.pango_font_get_glyph_extents(
                    pango_font, glyph_id, stream.ink_rect, stream.logical_rect)
                logical_width = font.widths[glyph_id] = round(
                    stream.logical_rect.width * 1000 * FROM_UNITS / font_size)

            # Set kerning, word spacing, letter spacing.
            kerning = logical_width + offset - width * 1000 * FROM_UNITS / font_size
            if kerning:
                string += f'>{int(kerning)}<'

            # Create list of emojis.
            if font.svg:
                svg_data = get_hb_object_data(font.hb_face, 'svg', glyph_id)
                if svg_data:
                    # Do as explained in specification
                    # https://learn.microsoft.com/typography/opentype/spec/svg
                    tree = ElementTree.fromstring(svg_data)
                    if tree.get('id') != f'glyph{glyph_id}':
                        defs = ElementTree.Element('defs')
                        for child in list(tree):
                            defs.append(child)
                            tree.remove(child)
                        tree.append(defs)
                        ElementTree.SubElement(
                            tree, 'use', attrib={'href': f'#glyph{glyph_id}'})
                    if 'viewBox' not in tree.attrib:
                        tree.attrib['viewBox'] = f'0 0 {font.upem} {font.upem}'
                    image = SVGImage(tree, None, None, None)
                    a = d = 1
                    emojis.append([image, font, a, d, x_advance, 0])
            elif font.png:
                png_data = get_hb_object_data(font.hb_font, 'png', glyph_id)
                if png_data:
                    pillow_image = Image.open(BytesIO(png_data))
                    image_id = f'{font.hash}{glyph_id}'
                    image = RasterImage(pillow_image, image_id, png_data)
                    d = logical_width / 1000
                    a = pillow_image.width / pillow_image.height * d
                    pango.pango_font_get_glyph_extents(
                        pango_font, glyph_id, stream.ink_rect,
                        stream.logical_rect)
                    f = -stream.logical_rect.y
                    f = f * FROM_UNITS / font_size - font_size
                    emojis.append([image, font, a, d, x_advance, f])
            elif font.colr:
                svg_data = get_hb_object_data(font.hb_font, 'colr', glyph_id)
                if svg_data:
                    tree = ElementTree.fromstring(svg_data)
                    image = SVGImage(tree, None, None, None)
                    a = d = 1
                    e = x_advance - kerning
                    emojis.append([image, font, a, d, e, -textbox.baseline])

            x_advance += (logical_width + offset - kerning) / 1000

        # Jyothisha: close a word span left open at the end of the run.
        if span_open is not None:
            string = _flush(stream, string)
            stream.end_marked_content()

        # Close the last glyphs list, remove if empty.
        if string[-1] == '<':
            string = string[:-1]
        else:
            string += '>'

    # Draw text.
    stream.show_text(string)

    return emojis


draw_first_line._jyotisha = True
