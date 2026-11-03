"""Convenient Enterprises stage 3: requirement library, URS/RFQ package, intake, compliance, Response Form, URS
response depth (ce-requirements section 8; acceptance tests 2 and 3)."""

import io
import zipfile
from decimal import Decimal
from pathlib import Path

import pytest
from ce_mgm import mgm

from proposal_builder import ce
from proposal_builder import ce_urs as U
from proposal_builder.calc import calculate
from proposal_builder.ce_models import CONSULTANT, URS, BomItem
from proposal_builder.models import CE
from proposal_builder.render.document import build_document, compile_document
from proposal_builder.render.urs_document import (
    build_package,
    build_response_form,
    write_docx,
    write_response_docx,
)
from proposal_builder.render.urs_questionnaire import (
    read_questionnaire,
    write_questionnaire,
)
from proposal_builder.revisions import issue
from proposal_builder.store import DataStore
from proposal_builder.ui.state import AppState

pypdf = pytest.importorskip("pypdf")
docx = pytest.importorskip("docx")

# URS/RFQ Template Rev 1.0, table of contents (sections 1 to 15) plus the FAT/SAT appendix headings
TEMPLATE_TOC = """1 Introduction|1.1 Summary|1.2 Project Adherence|1.3 Confidentiality Agreement|
1.4 Project Conceptualization and Quoting|1.5 Quoting|1.6 URS/RFQ Package Contents|2 Current Process and Product Data|
2.1 Current Process Steps|2.2 Product Scope|2.3 Product Prints|2.4 Process Data|3 System Requirements|
3.1 Control Interfaces|3.2 Process Parameters|3.3 Loading and Alignment|3.3.1 Component Loading|
3.3.2 Component Consumption|3.4 Process Flow|3.5 Process Data|3.6 Cosmetic or Functional Defects|3.7 Changeover Time|
3.8 System Size|3.9 System Durability|3.10 Plant Environment|3.11 Maintenance|3.12 Component Availability|
3.13 Interface Devices|4 Safety Features|4.1 Guarding|4.2 Noise|4.3 Ventilation|4.4 Compressed Media|
4.5 Electrical Components and Connections|4.6 E-Stops|4.7 Safety Device Circuits|
4.8 Stored Energy and Lock-out / Tag-out|4.9 Operator Ergonomics|5 Electrical and Control Specifications|
5.1 Common Electrical Standards|5.2 Control Panel and Devices|5.3 Machine Mounted Devices|
5.4 Programmable Logic Controller (PLC) and Human Machine Interfaces (HMI)|5.4.1 Program Retention|5.4.2 Hardware|
5.4.3 Control Access Levels|5.4.4 Product Recipe|5.4.5 Alarms and Diagnostics|6 Hydraulic Specifications|
6.1 Operating Pressures|6.2 Pumps|6.3 Solenoids|6.4 Fluids|6.5 Reservoirs|
6.6 Filters, Strainers, Flow Meters, and Gauges|6.7 Piping and Tubing|6.8 Component Marking|
7 Pneumatic Specifications|7.1 Operating Pressures|7.2 Safety Shut-off Valves|7.3 Filters, Regulators, and Lubricators|
7.4 Directional Control Valves|7.5 Mufflers|7.6 Cylinders|7.7 Component Marking|8 Tooling, Fixturing, and Gauging|
8.1 Component Marking|9 Available Utilities|9.1 Electrical|9.2 Pneumatic|9.3 Miscellaneous|10 Documentation|
10.1 Mechanical|10.2 Electrical|10.3 Controls|10.4 Miscellaneous|10.5 System User Manuals|10.6 System Layout|
10.7 Preventative Maintenance|11 Project Milestones, Approvals, and Payment Schedule|12 On-going Support|
13 Design and Document Ownership|14 Disclaimer|14.1 Content|14.2 Validity|
15 URS & RFQ Acknowledgement and Acceptance| Provider Contact Information| Provider Acceptance|
 Consumer Acceptance|16 Appendix: FAT/SAT Plan"""


def _toc():
    return [x.strip("\n") for x in TEMPLATE_TOC.replace("\n", "").split("|")]


@pytest.fixture
def lib() -> U.RequirementLibrary:
    return U.default_library()


@pytest.fixture
def st(tmp_path: Path) -> AppState:
    return AppState(DataStore(tmp_path / "data"))


def _pdf_text(pdf: bytes) -> str:
    return "\n".join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(pdf)).pages)


def test_library_matches_template_numbering(lib):
    items = [U.UrsItem(level=n.level, numbered=n.numbered) for n in lib.nodes]
    got = [f"{num} {n.heading}" for n, num in zip(lib.nodes, U.numbers(items), strict=True)]
    toc = _toc()
    assert [g for g in got if g.split(" ")[0].count(".") < 3 and not g.startswith("16.")][:len(toc)] == toc
    # the appendix cross-references (16.7.4 to 16.7.7) point at the right sections
    by_num = dict(g.split(" ", 1) for g in got if g[0].isdigit())
    assert by_num["16.7.4"] == "Controls and Software Verification"
    assert by_num["16.7.5"] == "Safety System Verification"
    assert by_num["16.7.7"] == "Measurement System/Metrology Verification"
    assert {t.key for t in lib.tags} >= {"hydraulics", "pneumatics", "plc", "recipes", "interfaces", "fatsat"}


def test_blank_template_package(lib):
    """Acceptance test 2: the library prints as the URS/RFQ Template with no manual edits."""
    doc = build_package(lib, None)
    assert doc["mode"] == U.TEMPLATE and doc["instructions"] and doc["doc_control"]
    d = docx.Document(io.BytesIO(write_docx(doc)))
    heads = [p.text.replace("\t", " ").replace(". ", " ", 1) for p in d.paragraphs if p.style.name.startswith("Heading")]
    toc = [t.strip() for t in _toc()]
    assert heads[:len(toc)] == toc
    text = "\n".join(p.text for p in d.paragraphs)
    assert "[Modify the below paragraphs as necessary" in text and "Please delete this page" in text
    assert "Request For Quotation (RFQ)" in text and "Confidential Information:" in text
    tables = [[c.text for c in t.rows[0].cells] for t in d.tables]
    assert ["Revision #", "Issue Date", "Revised Section", "Revisions Made"] in tables
    pdf = _pdf_text(compile_document(doc, None, template="urs.typ"))
    assert "Table of Contents" in pdf and "16.7.12" in pdf and "URS & RFQ Acknowledgement and Acceptance" in pdf


def test_issued_package_answers_tags_and_omit(lib):
    urs = U.from_library(lib, None)
    urs.answers.update(plant="Murphy", system_task="press bushings", min_length="4.5 in",
                       interface_devices="Leak tester\nLabel printer")
    urs.tags.update(hydraulics=False, interfaces=True)
    doc = build_package(lib, urs, mode=U.ISSUED)
    secs = {s["number"]: s for s in doc["sections"]}
    assert secs["6"]["na"] and secs["7"]["heading"] == "Pneumatic Specifications"
    flat = str(doc["sections"])
    assert "[Modify the below" not in flat and "Murphy plant" in flat and "press bushings" in flat
    assert "Leak tester" in flat and "There are no external devices" not in flat
    assert not doc["instructions"] and doc["doc_control"] is None and doc["prepared_by"] == ""
    co = {"name": "Convenient Enterprises", "legal": "Convenient Enterprises LLC", "email": "nick@convenient.enterprises"}
    branded = build_package(lib, urs, mode=U.ISSUED, company=co)
    assert branded["prepared_by"] == "Prepared by Convenient Enterprises LLC | nick@convenient.enterprises"
    d = docx.Document(io.BytesIO(write_docx(branded)))
    assert d.sections[0].footer.paragraphs[-1].text == branded["prepared_by"]
    urs.omit = U.OMIT_REMOVE
    secs = {s["number"]: s["heading"] for s in build_package(lib, urs, mode=U.ISSUED)["sections"]}
    assert secs["6"] == "Pneumatic Specifications" and secs["15"] == "Appendix: FAT/SAT Plan"
    left = dict(U.leftover_blanks(lib, urs))
    assert "2.2" in left and left["2.2"] == 7          # min length answered, 7 sizes still blank


def test_questionnaire_round_trip(lib):
    urs = U.from_library(lib, None)
    urs.answers["plant"] = "Murphy"
    data = write_questionnaire(lib, urs)
    answers, tags, dk = read_questionnaire(data)
    assert answers == {"plant": "Murphy"} and tags == {} and dk == []
    # the client fills it in: tick Yes for hydraulics, type a cycle time, tick don't know on volume
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        files = {n: z.read(n) for n in z.namelist()}
    xml = files["word/document.xml"].decode()

    def tick(tag: str) -> None:
        nonlocal xml
        i = xml.index(f'w:val="{tag}"')
        j = xml.index('w14:val="0"', i)
        xml = xml[:j] + 'w14:val="1"' + xml[j + 11:]
    tick("tag:hydraulics:yes")
    tick("var:volume_now:dk")
    i = xml.index('w:val="var:cycle_now"')
    j = xml.index("Click or tap here to enter text.", i)
    xml = xml[:j] + "49 seconds" + xml[j + len("Click or tap here to enter text."):]
    k = xml.index('w:val="var:cycle_now"')
    xml = xml[:k] + xml[k:].replace("<w:showingPlcHdr/>", "", 1)
    files["word/document.xml"] = xml.encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n, b in files.items():
            z.writestr(n, b)
    answers, tags, dk = read_questionnaire(buf.getvalue())
    assert tags == {"hydraulics": True} and answers["cycle_now"] == "49 seconds" and dk == ["volume_now"]


def test_compliance_and_response_form(lib):
    """Acceptance test 3: every requirement has a status; the Response Form lists Deviate and Clarify by section."""
    urs = U.for_client_spec("Cell URS", "URS-77", "B", "2026-10-01", lib)
    assert urs.items[0].number == "1" and any(it.number == "3.10" for it in urs.items)
    for it in urs.items:
        it.status = it.status or "comply"
    by_num = {it.number: it for it in urs.items}
    by_num["3.10"].status, by_num["3.10"].response = "deviate", "Rated for 40 to 100 deg F."
    by_num["3.9"].status, by_num["3.9"].response = "clarify", "Two shifts, 5 days."
    by_num["5.4.2"].status = "deviate"
    rows = U.response_form_rows(urs)
    assert [r.number for r in rows] == ["3.9", "3.10", "5.4.2"]
    assert rows[0].text.startswith("Clarification:")
    issues = U.compliance_issues(urs)
    assert any("5.4.2" in m and "no response text" in m for m in issues)
    assert not any("no compliance status" in m for m in issues)
    form = build_response_form(lib, urs)
    assert form["fields"][0] == ["URS/RFQ Reference Number", "URS-77"] and form["rows"][0][0] == "3.9"
    d = docx.Document(io.BytesIO(write_response_docx(form)))
    assert d.tables[-1].rows[2].cells[0].text == "3.10"
    assert "Rated for 40" in _pdf_text(compile_document(form, None, template="urs.typ"))
    U.client_revision(urs, "C")
    assert all(it.review for it in urs.items if it.kind != "information" and it.status)
    assert any("to review" in m for m in U.compliance_issues(urs))


def test_interview_skips_unused_variables(lib):
    urs = U.from_library(lib, None)
    asked = {q.key for _, qs in U.interview(lib, urs) for q in qs}
    assert {"interface_devices", "budget", "hydraulics"} <= asked
    urs.tags["interfaces"] = False
    for it in urs.items:              # the interface list sits inside a conditional; turning the section off
        if it.heading == "Interface Devices":
            it.on = False
    asked = {q.key for _, qs in U.interview(lib, urs) for q in qs}
    assert "interface_devices" not in asked


def test_store_and_urs_response_proposal(st: AppState):
    lib = st.requirements
    assert (st.store.root / "profiles/ce/requirements.json").exists() and lib.nodes
    project, rev = mgm(st.catalog, st.boilerplate_for(CE))
    rev.sections = sorted({ln.section for ln in rev.lines})
    ps = st.projects
    ps.create(project, rev)
    urs = U.for_client_spec("Tandem Jig URS", "MGM-1", "A", lib=lib)
    for it in urs.items:
        it.status = it.status or "comply"
    urs.items[3].status, urs.items[3].response = "deviate", "CDA signed at award."
    ps.save_urs(project.number, urs)
    assert ps.load_urs(project.number).items[3].response == "CDA signed at award."
    s = st.settings_for(CE)
    ce.set_depth(rev, URS, st.boilerplate_for(CE), s)
    assert rev.depth == URS and any(b.id == "compliance" and b.on for b in rev.blocks)
    rev.bom = [BomItem(description="Robot", manufacturer="Fanuc", model="LR Mate", qty=Decimal(1),
                       unit_cost=Decimal(24000), buyer=CONSULTANT)]
    ce.sync_hardware_line(rev, st.catalog, s, lambda sec, code: rev.new_line_id(sec))
    rev.lines[0].category = "tooling"
    res = calculate(rev, s, st.catalog.stock_classes, project)
    doc = build_document(project, rev, s, st.catalog, st.boilerplate_for(CE), res, urs=urs)
    assert doc["compliance"] and doc["compliance"][0]["status"] == "Comply"
    assert any(r["label"] == "Tooling" for r in doc["commercial"]["rows"]) and doc["commercial"]["major"]
    text = _pdf_text(compile_document(doc, st.store.path(s.company.logo_path)))
    assert "Compliance matrix" in text and "CDA signed at award." in text and "Fanuc LR Mate" in text
    assert "(Tandem Jig URS, Ref MGM-1, Rev A)" in text
    # issuing snapshots the requirements; later edits do not change the issued revision
    ps.save_revision(project.number, rev)
    issue(ps, project, rev)
    urs.items[3].response = "Changed later."
    ps.save_urs(project.number, urs)
    issued = ps.load_revision(project.number)
    assert issued.urs.items[3].response == "CDA signed at award."
    doc = build_document(project, issued, s, st.catalog, st.boilerplate_for(CE), urs=urs)
    assert any(r["response"] == "CDA signed at award." for r in doc["compliance"])
