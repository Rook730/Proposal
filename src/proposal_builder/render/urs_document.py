"""URS/RFQ package and Response Form (ce-requirements 8.2, 8.5): Word (.docx) and PDF from one document model.

build_package() turns a project URS (or the library itself, for the blank template) into a document model:
cover, revision history, contents and numbered sections whose bodies are parsed into paragraphs, bullets,
tables and signature forms. write_docx() and compile_document(..., template="urs.typ") print it.

Two modes: "template" prints the template notes ([!...], blue) and the instructions page, as the original
URS/RFQ Template does; "issued" drops the notes. Blanks ([ ], [ADDRESS]) print in both and are flagged on the
Issues tab until filled.
"""

from __future__ import annotations

import io
import re
from datetime import date

from .. import ce_urs as U

INLINE = re.compile(r"\*\*(.+?)\*\*|(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])|\[!([^\]]*)\]|\[([^\]]*)\]")


def runs(text: str, mode: str) -> list[dict]:
    """Inline runs: {"text", "b", "i", "note", "blank"}. Notes are dropped in issued mode."""
    out: list[dict] = []
    pos = 0
    for m in INLINE.finditer(text):
        if m.start() > pos:
            out.append({"text": text[pos:m.start()]})
        if m.group(1) is not None:
            out += [{**r, "b": True} for r in runs(m.group(1), mode)]
        elif m.group(2) is not None:
            out += [{**r, "i": True} for r in runs(m.group(2), mode)]
        elif m.group(3) is not None:
            if mode == U.TEMPLATE:
                out.append({"text": "[" + m.group(3) + "]", "note": True})
        else:
            out.append({"text": "[" + m.group(4) + "]", "blank": True})
        pos = m.end()
    if pos < len(text):
        out.append({"text": text[pos:]})
    if mode != U.TEMPLATE:      # tidy spaces left where a note was dropped
        for r in out:
            r["text"] = re.sub(r"  +", " ", r["text"])
        if out:
            out[0]["text"] = out[0]["text"].lstrip()
            out[-1]["text"] = out[-1]["text"].rstrip()
    return [r for r in out if r["text"]]


def blocks(text: str, mode: str) -> list[dict]:
    """Body text (already expanded) to blocks: p, li (level), table (rows of cells), form (rows of labels)."""
    out: list[dict] = []
    para: list[str] = []
    lines = text.split("\n")

    def flush() -> None:
        if para:
            r = runs(" ".join(s.strip() for s in para), mode)
            if r:
                out.append({"t": "p", "runs": r})
            para.clear()

    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s == "::form":
            flush()
            rows = []
            i += 1
            while i < len(lines) and lines[i].strip() != "::":
                if lines[i].strip():
                    rows.append([c.strip() for c in lines[i].split("|")])
                i += 1
            out.append({"t": "form", "rows": rows})
            i += 1
            continue
        if s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
                    rows.append([runs(c, mode) for c in cells])
                i += 1
            out.append({"t": "table", "rows": rows, "header": True})
            continue
        bm = re.match(r"^(\s*)- (.*)$", ln)
        if bm:
            flush()
            r = runs(bm.group(2), mode)
            if r:
                out.append({"t": "li", "level": len(bm.group(1)) // 2, "runs": r})
            i += 1
            continue
        if not s:
            flush()
        else:
            para.append(s)
        i += 1
    flush()
    return out


def _plain(rs: list[dict]) -> str:
    return "".join(r["text"] for r in rs)


def build_package(lib: U.RequirementLibrary, urs: U.ProjectUrs | None, project=None, mode: str = U.ISSUED,
                  company: dict | None = None) -> dict:
    """The URS/RFQ document model. urs=None prints the library as the blank template."""
    blank = urs is None
    if blank:
        urs = U.ProjectUrs(items=[U.UrsItem(level=n.level, heading=n.heading, body=n.body, kind=n.kind,
                                            applies=n.applies, numbered=n.numbered, pagebreak=n.pagebreak, on=n.on)
                                  for n in lib.nodes],
                           history=[U.UrsRevisionRow(revision="1.0", date="1/1/2019", section="N/A",
                                                     change="Original Release to Provider")],
                           author=lib.author)
        mode = U.TEMPLATE
    vals = U.values(lib, urs, project)
    list_vars = {v.name for v in lib.variables if v.type == "list"}
    show_all = mode == U.TEMPLATE
    live = U.effective_on(urs.items, urs.tags)
    nums = U.numbers(urs.items, live, urs.omit)
    sections = []
    for it, num, on in zip(urs.items, nums, live, strict=True):
        if not on and urs.omit == U.OMIT_REMOVE:
            continue
        body = U.expand(it.body, vals, urs.tags, list_vars, show_all) if on else ""
        sections.append({"number": num, "heading": it.heading, "level": max(1, min(3, it.level)),
                         "numbered": it.numbered and bool(num), "pagebreak": it.pagebreak, "na": not on,
                         "blocks": blocks(body, mode) if on else
                         [{"t": "p", "runs": [{"text": "Not applicable.", "i": True}]}]})
    name = vals.get("company") or "[COMPANY]"
    if blank:
        name, addr = "[COMPANY]", ["[Address]", "[Address]"]
    else:
        addr = [a for a in (urs.address_1, urs.address_2) if a] or ["[Address]", "[Address]"]
    doc = {
        "kind": "urs",
        "mode": mode,
        "company": company or {"name": name, "logo": ""},
        "client": name,
        "address": addr,
        "title": urs.title or "TITLE",
        "subtitle": urs.subtitle or ("SUBTITLE" if blank or mode == U.TEMPLATE else ""),
        "revision": urs.revision or "1.0",
        "month_year": urs.month_year or ("Month Year" if blank else date.today().strftime("%B %Y")),
        "issued": urs.issued or "Month Day, Year",
        "due": urs.due or "Month Day, Year",
        "revision_note": runs("[!Increment revision per following page]", mode),
        "confidentiality": runs(U._sub(lib.confidentiality, {"company": name}), mode),
        "history": [[r.revision, r.date, r.section, r.change] for r in urs.history],
        "instructions": blocks(lib.instructions, U.TEMPLATE) if mode == U.TEMPLATE else [],
        "doc_control": {"approvers": lib.approvers, "versions": lib.versions} if mode == U.TEMPLATE else None,
        "sections": sections,
        "author": urs.author or lib.author,
        "document_number": urs.document_number or "Not Assigned",
        "prepared_by": prepared_by(company),
    }
    return doc


def build_response_form(lib: U.RequirementLibrary, urs: U.ProjectUrs, project=None, mode: str = U.ISSUED,
                        min_rows: int = 12, company: dict | None = None) -> dict:
    vals = U.values(lib, urs, project)
    rows = [[r.number or r.heading, r.text] for r in U.response_form_rows(urs)]
    rows += [["", ""]] * max(0, min_rows - len(rows))
    return {
        "kind": "response",
        "mode": mode,
        "company": company or {"name": vals.get("company", ""), "logo": ""},
        "client": vals.get("company", ""),
        "fields": [["URS/RFQ Reference Number", urs.reference or urs.client.reference],
                   ["URS/RFQ Revision Number", urs.client.revision or urs.revision],
                   ["Completed By", urs.completed_by or lib.author],
                   ["Completed Date", urs.completed_date or date.today().strftime("%m/%d/%Y")]],
        "instructions": lib.response_instructions,
        "rows": rows,
        "doc_control": {"approvers": lib.approvers, "versions": lib.versions} if mode == U.TEMPLATE else None,
        "revision": urs.client.revision or urs.revision or "1.0",
        "author": urs.completed_by or lib.author,
        "document_number": urs.reference or urs.document_number or "Not Assigned",
        "prepared_by": prepared_by(company),
    }


def prepared_by(company: dict | None) -> str:
    """Small footer credit: the URS is the client's document, traceable to the company that prepared it."""
    if not company:
        return ""
    who = company.get("legal") or company.get("name") or ""
    contact = company.get("email") or company.get("phone") or ""
    return f"Prepared by {who}" + (f" | {contact}" if contact else "") if who else ""


def package_filename(project, urs: U.ProjectUrs, ext: str) -> str:
    base = f"{getattr(project, 'number', '')} URS-RFQ Rev {urs.revision or '1.0'}".strip()
    return f"{base}.{ext}"


def response_filename(project, urs: U.ProjectUrs, ext: str) -> str:
    return f"{getattr(project, 'number', '')} URS Response Form Rev {urs.client.revision or urs.revision}.{ext}".strip()


# ---------------------------------------------------------------- Word

BLUE = (0x1F, 0x4E, 0xD8)


def _docx_base():
    from docx import Document
    from docx.enum.style import WD_STYLE_TYPE
    from docx.shared import Pt, RGBColor

    d = Document()
    st = d.styles
    normal = st["Normal"]
    normal.font.name, normal.font.size = "Calibri", Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    for name, size, before in (("Heading 1", 14, 18), ("Heading 2", 12, 12), ("Heading 3", 11, 8)):
        h = st[name]
        h.font.name, h.font.size, h.font.bold = "Calibri", Pt(size), True
        h.font.color.rgb = RGBColor(0, 0, 0)
        h.paragraph_format.space_before, h.paragraph_format.space_after = Pt(before), Pt(4)
        rpr = h.element.get_or_add_rPr()
        for tag in ("w:rFonts",):
            el = rpr.find(_qn(tag))
            if el is not None:
                for a in list(el.attrib):
                    if "Theme" in a:
                        del el.attrib[a]
                el.set(_qn("w:ascii"), "Calibri")
                el.set(_qn("w:hAnsi"), "Calibri")
    if "URS Note" not in [s.name for s in st]:
        n = st.add_style("URS Note", WD_STYLE_TYPE.CHARACTER)
        n.font.color.rgb = RGBColor(*BLUE)
    sec = d.sections[0]
    from docx.shared import Inches
    sec.left_margin = sec.right_margin = Inches(1)
    sec.top_margin, sec.bottom_margin = Inches(0.9), Inches(0.8)
    return d


def _qn(tag: str):
    from docx.oxml.ns import qn
    return qn(tag)


def _add_runs(p, rs: list[dict]) -> None:
    from docx.shared import RGBColor
    for r in rs:
        run = p.add_run(r["text"])
        run.bold = bool(r.get("b"))
        run.italic = bool(r.get("i"))
        if r.get("note") or r.get("blank"):
            run.font.color.rgb = RGBColor(*BLUE)


def _field(p, code: str, placeholder: str = "1") -> None:
    """Insert a Word field (PAGE, NUMPAGES, TOC ...) into paragraph p."""
    from docx.oxml import OxmlElement
    for kind, text in (("begin", None), ("instr", code), ("separate", None), ("text", placeholder), ("end", None)):
        r = OxmlElement("w:r")
        if kind == "instr":
            t = OxmlElement("w:instrText")
            t.set(_qn("xml:space"), "preserve")
            t.text = f" {code} "
            r.append(t)
        elif kind == "text":
            t = OxmlElement("w:t")
            t.text = text
            r.append(t)
        else:
            fc = OxmlElement("w:fldChar")
            fc.set(_qn("w:fldCharType"), kind)
            r.append(fc)
        p._p.append(r)


def _table(d, rows: list[list], header: bool, widths=None, runs_cells: bool = True):
    from docx.shared import Pt
    t = d.add_table(rows=len(rows), cols=max(len(r) for r in rows))
    t.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            c = t.cell(i, j)
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            if runs_cells:
                _add_runs(p, cell)
            else:
                p.add_run(str(cell))
            if header and i == 0:
                for r in p.runs:
                    r.bold = True
                _shade(c, "D9D9D9")
    if widths:
        for row in t.rows:
            for j, w in enumerate(widths):
                if j < len(row.cells):
                    row.cells[j].width = w
    d.add_paragraph()
    return t


def _shade(cell, hex_fill: str) -> None:
    from docx.oxml import OxmlElement
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(_qn("w:val"), "clear")
    shd.set(_qn("w:color"), "auto")
    shd.set(_qn("w:fill"), hex_fill)
    tcpr.append(shd)


def _blocks_docx(d, bl: list[dict]) -> None:
    from docx.shared import Inches, Pt
    for b in bl:
        if b["t"] == "p":
            _add_runs(d.add_paragraph(), b["runs"])
        elif b["t"] == "li":
            lvl = min(b["level"], 2)
            style = "List Bullet" if lvl == 0 else f"List Bullet {lvl + 1}"
            p = d.add_paragraph(style=style)
            p.paragraph_format.space_after = Pt(2)
            _add_runs(p, b["runs"])
        elif b["t"] == "table":
            _table(d, b["rows"], b.get("header", True))
        elif b["t"] == "form":
            for row in b["rows"]:
                p = d.add_paragraph()
                p.paragraph_format.space_after = Pt(8)
                if len(row) == 1:
                    p.paragraph_format.tab_stops.add_tab_stop(Inches(1.8))
                    p.add_run(f"{row[0]}\t" + "_" * 58)
                else:
                    p.add_run(f"{row[0]}: " + "_" * 36 + f"  {row[1]}: " + "_" * 18)


def _footer(d, doc: dict) -> None:
    from docx.enum.text import WD_TAB_ALIGNMENT
    from docx.shared import Inches, Pt
    sec = d.sections[0]
    f = sec.footer
    p = f.paragraphs[0]
    p.paragraph_format.tab_stops.add_tab_stop(Inches(6.5), WD_TAB_ALIGNMENT.RIGHT)
    run = p.add_run(f"Revision: {doc['revision']}\tPage ")
    run.font.size = Pt(9)
    _field(p, "PAGE")
    p.add_run(" of ").font.size = Pt(9)
    _field(p, "NUMPAGES", "2")
    p2 = f.add_paragraph()
    r2 = p2.add_run(f"Author: {doc['author']}\nDocument Number: {doc['document_number']}")
    r2.font.size = Pt(8)
    if doc.get("prepared_by"):
        from docx.shared import RGBColor
        p3 = f.add_paragraph()
        p3.alignment = 2        # right
        r3 = p3.add_run(doc["prepared_by"])
        r3.font.size = Pt(7)
        r3.font.color.rgb = RGBColor(0x8C, 0x8C, 0x8C)
    d.core_properties.author = doc["author"]
    if doc.get("prepared_by"):
        d.core_properties.comments = doc["prepared_by"]
    h = sec.header.paragraphs[0]
    hr = h.add_run(doc.get("client") or "")
    hr.bold = True


def _doc_control_docx(d, dc: dict) -> None:
    from docx.shared import Pt
    p = d.add_paragraph()
    r = p.add_run("Document Version History and Approvals")
    r.bold, r.font.size = True, Pt(12)
    _table(d, [["Approver", "Role", "Signature", "Date"]] + [list(a) + ["", ""] for a in dc["approvers"]],
           True, runs_cells=False)
    _table(d, [["Version", "Issue Date", "Revised Section", "Revisions"]] + [list(v) for v in dc["versions"]],
           True, runs_cells=False)


def write_docx(doc: dict) -> bytes:
    """The URS/RFQ package as a Word document. Word fills in the contents page numbers when the file is opened
    (the document asks to update fields)."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.shared import Pt

    d = _docx_base()
    _footer(d, doc)
    if doc.get("instructions"):
        p = d.add_paragraph()
        p.add_run(doc["client"]).bold = True
        _blocks_docx(d, doc["instructions"])
        d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    if doc.get("doc_control"):
        _doc_control_docx(d, doc["doc_control"])
        d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    # cover
    for text, size, bold in [(doc["client"], 20, True)] + [(a, 12, False) for a in doc["address"]]:
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text)
        r.bold, r.font.size = bold, Pt(size)
    d.add_paragraph()
    for text, size in ((doc["title"], 26), (doc["subtitle"], 16)):
        if text:
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(text)
            r.bold, r.font.size = True, Pt(size)
    d.add_paragraph()
    for text in ("User Requirements Summary (URS)", "&", "Request For Quotation (RFQ)"):
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(text)
        r.font.size = Pt(16)
    d.add_paragraph()
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"Revision: {doc['revision']}\n{doc['month_year']}")
    if doc["revision_note"]:
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _add_runs(p, doc["revision_note"])
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"Issued for Quotation: {doc['issued']}\nQuotation Response Due: {doc['due']}")
    d.add_paragraph()
    p = d.add_paragraph()
    p.add_run("Confidential Information:").bold = True
    p = d.add_paragraph()
    _add_runs(p, doc["confidentiality"])
    for r in p.runs:
        r.font.size = Pt(9)
    d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    # revision history and contents
    p = d.add_paragraph()
    r = p.add_run("URS/RFQ Revision History")
    r.bold, r.font.size = True, Pt(12)
    _table(d, [["Revision #", "Issue Date", "Revised Section", "Revisions Made"]] + doc["history"], True,
           runs_cells=False)
    p = d.add_paragraph()
    r = p.add_run("Table of Contents")
    r.bold, r.font.size = True, Pt(14)
    _field(d.add_paragraph(), 'TOC \\o "1-3" \\h \\z \\u', "Right-click and choose Update Field to build the contents.")
    d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    for s in doc["sections"]:
        if s["pagebreak"]:
            d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        title = f"{s['number']}.\t{s['heading']}" if s["numbered"] else s["heading"]
        d.add_heading(title, level=s["level"])
        _blocks_docx(d, s["blocks"])
    # ask Word to refresh fields (contents, page count) when the file is opened
    settings = d.settings.element
    upd = OxmlElement("w:updateFields")
    upd.set(_qn("w:val"), "true")
    settings.append(upd)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def write_response_docx(doc: dict) -> bytes:
    from docx.shared import Inches, Pt
    d = _docx_base()
    _footer(d, doc)
    if doc.get("doc_control"):
        _doc_control_docx(d, doc["doc_control"])
    p = d.add_paragraph()
    r = p.add_run("URS/RFQ Response Form")
    r.bold, r.font.size = True, Pt(16)
    _table(d, [list(f) for f in doc["fields"]], False, widths=[Inches(2.4), Inches(4.1)], runs_cells=False)
    d.add_paragraph(doc["instructions"])
    _table(d, [["Section #", "Proposed Deviation or Correction"]] + doc["rows"], True,
           widths=[Inches(1.1), Inches(5.4)], runs_cells=False)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
