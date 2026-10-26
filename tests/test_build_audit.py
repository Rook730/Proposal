"""1.9.2 build sheet audit fixes."""

from decimal import Decimal as D
from importlib import resources

from proposal_builder import cw_catalog
from proposal_builder.buildsheet import BuildLabor, BuildMaterial, BuildSheet, PricingPolicy, pull_prices
from proposal_builder.models import Catalog, FinishPrice, LumberPrice, PriceReferences, SheetPrice
from proposal_builder.proposal import line_from_item


def seed_catalog() -> Catalog:
    return Catalog.model_validate_json((resources.files("proposal_builder") / "seed" / "catalog.json")
                                       .read_text(encoding="utf-8"))


def test_whole_sheets_bought_for_the_line():
    b = seed_catalog().item(3101).build
    t12 = b.totals(D(12))
    assert t12.whole_units == D("47.20")                      # 3.6 sheets charged as 4
    assert t12.materials == D("4") * 118 + 12 * D(51)
    assert b.totals(D(10)).whole_units == 0                   # 3 sheets exactly
    one = BuildMaterial(kind="sheet", qty=D("0.3"), unit_cost=D(118), buy_whole=True)
    assert one.line_quantity(D(1)) == 1 and one.line_cost(D(5)) == D(236)
    setup = BuildMaterial(kind="sheet", qty=D("0.5"), unit_cost=D(100), buy_whole=True, setup=True)
    assert setup.line_quantity(D(20)) == 1


def test_existing_templates_get_buy_whole_once():
    cat = Catalog()
    cw_catalog.apply(cat)
    cw_catalog.apply_restoration(cat)
    cat.item(3101).build.materials[0].buy_whole = False       # as saved by 1.8 / 1.9.0
    assert cw_catalog.apply_all(cat) and cat.item(3101).build.materials[0].buy_whole
    cat.item(3101).build.materials[0].buy_whole = False
    assert not cw_catalog.apply_all(cat) and not cat.item(3101).build.materials[0].buy_whole


def test_template_takes_settings_rates():
    cat = seed_catalog()
    policy = PricingPolicy(profit_pct=D("0.20"), shop_rate=D(80))
    ln = line_from_item(cat.item(3101), cat, "90.01", policy=policy)
    assert (ln.build.profit_pct, ln.build.shop_rate) == (D("0.20"), D(80))
    assert len(ln.build.labor) == len(cat.item(3101).build.labor)
    assert cat.item(3101).build.profit_pct == D("0.10")      # the template itself is unchanged
    assert line_from_item(cat.item(3101), cat, "90.02").build.profit_pct == D("0.10")


def test_labor_plus_profit_rate_excludes_overhead():
    t = seed_catalog().item(3101).build.totals(D(10))
    assert t.effective_rate == ((t.line_total - t.materials - t.overhead) / t.hours).quantize(D("0.01"))
    assert t.effective_rate == D("89.06")
    assert t.profit_margin.quantize(D("0.001")) == D("0.080")


def test_finish_takes_product_coats_and_pull_keeps_typed():
    prices = PriceReferences(
        finishes=[FinishPrice(id="f", product="Arm-R-Seal", container_price=D(30), coverage_sf=D(100), coats=D(3))],
        lumber=[LumberPrice(id="c4", species="Cherry", thickness="4/4", price=D(6)),
                LumberPrice(id="c8", species="Cherry", thickness="8/4", price=D("7.5"))],
        sheets=[SheetPrice(id="bb", product="Baltic birch", price=D(80))])
    b = BuildSheet.from_policy(PricingPolicy())
    fin = BuildMaterial(kind="finish", ref="f", name="Arm-R-Seal", qty=D(20))
    leg = BuildMaterial(kind="lumber", name="Cherry", pieces=D(3), thickness=D("0.75"), width=D(2), length=D(25))
    typed = BuildMaterial(kind="sheet", ref="bb", name="Baltic birch", qty=D(1), unit_cost=D(95), typed_cost=True)
    direct = BuildMaterial(kind="lumber", name="Walnut", qty=D(4), unit="BF", unit_cost=D(9))
    b.materials = [fin, leg, typed, direct]
    missing, kept = pull_prices(b, prices)
    assert fin.coats == 3 and fin.cost == D("18.00")
    assert (leg.nominal, leg.unit_cost) == ("4/4", D(6))
    assert typed.unit_cost == D(95) and kept == ["Baltic birch"]
    assert direct.unit_cost == D(9) and missing == []          # board feet typed directly: left alone
    leg.thickness = D("1.75")                                  # thicker legs: 8/4 now
    b.recalc()
    assert leg.stale
    pull_prices(b, prices)
    assert (leg.nominal, leg.unit_cost, leg.stale) == ("8/4", D("7.5"), False)
