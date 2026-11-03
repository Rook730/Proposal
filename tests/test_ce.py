"""Convenient Enterprises profile (CE stage 1): branding, catalog, billing, MGM rebuild (acceptance test 1)."""

import io
import json
from decimal import Decimal
from pathlib import Path

import pytest

from proposal_builder import ce
from proposal_builder.calc import calculate
from proposal_builder.models import CE, CW, KS, Brand, Settings, default_brand
from proposal_builder.render.ce_document import build_ce_document, build_estimate_document, estimate_filename
from proposal_builder.render.document import build_document, compile_document
from proposal_builder.store import DataStore
from proposal_builder.ui.state import AppState

from ce_mgm import mgm

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


def test_ce_profile_seeded(st: AppState):
    s = st.settings_for(CE)
    assert s.company.dba == "Convenient Enterprises" and s.company.email == "nick@convenient.enterprises"
    assert (st.store.root / "profiles/ce/logo.svg").exists()
    assert s.payment_rule == "fixed_fee" and s.deposit_pct == D("0.10")
    assert s.brand.layout == "band" and s.brand.font == "IBM Plex Sans"
    assert s.next_proposal_number() == st.settings.next_proposal_number()      # one shared sequence
    heads = st.boilerplate_for(CE).headings
    assert heads[:2] == ["Intro", "Scope"] and "Deliverables" in heads and heads[-1] == "Acceptance"


def test_brand_defaults_keep_old_looks():
    assert default_brand(Settings()) == Brand()                                 # Kept Spec blue
    from proposal_builder.buildsheet import PricingPolicy
    assert default_brand(Settings(pricing=PricingPolicy())).accent == "#A87B20"  # CW dark gold
    custom = Brand(accent="#123456")
    assert default_brand(Settings(brand=custom)) is custom


def test_ce_catalog_and_performer(st: AppState):
    cat = st.catalog
    assert [s.number for s in cat.sections_for(CE)] == [4000, 4100, 4200, 4300]
    assert all(s.number < 4000 or s.number > 4900 for s in cat.sections_for(KS) + cat.sections_for(CW))
    assert {i.code for i in cat.items_for(CE)} >= {4010, 4050, 4090, 4110, 4120, 4210, 4220, 4230}
    assert cat.rate("ce_eng").rate == 125 and cat.rate("ce_travel").rate == D("62.50")
    assert ce.billing(4000, cat) == "fixed" and ce.billing(4100, cat) == "estimate"
    assert st.settings.performer("Convenient Enterprises").income == "CE"
    # removing the performer sticks (the one-time addition does not come back)
    st.settings.performers = [p for p in st.settings.performers if p.name != "Convenient Enterprises"]
    st.save_settings()
    assert AppState(DataStore(st.store.root)).settings.performer("Convenient Enterprises") is None


def test_mgm_totals_deposit_and_option(st: AppState):
    """Acceptance test 1: fixed fee 10,000, support estimate 2,956.25, SISTEMA option outside the total."""
    project, rev = _mgm(st)
    s = st.settings_for(CE)
    res = calculate(rev, s, st.catalog.stock_classes, project)
    sp = ce.split(res.base, st.catalog)
    assert sp.fixed == D("10000.00") and sp.estimate == D("2956.25")
    assert res.base.total == D("12956.25")
    assert res.alternates[1].total == D("13956.25") and res.delta(1) == D("1000.00")
    pay = ce.payments(res.base, s, st.catalog)
    assert pay.deposit == D("1000.00") and pay.fixed_balance == D("9000.00")
    opts = ce.options(rev, res)
    assert [(o.name, o.amount) for o in opts] == [("ISO 13849-1 verification (SISTEMA)", D("1000.00"))]


def test_mgm_proposal_and_estimate_pdf(st: AppState):
    project, rev = _mgm(st)
    s, bp = st.settings_for(CE), st.boilerplate_for(CE)
    logo = st.store.path(s.company.logo_path)
    doc = build_document(project, rev, s, st.catalog, bp)       # dispatches on the project's company
    assert doc["template"] == "ce_proposal.typ"
    text = _text(compile_document(doc, logo))
    for h in ("P R O P O S A L", "S C O P E", "D E L I V E R A B L E S", "C O S T", "T E R M I N A T I O N",
              "A C C E P T A N C E"):
        assert h in text.replace("  ", " ") or h.replace(" ", "") in text.replace(" ", ""), h
    for s_ in ("$10,000.00", "$2,956.25", "$12,956.25", "$1,000.00", "Total with option: $13,956.25",
               "MGM Brakes (Client):", "Convenient Enterprises (Consultant):", "A 10% deposit of the fixed fee"):
        assert s_ in text, s_
    est = build_estimate_document(project, rev, s, st.catalog)
    etext = _text(compile_document(est, logo))
    for s_ in ("$12,956.25", "Deposit requested:", "$1,000.00", "September 27, 2026", "Optional items"):
        assert s_ in etext, s_
    total_line = [ln for ln in etext.splitlines() if ln.startswith("Total") and "option" not in ln]
    assert all("13,956.25" not in ln for ln in total_line)       # the option never lands in the total
    assert estimate_filename(project, rev).endswith("_Estimate_V1.0.pdf")


def test_ce_variables_in_terms(st: AppState):
    project, rev = _mgm(st)
    doc = build_ce_document(project, rev, st.settings_for(CE), st.catalog, st.boilerplate_for(CE))
    payment = next(b for m in doc["modules"] if m["heading"] == "Cost" for b in m["blocks"]
                   if b["title"] == "Payment terms")
    assert "10%" in payment["body"] and "1,000.00" in payment["body"]
    assert any(b["kind"] == "cost" for m in doc["modules"] for b in m["blocks"])
    assert json.dumps(doc)       # plain data
