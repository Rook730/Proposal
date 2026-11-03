"""Word requirements questionnaire (ce-requirements 8.3): the intake questions in plain language, answered in Word
with content controls (text boxes and check boxes), then imported back. Same answer set as the in-app interview.

Each control carries a tag: "tag:<key>:yes|no|dk" (check boxes for a yes/no section question), "var:<name>"
(text answer) and "var:<name>:dk" (don't know). Import reads the tags, so the client may add notes elsewhere in
the document without breaking it.
"""

from __future__ import annotations

import io
import zipfile

from lxml import etree

from .. import ce_urs as U

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
NS = {"w": W, "w14": W14}
BOX_ON, BOX_OFF = "☒", "☐"


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _text_sdt(tag: str, alias: str, value: str, multiline: bool) -> str:
    placeholder = not value
    shown = value or "Click or tap here to enter text."
    runs = []
    for i, line in enumerate(shown.split("\n")):
        if i:
            runs.append("<w:r><w:br/></w:r>")
        color = '<w:rPr><w:color w:val="808080"/></w:rPr>' if placeholder else ""
        runs.append(f'<w:r>{color}<w:t xml:space="preserve">{_esc(line)}</w:t></w:r>')
    return (f'<w:sdt xmlns:w="{W}"><w:sdtPr><w:alias w:val="{_esc(alias[:60])}"/><w:tag w:val="{_esc(tag)}"/>'
            + ("<w:showingPlcHdr/>" if placeholder else "")
            + f'<w:text{" w:multiLine=\"1\"" if multiline else ""}/></w:sdtPr>'
            + f'<w:sdtContent>{"".join(runs)}</w:sdtContent></w:sdt>')


def _box_sdt(tag: str, checked: bool) -> str:
    return (f'<w:sdt xmlns:w="{W}" xmlns:w14="{W14}"><w:sdtPr><w:tag w:val="{_esc(tag)}"/>'
            f'<w14:checkbox><w14:checked w14:val="{1 if checked else 0}"/>'
            '<w14:checkedState w14:val="2612" w14:font="MS Gothic"/>'
            '<w14:uncheckedState w14:val="2610" w14:font="MS Gothic"/></w14:checkbox></w:sdtPr>'
            '<w:sdtContent><w:r><w:rPr><w:rFonts w:ascii="MS Gothic" w:eastAsia="MS Gothic" w:hAnsi="MS Gothic"/>'
            f'</w:rPr><w:t>{BOX_ON if checked else BOX_OFF}</w:t></w:r></w:sdtContent></w:sdt>')


def write_questionnaire(lib: U.RequirementLibrary, urs: U.ProjectUrs, project=None,
                        company_name: str = "Convenient Enterprises") -> bytes:
    from docx import Document
    from docx.oxml import parse_xml
    from docx.shared import Pt, RGBColor

    d = Document()
    d.styles["Normal"].font.name = "Calibri"
    d.styles["Normal"].font.size = Pt(11)
    client = getattr(project, "client_name", "") or ""
    name = getattr(project, "project_name", "") or urs.title
    d.add_heading("Requirements questionnaire", level=0)
    p = d.add_paragraph()
    p.add_run(" | ".join(x for x in (client, name, getattr(project, "number", "")) if x)).bold = True
    d.add_paragraph(
        f"These questions help {company_name} write the requirements for your machine. Answer in plain words; "
        "rough numbers are fine. Click a gray box to type your answer, and tick a box for yes/no questions. If you "
        "are not sure, tick \"Don't know\" and we will work it out together. Return this file by email when done.")
    for topic, questions in U.interview(lib, urs):
        d.add_heading(topic.title, level=1)
        for q in questions:
            qp = d.add_paragraph()
            qp.paragraph_format.space_before = Pt(8)
            qp.paragraph_format.keep_with_next = True
            qp.add_run(q.text).bold = True
            if q.example:
                ep = d.add_paragraph()
                ep.paragraph_format.keep_with_next = True
                er = ep.add_run(f"Example: {q.example}")
                er.italic, er.font.size = True, Pt(9)
                er.font.color.rgb = RGBColor(0x60, 0x60, 0x60)
            ap = d.add_paragraph()
            if q.kind == "tag":
                cur = urs.tags.get(q.key)
                for label, val, state in (("Yes", "yes", cur is True), ("No", "no", cur is False),
                                          ("Don't know", "dk", False)):
                    ap._p.append(parse_xml(_box_sdt(f"tag:{q.key}:{val}", state)))
                    ap.add_run(f" {label}      ")
            else:
                cur = urs.answers.get(q.key, "")
                ap._p.append(parse_xml(_text_sdt(f"var:{q.key}", q.text, cur, q.type == "list")))
                dk = d.add_paragraph()
                dk._p.append(parse_xml(_box_sdt(f"var:{q.key}:dk", False)))
                r = dk.add_run(" Don't know")
                r.font.size = Pt(9)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def _sdt_text(sdt) -> str:
    content = sdt.find("w:sdtContent", NS)
    if content is None:
        return ""
    parts = []
    for el in content.iter():
        tag = etree.QName(el).localname
        if tag == "t":
            parts.append(el.text or "")
        elif tag in ("br", "cr") or tag == "p" and parts:
            parts.append("\n")
    return "".join(parts).strip()


def _checked(sdt) -> bool:
    c = sdt.find("w:sdtPr/w14:checkbox/w14:checked", NS)
    if c is not None and c.get(f"{{{W14}}}val") in ("1", "true"):
        return True
    return any(ch in _sdt_text(sdt) for ch in (BOX_ON, "☑", "✓", "X", "x"))


def read_questionnaire(data: bytes) -> tuple[dict[str, str], dict[str, bool], list[str]]:
    """(answers, tags, don't know keys) from a returned questionnaire. Placeholder text counts as blank."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        root = etree.fromstring(z.read("word/document.xml"))
    answers: dict[str, str] = {}
    tags: dict[str, bool] = {}
    dont_know: list[str] = []
    for sdt in root.iter(f"{{{W}}}sdt"):
        tag_el = sdt.find("w:sdtPr/w:tag", NS)
        if tag_el is None:
            continue
        tag = tag_el.get(f"{{{W}}}val", "")
        parts = tag.split(":")
        if parts[0] == "tag" and len(parts) == 3:
            if _checked(sdt):
                if parts[2] == "dk":
                    dont_know.append(parts[1])
                else:
                    tags[parts[1]] = parts[2] == "yes"
        elif parts[0] == "var" and len(parts) == 2:
            placeholder = sdt.find("w:sdtPr/w:showingPlcHdr", NS) is not None
            text = "" if placeholder else _sdt_text(sdt)
            if text and text != "Click or tap here to enter text.":
                answers[parts[1]] = text
        elif parts[0] == "var" and len(parts) == 3 and parts[2] == "dk" and _checked(sdt):
            dont_know.append(parts[1])
    for k in dont_know:
        answers.pop(k, None)
    return answers, tags, dont_know
