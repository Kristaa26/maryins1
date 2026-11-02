"""
MaryLab Official Player Walkthrough builder.

Clones the MaryLab Word template (so all house styles, theme, header and footer
are inherited verbatim), clears the body, and rebuilds it from a structured
machine description. The goal is a document that is visually identical in design
to MaryLab_Official_Player_Walkthrough_Template.docx but carries real,
machine-specific content.

Design tokens pulled from the template:
    BLUE  304FC7   accent / key terms
    NAVY  17304D   dark headings, numbered-list markers, table header fill
    CODE  1C405B   monospace command/output text
    FILL  F3F7FA   light callout background
Styles used (all defined in the template): Label, Section eyebrow, Heading 1,
Heading 2, Number clean, Bullet clean, Table body, Normal.

Usage: see build_vaultline.py for a worked example.
"""
from docx import Document
from docx.shared import Pt, RGBColor, Twips
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

BLUE = RGBColor(0x30, 0x4F, 0xC7)
NAVY = RGBColor(0x17, 0x30, 0x4D)
CODE = RGBColor(0x1C, 0x40, 0x5B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FILL = "F3F7FA"
NAVY_HEX = "17304D"


def _shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def _cell_borders(cell, color=NAVY_HEX, sz="2"):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), sz)
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), color)
        borders.append(e)
    tcPr.append(borders)


class Walkthrough:
    def __init__(self, template_path):
        self.doc = Document(template_path)
        self._num = 0
        self._clear_body()

    def _clear_body(self):
        body = self.doc.element.body
        for child in list(body):
            if child.tag == qn("w:sectPr"):
                continue  # keep page setup / header-footer linkage
            body.remove(child)

    # ---- primitives --------------------------------------------------------
    def _p(self, style=None):
        p = self.doc.add_paragraph()
        if style:
            p.style = self.doc.styles[style]
        return p

    def _run(self, p, text, *, bold=False, color=None, font=None, size=None):
        r = p.add_run(text)
        if bold:
            r.bold = True
        if color is not None:
            r.font.color.rgb = color
        if font:
            r.font.name = font
        if size is not None:
            r.font.size = Pt(size)
        return r

    def _segments(self, p, segments):
        """segments: list of str (plain) or (text, 'b') bold-blue key term."""
        for seg in segments:
            if isinstance(seg, tuple):
                self._run(p, seg[0], bold=True, color=BLUE)
            else:
                self._run(p, seg)

    # ---- title block -------------------------------------------------------
    def title(self, name):
        p = self._p()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(11)
        self._run(p, name, bold=True, color=BLUE, font="Aptos Display", size=29)

    def subtitle(self, author):
        p = self._p()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(11)
        self._run(p, author, bold=True, color=BLUE, font="Aptos Display", size=18)

    def tagline(self, text):
        p = self._p()
        p.paragraph_format.space_after = Pt(17)
        self._run(p, text)

    def callout(self, heading, body):
        t = self.doc.add_table(rows=1, cols=1)
        cell = t.cell(0, 0)
        _shade(cell, FILL)
        cell.paragraphs[0].text = ""
        hp = cell.paragraphs[0]
        hp.paragraph_format.space_after = Pt(2)
        self._run(hp, heading, bold=True, color=NAVY, size=8)
        bp = cell.add_paragraph()
        bp.paragraph_format.space_after = Pt(0)
        self._run(bp, body, size=8.5)
        self.spacer()

    # ---- profile table -----------------------------------------------------
    def profile(self, rows):
        t = self.doc.add_table(rows=len(rows) + 1, cols=2)
        t.style = self.doc.styles["Table Grid"]
        t.columns[0].width = Twips(4218)
        t.columns[1].width = Twips(6235)
        # header
        hdr = t.rows[0].cells
        for cell, label in zip(hdr, ("ATTRIBUTE", "DETAILS")):
            _shade(cell, NAVY_HEX)
            _cell_borders(cell)
            cell.paragraphs[0].style = self.doc.styles["Table body"]
            self._run(cell.paragraphs[0], label, bold=True, color=WHITE)
        for i, (k, v) in enumerate(rows, start=1):
            c = t.rows[i].cells
            for cell in c:
                _cell_borders(cell)
                cell.paragraphs[0].style = self.doc.styles["Table body"]
            self._run(c[0].paragraphs[0], k, bold=True, color=NAVY)
            self._run(c[1].paragraphs[0], v)
        self.spacer()

    # ---- section / heading -------------------------------------------------
    def eyebrow(self, text, first=False):
        p = self._p("Section eyebrow")
        if not first:
            p.paragraph_format.page_break_before = True
        self._run(p, text)

    def h1(self, text):
        self._p("Heading 1").add_run(text)

    def h2(self, text):
        self._p("Heading 2").add_run(text)

    def label(self, text):
        self._p("Label").add_run(text)

    def body(self, *segments):
        p = self._p()
        self._segments(p, list(segments))
        return p

    def lead(self, lead_text, *segments):
        """Bold lead-in like  **Next step:** rest..."""
        p = self._p()
        self._run(p, lead_text + " ", bold=True)
        self._segments(p, list(segments))
        return p

    def code(self, *lines):
        for i, line in enumerate(lines):
            p = self._p()
            p.paragraph_format.space_after = Pt(0)
            self._run(p, line, font="Consolas", color=CODE, size=8)

    def numbered(self, items, cont=False):
        """Numbered 'Number clean' items. cont=True continues the running
        counter across intervening code blocks; otherwise it resets to 1."""
        if not cont:
            self._num = 0
        for segs in items:
            self._num += 1
            p = self._p("Number clean")
            self._run(p, f"{self._num}.  ", bold=True, color=NAVY)
            self._segments(p, segs if isinstance(segs, list) else [segs])

    def bullets(self, items):
        for segs in items:
            p = self._p("Bullet clean")
            self._segments(p, segs if isinstance(segs, list) else [segs])

    def spacer(self):
        p = self._p()
        p.paragraph_format.space_after = Pt(0)

    def save(self, path):
        self.doc.save(path)
