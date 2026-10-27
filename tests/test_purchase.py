"""Purchase list and price age (1.10.0)."""

from datetime import date
from decimal import Decimal as D

from proposal_builder.buildsheet import BuildMaterial, BuildSheet, PricingPolicy, is_old, old_prices
from proposal_builder.calc import calculate
from proposal_builder.models import FinishPrice, LumberPrice, PriceReferences, Settings, SheetPrice
from proposal_builder.proposal import Line, PriceSource, Revision
from proposal_builder.purchase import purchase_list

PRICES = PriceReferences(
    lumber=[LumberPrice(id="c8", species="Cherry", thickness="8/4", price=D("7.50"), supplier="Hearne",
                        date=date(2026, 9, 1))],
    sheets=[SheetPrice(id="bb", product="Baltic birch", thickness='3/4"', width_in=D(60), length_in=D(60),
                       price=D(90), date=date(2025, 1, 1))],
    finishes=[FinishPrice(id="oil", product="Rubio", container="350 ml", container_price=D(60), coverage_sf=D(100))],
)


def sheet(*mats: BuildMaterial) -> BuildSheet:
    b = BuildSheet.from_policy(PricingPolicy())
    b.materials = list(mats)
    b.recalc()
    return b


def built(rev: Revision, section: int, qty: int, build: BuildSheet, alternate: int | None = None) -> Line:
    ln = Line(id=rev.new_line_id(section), section=section, title=f"piece {section}", qty=D(qty),
              price_basis=PriceSource.BUILT, build=build, alternate=alternate)
    return rev.add_line(ln)


def test_purchase_list_totals_across_lines_then_rounds_up():
    rev = Revision()
    half = BuildMaterial(kind="sheet", ref="bb", name="Baltic birch", qty=D("0.5"), unit="SHT", unit_cost=D(90),
                         buy_whole=True)
    cherry = BuildMaterial(kind="lumber", ref="Cherry", name="Cherry", pieces=D(4), thickness=D("1.75"), width=D(2),
                           length=D(25), unit_cost=D("7.50"), priced_as="8/4")
    oil = BuildMaterial(kind="finish", ref="oil", name="Rubio", qty=D(30), unit="SF", coats=D(2), unit_cost=D("0.6"))
    built(rev, 3100, 1, sheet(half, cherry, oil))
    built(rev, 3200, 2, sheet(half.model_copy(), cherry.model_copy()))
    built(rev, 3300, 5, sheet(half.model_copy()), alternate=1)            # alternates are not bought
    rev.add_line(Line(id=rev.new_line_id(3000), section=3000, title="Delivery", qty=D(1), unit_price=D(0)))
    res = calculate(rev, Settings(), [])
    pl = purchase_list(rev, res, PRICES)
    by = {r.kind: r for r in pl.rows}
    assert by["sheet"].needed == D("1.5") and by["sheet"].buy == 2        # 0.5 + 2 x 0.5, bought once: 2 sheets
    assert by["sheet"].lines == ["31.01", "32.01"]
    lum = by["lumber"]                                                     # 4 x 2 x 2 x 25 / 144 x 1.5 = 4.17 BF a piece
    assert lum.name.startswith("Cherry 8/4") and lum.needed == D("4.17") * 3 and lum.buy == 13
    assert lum.est_cost == D("97.50") and lum.supplier == "Hearne"
    assert by["finish"].needed == 60 and by["finish"].containers == 1 and by["finish"].est_cost == D(60)
    assert pl.skipped == ["30.01"]
    assert pl.total() == D(180) + D("97.50") + D(60)


def test_old_prices_flag_old_and_undated_references_only():
    today = date(2026, 10, 26)
    assert not is_old(date(2026, 5, 1), 182, today) and is_old(date(2026, 4, 1), 182, today) and is_old(None, 182)
    b = sheet(BuildMaterial(kind="sheet", ref="bb", name="Baltic birch", qty=D(1), unit_cost=D(90)),
              BuildMaterial(kind="lumber", ref="Cherry", name="Cherry", qty=D(3), unit_cost=D("7.5"), priced_as="8/4"),
              BuildMaterial(kind="finish", ref="oil", name="Rubio", qty=D(10), unit_cost=D("0.6")),
              BuildMaterial(kind="hardware", name="Typed hinge", qty=D(2), unit_cost=D(5), typed_cost=True))
    assert old_prices(b, PRICES, 182, today) == ["Baltic birch (2025.01.01)", "Rubio (no date)"]
    assert old_prices(b, PRICES, 800, today) == ["Rubio (no date)"]
