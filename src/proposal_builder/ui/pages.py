"""Catalog manager pages (milestone 1)."""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

from nicegui import ui
from pydantic import ValidationError

from ..models import (
    AllowanceRange,
    BoilerplateBlock,
    CatalogItem,
    Performer,
    basis_label,
    PriceSource,
    Rate,
    Section,
    StockClass,
    Tier,
    Unit,
    Variable,
)
from .state import get_state, set_data_dir
from .widgets import keep_current, Col, EditableGrid, layout, to_decimal, warn


def md_breaks(text: str) -> str:
    """Single newlines are line breaks (as typed in Excel); blank lines are paragraphs."""
    return re.sub(r"(?<!\n)\n(?!\n)", "  \n", text or "")


def _fmt_money(v: Decimal | None) -> str:
    return "" if v is None else f"${v:,.2f}"


def _fmt_pct(v: Decimal | None) -> str:
    return "" if v is None else f"{(v * 100).normalize():f}%"


# ---------------------------------------------------------------- items


def _item_rows() -> list[dict]:
    st = get_state()
    cat = st.catalog
    sections = {s.number: s.name for s in cat.sections}
    rows = []
    for i in sorted(cat.items, key=lambda x: x.code):
        price = cat.unit_price(i)
        shown = _fmt_pct(price) if i.price_source is PriceSource.PERCENT else _fmt_money(price)
        if i.price_source is PriceSource.RATE:
            shown += f"  ({i.rate_key})"
        elif i.price_source is PriceSource.ALLOWANCE:
            shown += f"  ({i.default_tier.value})" if price is not None else "range"
        flags = " ".join(f for f, on in [("allow.", i.is_allowance), ("not incl.", i.not_included),
                                         ("owner", i.owner_furnished),
                                         ("credit", i.credit_if_unused), ("inactive", not i.active)] if on)
        rows.append({
            "code": i.code, "section": f"{i.section} {sections.get(i.section, '?')}",
            "group": i.group, "title": i.title, "unit": i.unit, "source": basis_label(i.price_source),
            "price": shown, "performer": i.performer, "flags": flags,
            "description": i.description,
        })
    return rows


def item_dialog(item: CatalogItem | None, on_saved) -> None:
    st = get_state()
    cat = st.catalog
    is_new = item is None
    src = item or CatalogItem(code=0, section=cat.sections[0].number if cat.sections else 100, title="")
    f = src.model_dump()

    with ui.dialog() as dlg, ui.card().classes("w-[860px] max-w-full"):
        ui.label("New catalog item" if is_new else f"Item {src.code}").classes("text-lg font-semibold")
        with ui.grid(columns=4).classes("w-full gap-x-4"):
            code = ui.number("Code", value=f["code"] or None, format="%d").props("dense")
            section = ui.select(keep_current({s.number: f"{s.number} {s.name}" for s in cat.sections}, f["section"]),
                                label="Section", value=f["section"]).props("dense").classes("col-span-2")
            group = ui.input("Group (MEP sub-heading)", value=f["group"]).props("dense")
            title = ui.input("Title", value=f["title"]).props("dense").classes("col-span-3")
            unit = ui.select(cat.unit_options(f["unit"]), label="Unit", value=f["unit"]).props("dense")
        desc = ui.textarea("General description (printed on every use)", value=f["description"]) \
            .props("dense autogrow").classes("w-full")
        with ui.row().classes("items-center gap-3 mt-1"):
            ui.label("Price").classes("font-semibold text-sm")
            source = ui.toggle({p.value: basis_label(p).capitalize() for p in PriceSource},
                               value=f["price_source"]).props("dense no-caps")
        with ui.grid(columns=4).classes("w-full gap-x-4"):
            price_val = f["price"]
            if price_val is not None and f["price_source"] == PriceSource.PERCENT.value:
                price_val = price_val * 100
            price = ui.number("Price ($)", value=float(price_val) if price_val is not None else None).props("dense")
            rate = ui.select(keep_current({"": "-", **{r.key: f"{r.key}: {r.name} (${r.rate}/{r.unit})"
                                                       for r in cat.rates}}, f["rate_key"]),
                             label="Rate", value=f["rate_key"] or "").props("dense").classes("col-span-2")
            tier = ui.select({t.value: t.value for t in Tier}, label="Default range tier",
                             value=f["default_tier"]).props("dense")
        allow = ui.select(keep_current({a.id: f"{a.category}: {a.description} ({a.unit} {a.low} to {a.high})"
                                        for a in cat.allowances}, f["allowance_ids"]),
                          label="Linked price ranges (the first is the default)", value=f["allowance_ids"],
                          multiple=True).props("dense use-chips").classes("w-full")

        def refresh_source(_=None) -> None:
            b = source.value
            price.set_visibility(b in ("fixed", "percent"))
            price.props(f'label="{"Percent of subtotal (%)" if b == "percent" else "Price ($)"}"')
            rate.set_visibility(b == "rate")
            tier.set_visibility(b == "allowance")
            allow.set_visibility(b == "allowance")
        source.on_value_change(refresh_source)
        refresh_source()
        with ui.grid(columns=4).classes("w-full gap-x-4"):
            performer = ui.select(keep_current({n: n or "-" for n in st.settings.performer_names()}, f["performer"]),
                                  label="Default performer", value=f["performer"]).props("dense")
            stock = ui.select(keep_current({"": "-", **{s.key: s.name for s in cat.stock_classes}}, f["stock_class"]),
                              label="Stock class", value=f["stock_class"] or "").props("dense")
            isa = ui.checkbox("Allowance (prints on proposal)", value=f["is_allowance"])
            ni = ui.checkbox("Not included ($0 line)", value=f["not_included"])
            of = ui.checkbox("Owner-furnished", value=f["owner_furnished"])
            cu = ui.checkbox("Credit if unused", value=f["credit_if_unused"])
            active = ui.checkbox("Active", value=f["active"])
        notes = ui.textarea("Internal notes (never printed)", value=f["internal_notes"]) \
            .props("dense autogrow").classes("w-full")

        def save() -> None:
            try:
                new_code = int(code.value or 0)
                if new_code <= 0:
                    raise ValueError("code is required")
                if any(i.code == new_code for i in cat.items if i is not item):
                    raise ValueError(f"code {new_code} already exists")
                ps = PriceSource(source.value)
                p = to_decimal(price.value)
                if p is not None and ps is PriceSource.PERCENT:
                    p = p / 100
                new = CatalogItem(
                    code=new_code, section=section.value, group=group.value or "",
                    title=(title.value or "").strip(), description=desc.value or "", unit=unit.value,
                    price_source=ps,
                    price=p if ps in (PriceSource.FIXED, PriceSource.PERCENT) else None,
                    rate_key=(rate.value or None) if ps is PriceSource.RATE else None,
                    # links stay stored when hidden, so switching back to Range finds them again
                    allowance_ids=list(allow.value or []), default_tier=Tier(tier.value),
                    performer=performer.value or "", stock_class=stock.value or None,
                    is_allowance=isa.value, not_included=ni.value, owner_furnished=of.value,
                    credit_if_unused=cu.value, internal_notes=notes.value or "", active=active.value,
                )
                if not new.title:
                    raise ValueError("title is required")
            except (ValidationError, ValueError, TypeError) as err:
                ui.notify(f"Not saved: {err}", type="negative", multi_line=True)
                return
            if is_new:
                cat.items.append(new)
            else:
                cat.items[cat.items.index(item)] = new
            cat.items.sort(key=lambda x: x.code)
            warn(st.save_catalog())
            dlg.close()
            on_saved()

        def delete() -> None:
            cat.items.remove(item)
            warn(st.save_catalog())
            dlg.close()
            on_saved()

        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            if not is_new:
                ui.button("Delete", icon="delete", on_click=delete).props("flat color=negative")
            ui.button("Cancel", on_click=dlg.close).props("flat")
            ui.button("Save", icon="save", on_click=save)
    dlg.open()


@ui.page("/items")
def items_page() -> None:
    layout("Catalog items")
    st = get_state()

    def refresh() -> None:
        grid.options["rowData"] = _item_rows()
        grid.update()

    def open_selected(e) -> None:
        code = e.args["data"]["code"]
        item_dialog(st.catalog.item(code), refresh)

    with ui.row().classes("gap-2 mb-2 items-center"):
        ui.button("New item", icon="add", on_click=lambda: item_dialog(None, refresh)).props("dense")
        flt = ui.input(placeholder="Search code, title, description").props("dense clearable").classes("w-80")
        ui.label("Double-click a row to edit.").classes("text-xs text-gray-500")
    grid = ui.aggrid({
        "columnDefs": [
            {"field": "code", "headerName": "Code", "width": 80, "sort": "asc"},
            {"field": "section", "headerName": "Section", "width": 200, "filter": True},
            {"field": "group", "headerName": "Group", "width": 100},
            {"field": "title", "headerName": "Title", "width": 230},
            {"field": "unit", "headerName": "Unit", "width": 70},
            {"field": "source", "headerName": "Source", "width": 95},
            {"field": "price", "headerName": "Default price", "width": 150},
            {"field": "performer", "headerName": "Performer", "width": 180},
            {"field": "flags", "headerName": "Flags", "width": 120},
            {"field": "description", "headerName": "Description", "flex": 1, "minWidth": 300,
             "tooltipField": "description"},
        ],
        "rowData": _item_rows(),
        "defaultColDef": {"sortable": True, "resizable": True},
        "rowHeight": 32, "headerHeight": 36,
    }, auto_size_columns=False).classes("w-full").style("height:78vh")
    grid.on("cellDoubleClicked", open_selected)
    flt.on_value_change(lambda e: grid.run_grid_method("setGridOption", "quickFilterText", e.value or ""))


# ---------------------------------------------------------------- simple tables


@ui.page("/sections")
def sections_page() -> None:
    layout("Sections")
    st = get_state()
    ui.label("Sections print in number order. Changing a number does not move its items.") \
        .classes("text-xs text-gray-500")

    def new() -> Section:
        n = max((s.number for s in st.catalog.sections), default=0) + 100
        return Section(number=n, name="New section", key=f"Section{n}")

    def save():
        st.catalog.sections.sort(key=lambda s: s.number)
        return st.save_catalog()

    EditableGrid(lambda: st.catalog.sections,
                 [Col("number", "Number", "number", width=110), Col("name", "Name", flex=2),
                  Col("key", "Key", flex=1)], save, new)


@ui.page("/rates")
def rates_page() -> None:
    layout("Rates")
    st = get_state()
    ui.label("Items priced by rate pick up rate changes. Saved proposals keep their snapshot.") \
        .classes("text-xs text-gray-500")
    EditableGrid(lambda: st.catalog.rates,
                 [Col("key", "Key", width=140), Col("name", "Name", flex=2),
                  Col("unit", "Unit", "select", [u.code for u in st.catalog.units], width=90),
                  Col("rate", "Rate ($)", "number", width=120)],
                 st.save_catalog,
                 lambda: Rate(key=f"rate{len(st.catalog.rates) + 1}", name="New rate", rate=Decimal(0)))


@ui.page("/allowances")
def allowances_page() -> None:
    layout("Price ranges")
    st = get_state()
    ui.label("Mid is computed as (low + high) / 2. Link ranges to items on the item form.") \
        .classes("text-xs text-gray-500")
    EditableGrid(lambda: st.catalog.allowances,
                 [Col("category", "Category", width=150), Col("description", "Description", flex=2),
                  Col("unit", "Unit", "select", [u.code for u in st.catalog.units], width=80),
                  Col("low", "Low ($)", "number", width=100), Col("high", "High ($)", "number", width=100),
                  Col("mid", "Mid ($)", "number", width=100, editable=False),
                  Col("basis", "Basis", flex=1), Col("id", "ID", width=200, editable=False)],
                 st.save_catalog,
                 lambda: AllowanceRange(id=f"new-{len(st.catalog.allowances) + 1}", category="New",
                                        description="New range", unit="EA", low=Decimal(0), high=Decimal(0)))


@ui.page("/units")
def units_page() -> None:
    layout("Units")
    st = get_state()

    ui.label("Renaming a unit updates catalog items, rates and price ranges that use it. Saved proposals keep "
             "the unit they were written with; change it on the line if needed.").classes("text-xs text-gray-500")
    st.catalog.units.sort(key=lambda u: u.code)   # sorted on open only: grid rows map to list positions
    prev = [u.code for u in st.catalog.units]

    def save():
        now = [u.code for u in st.catalog.units]
        msgs = []
        if len(now) == len(prev):
            for old, new in zip(prev, now):
                if old != new and old not in now:
                    n = st.catalog.rename_unit(old, new)
                    msgs.append(f"Renamed {old} to {new}" + (f"; updated {n} catalog entries" if n else ""))
        elif len(now) < len(prev):
            for gone in set(prev) - set(now):
                users = st.catalog.unit_users(gone)
                if users:
                    msgs.append(f"Deleted {gone}, still used by {len(users)}: {', '.join(users[:6])}"
                                + ("..." if len(users) > 6 else "") + ". Pick a new unit on those.")
        prev[:] = [u.code for u in st.catalog.units]
        for msg in msgs:
            ui.notify(msg, type="info", multi_line=True, timeout=8000)
        return st.save_catalog()

    EditableGrid(lambda: st.catalog.units,
                 [Col("code", "Unit", width=120), Col("description", "Description", flex=1)],
                 save, lambda: Unit(code="NEW", description="New unit"), height="60vh")


@ui.page("/stock")
def stock_page() -> None:
    layout("Stock lengths")
    st = get_state()
    ui.label("Lengths in feet, comma separated. Waste % is under Settings.").classes("text-xs text-gray-500")
    EditableGrid(lambda: st.catalog.stock_classes,
                 [Col("key", "Key", width=140), Col("name", "Name", flex=1),
                  Col("lengths_ft", "Lengths (ft)", "list", flex=1)],
                 st.save_catalog,
                 lambda: StockClass(key=f"class{len(st.catalog.stock_classes) + 1}", name="New class",
                                    lengths_ft=[Decimal(8)]), height="40vh")


# ---------------------------------------------------------------- boilerplate


def block_dialog(block: BoilerplateBlock | None, heading: str, on_saved) -> None:
    st = get_state()
    bp = st.boilerplate
    is_new = block is None
    with ui.dialog() as dlg, ui.card().classes("w-[900px] max-w-full"):
        ui.label(f"{heading}: {'new block' if is_new else block.title or block.id}").classes("text-lg font-semibold")
        with ui.row().classes("w-full gap-4"):
            title = ui.input("Sub-heading", value="" if is_new else block.title).props("dense").classes("flex-1")
            on = ui.switch("On by default", value=True if is_new else block.default_on)
        ui.label("Markdown. Use {variable} placeholders; they resolve per proposal.").classes("text-xs text-gray-500")
        with ui.row().classes("w-full no-wrap gap-4"):
            body = ui.textarea(value="" if is_new else block.body).props("outlined autogrow") \
                .classes("w-1/2 font-mono text-sm")
            preview = ui.markdown(md_breaks(body.value)).classes("w-1/2 border rounded p-2 text-sm")
        body.on_value_change(lambda e: preview.set_content(md_breaks(e.value or "")))

        def save() -> None:
            if is_new:
                order = max((b.order for b in bp.by_heading(heading)), default=0) + 10
                base = (title.value or "block").lower().replace(" ", "-")
                bid, n = base, 2
                while any(b.id == bid for b in bp.blocks):
                    bid, n = f"{base}-{n}", n + 1
                bp.blocks.append(BoilerplateBlock(id=bid, heading=heading, title=title.value or "",
                                                  body=body.value or "", default_on=on.value, order=order))
            else:
                block.title, block.body, block.default_on = title.value or "", body.value or "", on.value
            st.save_boilerplate()
            dlg.close()
            on_saved()

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dlg.close).props("flat")
            ui.button("Save", icon="save", on_click=save)
    dlg.open()


@ui.page("/boilerplate")
def boilerplate_page() -> None:
    layout("Boilerplate")
    st = get_state()
    ui.label("Library text. Each proposal starts with the blocks that are on by default and can "
             "toggle or edit them without changing this library.").classes("text-xs text-gray-500 mb-2")

    @ui.refreshable
    def body() -> None:
        bp = st.boilerplate
        for heading in bp.headings:
            blocks = bp.by_heading(heading)
            with ui.expansion(f"{heading} ({len(blocks)})", value=False).classes("w-full border rounded mb-2"):
                for b in blocks:
                    with ui.row().classes("w-full items-start no-wrap gap-3 py-1 border-b"):
                        ui.switch(value=b.default_on,
                                  on_change=lambda e, b=b: (setattr(b, "default_on", e.value), st.save_boilerplate()))
                        with ui.column().classes("flex-1 gap-0"):
                            ui.label(b.title or f"[{b.id}]").classes("font-semibold")
                            ui.label(b.body[:220] + ("..." if len(b.body) > 220 else "")) \
                                .classes("text-xs text-gray-600 whitespace-pre-line")
                        ui.button(icon="arrow_upward", on_click=lambda b=b: move(b, -1)).props("flat dense round")
                        ui.button(icon="arrow_downward", on_click=lambda b=b: move(b, 1)).props("flat dense round")
                        ui.button(icon="edit", on_click=lambda b=b, h=heading: block_dialog(b, h, body.refresh)) \
                            .props("flat dense round")
                        ui.button(icon="delete", on_click=lambda b=b: remove(b)).props("flat dense round color=negative")
                ui.button("Add block", icon="add",
                          on_click=lambda h=heading: block_dialog(None, h, body.refresh)).props("flat dense")

    def move(b: BoilerplateBlock, d: int) -> None:
        sib = st.boilerplate.by_heading(b.heading)
        i = sib.index(b)
        j = i + d
        if 0 <= j < len(sib):
            sib[i].order, sib[j].order = sib[j].order, sib[i].order
            st.save_boilerplate()
            body.refresh()

    async def remove(b: BoilerplateBlock) -> None:
        with ui.dialog() as dlg, ui.card():
            ui.label(f"Delete block '{b.title or b.id}'?")
            with ui.row():
                ui.button("Cancel", on_click=lambda: dlg.submit(False)).props("flat")
                ui.button("Delete", on_click=lambda: dlg.submit(True)).props("color=negative")
        if await dlg:
            st.boilerplate.blocks.remove(b)
            st.save_boilerplate()
            body.refresh()

    body()


# ---------------------------------------------------------------- settings


@ui.page("/settings")
def settings_page() -> None:
    layout("Settings")
    st = get_state()
    s = st.settings
    c = s.company

    def bind(obj, attr, conv=lambda v: v):
        def handler(e):
            try:
                setattr(obj, attr, conv(e.value))
            except (ValidationError, ValueError, TypeError) as err:
                ui.notify(f"Not saved: {err}", type="negative")
                return
            st.save_settings()
        return handler

    pct = lambda v: (to_decimal(v) or Decimal(0)) / 100  # noqa: E731

    with ui.row().classes("w-full gap-8 items-start"):
        with ui.card().classes("w-[440px]"):
            ui.label("Company").classes("font-semibold")
            for label, attr in [("Legal name", "legal_name"), ("DBA", "dba"), ("Address", "address"),
                                ("Phone", "phone"), ("Email", "email"), ("Logo file (in data folder)", "logo_path")]:
                ui.input(label, value=getattr(c, attr)).props("dense").classes("w-full") \
                    .on_value_change(bind(c, attr))
        with ui.card().classes("w-[360px]"):
            ui.label("Defaults").classes("font-semibold")
            ui.number("Proposal year (YY)", value=s.proposal_year, format="%d").props("dense") \
                .on_value_change(bind(s, "proposal_year", int))
            ui.number("Next proposal sequence", value=s.next_proposal_seq, format="%d").props("dense") \
                .on_value_change(bind(s, "next_proposal_seq", int))
            ui.label().bind_text_from(s, "next_proposal_seq", lambda _: f"Next number: {s.next_proposal_number()}") \
                .classes("text-xs text-gray-500")
            ui.number("Stick goods waste %", value=float(s.default_waste_pct * 100)).props("dense") \
                .on_value_change(bind(s, "default_waste_pct", pct))
            ui.number("Deposit %", value=float(s.deposit_pct * 100)).props("dense") \
                .on_value_change(bind(s, "deposit_pct", pct))
            ui.number("Retainage %", value=float(s.retainage_pct * 100)).props("dense") \
                .on_value_change(bind(s, "retainage_pct", pct))
            ui.number("Proposal validity (days)", value=s.validity_days, format="%d").props("dense") \
                .on_value_change(bind(s, "validity_days", int))
            def set_dark(e) -> None:
                s.dark_mode = bool(e.value)
                st.save_settings()
                ui.navigate.reload()
            ui.switch("Dark mode", value=s.dark_mode, on_change=set_dark).props("dense")
            ui.number("License threshold warning ($, 0 = off)", value=float(s.license_threshold), format="%.0f") \
                .props("dense").on_value_change(bind(s, "license_threshold", lambda x: Decimal(str(x or 0))))
            ui.textarea("Request for quote: text above the scope ({company_email} and proposal variables work)",
                        value=s.rfq_note).props("dense autogrow").classes("w-full") \
                .on_value_change(bind(s, "rfq_note"))
            ui.textarea("Quote comparison: note under the table", value=s.comparison_note) \
                .props("dense autogrow").classes("w-full").on_value_change(bind(s, "comparison_note"))
        with ui.card().classes("w-[420px]"):
            ui.label("Data folder").classes("font-semibold")
            ui.label(str(st.store.root)).classes("text-xs break-all")
            folder = ui.input("Change to (point at your Proton Drive folder)").props("dense").classes("w-full")

            def change() -> None:
                from ..store import save_data_dir
                p = Path(folder.value or "").expanduser()
                if not str(folder.value or "").strip():
                    ui.notify("Enter a folder path.")
                    return
                save_data_dir(p)
                set_data_dir(p)
                ui.notify(f"Data folder set to {p}. Seed files copied if it was empty.")
                ui.navigate.reload()

            ui.button("Use this folder", on_click=change).props("dense outline")
            ui.separator().classes("my-2")

            def backup() -> None:
                try:
                    path = st.store.backup_zip()
                except OSError as e:
                    ui.notify(f"Backup failed: {e}", type="negative")
                    return
                ui.notify(f"Backup saved: {path}", type="positive", multi_line=True)

            ui.label("Every save keeps the previous version in backups/. A full backup zips the whole "
                     "data folder (catalog, settings, every project and PDF).").classes("text-xs text-gray-500")
            ui.button("Create full backup (.zip)", icon="archive", on_click=backup).props("dense outline")
            ui.separator().classes("my-2")
            from .. import __version__
            from .update_ui import check_now
            ui.label(f"Program version v{__version__}. The app checks for a newer version when it starts and "
                     "shows an Update button in the top bar.").classes("text-xs text-gray-500")
            ui.button("Check for updates", icon="system_update", on_click=check_now).props("dense outline")

    ui.label("Lists").classes("font-semibold mt-6")
    ui.label("Dropdown choices used across the app. Type and press Enter to add; click the x to remove. "
             "Removing a choice does not change records that already use it.").classes("text-xs text-gray-500")
    with ui.card().classes("w-full max-w-[1100px]"):
        ui.label("Performers").classes("font-semibold text-sm")
        ui.label("Printed note goes at the start of a line's description. Income puts the line in the Kept Spec (KS) "
                 "or Convenient Woodworking (CW) column of the Income tab; blank means pass-through. Renaming a "
                 "performer updates catalog items; saved proposals keep the name they were written with.") \
            .classes("text-xs text-gray-500")
        prev = [x.name for x in s.performers]

        def save_performers():
            now = [x.name for x in s.performers]
            if len(now) == len(prev):
                for old, new in zip(prev, now):
                    if old != new and old not in now:
                        n = 0
                        for it in st.catalog.items:
                            if it.performer == old:
                                it.performer, n = new, n + 1
                        if n:
                            st.save_catalog()
                            ui.notify(f"Renamed {old} to {new}; updated {n} catalog items", type="info")
            elif len(now) < len(prev):
                for gone in set(prev) - set(now):
                    used = [str(it.code) for it in st.catalog.items if it.performer == gone]
                    if used:
                        ui.notify(f"{gone} is still the default performer on items {', '.join(used[:8])}"
                                  + ("..." if len(used) > 8 else ""), type="warning", multi_line=True)
            prev[:] = now
            st.save_settings()

        from ..models import PerformerDef
        EditableGrid(lambda: s.performers,
                     [Col("name", "Performer", width=230), Col("note", "Printed note", flex=1),
                      Col("income", "Income", "select", ["", "KS", "CW"], width=100)],
                     save_performers, lambda: PerformerDef(name="New performer"), height="26vh")

        lists = s.lists
        with ui.grid(columns=2).classes("w-full gap-x-6 gap-y-2 mt-2"):
            for attr, label in (("co_actions", "Change order actions"), ("contact_roles", "Contact roles"),
                                ("lead_sources", "How they found you"), ("trades", "Contractor trades"),
                                ("quote_scopes", "Quote scopes"), ("address_labels", "Address labels")):
                ui.input_chips(label, value=list(getattr(lists, attr)),
                               on_change=lambda e, a=attr: (setattr(lists, a, [x.strip() for x in (e.value or [])
                                                                                if str(x).strip()]),
                                                            st.save_settings())) \
                    .props("dense").classes("w-full")

    ui.label("Global variables").classes("font-semibold mt-6")
    ui.label("Referenced in boilerplate and line notes as {name}. Proposal variables override these.") \
        .classes("text-xs text-gray-500")
    EditableGrid(lambda: s.global_variables,
                 [Col("name", "Name", width=200), Col("value", "Value", flex=1), Col("unit", "Unit", width=100),
                  Col("description", "Description", flex=2)],
                 lambda: st.save_settings(),
                 lambda: Variable(name=f"var{len(s.global_variables) + 1}", value=""), height="30vh")


@ui.page("/")
def index() -> None:
    ui.navigate.to("/projects")
