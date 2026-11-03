"""Convenient Enterprises stage 2: hours buildup, BOM pass-through, milestones, schedule, depth, trips, ECNs."""

import io
from decimal import Decimal
from pathlib import Path

import pytest
from ce_mgm import mgm

from proposal_builder import ce, ce_catalog
from proposal_builder.calc import calculate
from proposal_builder.ce_models import (
    CONSULTANT,
    DETAILED,
    LETTER,
    BomItem,
    Milestone,
    TaskHours,
    TravelDestination,
)
from proposal_builder.closeout import (
    ChangeOrder,
    ChangeOrderLog,
    COFunding,
    COItem,
    contract_context,
    price_change_orders,
)
from proposal_builder.income import ce_estimate_report
from proposal_builder.models import CE, Boilerplate, Settings
from proposal_builder.proposal import contract_revision
from proposal_builder.render.ce_document import build_ce_document
from proposal_builder.render.closeout_docs import change_order_document
from proposal_builder.render.document import compile_document
from proposal_builder.store import DataStore
from proposal_builder.ui.state import AppState

pypdf = pytest.importorskip("pypdf")
D = Decimal


@pytest.fixture
def st(tmp_path: Path) -> AppState:
    return AppState(DataStore(tmp_path / "data"))


def _mgm(st):
    project, rev = mgm(st.catalog, st.boilerplate_for(CE))
    rev.sections = sorted({ln.section for ln in rev.lines})
    return project, rev


def _text(pdf: bytes) -> str:
    return "\n".join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(pdf)).pages)


def test_seeded_templates_and_library(st: AppState):
    s, bp = st.settings_for(CE), st.boilerplate_for(CE)
    assert s.task_templates and s.destinations[0].name == "Murphy, NC" and s.destinations[0].round_trip_miles == 110
    assert sum((m.pct for m in s.milestone_template), D(0)) + s.deposit_pct == 1
    assert "Assumptions" in bp.headings
    assert {b.id for b in bp.blocks} >= set(ce_catalog.DETAILED_IDS)
    assert all(not b.default_on for b in bp.blocks if b.id in ce_catalog.DETAILED_IDS)
    assert st.catalog.item(4310).section == 4300 and st.catalog.section(4300).billing == "estimate"


def test_upgrades_apply_once_to_stage1_folders():
    bp = Boilerplate(headings=["Intro", "Exclusions", "Time Table", "Cost"])
    assert ce_catalog.upgrade_library(bp) and not ce_catalog.upgrade_library(bp)
    assert bp.headings == ["Intro", "Exclusions", "Assumptions", "Time Table", "Cost"]
    bp.blocks = [b for b in bp.blocks if b.id != "bom"]          # deleted by the user: stays deleted
    assert not ce_catalog.upgrade_library(bp) and "bom" not in {b.id for b in bp.blocks}
    s = Settings()
    assert ce_catalog.upgrade_settings(s) and s.task_templates and not ce_catalog.upgrade_settings(s)


def test_hours_buildup_sets_quantity(st: AppState):
    project, rev = _mgm(st)
    s = st.settings_for(CE)
    rev.lines[0].tasks = [TaskHours(name="Design", hours=D(50)), TaskHours(name="PLC", hours=D("22.5"))]
    res = calculate(rev, s, st.catalog.stock_classes, project)
    assert res.lines[rev.lines[0].id].qty == D("72.5") and res.lines[rev.lines[0].id].cost == D("9062.50")


def test_bom_hardware_line_sync_and_income(st: AppState):
    project, rev = _mgm(st)
    s = st.settings_for(CE)
    nid = lambda sec, code: rev.new_line_id(sec)
    rev.bom = [BomItem(description="Safety relay", qty=D(1), unit_cost=D(300)),                 # client buys
               BomItem(description="Valve", qty=D(3), unit_cost=D(200), buyer=CONSULTANT)]
    ln = ce.sync_hardware_line(rev, st.catalog, s, nid)
    assert ln.unit_price == D("660.00") and 4300 in rev.sections
    res = calculate(rev, s, st.catalog.stock_classes, project)
    assert ce.split(res.base, st.catalog).estimate == D("2956.25") + D("660.00")
    rep = ce_estimate_report(rev, res, res.base, s)
    hw = next(x for x in rep.groups[0].lines if x.line_id == ln.id)
    assert hw.estimate == D("60.00")                                  # only the sourcing fee is income
    rev.bom[1].qty = D(4)
    assert ce.sync_hardware_line(rev, st.catalog, s, nid).unit_price == D("880.00")
    rev.bom[1].buyer = "client"
    assert ce.sync_hardware_line(rev, st.catalog, s, nid) is None
    assert all(l.code != 4310 for l in rev.lines) and 4300 not in rev.sections


def test_milestones_and_depth(st: AppState):
    project, rev = _mgm(st)
    s, bp = st.settings_for(CE), st.boilerplate_for(CE)
    ce.set_depth(rev, DETAILED, bp, s)
    assert rev.depth == DETAILED and rev.milestones and rev.phases
    assert all(b.on for b in rev.blocks if b.id in ce_catalog.DETAILED_IDS)
    res = calculate(rev, s, st.catalog.stock_classes, project)
    rows, left = ce.milestone_schedule(rev, res.base, s, st.catalog)
    assert left == 0 and sum((r.amount for r in rows), D(0)) == D("10000.00")
    assert [r.amount for r in rows] == [D("1000.00"), D("4000.00"), D("3000.00"), D("2000.00")]
    rev.milestones.append(Milestone(name="Extra", pct=D("0.05")))
    assert ce.milestone_schedule(rev, res.base, s, st.catalog)[1] == D("-0.05")
    ce.set_depth(rev, LETTER, bp, s)
    assert not any(b.on for b in rev.blocks if b.id in ce_catalog.DETAILED_IDS)


def test_detailed_pdf_tables(st: AppState):
    project, rev = _mgm(st)
    s, bp = st.settings_for(CE), st.boilerplate_for(CE)
    ce.set_depth(rev, DETAILED, bp, s)
    rev.bom = [BomItem(manufacturer="Pilz", model="PNOZ s4", part_number="750104", description="Safety relay")]
    text = _text(compile_document(build_ce_document(project, rev, s, st.catalog, bp), st.store.path(s.company.logo_path)))
    for t in ("Bill of materials", "Pilz PNOZ s4", "750104", "Milestone payments", "Design approval", "$4,000.00",
              "Schedule", "Weeks 0 to 3", "A S S U M P T I O N S"):
        assert t in text or t.replace(" ", "") in text.replace(" ", ""), t


def test_trip_lines(st: AppState):
    project, rev = _mgm(st)
    rev.lines = [ln for ln in rev.lines if ln.section != 4200]
    dest = TravelDestination(name="Murphy, NC", one_way_hours=D("2.5"), round_trip_miles=D(180), overnight=True)
    made = ce.trip_lines(rev, st.catalog, dest, trips=2, nights=1, new_id=lambda sec, code: rev.new_line_id(sec))
    assert [(l.code, l.qty) for l in made] == [(4210, D("5.0")), (4220, D(1)), (4230, D(360))]
    res = calculate(rev, st.settings_for(CE), st.catalog.stock_classes, project)
    assert sum((res.lines[l.id].cost for l in made), D(0)) == D("312.50") + D(300) + D("261.00")


def test_ecn_no_markup_and_hours(st: AppState):
    project, rev = _mgm(st)
    s = st.settings_for(CE)
    acc = contract_revision(rev, [])
    ctr = contract_context(acc, s, st.catalog.stock_classes, project)
    assert ctr.markup_pct == 0 and ctr.tax_rate == 0
    item = COItem(description="Add a second light curtain", hours=D(6), rate=D(125))   # final cost follows
    assert item.final_cost == D("750.00")
    co = ChangeOrder(number="26007-01", funding=COFunding.CLIENT, items=[item])
    pr = price_change_orders(ChangeOrderLog(orders=[co]), ctr)["26007-01"]
    assert pr.price == D("750.00") and pr.billed == D("750.00")
    doc = change_order_document(project, ctr, co, pr, s)
    assert doc["co"]["doc_title"] == "Engineering Change Notice"
    text = _text(compile_document(doc, st.store.path(s.company.logo_path), template="co.typ"))
    assert "6 HR at $125.00" in text and "Overhead" not in text and "ECN price" in text


def test_issue_checks(st: AppState):
    project, rev = _mgm(st)
    s, bp = st.settings_for(CE), st.boilerplate_for(CE)
    res = calculate(rev, s, st.catalog.stock_classes, project)
    assert ce.checks(rev, res.base, s, st.catalog, bp) == []          # library disclaimers are not flagged
    ce.set_depth(rev, DETAILED, bp, s)
    from proposal_builder.calc import undefined_references
    assert not any(undefined_references(b.body, {}) for b in rev.blocks if b.id in ("bom", "milestones", "timeline"))
    rev.milestones.append(Milestone(name="Extra", pct=D("0.05")))
    rev.bom = [BomItem(description="Safety PLC", qty=D(1), unit_cost=D(2500)),
               BomItem(description="Valve", qty=D(2), buyer=CONSULTANT)]
    rev.lines[0].notes = "We guarantee the cycle time."
    scope = next(b for b in rev.blocks if b.id == "objective")
    scope.body += " The design will be PE stamped."
    msgs = [m for _, m, _ in ce.checks(rev, res.base, s, st.catalog, bp)]
    assert any("105%" in m for m in msgs)
    assert any("Valve" in m and "no cost" in m for m in msgs)
    assert any("Safety PLC" in m and "make and model" in m for m in msgs)
    assert any(m.startswith(rev.lines[0].id) and "guarantee" in m for m in msgs)
    assert any("pe, stamped" in m for m in msgs)
    assert any("Client buys all hardware" in m for m in msgs)
    assert ce.new_cert_words("not PE-stamped calculations", "not PE-stamped calculations") == []
