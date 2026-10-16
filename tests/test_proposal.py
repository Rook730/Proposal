import json
import os
from decimal import Decimal
from importlib import resources
from pathlib import Path

import pytest

from proposal_builder.calc import (
    calculate,
    numeric,
    payment_schedule,
    render,
    stock_round,
    undefined_references,
    variable_map,
)
from proposal_builder.models import Catalog, PriceSource, Settings, Variable
from proposal_builder.proposal import (
    Alternate,
    Line,
    LineTier,
    Project,
    Revision,
    catalog_differences,
    line_from_item,
    pull_update,
)
from proposal_builder.store import DataStore, ProjectStore

FIXTURE = Path(__file__).parent / "fixtures" / "26005_anon.json"
D = Decimal


def seed(name):
    return (resources.files("proposal_builder") / "seed" / name).read_text(encoding="utf-8")


@pytest.fixture
def catalog():
    return Catalog.model_validate_json(seed("catalog.json"))


@pytest.fixture
def settings():
    return Settings.model_validate_json(seed("settings.json"))


@pytest.fixture
def p26005():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return Project.model_validate(data["project"]), Revision.model_validate(data["revision"])


# ---------------------------------------------------------------- acceptance


def test_26005_totals_match_excel(p26005, settings, catalog):
    project, rev = p26005
    res = calculate(rev, settings, catalog.stock_classes, project)
    assert res.errors == []
    assert res.base.subtotal == D("32818.00")
    assert res.base.total == D("41186.59")
    assert res.alternates[1].subtotal == D("30438.00")
    assert res.alternates[1].total == D("38199.69")
    assert res.base.percent_items == {"1.02": D("164.09"), "13.01": D("1640.90"), "13.02": D("1640.90"),
                                      "14.01": D("1640.90"), "14.02": D("3281.80")}


def test_26005_section_totals(p26005, settings, catalog):
    project, rev = p26005
    res = calculate(rev, settings, catalog.stock_classes, project)
    expected = {100: "300", 200: "2145", 300: "390", 500: "1000", 600: "2200", 800: "1250",
                900: "4125", 1000: "0", 1100: "20308", 1200: "300", 1300: "800", 1400: "0"}
    for sec, val in expected.items():
        assert res.base.section_total(sec, with_pct=False) == D(val), sec
    assert res.alternates[1].section_total(1100, with_pct=False) == D("17928")
    assert res.base.section_total(100) == D("464.09")
    assert res.base.section_total(1300) == D("4081.80")


@pytest.mark.skipif(not os.environ.get("PROPOSAL_XLSX"), reason="set PROPOSAL_XLSX to the workbook path")
def test_import_26005_from_workbook(catalog, settings):
    from proposal_builder.import_proposal import import_proposal_sheet
    project, rev = import_proposal_sheet(Path(os.environ["PROPOSAL_XLSX"]), "26005 Proposal",
                                         catalog, settings, [])
    res = calculate(rev, settings, catalog.stock_classes, project)
    assert (res.base.total, res.alternates[1].total) == (D("41186.59"), D("38199.69"))
    assert {v.name: v.value for v in rev.variables}["hood_cfm"] == "400"


# ---------------------------------------------------------------- alternates


def _simple_rev():
    rev = Revision(sections=[100, 1400])
    for title, price in [("A", "1000"), ("B", "500"), ("C", "200")]:
        rev.add_line(Line(id=rev.new_line_id(100), section=100, title=title, unit_price=D(price)))
    rev.add_line(Line(id=rev.new_line_id(1400), section=1400, title="Profit",
                      price_basis=PriceSource.PERCENT, unit_price=D("0.10")))
    return rev


def test_alternate_kinds_and_combinations(settings):
    rev = _simple_rev()
    # alt 1: swap A for A' (800); alt 2: add D (300); alt 3: deduct A (conflicts with alt 1)
    rev.add_line(Line(id=rev.new_line_id(100), section=100, title="A'", unit_price=D(800), alternate=1))
    rev.add_line(Line(id=rev.new_line_id(100), section=100, title="D", unit_price=D(300), alternate=2))
    rev.alternates = [Alternate(number=1, removes=["1.01"]), Alternate(number=2), Alternate(number=3, removes=["1.01"])]
    res = calculate(rev, settings, [])
    assert res.base.subtotal == D(1700) and res.base.total == D(1870)
    assert res.alternates[1].total == D("1650.00")      # 1500 + 10%
    assert res.alternates[2].total == D("2200.00")      # 2000 + 10%
    assert res.alternates[3].total == D("770.00")       # 700 + 10%
    assert res.conflicts == [(1, 3)]
    names = [c.name for c in res.combinations]
    assert names == ["Alt 1 + Alt 2", "Alt 2 + Alt 3"]
    combo = res.combinations[0]
    assert combo.total == res.base.total + res.delta(1) + res.delta(2)   # additive
    assert rev.alternate(1).kind(True) == "swap"
    assert rev.alternate(2).kind(True) == "add"
    assert rev.alternate(3).kind(False) == "deduct"


def test_excluded_sections_do_not_count(settings):
    rev = _simple_rev()
    rev.sections = [1400]
    assert calculate(rev, settings, []).base.subtotal == 0


def test_payment_schedule(settings):
    ps = payment_schedule(D("41186.59"), settings)
    assert ps == {"deposit": D("10296.65"), "progress": D("28830.61"), "retainage": D("2059.33")}
    assert sum(ps.values()) == D("41186.59")


# ---------------------------------------------------------------- variables


def test_variables_precedence_and_render(settings):
    settings.global_variables = [Variable(name="hood_cfm", value="300"), Variable(name="g", value="global")]
    rev = Revision(variables=[Variable(name="hood_cfm", value="400")])
    project = Project(number="26006", client_name="X", project_name="Bath")
    v = variable_map(project, rev, settings)
    assert v["hood_cfm"] == "400" and v["g"] == "global" and v["deposit_pct"] == "25%"
    text = "Hood {hood_cfm} CFM for {project_name}; {units_table}; {missing}"
    assert render(text, v) == "Hood 400 CFM for Bath; {units_table}; {missing}"
    assert undefined_references(text, v) == {"missing"}


def test_bound_quantity_and_price(settings):
    rev = Revision(sections=[1100], variables=[Variable(name="pull_count", value="26"),
                                               Variable(name="pull_price", value="$30")])
    rev.add_line(Line(id="11.01", section=1100, title="Pulls", qty_var="pull_count", price_var="pull_price"))
    res = calculate(rev, settings, [])
    assert res.lines["11.01"].cost == D("780.00")
    rev.variables[0].value = "28"
    assert calculate(rev, settings, []).lines["11.01"].cost == D("840.00")


def test_undefined_bound_variable_is_reported(settings):
    rev = Revision(sections=[1100])
    rev.add_line(Line(id="11.01", section=1100, title="x", qty_var="nope", unit_price=D(1)))
    assert "not defined" in calculate(rev, settings, []).errors[0]


def test_numeric():
    assert numeric('~90"') == D(90) and numeric("$1,200.50") == D("1200.50")
    with pytest.raises(ValueError):
        numeric("abc")


# ---------------------------------------------------------------- stock rounding


def test_stock_round_50lf():
    r = stock_round(D(50), D("0.10"), [D(x) for x in (8, 10, 12, 16, 20)])
    assert r.need == D("55.0")
    assert r.total == D(56)                       # 55 is not reachable with even lengths
    assert r.pieces == {D(20): 2, D(16): 1}
    assert r.describe() == "2 x 20', 1 x 16' = 56 LF"


def test_stock_round_exact_and_fewest_pieces():
    r = stock_round(D(40), D(0), [D(8), D(10), D(20)])
    assert r.total == D(40) and r.pieces == {D(20): 2}


def test_stock_line_quantity(settings, catalog):
    rev = Revision(sections=[900])
    rev.add_line(Line(id="9.01", section=900, title="Crown", unit="LF", takeoff=D(50),
                      stock_class="trim", unit_price=D(10)))
    res = calculate(rev, settings, catalog.stock_classes)
    assert res.lines["9.01"].qty == D(56) and res.lines["9.01"].cost == D("560.00")


# ---------------------------------------------------------------- snapshot rule


def test_catalog_edits_do_not_change_lines(catalog):
    rev = Revision()
    ln = rev.add_line(line_from_item(catalog.item(210), catalog, rev.new_line_id(200)))
    assert ln.unit_price == D(75) and ln.price_basis is PriceSource.RATE
    catalog.rate("pm").rate = D(85)
    catalog.item(210).description = "changed"
    assert ln.unit_price == D(75)
    assert set(catalog_differences(ln, catalog)) == {"general_description", "rate"}
    assert set(pull_update(ln, catalog)) == {"general_description", "rate"}
    assert ln.unit_price == D(85) and ln.general_description == "changed"
    assert catalog_differences(ln, catalog) == {}


def test_allowance_line_tiers(catalog):
    item = catalog.item(1121)
    ln = line_from_item(item, catalog, "11.01")
    a = catalog.allowance(item.allowance_ids[0])
    assert ln.unit_price == a.high and ln.unit == a.unit and ln.is_allowance
    ln.tier = LineTier.LOW
    assert ln.tier_price() == a.low


def test_line_ids_reuse_and_reservation():
    rev = Revision()
    a = rev.add_line(Line(id=rev.new_line_id(500), section=500, title="a", code=510))
    b = rev.add_line(Line(id=rev.new_line_id(500), section=500, title="b", code=520))
    assert (a.id, b.id) == ("5.01", "5.02")
    rev.remove_line(a.id)
    assert rev.new_line_id(500) == "5.01"                         # draft never issued: lowest free ID
    issued = [Line(id="5.01", section=500, title="a", code=510), Line(id="5.02", section=500, title="b", code=520)]
    reserved = {ln.id for ln in issued}
    assert rev.new_line_id(500, reserved, code=999, history=issued) == "5.03"   # 5.01 meant item 510
    assert rev.new_line_id(500, reserved, code=510, history=issued) == "5.01"   # 510 gets its ID back


def test_add_line_by_code_order():
    rev = Revision()
    for code in (210, 230, 250):
        rev.add_line(Line(id=rev.new_line_id(200), section=200, title=str(code), code=code))
    rev.add_line(Line(id=rev.new_line_id(200), section=200, title="240", code=240), by_code=True)
    assert [ln.code for ln in rev.section_lines(200)] == [210, 230, 240, 250]
    assert 200 in rev.sections


# ---------------------------------------------------------------- storage


def test_project_store_roundtrip(tmp_path, p26005):
    project, rev = p26005
    ds = DataStore(tmp_path)
    ds.initialize_from_seed()
    ps = ProjectStore(ds)
    folder = ps.create(project, rev)
    assert folder.name == "26005_Client_Kitchen_Renovation"
    assert ps.list_revisions("26005") == ["1.0"]
    loaded = ps.load_revision("26005")
    assert loaded == rev
    rev.lines[0].qty = D(2)
    ps.save_revision("26005", rev)
    assert ps.load_revision("26005", "1.0").lines[0].qty == D(2)
    assert [p.number for p in ps.list_projects()] == ["26005"]
    with pytest.raises(ValueError):
        ps.create(project, rev)
