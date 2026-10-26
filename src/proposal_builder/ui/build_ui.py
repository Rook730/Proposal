"""Build sheet dialog (Convenient Woodworking): the internal cost build-up behind a Built line. Never printed."""

from __future__ import annotations

from decimal import Decimal
from typing import Callable

from nicegui import ui
from pydantic import ValidationError

from ..buildsheet import MATERIAL_KINDS, YIELD_TIERS, BuildLabor, BuildMaterial, BuildSheet, PricingPolicy, rough_for
from ..models import Catalog, PriceReferences
from .widgets import Col, EditableGrid, to_decimal

ZERO = Decimal(0)


def money(v: Decimal | None) -> str:
    if v is None:
        return ""
    return f"-${-v:,.2f}" if v < 0 else f"${v:,.2f}"


def _n(v) -> float | None:
    return float(v) if v is not None else None


def price_material(m: BuildMaterial, prices: PriceReferences, sheet: BuildSheet) -> bool:
    """Set the unit cost from the price references. Lumber is priced for the nominal its parts need.
    Returns False when no price was found."""
    if m.kind == "lumber":
        if m.thickness is not None:
            m.nominal, _ = rough_for(m.thickness, sheet.rough_map)
        species = m.ref or m.name
        lp = prices.lumber_price(species, m.nominal) if m.nominal else None
        if lp is None:
            return False
        m.unit_cost, m.priced_as, m.ref = lp.price, lp.thickness, lp.species
        return True
    ref = prices.find(m.kind, m.ref) if m.ref else None
    if ref is None:
        return False
    if m.kind == "finish":
        m.unit_cost = ref.per_sf_coat
    else:
        m.unit_cost = ref.price
    return True


def _ref_options(kind: str, prices: PriceReferences) -> dict[str, str]:
    if kind == "lumber":
        species = sorted({x.species for x in prices.lumber})
        return {sp: f"{sp} ({', '.join(f'{x.thickness} ${x.price}' for x in prices.lumber if x.species == sp)})"
                for sp in species}
    if kind == "sheet":
        return {x.id: f"{x.product} {x.thickness} ({x.width_in.normalize():f}x{x.length_in.normalize():f}) "
                      f"${x.price}/sheet" for x in prices.sheets}
    if kind == "dimensional":
        return {x.id: f"{x.material} {x.size} x {x.length_ft.normalize():f}' ${x.price}" for x in prices.dimensional}
    if kind == "hardware":
        return {x.id: f"{x.name} {x.part_number} ({x.supplier}) ${x.price}/{x.unit}" for x in prices.hardware}
    if kind == "finish":
        return {x.id: f"{x.product} ${x.per_sf_coat:.4f}/SF per coat" for x in prices.finishes}
    if kind == "veneer":
        return {x.id: f"{x.species} {x.thickness} ${x.price}/SF".replace("  ", " ") for x in prices.veneer}
    if kind == "outsourced":
        return {x.id: f"{x.service} ({x.supplier}) ${x.price}/{x.basis}" for x in prices.outsourced}
    return {}


def add_material_dialog(sheet: BuildSheet, catalog: Catalog, on_added: Callable[[], None]) -> None:
    prices = catalog.prices
    with ui.dialog() as dlg, ui.card().classes("w-[640px] max-w-full"):
        ui.label("Add material").classes("text-lg font-semibold")
        kind = ui.toggle({k: v for k, v in MATERIAL_KINDS.items()}, value="lumber").props("dense no-caps")
        ref = ui.select({}, label="From price references", with_input=True).props("dense").classes("w-full")
        name = ui.input("Name (for a typed row)").props("dense").classes("w-full")
        with ui.grid(columns=4).classes("w-full gap-x-3"):
            pieces = ui.number("Pieces per unit", value=1).props("dense")
            thick = ui.number('Finished T (in)', value=0.75).props("dense")
            width = ui.number("W (in)").props("dense")
            length = ui.number("L (in)").props("dense")
            ytier = ui.select({t: t for t in YIELD_TIERS}, value="medium", label="Yield").props("dense")
            qty = ui.number("Qty per unit", value=1).props("dense")
            unit = ui.input("Unit", value="EA").props("dense")
            coats = ui.number("Coats").props("dense")
            cost = ui.number("Unit cost ($) (blank = from references)").props("dense").classes("col-span-2")
        setup = ui.checkbox("Setup (once per line, not per piece)")
        hint = ui.label().classes("text-xs text-gray-500")

        def kind_changed(_=None) -> None:
            k = kind.value
            ref.set_options(_ref_options(k, prices), value=None)
            lumber, veneer = k == "lumber", k == "veneer"
            for el in (pieces, width, length, ytier):
                el.set_visibility(lumber or veneer)
            thick.set_visibility(lumber)
            qty.set_visibility(not (lumber or veneer))
            unit.set_visibility(not (lumber or veneer))
            coats.set_visibility(k == "finish")
            unit.set_value({"sheet": "SHT", "dimensional": "PC", "finish": "SF"}.get(k, "EA"))
            qty.props(f'label="{"Surface SF per unit" if k == "finish" else "Qty per unit"}"')
            hint.set_text({"lumber": "Board feet = pieces x nominal thickness x W x L / 144 x yield. The nominal "
                                     "comes from the finished thickness (3/4 from 4/4, 1-3/4 from 8/4).",
                           "sheet": "Sheets per unit; use a fraction when one sheet makes several pieces.",
                           "veneer": "Square feet = pieces x W x L / 144 x yield. Add the substrate as its own "
                                     "lumber or sheet goods row.",
                           "finish": "Cost = SF x coats x the product's price per SF per coat."}.get(k, ""))
        kind.on_value_change(kind_changed)
        kind_changed()

        def add() -> None:
            k = kind.value
            try:
                m = BuildMaterial(kind=k, setup=setup.value, ref=ref.value or "",
                                  name=(name.value or "").strip() or (ref.options.get(ref.value, "") if ref.value
                                                                      else "").split(" $")[0].split(" (")[0])
                if k == "lumber":
                    m.pieces, m.thickness = to_decimal(pieces.value), to_decimal(thick.value)
                    m.width, m.length, m.yield_tier = to_decimal(width.value), to_decimal(length.value), ytier.value
                    if None in (m.pieces, m.thickness, m.width, m.length):
                        raise ValueError("enter pieces, T, W and L")
                    m.name = m.name or "Lumber"
                elif k == "veneer":
                    m.pieces, m.width, m.length = to_decimal(pieces.value), to_decimal(width.value), to_decimal(length.value)
                    m.yield_tier = ytier.value
                    if None in (m.pieces, m.width, m.length):
                        raise ValueError("enter pieces, W and L")
                    m.name = m.name or "Veneer"
                else:
                    m.qty = to_decimal(qty.value) or Decimal(1)
                    m.unit = unit.value or "EA"
                    m.coats = to_decimal(coats.value) if k == "finish" else None
                if not m.name:
                    raise ValueError("pick an item or type a name")
            except (ValidationError, ValueError) as err:
                ui.notify(f"Not added: {err}", type="warning")
                return
            sheet.materials.append(m)
            sheet.recalc()
            typed = to_decimal(cost.value)
            if typed is not None:
                m.unit_cost = typed
                m.priced_as = m.nominal
            elif not price_material(m, prices, sheet):
                ui.notify(f"No price found for {m.name}{' ' + m.nominal if m.nominal else ''}; enter the unit cost "
                          "in the grid.", type="warning")
            dlg.close()
            on_added()

        with ui.row().classes("w-full justify-end"):
            ui.button("Cancel", on_click=dlg.close).props("flat")
            ui.button("Add", icon="add", on_click=add)
    dlg.open()


def build_dialog(build: BuildSheet | None, qty: Decimal, catalog: Catalog, policy: PricingPolicy | None,
                 on_save: Callable[[BuildSheet], None], readonly: bool = False, title: str = "") -> None:
    """Edit a copy of the build sheet; on_save gets the edited sheet."""
    work = build.model_copy(deep=True) if build is not None else BuildSheet.from_policy(policy or PricingPolicy())
    phases = list(policy.phases) if policy else []
    phases += sorted({x.phase for x in work.labor if x.phase and x.phase not in phases})
    q = qty if qty and qty > 0 else Decimal(1)

    with ui.dialog().props("maximized") as dlg, ui.card().classes("w-full h-full p-0 gap-0") \
            .style("display:flex; flex-direction:column"):
        with ui.row().classes("w-full items-center px-4 pt-3 pb-1"):
            ui.label(f"Build sheet{': ' + title if title else ''}").classes("text-lg font-semibold")
            ui.label("Internal only, never printed. Prices here are this line's copy; Pull prices refreshes them "
                     "from Catalog > Price references.").classes("text-xs text-gray-500")
        body = ui.column().classes("w-full gap-2 px-4 overflow-y-auto").style("flex:1 1 auto")
        with body:
            @ui.refreshable
            def summary() -> None:
                t = work.totals(q)
                one = work.totals(Decimal(1))
                with ui.row().classes("w-full gap-0 border border-gray-300 rounded items-stretch"):
                    def fig(label, value, sub=""):
                        with ui.column().classes("px-3 py-1 gap-0 border-r border-gray-200"):
                            ui.label(label).classes("text-[11px] uppercase text-gray-500 whitespace-nowrap")
                            ui.label(value).classes("text-base font-semibold pb-brand whitespace-nowrap")
                            if sub:
                                ui.label(sub).classes("text-[11px] text-gray-500 whitespace-nowrap")
                    fig("Qty", f"{q.normalize():f}")
                    fig("Materials", money(t.materials), f"{money(t.setup_materials)} setup" if t.setup_materials else "")
                    if t.outsourced:
                        fig("Outsourced", money(t.outsourced))
                    fig("Hours", f"{t.hours.normalize():f}",
                        f"{t.setup_hours.normalize():f} setup + {t.unit_hours.normalize():f} each")
                    fig("Labor", money(t.labor), f"at {money(t.shop_rate)}/hr")
                    fig("Cost", money(t.cost))
                    fig("Overhead", money(t.overhead), f"{work.overhead_pct * 100:.1f}%")
                    fig("Profit", money(t.profit), f"{work.profit_pct * 100:.1f}%")
                    fig("Unit price", money(t.unit_price), f"rounded up from {money(t.line_price / q)}")
                    fig("Line total", money(t.line_total))
                    fig("Per shop hour", money(t.effective_rate), "after materials")
                    if q != 1:
                        fig("Price for 1", money(one.unit_price))
                stale = [m.name for m in work.materials if m.stale]
                unpriced = [m.name for m in work.materials if not m.unit_cost]
                if stale:
                    ui.label(f"Priced for a different thickness: {', '.join(stale)}. Use Pull prices.") \
                        .classes("text-xs text-orange-700")
                if unpriced:
                    ui.label(f"No unit cost: {', '.join(unpriced)}.").classes("text-xs text-orange-700")
            summary()

            def changed() -> None:
                work.recalc()
                summary.refresh()
                if holder.get("mats"):
                    holder["mats"].refresh()

            holder: dict = {}
            with ui.row().classes("items-end gap-3"):
                for label, attr, pct in (("Shop rate ($/hr)", "shop_rate", False), ("Overhead %", "overhead_pct", True),
                                         ("Profit %", "profit_pct", True), ("Round up to ($)", "rounding", False)):
                    val = getattr(work, attr)
                    inp = ui.number(label, value=float(val * 100 if pct else val)).props("dense").classes("w-36")

                    def set_val(e, attr=attr, pct=pct) -> None:
                        try:
                            v = to_decimal(e.value) or ZERO
                            setattr(work, attr, v / 100 if pct else v)
                        except (ValidationError, ValueError) as err:
                            ui.notify(str(err), type="warning")
                            return
                        summary.refresh()
                    inp.on_value_change(set_val)
                    if readonly:
                        inp.disable()
                ui.label(f"Yield: low {work.yield_low}, medium {work.yield_medium}, high {work.yield_high}") \
                    .classes("text-xs text-gray-500")

            with ui.row().classes("items-center gap-2 mt-2"):
                ui.label("Materials").classes("font-semibold")
                if not readonly:
                    ui.button("Add material", icon="add", on_click=lambda: add_material_dialog(work, catalog, changed)) \
                        .props("dense outline no-caps")

                    def pull() -> None:
                        work.recalc()
                        missing = [m.name for m in work.materials if (m.ref or m.kind == "lumber")
                                   and not price_material(m, catalog.prices, work)]
                        changed()
                        ui.notify("Prices pulled from the price references."
                                  + (f" Not found: {', '.join(missing)}" if missing else ""),
                                  type="warning" if missing else "positive", multi_line=True)
                    ui.button("Pull prices", icon="sync", on_click=pull).props("dense flat no-caps")
            holder["mats"] = EditableGrid(
                lambda: work.materials,
                [Col("setup", "Setup", "bool", width=95), Col("kind", "Kind", "lookup", width=125, lookup=MATERIAL_KINDS),
                 Col("name", "Item", width=260), Col("pieces", "Pcs", "number", width=80),
                 Col("thickness", "T", "number", width=75), Col("width", "W", "number", width=75),
                 Col("length", "L", "number", width=75), Col("yield_tier", "Yield", "select", list(YIELD_TIERS), width=105),
                 Col("nominal", "Nominal", width=105, editable=False), Col("qty", "Qty", "number", width=85),
                 Col("unit", "Unit", width=85), Col("coats", "Coats", "number", width=90),
                 Col("unit_cost", "Unit cost", "money", width=120), Col("cost", "Cost", "money", width=110, editable=False),
                 Col("notes", "Notes", flex=1)],
                lambda: changed(), lambda: BuildMaterial(kind="other", name=""), height="34vh", readonly=readonly,
                empty="No materials yet. Use Add material (from the price references) or Add row (typed).")
            ui.label("Lumber parts: Pcs, T, W, L are finished inches per unit; Qty becomes board feet at the nominal "
                     "thickness times the yield. Setup rows count once per line.").classes("text-xs text-gray-500")

            ui.label("Labor").classes("font-semibold mt-2")

            def labor_saved() -> None:
                summary.refresh()
            EditableGrid(lambda: work.labor,
                         [Col("setup", "Setup", "bool", width=95),
                          Col("phase", "Phase", "select", phases or [""], width=220),
                          Col("hours", "Hours", "number", width=100), Col("notes", "Notes", flex=1)],
                         labor_saved, lambda: BuildLabor(phase=phases[0] if phases else ""),
                         height="26vh", readonly=readonly,
                         empty="No labor yet. Use Add row. Setup hours (design, jigs, programming) count once.")
            notes = ui.textarea("Notes (internal)", value=work.notes).props("dense autogrow").classes("w-full")
            if readonly:
                notes.disable()

        def save() -> None:
            work.notes = notes.value or ""
            work.recalc()
            dlg.close()
            on_save(work)

        with ui.row().classes("w-full items-center justify-end gap-2 px-4 py-2 border-t"):
            ui.button("Close" if readonly else "Cancel", on_click=dlg.close).props("flat")
            if not readonly:
                ui.button("Use this build sheet", icon="done", on_click=save)
    dlg.open()
