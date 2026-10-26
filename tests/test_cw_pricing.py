"""Convenient Woodworking pricing: build sheets, Built lines, rush fee, sales tax, deposit rule, income."""

from decimal import Decimal as D
from importlib import resources

import pytest

from proposal_builder import cw_catalog
from proposal_builder.buildsheet import BuildLabor, BuildMaterial, BuildSheet, PricingPolicy, rough_for
from proposal_builder.calc import calculate, payment_schedule
from proposal_builder.closeout import ChangeOrder, ChangeOrderLog, COItem, contract_context, price_change_orders
from proposal_builder.income import estimate_report
from proposal_builder.models import Boilerplate, Catalog, PriceSource, Settings
from proposal_builder.proposal import Alternate, Line, Project, Revision, default_blocks, line_from_item


def seed(path):
    return (resources.files("proposal_builder") / "seed" / path).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def cw():
    return (Settings.model_validate_json(seed("cw/settings.json")), Catalog.model_validate_json(seed("catalog.json")),
            Boilerplate.model_validate_json(seed("cw/boilerplate.json")))


def box_rev(catalog: Catalog, qty=10, taxable=True, rush=D(0)) -> Revision:
    rev = Revision(taxable=taxable, tax_county="Buncombe", tax_rate=D("0.07"), rush_pct=rush)
    piece = rev.add_piece("Square box")
    ln = line_from_item(catalog.item(3101), catalog, rev.new_line_id(piece.number))
    ln.section, ln.qty = piece.number, D(qty)
    rev.add_line(ln)
    return rev


def test_square_box_template_prices_like_the_estimate(cw):
    _, cat, _ = cw
    b = cat.item(3101).build
    t = b.totals(D(10))
    assert (t.cost, t.overhead, t.profit) == (D("2401.50"), D("360.23"), D("240.15"))
    assert t.unit_price == D("305.00") and t.line_total == D("3050.00")
    assert t.materials == D("864.00") and t.hours == D("20.5")
    assert b.totals(D(1)).unit_price == D("555.00")            # setup carried by one box


def test_lumber_parts_board_feet_and_nominal():
    b = BuildSheet.from_policy(PricingPolicy())
    b.materials = [BuildMaterial(kind="lumber", name="Cherry", pieces=D(1), thickness=D("0.75"), width=D(24),
                                 length=D(21), unit_cost=D(6), priced_as="4/4"),
                   BuildMaterial(kind="lumber", name="Cherry", pieces=D(3), thickness=D("1.75"), width=D(2),
                                 length=D(25), yield_tier="high", unit_cost=D(6), priced_as="4/4")]
    b.recalc()
    top, legs = b.materials
    assert (top.nominal, top.qty, top.unit) == ("4/4", D("5.25"), "BF")      # 1 x 24 x 21 / 144 x 1.5
    assert (legs.nominal, legs.qty) == ("8/4", D("3.75"))                    # 3 x 2 x 2 x 25 / 144 x 1.8
    assert legs.stale and not top.stale
    assert rough_for(D("4.5"), PricingPolicy().rough_map) == ("19/4", D("4.75"))


def test_built_line_with_tax_rush_and_deposit(cw):
    s, cat, _ = cw
    rev = box_rev(cat)
    res = calculate(rev, s, cat.stock_classes)
    assert res.base.subtotal == D("3050.00") and res.base.tax == D("213.50") and res.base.total == D("3263.50")
    ps = payment_schedule(res.base.total, s)
    assert (ps["deposit"], ps["balance"]) == (D("1958.10"), D("1305.40"))
    rush = calculate(box_rev(cat, rush=D("0.20")), s, cat.stock_classes)
    assert (rush.base.rush, rush.base.tax, rush.base.total) == (D("610.00"), D("256.20"), D("3916.20"))
    small = payment_schedule(D(400), s)
    assert small["deposit"] == D("100.00")                                   # 25% under $500
    assert not box_rev(cat, taxable=False).taxable
    assert calculate(box_rev(cat, taxable=False), s, cat.stock_classes).base.total == D("3050.00")


def test_alternate_recomputes_tax(cw):
    s, cat, _ = cw
    rev = box_rev(cat)
    base_id = rev.lines[0].id
    alt_line = line_from_item(cat.item(3101), cat, rev.new_line_id(rev.lines[0].section))
    alt_line.section, alt_line.qty, alt_line.alternate = rev.lines[0].section, D(12), 1
    rev.add_line(alt_line)
    rev.alternates.append(Alternate(number=1, name="Twelve boxes", removes=[base_id]))
    res = calculate(rev, s, cat.stock_classes)
    alt = res.alternates[1]
    assert alt.subtotal == res.lines[alt_line.id].cost
    assert alt.tax == (alt.subtotal * D("0.07")).quantize(D("0.01"))


def test_cw_income_excludes_materials_and_tax(cw):
    s, cat, _ = cw
    rev = box_rev(cat)
    res = calculate(rev, s, cat.stock_classes)
    rep = estimate_report(rev, res, res.base, s)
    assert rep.total("estimate", "CW") == D("2186.00")                       # 3050 - 864 materials
    assert rep.total("estimate", "KS") == D(0)
    assert rep.contract_price == D("3050.00")


def test_cw_change_order_markup_and_tax(cw):
    s, cat, _ = cw
    rev = box_rev(cat)
    ctx = contract_context(rev, s, cat.stock_classes)
    assert ctx.markup_pct == D("0.25") and ctx.tax_rate == D("0.07")
    log = ChangeOrderLog(orders=[ChangeOrder(number="26006-01", items=[COItem(original_cost=D(0), final_cost=D(100))])])
    pr = price_change_orders(log, ctx)["26006-01"]
    assert (pr.markup, pr.tax, pr.price) == (D("25.00"), D("8.75"), D("133.75"))


def test_cw_catalog_applies_once_and_respects_deletes():
    cat = Catalog.model_validate_json(seed("catalog.json"))
    assert cw_catalog.MARKER in cat.migrations
    assert not cw_catalog.apply(cat)
    cat.items = [i for i in cat.items if i.code != 3050]
    assert not cw_catalog.apply(cat)
    assert cat.item(3050) is None
    fresh = Catalog()
    assert cw_catalog.apply(fresh)
    assert fresh.item(3101).price_source is PriceSource.BUILT
    assert fresh.prices.lumber_price("Cherry", "8/4").price == D("7.5")
    assert {u.code for u in fresh.units} >= {"BF", "SHT", "MI"}


def test_cw_document_totals_signature_and_payments(cw):
    s, cat, bp = cw
    from proposal_builder.render.document import build_document
    rev = box_rev(cat)
    rev.blocks = default_blocks(bp.blocks)
    p = Project(number="26006", project_name="Boxes", client_name="Borg Warner Turbo", profile="cw",
                attention="Chris Hodges", po_number="PO-123")
    doc = build_document(p, rev, s, cat, bp)
    labels = [t["label"] for t in doc["totals"]]
    assert labels == ["Subtotal:", "Sales tax (Buncombe County, 7%)", "Total Price"]
    assert doc["company_signature"] is False
    assert doc["sections"][0]["name"] == "Square box"
    assert doc["client"]["attention"] == "Chris Hodges" and doc["client"]["po"] == "PO-123"
    pay = next(g for g in doc["groups"] if g["heading"] == "Payment Schedule")["payments"]
    assert [x["label"] for x in pay][:2] == ["Deposit due at signing (60%)",
                                              "Balance due at delivery or completion of installation"]


def test_cw_terms_have_no_undefined_variables(cw):
    s, cat, bp = cw
    from proposal_builder.calc import DOCUMENT_VARIABLES, SPECIAL_PLACEHOLDERS, referenced, variable_map
    p = Project(number="1", profile="cw")
    rev = box_rev(cat)
    known = set(variable_map(p, rev, s)) | DOCUMENT_VARIABLES | SPECIAL_PLACEHOLDERS
    used = {n for b in bp.blocks for n in referenced(b.body)}
    assert used - known == {"project_overview"}        # filled in per proposal


def test_cw_pdf_compiles(cw):
    pytest.importorskip("typst")
    pypdf = pytest.importorskip("pypdf")
    import io
    from proposal_builder.models import Variable
    from proposal_builder.render.document import build_document, compile_document
    s, cat, bp = cw
    rev = box_rev(cat)
    rev.blocks = default_blocks(bp.blocks)
    rev.variables = [Variable(name="project_overview", value="Ten boxes.")]
    p = Project(number="26006", project_name="Boxes", client_name="Borg Warner Turbo", profile="cw")
    logo = resources.files("proposal_builder") / "seed" / "cw" / "logo.svg"
    from pathlib import Path
    pdf = compile_document(build_document(p, rev, s, cat, bp), Path(str(logo)))
    text = "".join(pg.extract_text() for pg in pypdf.PdfReader(io.BytesIO(pdf)).pages)
    for want in ("Square box", "Sales tax", "3,263.50", "Deposit due at signing", "Natural variation of wood"):
        assert want in text, want
