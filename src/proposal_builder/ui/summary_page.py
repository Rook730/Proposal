"""Income summary across projects for a timeframe."""

from __future__ import annotations

from datetime import date, timedelta

from nicegui import run, ui

from ..income import CW, KS
from ..proposal import WON_STATUSES, ProjectStatus
from ..summary import all_project_income, in_window, pipeline, to_csv
from .state import get_state
from .widgets import BRAND, layout


def _m(v) -> str:
    return "" if v is None else (f"-${-v:,.2f}" if v < 0 else f"${v:,.2f}")


def _p(v) -> str:
    return "" if v is None else f"{v * 100:.1f}%"


PRESETS = {
    "This year": lambda t: (date(t.year, 1, 1), date(t.year, 12, 31)),
    "Last year": lambda t: (date(t.year - 1, 1, 1), date(t.year - 1, 12, 31)),
    "Last 12 months": lambda t: (t - timedelta(days=365), t),
    "This quarter": lambda t: (date(t.year, 3 * ((t.month - 1) // 3) + 1, 1), t),
    "All time": lambda t: (None, None),
}


@ui.page("/summary")
async def summary_page() -> None:
    layout("Income summary")
    st = get_state()
    ui.label("Income summary").classes("text-xl font-semibold")
    ui.label("Projects are placed by acceptance date (proposals never accepted use the date they were issued). "
             "Income counts the same items as each project's Income tab; Kept Spec includes overhead, profit and "
             "change order items. Share is of the Total Price for estimates and of the final cost for actuals. "
             "Internal only.").classes("text-xs text-gray-500 mb-2")

    rows_all = await run.io_bound(all_project_income, st.projects, st.settings, st.catalog)
    state = {"start": date(date.today().year, 1, 1), "end": date(date.today().year, 12, 31),
             "statuses": [s.value for s in WON_STATUSES], "kind": "actual"}

    with ui.row().classes("items-end gap-3 flex-wrap"):
        preset = ui.select(list(PRESETS), value="This year", label="Timeframe").props("dense").classes("w-40")
        d_from = ui.input("From", value=state["start"].isoformat()).props("dense type=date").classes("w-40")
        d_to = ui.input("To", value=state["end"].isoformat()).props("dense type=date").classes("w-40")
        stat = ui.select([s.value for s in ProjectStatus], value=state["statuses"], label="Status",
                         multiple=True).props("dense use-chips").classes("min-w-[320px]")
        kind = ui.toggle({"estimate": "Estimate", "actual": "Actual"}, value="actual").props("dense no-caps")
        ui.button("Export CSV", icon="download", on_click=lambda: export()).props("dense outline")

    @ui.refreshable
    def body() -> None:
        window = in_window(rows_all, state["start"], state["end"])
        shown = [r for r in window if r.project.status.value in state["statuses"]]
        k = state["kind"]

        def amt(r, entity=None):
            kk = k if (k == "estimate" or r.report.actual_total is not None) else "estimate"
            return r.amount(kk, entity), kk

        data, tot = [], {"price": 0, "base": 0, KS: 0, CW: 0, "all": 0}
        for r in sorted(shown, key=lambda r: (r.when, r.project.number)):
            ks, kk = amt(r, KS)
            cw, _ = amt(r, CW)
            al, _ = amt(r)
            share = r.share(kk)
            data.append({"number": r.project.number, "client": r.project.client_name,
                         "name": r.project.project_name, "status": r.project.status.value,
                         "date": r.when.isoformat() + ("" if r.basis == "accepted" else f" ({r.basis})"),
                         "price": _m(r.total_price), "ks": _m(ks), "cw": _m(cw), "all": _m(al),
                         "share": _p(share), "basis": "" if kk == k else "estimate"})
            tot["price"] += r.total_price
            tot["base"] += (r.report.final_price if kk == "actual" else r.report.contract_price) or 0
            tot[KS] += ks
            tot[CW] += cw
            tot["all"] += al
        base = tot["base"]   # Total Price for estimates, final cost for actuals (matches each row's share)
        pinned = [{"number": "Total", "client": f"{len(data)} project" + ("" if len(data) == 1 else "s"),
                   "price": _m(tot["price"]), "ks": _m(tot[KS]), "cw": _m(tot[CW]), "all": _m(tot["all"]),
                   "share": _p(tot["all"] / base if base else None)}] if data else []

        with ui.row().classes("gap-3 my-3"):
            for label, value, sub in (
                    ("Kept Spec", _m(tot[KS]), _p(tot[KS] / base if base else None) + " of price"),
                    ("Convenient Woodworking", _m(tot[CW]), _p(tot[CW] / base if base else None) + " of price"),
                    ("Combined", _m(tot["all"]), _p(tot["all"] / base if base else None) + f" of {_m(base)}")):
                with ui.card().classes("px-4 py-2 gap-0"):
                    ui.label(label).classes("text-xs uppercase text-gray-500")
                    ui.label(value).classes("text-lg font-semibold").style(f"color:{BRAND}")
                    ui.label(sub).classes("text-xs text-gray-500")
            pl = pipeline(window)
            with ui.card().classes("px-4 py-2 gap-0"):
                ui.label("Proposals in this timeframe").classes("text-xs uppercase text-gray-500")
                ui.label(f"{pl.won} won, {pl.lost} lost, {pl.open} open").classes("text-lg font-semibold") \
                    .style(f"color:{BRAND}")
                ui.label(f"Win rate {_p(pl.win_rate)} by count, {_p(pl.win_rate_value)} by value; "
                         f"{_m(pl.won_value)} won of {_m(pl.proposed_value)} proposed").classes("text-xs text-gray-500")

        g = ui.aggrid({
            "columnDefs": [
                {"field": "number", "headerName": "Project", "width": 95},
                {"field": "client", "headerName": "Client", "width": 170},
                {"field": "name", "headerName": "Name", "flex": 1, "minWidth": 150},
                {"field": "status", "headerName": "Status", "width": 105},
                {"field": "date", "headerName": "Date", "width": 150},
                {"field": "price", "headerName": "Total Price", "width": 125, "type": "rightAligned"},
                {"field": "ks", "headerName": "Kept Spec", "width": 120, "type": "rightAligned"},
                {"field": "cw", "headerName": "Conv. Woodworking", "width": 150, "type": "rightAligned"},
                {"field": "all", "headerName": "Combined", "width": 120, "type": "rightAligned"},
                {"field": "share", "headerName": "Share", "width": 80, "type": "rightAligned"},
                {"field": "basis", "headerName": "", "width": 85, "headerTooltip": "Shown as estimate: not accepted"},
            ],
            "rowData": data, "pinnedBottomRowData": pinned, "rowHeight": 32, "headerHeight": 36,
        }, auto_size_columns=False).classes("w-full").style("height:56vh")
        g.on("cellDoubleClicked", lambda e: e.args["data"].get("number", "Total") != "Total"
             and ui.navigate.to(f"/project/{e.args['data']['number']}"))
        ui.label("Double-click a project to open it. Projects not yet accepted have no actuals and show their "
                 "estimate.").classes("text-xs text-gray-500")

    def refresh_from_inputs() -> None:
        try:
            state["start"] = date.fromisoformat(d_from.value) if d_from.value else None
            state["end"] = date.fromisoformat(d_to.value) if d_to.value else None
        except ValueError:
            return
        state["statuses"] = list(stat.value or [])
        state["kind"] = kind.value
        body.refresh()

    def apply_preset(e) -> None:
        a, b = PRESETS[e.value](date.today())
        d_from.set_value(a.isoformat() if a else "")
        d_to.set_value(b.isoformat() if b else "")
        refresh_from_inputs()

    def export() -> None:
        window = in_window(rows_all, state["start"], state["end"])
        shown = [r for r in window if r.project.status.value in state["statuses"]]
        name = f"income_{state['start'] or 'start'}_{state['end'] or 'end'}_{state['kind']}.csv"
        out = st.store.root / "exports" / name
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(to_csv(shown, state["kind"]), encoding="utf-8-sig")   # BOM: Excel reads UTF-8
        except OSError as e:
            ui.notify(f"Export failed: {e}", type="negative")
            return
        ui.notify(f"Saved {out}", type="positive", multi_line=True)
        ui.download.content(out.read_bytes(), name)

    preset.on_value_change(apply_preset)
    for el in (d_from, d_to, stat, kind):
        el.on_value_change(lambda _: refresh_from_inputs())
    body()
