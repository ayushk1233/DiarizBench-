"""T12 — build the main submission PDF from docs/main.md.

A small, dependency-light Markdown subset -> reportlab renderer, so the report is
reproducible from a text source and does not depend on LaTeX or a browser.

Supported syntax
  # / ## / ###      headings (H1 starts a new page)
  paragraph text     blank-line separated; **bold**, *italic*, `code`, [text](url)
  - item             bullets (two-space indent for a sub-bullet)
  1. item            numbered list
  | a | b |          table (second row = |---| separator; :---: alignment optional)
  ^ caption          caption for the preceding table/figure
  [[fig:name.png|caption]]        figure from data/runs/figures
  [[page]]                        page break
  [[toc]]                         table of contents (page numbers via multiBuild)
  > text              callout box
  ---                 horizontal rule / section separator

Usage:
  .venv-harness/bin/python scripts/t12/build_main.py [--author "First Last"] [--out path.pdf]
"""
from __future__ import annotations

import argparse
import os
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image,
                                KeepTogether, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SOURCE = os.path.join(ROOT, "docs", "main.md")
FIGDIR = os.path.join(ROOT, "data", "runs", "figures")

PAGE_W, PAGE_H = A4
MARGIN_L = MARGIN_R = 21 * mm
MARGIN_T = 19 * mm
MARGIN_B = 17 * mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

INK = colors.HexColor("#14213d")
ACCENT = colors.HexColor("#0b6e4f")
MUTED = colors.HexColor("#5b6472")
RULE = colors.HexColor("#c9cfd8")
BOXBG = colors.HexColor("#f2f5f7")

TITLE = "DiarizBench"
SUBTITLE = "A diarization leaderboard for multilingual product teams"

# ---------------------------------------------------------------- fonts
def register_fonts():
    """Georgia for prose, Helvetica for headings/tables (both ship with macOS)."""
    sup = "/System/Library/Fonts/Supplemental"
    try:
        pdfmetrics.registerFont(TTFont("Body", f"{sup}/Georgia.ttf"))
        pdfmetrics.registerFont(TTFont("Body-Bold", f"{sup}/Georgia Bold.ttf"))
        pdfmetrics.registerFont(TTFont("Body-Italic", f"{sup}/Georgia Italic.ttf"))
        pdfmetrics.registerFont(TTFont("Body-BoldItalic", f"{sup}/Georgia Bold Italic.ttf"))
        pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold",
                                      italic="Body-Italic", boldItalic="Body-BoldItalic")
        return "Body"
    except Exception:  # pragma: no cover - fallback for non-macOS builders
        return "Times-Roman"


BODY = register_fonts()
SANS = "Helvetica"
SANS_B = "Helvetica-Bold"
MONO = "Courier"


def styles():
    s = getSampleStyleSheet()
    out = {}
    out["body"] = ParagraphStyle(
        "body", fontName=BODY, fontSize=9.5, leading=13.6, alignment=TA_JUSTIFY,
        textColor=colors.HexColor("#1c1c1c"), spaceAfter=4.9,
        allowWidows=0, allowOrphans=0)
    out["lead"] = ParagraphStyle(
        "lead", parent=out["body"], fontSize=10.4, leading=15.6, textColor=INK,
        spaceAfter=7)
    out["H1"] = ParagraphStyle(
        "H1", fontName=SANS_B, fontSize=16, leading=19, textColor=INK,
        spaceBefore=14, spaceAfter=3, alignment=TA_LEFT)
    out["H2"] = ParagraphStyle(
        "H2", fontName=SANS_B, fontSize=11, leading=14, textColor=INK,
        spaceBefore=10, spaceAfter=3)
    out["H3"] = ParagraphStyle(
        "H3", fontName=SANS_B, fontSize=9.6, leading=12.5, textColor=ACCENT,
        spaceBefore=8, spaceAfter=2)
    out["bullet"] = ParagraphStyle(
        "bullet", parent=out["body"], leftIndent=11, bulletIndent=3,
        spaceAfter=2.4, alignment=TA_LEFT)
    out["bullet2"] = ParagraphStyle(
        "bullet2", parent=out["bullet"], leftIndent=22, bulletIndent=13,
        textColor=colors.HexColor("#33383f"))
    out["num"] = ParagraphStyle(
        "num", parent=out["body"], leftIndent=15, bulletIndent=2,
        spaceAfter=2.4, alignment=TA_LEFT)
    out["caption"] = ParagraphStyle(
        "caption", fontName=SANS, fontSize=7.8, leading=10.4, textColor=MUTED,
        spaceBefore=3, spaceAfter=9, alignment=TA_LEFT)
    out["th"] = ParagraphStyle(
        "th", fontName=SANS_B, fontSize=7.4, leading=9.2, textColor=colors.white)
    out["td"] = ParagraphStyle(
        "td", fontName=SANS, fontSize=7.6, leading=9.6,
        textColor=colors.HexColor("#1c1c1c"))
    out["tdr"] = ParagraphStyle("tdr", parent=out["td"], alignment=TA_RIGHT)
    out["tdc"] = ParagraphStyle("tdc", parent=out["td"], alignment=1)
    out["callout"] = ParagraphStyle(
        "callout", parent=out["body"], fontSize=9.2, leading=13.4, spaceAfter=0,
        alignment=TA_LEFT)
    out["toc0"] = ParagraphStyle(
        "toc0", fontName=SANS_B, fontSize=9.4, leading=13.2, textColor=INK)
    out["kpi_num"] = ParagraphStyle(
        "kpi_num", fontName=SANS_B, fontSize=17, leading=20, textColor=INK)
    out["kpi_lab"] = ParagraphStyle(
        "kpi_lab", fontName=SANS, fontSize=7.2, leading=9, textColor=MUTED)
    out["tochead"] = ParagraphStyle(
        "tochead", fontName=SANS_B, fontSize=16, leading=19, textColor=INK)
    out["code"] = ParagraphStyle(
        "code", fontName="Courier", fontSize=7.4, leading=10.4,
        textColor=colors.HexColor("#24292f"))
    out["toc1"] = ParagraphStyle(
        "toc1", fontName=SANS, fontSize=8.6, leading=11.0, textColor=MUTED,
        leftIndent=12)
    return out


ST = styles()

# ---------------------------------------------------------------- inline markup
def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text: str) -> str:
    t = esc(text)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               r'<link href="\2" color="#0b6e4f">\1</link>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"`([^`]+)`", r'<font face="Courier" size="8.4">\1</font>', t)
    t = t.replace("&amp;nbsp;", "\u00a0")
    return t


def is_numeric(cell: str) -> bool:
    c = cell.strip().replace("**", "")
    return bool(re.fullmatch(r"[−+\-–]?[\d.,]+(\s*(%|pp|s|×|ms|x))?(\s*\[.*\])?", c))


# ---------------------------------------------------------------- flowables
def make_table(rows, widths=None, header=True):
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    # column weight from the longest cell (capped), first column favoured
    weights = []
    for j in range(ncol):
        longest = max(len(re.sub(r"\*\*|`", "", r[j])) for r in rows)
        weights.append(min(max(longest, 7), 46))
    if widths:
        tot = float(sum(widths))
        colw = [CONTENT_W * w / tot for w in widths]
    else:
        weights[0] *= 1.22
        tot = sum(weights)
        colw = [CONTENT_W * w / tot for w in weights]

    numeric_col = [False] * ncol
    for j in range(ncol):
        vals = [r[j] for r in rows[1:]] if header else [r[j] for r in rows]
        vals = [v for v in vals if v.strip()]
        if vals:
            numeric_col[j] = sum(is_numeric(v) for v in vals) / len(vals) >= 0.6

    data = []
    for i, r in enumerate(rows):
        line = []
        for j, cell in enumerate(r):
            if i == 0 and header:
                line.append(Paragraph(inline(cell), ST["th"]))
            else:
                style = ST["tdr"] if numeric_col[j] else ST["td"]
                line.append(Paragraph(inline(cell), style))
        data.append(line)

    t = Table(data, colWidths=colw, repeatRows=1 if header else 0)
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.35, RULE),
    ]
    if header:
        cmds += [("BACKGROUND", (0, 0), (-1, 0), INK),
                 ("TOPPADDING", (0, 0), (-1, 0), 4),
                 ("BOTTOMPADDING", (0, 0), (-1, 0), 4.5)]
        for i in range(2, len(data), 2):
            cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f6f7f9")))
    t.setStyle(TableStyle(cmds))
    return t


def callout(paras):
    inner = [Paragraph(inline(p), ST["callout"]) for p in paras]
    t = Table([[inner]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BOXBG),
        ("LINEBEFORE", (0, 0), (0, -1), 2.4, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return [Spacer(1, 2), t, Spacer(1, 8)]


# ---------------------------------------------------------------- document
class Doc(BaseDocTemplate):
    def __init__(self, path, author):
        super().__init__(path, pagesize=A4, leftMargin=MARGIN_L, rightMargin=MARGIN_R,
                         topMargin=MARGIN_T, bottomMargin=MARGIN_B,
                         title=f"{TITLE} — Voice Arena take-home",
                         author=author, subject=SUBTITLE)
        self.author_name = author
        frame = Frame(MARGIN_L, MARGIN_B, CONTENT_W, PAGE_H - MARGIN_T - MARGIN_B,
                      id="body", leftPadding=0, rightPadding=0, topPadding=0,
                      bottomPadding=0)
        title_frame = Frame(MARGIN_L, MARGIN_B, CONTENT_W, PAGE_H - MARGIN_T - MARGIN_B,
                            id="title")
        self.addPageTemplates([
            PageTemplate(id="title", frames=[title_frame], onPage=self.title_page),
            PageTemplate(id="body", frames=[frame], onPage=self.body_page),
        ])
        self._toc_level = 0

    def title_page(self, canv, doc):
        canv.saveState()
        canv.setFillColor(INK)
        canv.rect(0, PAGE_H - 62 * mm, PAGE_W, 62 * mm, stroke=0, fill=1)
        canv.setFillColor(colors.HexColor("#7fd1b0"))
        canv.rect(0, PAGE_H - 63.2 * mm, PAGE_W, 1.2 * mm, stroke=0, fill=1)
        canv.setFillColor(colors.white)
        canv.setFont(SANS_B, 27)
        canv.drawString(MARGIN_L, PAGE_H - 34 * mm, TITLE)
        canv.setFont(SANS, 11.5)
        canv.drawString(MARGIN_L, PAGE_H - 43 * mm, SUBTITLE)
        canv.setFont(SANS, 8.6)
        canv.setFillColor(colors.HexColor("#b9c6d6"))
        canv.drawString(MARGIN_L, PAGE_H - 53 * mm,
                        "Voice Arena take-home  ·  Q1  ·  diarization benchmark design and measured pilot")
        canv.restoreState()

    def body_page(self, canv, doc):
        canv.saveState()
        # header
        canv.setFont(SANS, 7.2)
        canv.setFillColor(MUTED)
        canv.drawString(MARGIN_L, PAGE_H - 12 * mm, f"{TITLE}  ·  {SUBTITLE}")
        canv.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 12 * mm, self.author_name)
        canv.setStrokeColor(RULE)
        canv.setLineWidth(0.4)
        canv.line(MARGIN_L, PAGE_H - 14 * mm, PAGE_W - MARGIN_R, PAGE_H - 14 * mm)
        # footer
        canv.line(MARGIN_L, MARGIN_B - 6 * mm, PAGE_W - MARGIN_R, MARGIN_B - 6 * mm)
        canv.setFont(SANS, 7.2)
        canv.setFillColor(MUTED)
        canv.drawString(MARGIN_L, MARGIN_B - 10.5 * mm,
                        "Experiment frozen at T11 — every number in this document traces to a saved result (Appendix C).")
        canv.setFont(SANS_B, 7.6)
        canv.setFillColor(INK)
        total = getattr(doc, "total_pages", None)
        canv.drawRightString(PAGE_W - MARGIN_R, MARGIN_B - 10.5 * mm,
                             f"{doc.page} / {total}" if total else str(doc.page))
        canv.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            name = flowable.style.name
            if name == "H1":
                self.notify("TOCEntry", (0, flowable.getPlainText(), self.page))
            elif name == "H2":
                self.notify("TOCEntry", (1, flowable.getPlainText(), self.page))


# ---------------------------------------------------------------- parser
def parse(md: str):
    story = []
    raw_lines = md.split("\n")
    lines = []
    for ln in raw_lines:
        if (ln.startswith("  ") and not re.match(r"\s*(- |\d+\. )", ln)
                and lines and lines[-1].strip()):
            lines[-1] = lines[-1].rstrip() + " " + ln.strip()
        else:
            lines.append(ln)
    i = 0
    pending_caption = None
    pending_widths = None
    last_was_break = False

    def flush_caption():
        nonlocal pending_caption
        if pending_caption:
            story.append(Paragraph(inline(pending_caption), ST["caption"]))
            pending_caption = None

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        if not line.strip():
            i += 1
            continue

        if line.startswith("[[toc]]"):
            toc = TableOfContents()
            toc.levelStyles = [ST["toc0"], ST["toc1"]]
            toc.dotsMinLevel = 0
            toc.tableStyle = TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5),
            ])
            story.append(NextPageTemplate("body"))
            story.append(PageBreak())
            story.append(Paragraph("Contents", ST["tochead"]))
            story.append(Spacer(1, 4))
            story.append(toc)
            story.append(PageBreak())
            i += 1
            continue

        if line.startswith("[[kpi:"):
            flush_caption()
            items = [x.strip() for x in line[6:].rstrip("]").split("|")]
            cells = []
            for it in items:
                num, _, lab = it.partition(" ")
                cells.append([Paragraph(num, ST["kpi_num"]), Paragraph(lab, ST["kpi_lab"])])
            kt = Table([cells], colWidths=[CONTENT_W / len(items)] * len(items))
            kt.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f6f8")),
                ("LINEBEFORE", (1, 0), (-1, -1), 0.5, colors.white),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(kt)
            story.append(Spacer(1, 10))
            i += 1
            continue

        if line.startswith("[[widths:"):
            pending_widths = [float(x) for x in line[9:].rstrip("]").split(",")]
            i += 1
            continue

        if line.startswith("[[space:"):
            mm_ = float(line[8:].rstrip("]"))
            story.append(Spacer(1, mm_ * mm))
            i += 1
            continue

        if line.startswith("[[page]]"):
            flush_caption()
            story.append(PageBreak())
            i += 1
            continue

        if line.startswith("```"):
            flush_caption()
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            t = Table([[Paragraph(esc("\n".join(block)).replace("\n", "<br/>"),
                                  ST["code"])]], colWidths=[CONTENT_W])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f4f6")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBEFORE", (0, 0), (0, -1), 2, RULE),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))
            continue

        if line.startswith("# "):
            flush_caption()
            if not (story and isinstance(story[-1], PageBreak)):
                story.append(CondPageBreak(62 * mm))
            text = line[2:].strip()
            story.append(Paragraph(inline(text), ST["H1"]))
            story.append(Spacer(1, 2))
            story.append(HRule())
            story.append(Spacer(1, 7))
            i += 1
            continue

        if line.startswith("## "):
            flush_caption()
            story.append(CondPageBreak(42 * mm))
            story.append(Paragraph(inline(line[3:].strip()), ST["H2"]))
            i += 1
            continue

        if line.startswith("### "):
            flush_caption()
            story.append(Paragraph(inline(line[4:].strip()), ST["H3"]))
            i += 1
            continue

        if line.startswith("[[fig:"):
            flush_caption()
            body = line[6:].rstrip("]")
            name, _, cap = body.partition("|")
            path = os.path.join(FIGDIR, name.strip())
            from reportlab.lib.utils import ImageReader
            iw, ih = ImageReader(path).getSize()
            w = CONTENT_W
            h = w * ih / iw
            max_h = 90 * mm
            if h > max_h:
                h = max_h
                w = h * iw / ih
            img = Image(path, width=w, height=h)
            story.append(KeepTogether([Spacer(1, 3), img,
                                       Paragraph(inline(cap.strip()), ST["caption"])]))
            pending_caption = None
            i += 1
            continue

        if line.startswith("^ "):
            pending_caption = line[2:].strip()
            i += 1
            continue

        if line.strip() == "---":
            flush_caption()
            story.append(Spacer(1, 4))
            story.append(HRule())
            story.append(Spacer(1, 4))
            i += 1
            continue

        if line.startswith("|"):
            flush_caption()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            tbl = make_table(rows, widths=pending_widths)
            pending_widths = None
            cap = None
            if i < len(lines) and lines[i].startswith("^ "):
                cap = lines[i][2:].strip()
                i += 1
            if cap:
                story.append(KeepTogether([Spacer(1, 3), tbl,
                                           Paragraph(inline(cap), ST["caption"])]))
            else:
                story.append(Spacer(1, 3))
                story.append(tbl)
                story.append(Spacer(1, 2))
            continue

        if line.startswith("> "):
            flush_caption()
            paras = []
            current = []
            while i < len(lines) and lines[i].startswith(">"):
                part = lines[i].lstrip("> ").strip()
                if part:
                    current.append(part)
                elif current:
                    paras.append(" ".join(current))
                    current = []
                i += 1
            if current:
                paras.append(" ".join(current))
            story.extend(callout([p for p in paras if p]))
            continue

        m = re.match(r"^(\s*)- (.*)$", line)
        if m:
            flush_caption()
            indent = len(m.group(1))
            style = ST["bullet2"] if indent >= 2 else ST["bullet"]
            story.append(Paragraph(inline(m.group(2)), style, bulletText="•"))
            i += 1
            continue

        m = re.match(r"^(\d+)\. (.*)$", line)
        if m:
            flush_caption()
            story.append(Paragraph(inline(m.group(2)), ST["num"],
                                   bulletText=f"{m.group(1)}."))
            i += 1
            continue

        # paragraph: gather until blank line / block start
        flush_caption()
        buf = [line.strip()]
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if (not nxt.strip() or nxt.startswith(("#", "|", "- ", "> ", "[[", "^ ", "---"))
                    or re.match(r"^\d+\. ", nxt)):
                break
            buf.append(nxt.strip())
            i += 1
        story.append(Paragraph(inline(" ".join(buf)), ST["body"]))

    flush_caption()
    return story


class HRule(Table):
    """Thin horizontal rule that participates in flow."""

    def __init__(self):
        super().__init__([[""]], colWidths=[CONTENT_W], rowHeights=[0.1])
        self.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 1.1, INK)]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--author", default="Ayush Kumar")
    ap.add_argument("--out", default=os.path.join(ROOT, "submission", "Q1_Main.pdf"))
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    md = open(SOURCE, encoding="utf-8").read()
    story = parse(md)

    # pass 1: learn the page count (footer is the only difference)
    tmp = args.out.replace(".pdf", "_pass1.pdf")
    doc = Doc(tmp, args.author)
    doc.multiBuild(story)
    import pypdfium2 as pdfium
    total = len(pdfium.PdfDocument(tmp))

    # pass 2: final, with "page / total" footer
    story = parse(md)
    doc = Doc(args.out, args.author)
    doc.total_pages = total
    doc.multiBuild(story)
    print(f"wrote {args.out} ({total} pages)")

    if os.path.exists(tmp):
        os.remove(tmp)


if __name__ == "__main__":
    main()
