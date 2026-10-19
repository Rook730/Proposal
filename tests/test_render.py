import io
import json
import re
from decimal import Decimal
from importlib import resources
from pathlib import Path

import pytest

from proposal_builder.models import Boilerplate, Catalog, Settings
from proposal_builder.proposal import Line, Project, Revision
from proposal_builder.render.document import build_document, compile_document, pdf_filename
from proposal_builder.render.markup import md_to_typst

pypdf = pytest.importorskip("pypdf")
typst = pytest.importorskip("typst")

FIXTURE = Path(__file__).parent / "fixtures" / "26005_anon.json"
LOGO = Path(__file__).parents[1] / "src" / "proposal_builder" / "seed" / "logo.png"


def seed(name):
    return (resources.files("proposal_builder") / "seed" / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def env():
    return (Settings.model_validate_json(seed("settings.json")),
            Catalog.model_validate_json(seed("catalog.json")),
            Boilerplate.model_validate_json(seed("boilerplate.json")))


def pages_text(pdf: bytes) -> list[str]:
    return [p.extract_text() for p in pypdf.PdfReader(io.BytesIO(pdf)).pages]


# ---------------------------------------------------------------- markup


def test_markup_escapes_and_structure():
    out = md_to_typst("Cost $5 #1 a_b http://x.com [x]\nnext line\n\n- one\n- **two**\n\n1. first")
    assert "\\$5 \\#1 a\\_b http:\\/\\/x.com \\[x\\] \\" in out
    assert "- one\n- *two*" in out
    assert "1. first" in out


def test_markup_compiles_hostile_text(tmp_path, env):
    settings, catalog, bp = env
    rev = Revision(sections=[100])
    rev.add_line(Line(id="1.01", section=100, title="Weird #title $ *x*", unit_price=Decimal(1),
                      notes="Brackets [a] <b> @c ~d `e` \\f // g = h -- i + j\n- list\n1. num"))
    doc = build_document(Project(number="1", project_name="T"), rev, settings, catalog, bp)
    pdf = compile_document(doc, None)
    assert pdf[:4] == b"%PDF"
    text = " ".join(pages_text(pdf))
    assert "Weird #title $ *x*" in text and "Brackets [a] <b> @c" in text


# ---------------------------------------------------------------- 26005


def test_26005_pdf(env):
    settings, catalog, bp = env
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    project, rev = Project.model_validate(data["project"]), Revision.model_validate(data["revision"])
    pdf = compile_document(build_document(project, rev, settings, catalog, bp), LOGO)
    pages = pages_text(pdf)
    text = "\n".join(pages)
    for s in ["41,186.59", "38,199.69", "32,818.00", "30,438.00", "20,308.00", "17,928.00", "10,296.65",
              "Payment Schedule", "Scope Clarifications & Exclusions", "Client Signature"]:
        assert s in text, s
    assert "{" not in text.replace("{units_table}", ""), "unresolved variable in output"
    assert re.search(r"1 of \d+", pages[0])
    assert pdf_filename(project, rev) == "26005_Client_KitchenRenovation_Proposal_V1.0.pdf"


# ---------------------------------------------------------------- pagination


def _long_rev(n_lines: int, words: int) -> Revision:
    rev = Revision(sections=[1100])
    for i in range(n_lines):
        rev.add_line(Line(id=rev.new_line_id(1100), section=1100, title=f"Line {i}",
                          unit_price=Decimal(10), notes=("word " * words).strip()))
    return rev


@pytest.mark.parametrize("n_lines,words", [(n, w) for n in (14, 17, 21) for w in (25, 40, 60)])
def test_last_line_stays_with_totals(env, n_lines, words):
    settings, catalog, bp = env
    rev = _long_rev(n_lines, words)
    rev.blocks = []
    pdf = compile_document(build_document(Project(number="9", project_name="P"), rev, settings, catalog, bp), None)
    pages = pages_text(pdf)
    last_id = rev.lines[-1].id
    totals_page = next(i for i, p in enumerate(pages) if "Totals:" in p)
    assert last_id in pages[totals_page].split("Totals:")[0], "last line separated from section totals"
    for p in pages:
        if "Line " in p and "Items" not in p:
            pytest.fail("continuation page without the column header")
    first_page_with_lines = next(i for i, p in enumerate(pages) if "Line 0" in p)
    assert "Line 1" in pages[first_page_with_lines], "first two lines split from the header"


def test_allowance_flag_prints_on_line():
    from proposal_builder.render.document import _line_body
    from proposal_builder.models import Performer
    ln = Line(id="11.01", section=1100, title="Tile", general_description="Tile material.", is_allowance=True,
              performer=Performer.SUB)
    assert _line_body(ln, {}).startswith("*Allowance.* _Performed by a licensed subcontractor._ Tile material.")
    ln.is_allowance = False
    assert "Allowance" not in _line_body(ln, {})


def test_rates_table_uses_line_snapshots_for_cw_and_ks():
    from proposal_builder.models import Performer, PriceSource
    from proposal_builder.render.document import rates_table
    cat = Catalog.model_validate_json(seed("catalog.json"))
    rev = Revision(sections=[200, 600])
    rev.add_line(Line(id="6.01", section=600, title="Elec", price_basis=PriceSource.RATE, rate_key="licensed",
                      unit="HR", unit_price=Decimal(95), performer=Performer.SUB))
    rev.add_line(Line(id="6.02", section=600, title="CW", price_basis=PriceSource.RATE, rate_key="cw",
                      unit="HR", unit_price=Decimal(80), performer=Performer.CW))
    rev.add_line(Line(id="2.01", section=200, title="PM", price_basis=PriceSource.RATE, rate_key="pm",
                      unit="HR", unit_price=Decimal(75), performer=Performer.KEPT_SPEC))
    rows = rates_table(rev, cat)
    assert rows == [["Project management / client meetings", "Kept Spec Advisors", "$75.00 / HR"],
                    ["Convenient Woodworking trade labor", "Convenient Woodworking", "$80.00 / HR"]]


def test_owner_supplied_prints_in_parentheses_and_incl_total():
    from proposal_builder.models import PriceSource
    st = Settings.model_validate_json(seed("settings.json"))
    cat = Catalog.model_validate_json(seed("catalog.json"))
    bp = Boilerplate.model_validate_json(seed("boilerplate.json"))
    rev = Revision(sections=[1100, 1400])
    rev.add_line(Line(id="11.01", section=1100, title="Tile", unit_price=Decimal(1000)))
    rev.add_line(Line(id="11.02", section=1100, title="Range", unit_price=Decimal(3200), owner_furnished=True))
    rev.add_line(Line(id="14.01", section=1400, title="Profit", price_basis=PriceSource.PERCENT,
                      unit_price=Decimal("0.10")))
    doc = build_document(Project(number="26999", client_name="X", project_name="Y"), rev, st, cat, bp)
    row = next(r for s in doc["sections"] for r in s["rows"] if r["id"] == "11.02")
    assert row["owner"] and row["cost"] == "3,200.00"
    labels = {t["label"]: t["amount"] for t in doc["totals"]}
    assert labels["Total Price"] == "1,100.00"
    assert labels["Total *Incl. Owner-supplied items"] == "4,300.00"
    assert not any("Alternate" in k and "Owner" in k for k in labels)
    compile_document(doc, None, "pdf")
