"""Proposal editor: lines, variables, alternates, terms, issues, revisions."""

from __future__ import annotations

import base64
import os
import re
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from nicegui import run, ui
from pydantic import ValidationError

from ..calc import Results, calculate, payment_schedule, referenced, render, undefined_references, variable_map
from ..models import Performer, PriceSource, Variable
from ..proposal import (
    Alternate,
    Line,
    LineTier,
    Project,
    ProjectStatus,
    Revision,
    catalog_differences,
    line_from_item,
    pull_update,
)
from ..proposal import ProposalBlock, RevisionState
from ..render.document import build_document, compile_document, pdf_filename
from ..revisions import (
    RevisionError,
    create_revision,
    finalize,
    issue,
    mark_accepted,
    previous_issued,
    revision_diff,
)
from .pages import md_breaks
from .state import get_state
from .widgets import keep_current, BRAND, Col, EditableGrid, layout, to_decimal

ALT_COLORS = {1: "#DCE8F7", 2: "#E3F1E8", 3: "#F6ECDD"}
PCT_COLOR = "#E6E8EB"
MAX_ALTERNATES = 3


def money(v: Decimal | None) -> str:
    return "" if v is None else f"${v:,.2f}"


def _num(v) -> float | None:
    return None if v is None else float(v)


class Editor:
    def __init__(self, number: str, rev: str | None = None):
        self.st = get_state()
        self.project: Project = self.st.projects.load_project(number)
        self.revs: list[str] = self.st.projects.list_revisions(number)
        self.rev: Revision = self.st.projects.load_revision(number, rev if rev in self.revs else None)
        self.is_latest = self.rev.rev == self.revs[-1]
        # line IDs that appeared in an issued revision keep their meaning (see Revision.new_line_id)
        self.history: list[Line] = []
        for r in self.revs:
            if r != self.rev.rev:
                old = self.st.projects.load_revision(number, r)
                if old.locked:
                    self.history += old.lines
        self.reserved = {ln.id for ln in self.history}
        self.section_filter: int | None = None
        self.last_edited: str | None = None      # line ID highlighted in the grid after an edit
        self.income_kind: str | None = None      # Income tab: "estimate" or "actual"
        self._grid_filter_shown: int | None = None
        self.results: Results = self._calc()

    # ------------------------------------------------------------ model plumbing
    @property
    def cat(self):
        return self.st.catalog

    def _calc(self) -> Results:
        return calculate(self.rev, self.st.settings, self.cat.stock_classes, self.project)

    def variables(self) -> dict[str, str]:
        return variable_map(self.project, self.rev, self.st.settings)

    @property
    def locked(self) -> bool:
        return self.rev.locked

    def new_id(self, section: int, code: int | None = None) -> str:
        return self.rev.new_line_id(section, self.reserved, code, self.history)

    def save(self, refresh_grid: bool = True) -> None:
        if self.locked:
            ui.notify(f"Rev {self.rev.rev} is {self.rev.state.value.lower()} and read-only. "
                      "Create a new revision to make changes.", type="warning")
            return
        self.st.projects.save_revision(self.project.number, self.rev)
        self.results = self._calc()
        self.totals_bar.refresh()
        self.sections_panel.refresh()
        self.alternates_panel.refresh()
        self.issues_panel.refresh()
        self.income_panel.refresh()
        if refresh_grid:
            self.refresh_grid()

    def save_project(self) -> None:
        self.st.projects.save_project(self.project)
        self.header.refresh()

    def section_name(self, number: int) -> str:
        s = self.cat.section(number)
        return f"{number} {s.name}" if s else str(number)

    # ------------------------------------------------------------ page
    def build(self) -> None:
        layout(f"{self.project.number} {self.project.project_name}", drawer=False)
        # dialogs live here, outside any refreshable panel, so a refresh (e.g. after a save) never deletes
        # a dialog that is being opened from a button inside that panel
        self.host = ui.element("div")
        ui.add_css(f"""
            .pb-pct {{ background: {PCT_COLOR} !important; }}
            .pb-alt1 {{ background: {ALT_COLORS[1]} !important; }}
            .pb-alt2 {{ background: {ALT_COLORS[2]} !important; }}
            .pb-alt3 {{ background: {ALT_COLORS[3]} !important; }}
            .pb-out {{ color: #9aa0a6; font-style: italic; }}
            .pb-last {{ box-shadow: inset 4px 0 0 #E8A33D; }}
            .pb-last .ag-cell {{ font-weight: 600; }}
        """)
        self.header()
        self.totals_bar()
        with ui.tabs().props("dense inline-label align=left").classes("w-full border-b") as tabs:
            t_lines = ui.tab("Lines", icon="list")
            t_vars = ui.tab("Variables", icon="data_object")
            t_alts = ui.tab("Alternates", icon="call_split")
            t_terms = ui.tab("Terms & options", icon="article")
            t_issues = ui.tab("Issues", icon="report")
            t_income = ui.tab("Income", icon="savings")
            t_quotes = ui.tab("Sub quotes", icon="request_quote")
        with ui.tab_panels(tabs, value=t_lines).classes("w-full"):
            with ui.tab_panel(t_lines).classes("p-0 pt-2"):
                self.lines_tab()
            with ui.tab_panel(t_vars):
                self.variables_tab()
            with ui.tab_panel(t_alts):
                self.alternates_panel()
            with ui.tab_panel(t_terms):
                self.terms_panel()
            with ui.tab_panel(t_issues):
                self.issues_panel()
            with ui.tab_panel(t_income):
                self.income_panel()
            with ui.tab_panel(t_quotes):
                self.quotes_panel()

    # ------------------------------------------------------------ sub quotes
    def _pdf_dir(self) -> Path:
        d = self.st.projects.project_dir(self.project.number) / "pdf"
        d.mkdir(exist_ok=True)
        return d

    def _logo_path(self):
        lp = self.st.settings.company.logo_path
        return self.st.store.path(lp) if lp else None

    @ui.refreshable_method
    def quotes_panel(self) -> None:
        from ..crm import line_contractor
        from ..quotes import Quote, comparison_document, contractor_lines, rfq_document
        from .pdf_ui import export_pdf, preview_pdf
        st, num = self.st, self.project.number
        book = st.contractors
        log = st.projects.load_quotes(num)

        ui.label("Request a quote").classes("font-semibold")
        ui.label("Builds a PDF of the lines assigned to one contractor (title, description, notes, unit, quantity) "
                 "with the project number, name and site address. No prices and no client name. Assign contractors "
                 "on the lines (line form, Contractor).").classes("text-xs text-gray-500")
        on_lines = {}
        for ln in self.rev.lines:
            c = line_contractor(book, ln)
            if c and not ln.is_percent:
                on_lines.setdefault(c.id, []).append(ln.id)
        with ui.row().classes("items-end gap-3"):
            sel = ui.select({cid: f"{book.get(cid).company} ({', '.join(ids)})" for cid, ids in on_lines.items()},
                            label="Contractor", value=next(iter(on_lines), None)).props("dense").classes("min-w-[360px]")

            def rfq_doc():
                con = book.get(sel.value)
                if con is None:
                    ui.notify("No contractor is assigned to any line yet.", type="warning")
                    return None, None
                doc = rfq_document(self.project, self.rev, con, contractor_lines(self.rev, book, con.id),
                                   st.settings, self.cat.stock_classes)
                name = re.sub(r"[^A-Za-z0-9_]+", "", f"{num}_RFQ_{con.company.replace(' ', '')}_V{self.rev.rev}") + ".pdf"
                return doc, name

            async def rfq_preview() -> None:
                doc, _ = rfq_doc()
                if doc:
                    await preview_pdf(doc, "rfq.typ", "Request for quote", self._logo_path())

            async def rfq_export() -> None:
                doc, name = rfq_doc()
                if doc:
                    await export_pdf(doc, "rfq.typ", name, self._pdf_dir(), self._logo_path())
            ui.button("Preview", icon="visibility", on_click=rfq_preview).props("dense outline")
            ui.button("Export PDF", icon="picture_as_pdf", on_click=rfq_export).props("dense")

        def save_quotes() -> None:
            st.projects.save_quotes(num, log)
            scopes_now = log.scopes()
            cmp_sel.set_options(scopes_now, value=cmp_sel.value if cmp_sel.value in scopes_now
                                else (scopes_now[0] if scopes_now else None))

        ui.separator().classes("my-3")
        ui.label("Quotes received").classes("font-semibold")
        ui.label("Log each quote. Quotes with the same scope name are compared. With a single quote, put the price "
                 "on the line (unit price, quote ref and quote amount) as before; pick the winner the same way.") \
            .classes("text-xs text-gray-500")
        EditableGrid(lambda: log.quotes,
                     [Col("scope", "Scope", width=150),
                      Col("contractor_id", "Contractor", "lookup", width=190,
                          lookup={c.id: c.company for c in book.sorted()}),
                      Col("line_ids", "Lines", "strlist", width=120),
                      Col("amount", "Price", "number", width=110),
                      Col("received", "Received", "date", width=115),
                      Col("valid_until", "Valid until", "date", width=115),
                      Col("notes", "Inclusions / exclusions / notes", flex=1)],
                     save_quotes,
                     lambda: Quote(scope=(log.quotes[-1].scope if log.quotes else ""), received=date.today()),
                     height="30vh")

        ui.label("Compare for the client").classes("font-semibold mt-3")
        ui.label("A separate PDF (not part of the proposal) listing each contractor's price for one scope, lowest "
                 "first.").classes("text-xs text-gray-500")
        with ui.row().classes("items-end gap-3"):
            scopes = log.scopes()
            cmp_sel = ui.select(scopes, value=scopes[0] if scopes else None, label="Scope").props("dense") \
                .classes("min-w-[240px]")

            def cmp_doc():
                qs = log.for_scope(cmp_sel.value or "")
                if not qs:
                    ui.notify("Pick a scope with logged quotes.", type="warning")
                    return None, None
                doc = comparison_document(self.project, self.rev, cmp_sel.value, qs, book, st.settings)
                name = re.sub(r"[^A-Za-z0-9_]+", "", f"{num}_QuoteComparison_{cmp_sel.value.replace(' ', '')}") + ".pdf"
                return doc, name

            async def cmp_preview() -> None:
                doc, _ = cmp_doc()
                if doc:
                    await preview_pdf(doc, "comparison.typ", "Quote comparison", self._logo_path())

            async def cmp_export() -> None:
                doc, name = cmp_doc()
                if doc:
                    await export_pdf(doc, "comparison.typ", name, self._pdf_dir(), self._logo_path())
            ui.button("Preview", icon="visibility", on_click=cmp_preview).props("dense outline")
            ui.button("Export PDF", icon="picture_as_pdf", on_click=cmp_export).props("dense")

    # ------------------------------------------------------------ income (internal)
    @ui.refreshable_method
    def income_panel(self) -> None:
        from ..closeout import accepted_revision, build_ledger, contract_context
        from ..income import contract_report, estimate_report
        s, ps, num = self.st.settings, self.st.projects, self.project.number
        ui.label("What Kept Spec keeps on this project, before your own business expenses. Counts lines performed "
                 "by Kept Spec Advisors or Convenient Woodworking, overhead, profit, change order management time, "
                 "and overhead and profit on change orders and line variance. Subcontractors, materials, "
                 "allowances, builder's risk, contingency and owner-supplied items pass through. Never printed.") \
            .classes("text-xs text-gray-500 mb-2")
        revs = [self.rev if r == self.rev.rev else ps.load_revision(num, r) for r in self.revs]
        acc = accepted_revision(revs)
        if acc is not None:
            contract = contract_context(acc, s, self.cat.stock_classes, self.project)
            ledger = build_ledger(contract, ps.load_change_orders(num), ps.load_reconciliation(num))
            rep = contract_report(ledger, s)
            ui.label(f"Contract: Rev {acc.rev} (accepted). Actual uses closeout data from Change orders & ledger.") \
                .classes("text-sm font-semibold")
        else:
            r = self.results
            rep = estimate_report(self.rev, r, r.base, s)
            ui.label(f"Rev {self.rev.rev}, base proposal. The Actual column appears once a revision is accepted.") \
                .classes("text-sm font-semibold")
        has_act = rep.actual_total is not None
        kind = self.income_kind if (has_act and self.income_kind) else ("actual" if has_act else "estimate")

        def m(v) -> str:
            return "" if v is None else (f"-${-v:,.2f}" if v < 0 else f"${v:,.2f}")

        def pct(v) -> str:
            return "" if v is None else f"{v * 100:.1f}%"

        if has_act:
            def set_kind(e) -> None:
                self.income_kind = e.value
                self.income_panel.refresh()
            ui.toggle({"estimate": "Estimate", "actual": "Actual"}, value=kind, on_change=set_kind) \
                .props("dense no-caps").classes("my-1")
        cols = [{"name": "item", "label": "Income", "field": "item", "align": "left"},
                {"name": "ks", "label": "Kept Spec", "field": "ks", "align": "right"},
                {"name": "cw", "label": "Convenient Woodworking", "field": "cw", "align": "right"},
                {"name": "all", "label": "Combined", "field": "all", "align": "right"},
                {"name": "note", "label": "", "field": "note", "align": "left",
                 "style": "white-space:normal;max-width:380px", "classes": "text-xs text-gray-500"}]
        rows = []
        for g in rep.groups:
            v = getattr(g, kind)
            rows.append({"item": g.name, "ks": m(v) if g.entity == "KS" else "", "cw": m(v) if g.entity == "CW" else "",
                         "all": m(v), "note": g.note})
        rows.append({"item": "Total income", "ks": m(rep.total(kind, "KS")), "cw": m(rep.total(kind, "CW")),
                     "all": m(rep.total(kind)), "note": ""})
        price = rep.contract_price if kind == "estimate" else rep.final_price
        rows.append({"item": "Share of price", "ks": pct(rep.share(kind, "KS")), "cw": pct(rep.share(kind, "CW")),
                     "all": pct(rep.share(kind)),
                     "note": ("of Total Price " if kind == "estimate" else "of final cost ") + m(price)})
        ui.table(columns=cols, rows=rows, row_key="item").props("dense flat bordered").classes("w-full max-w-[1100px]")
        if has_act and rep.lines_without_actuals:
            ui.label(f"{rep.lines_without_actuals} of your lines have no actual hours or cost entered yet; "
                     "they are counted at their contract amount.").classes("text-xs text-orange-700 mt-1")

        for g in rep.groups:
            if not g.lines:
                continue
            with ui.expansion(f"{g.name} ({len(g.lines)})").classes("w-full max-w-[1000px] border rounded mt-2"):
                lc = [{"name": "id", "label": "ID", "field": "id", "align": "left"},
                      {"name": "title", "label": "Title", "field": "title", "align": "left"},
                      {"name": "est", "label": "Estimate", "field": "est", "align": "right"}]
                if has_act:
                    lc.append({"name": "act", "label": "Actual", "field": "act", "align": "right"})
                ui.table(columns=lc, rows=[{"id": x.line_id, "title": x.title, "est": m(x.estimate),
                                            "act": m(x.actual) + ("" if x.entered or not has_act else " (contract)")}
                                           for x in g.lines], row_key="id").props("dense flat").classes("w-full")

        if acc is None and (self.results.alternates or self.results.combinations):
            ui.label("By option").classes("font-semibold text-sm mt-4")
            opts = [("Base", self.results.base)] + [(sc.name, sc) for _, sc in sorted(self.results.alternates.items())]
            opts += [(c.name, c) for c in self.results.combinations]
            orow = []
            for name, sc in opts:
                er = estimate_report(self.rev, self.results, sc, s)
                orow.append({"o": name, "p": m(sc.total), "ks": m(er.total("estimate", "KS")),
                             "cw": m(er.total("estimate", "CW")), "i": m(er.total()), "s": pct(er.share())})
            ui.table(columns=[{"name": "o", "label": "Option", "field": "o", "align": "left"},
                              {"name": "p", "label": "Total Price", "field": "p", "align": "right"},
                              {"name": "ks", "label": "Kept Spec", "field": "ks", "align": "right"},
                              {"name": "cw", "label": "Conv. Woodworking", "field": "cw", "align": "right"},
                              {"name": "i", "label": "Combined", "field": "i", "align": "right"},
                              {"name": "s", "label": "Share", "field": "s", "align": "right"}],
                     rows=orow, row_key="o").props("dense flat bordered").classes("max-w-[800px]")

    @ui.refreshable_method
    def header(self) -> None:
        p = self.project
        with ui.row().classes("w-full items-start gap-4 no-wrap"):
            ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/projects")).props("flat round dense")
            with ui.column().classes("gap-0 min-w-0"):
                ui.label(f"{p.number}  {p.project_name}").classes("text-xl font-semibold")
                ui.label("  |  ".join(x for x in (p.client_name, p.site_address) if x)).classes("text-sm text-gray-600")
            ui.space()
            with ui.column().classes("items-end gap-2"):
                with ui.row().classes("items-center gap-3 no-wrap"):
                    ui.select({r: f"Rev {r}" for r in self.revs}, value=self.rev.rev, label="Revision",
                              on_change=lambda e: ui.navigate.to(f"/project/{p.number}?rev={e.value}")) \
                        .props("dense outlined").classes("w-28")
                    color = {RevisionState.DRAFT: "grey-7", RevisionState.ISSUED: "blue-8",
                             RevisionState.ACCEPTED: "green-8", RevisionState.SUPERSEDED: "grey-5"}[self.rev.state]
                    ui.badge(self.rev.state.value, color=color).classes("text-sm px-2 py-1")
                    ui.label(f"{self.rev.proposal_date:%Y.%m.%d}").classes("text-sm")
                    if p.archived_on:
                        ui.badge("Archived", color="grey-7").classes("text-sm px-2 py-1") \
                            .tooltip("Restore it from the Projects list (Archive / restore)")
                    ui.select([s.value for s in ProjectStatus], value=p.status.value, label="Project status",
                              on_change=lambda e: (p.set_status(ProjectStatus(e.value)), self.save_project())) \
                        .props("dense outlined").classes("w-36")
                with ui.row().classes("items-center gap-2 no-wrap"):
                    ui.button("Project info", icon="edit", on_click=self.project_dialog).props("outline dense")
                    ui.button("Change orders & ledger", icon="balance",
                              on_click=lambda: ui.navigate.to(f"/project/{p.number}/closeout")).props("outline dense")
                    ui.button("Preview", icon="visibility", on_click=self.preview).props("outline dense")
                    ui.button("Export PDF", icon="picture_as_pdf", on_click=self.export_pdf).props("outline dense")
                    if not self.locked:
                        ui.button(f"Issue Rev {self.rev.rev}", icon="lock", on_click=self.issue_dialog).props("dense")
                    elif self.is_latest and self.rev.state is RevisionState.ISSUED:
                        ui.button("New revision", icon="note_add", on_click=self.new_revision).props("dense")
                        if not self.rev.is_contract:
                            ui.button("Finalize...", icon="fact_check", on_click=self.accept_dialog) \
                                .props("dense color=positive")
                        else:
                            ui.button("Mark accepted", icon="handshake", on_click=self.mark_accepted_dialog) \
                                .props("dense color=positive")
        if self.locked:
            with ui.row().classes("w-full items-center gap-2 px-3 py-2 rounded") \
                    .style("background:#FFF4E5;border:1px solid #F0C36D"):
                ui.icon("lock", color="orange-9")
                issued = f" Issued {self.rev.issued_at:%Y-%m-%d %H:%M}." if self.rev.issued_at else ""
                msg = f"Rev {self.rev.rev} is {self.rev.state.value.lower()} and read-only.{issued}"
                if self.rev.state is RevisionState.SUPERSEDED or not self.is_latest:
                    msg += f" The latest revision is {self.revs[-1]}."
                elif self.rev.state is RevisionState.ACCEPTED:
                    msg += " Scope changes after acceptance go through change orders."
                elif self.rev.is_contract:
                    msg += " Final revision out for signature: Mark accepted when signed, or New revision to adjust."
                else:
                    msg += " Use New revision to make changes, or Finalize once the client has chosen."
                ui.label(msg).classes("text-sm")
                if not self.is_latest:
                    ui.button(f"Open Rev {self.revs[-1]}",
                              on_click=lambda: ui.navigate.to(f"/project/{p.number}?rev={self.revs[-1]}")) \
                        .props("flat dense")

    @ui.refreshable_method
    def totals_bar(self) -> None:
        r = self.results
        with ui.row().classes("w-full items-stretch gap-3 my-2"):
            def tile(label, value, sub="", color=BRAND, bg="white"):
                with ui.card().classes("px-4 py-2 gap-0").style(f"background:{bg}"):
                    ui.label(label).classes("text-xs uppercase text-gray-500")
                    ui.label(value).classes("text-lg font-semibold").style(f"color:{color}")
                    if sub:
                        ui.label(sub).classes("text-xs text-gray-500")
            tile("Subtotal", money(r.base.subtotal))
            tile("Percent items", money(r.base.percent_total),
                 f"{(r.base.percent_total / r.base.subtotal * 100):.1f}% of subtotal" if r.base.subtotal else "")
            tile("Total", money(r.base.total),
                 f"{money(r.base.total_incl_owner)} incl. owner-supplied" if r.base.owner_supplied else "")
            for n, sc in r.alternates.items():
                d = r.delta(n)
                tile(f"Alt {n}", money(sc.total), f"{'+' if d >= 0 else '-'}{money(abs(d))} vs base",
                     bg=ALT_COLORS.get(n, "white"))
            ps = payment_schedule(r.base.total, self.st.settings)
            tile("Deposit", money(ps["deposit"]), f"retainage {money(ps['retainage'])}")
            if r.errors:
                tile("Issues", str(len(r.errors)), "see Issues tab", color="#B00020")

    # ------------------------------------------------------------ lines tab
    def lines_tab(self) -> None:
        with ui.row().classes("w-full no-wrap gap-3 items-start"):
            with ui.card().classes("w-72 p-2 shrink-0"):
                self.sections_panel()
            with ui.column().classes("grow gap-2 min-w-0"):
                with ui.row().classes("gap-2 items-center").bind_visibility_from(self, "locked", lambda v: not v):
                    ui.button("Add from catalog", icon="playlist_add", on_click=self.catalog_picker).props("dense")
                    ui.button("Custom line", icon="add", on_click=self.custom_line).props("dense outline")
                    ui.separator().props("vertical")
                    ui.button(icon="edit", on_click=self._edit_selected).props("dense flat").tooltip("Edit line")
                    ui.button(icon="content_copy", on_click=self._duplicate_selected).props("dense flat") \
                        .tooltip("Duplicate")
                    ui.button(icon="arrow_upward", on_click=lambda: self._move_selected(-1)).props("dense flat") \
                        .tooltip("Move up")
                    ui.button(icon="arrow_downward", on_click=lambda: self._move_selected(1)).props("dense flat") \
                        .tooltip("Move down")
                    ui.button(icon="delete", on_click=self._delete_selected).props("dense flat color=negative") \
                        .tooltip("Delete")
                    ui.label("Double-click ID, notes or cost to open a line; other cells edit in place.") \
                        .classes("text-xs text-gray-500")
                flt = ui.input(placeholder="Filter lines").props("dense clearable").classes("w-56")
                self.grid = ui.aggrid(self._grid_options(), auto_size_columns=False) \
                    .classes("w-full").style("height:64vh")
                self.grid.on("cellDoubleClicked", self._dblclick)
                self.grid.on("cellValueChanged", self._cell_changed)
                flt.on_value_change(lambda e: self.grid.run_grid_method("setGridOption", "quickFilterText",
                                                                       e.value or ""))

    def _grid_options(self) -> dict:
        ed = not self.locked
        self._grid_filter_shown = self.section_filter
        perf = [p.value for p in Performer]
        units = [u.code for u in self.cat.units]
        return {
            "columnDefs": [
                {"field": "id", "headerName": "ID", "width": 72, "pinned": "left"},
                {"field": "code", "headerName": "Code", "width": 72},
                {"field": "section_name", "headerName": "Section", "width": 130, "hide": self.section_filter is not None},
                {"field": "title", "headerName": "Title", "width": 180, "editable": ed},
                {"field": "notes", "headerName": "Notes", "flex": 1, "minWidth": 160, "tooltipField": "notes"},
                {"field": "performer", "headerName": "Performer", "width": 140, "editable": ed,
                 "cellEditor": "agSelectCellEditor", "cellEditorParams": {"values": perf}},
                {"field": "unit", "headerName": "Unit", "width": 70, "editable": ed,
                 "cellEditor": "agSelectCellEditor", "cellEditorParams": {"values": units}},
                {"field": "qty", "headerName": "Qty", "width": 80, "type": "rightAligned",
                 "cellDataType": "number", ":editable": "p => !p.data.qty_locked" if ed else "p => false"},
                {"field": "price", "headerName": "Unit price", "width": 110, "type": "rightAligned",
                 "cellDataType": "number", "editable": ed,
                 ":valueFormatter": "p => p.value == null ? '' : (p.data.pct ? p.value + '%' : "
                                    "'$' + Number(p.value).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}))"},
                {"field": "cost", "headerName": "Cost", "width": 115, "type": "rightAligned"},
                {"field": "basis", "headerName": "Basis", "width": 100},
                {"field": "flags", "headerName": "Flags", "width": 120, "tooltipField": "flags"},
            ],
            "rowData": self._rows(),
            "rowSelection": {"mode": "singleRow", "checkboxes": False, "enableClickSelection": True},
            "rowHeight": 32, "headerHeight": 36,
            "stopEditingWhenCellsLoseFocus": True,
            "defaultColDef": {"resizable": True},
            "rowClassRules": {"pb-pct": "data.pct", "pb-alt1": "data.alt === 1", "pb-alt2": "data.alt === 2",
                              "pb-alt3": "data.alt === 3", "pb-out": "data.excluded", "pb-last": "data.last"},
            # stable row identity: refreshing rowData updates rows in place, so scroll and selection stay put
            ":getRowId": "p => p.data.id",
            "tooltipShowDelay": 400,
        }

    def _ordered_lines(self) -> list[Line]:
        order = list(self.rev.sections) + sorted({ln.section for ln in self.rev.lines} - set(self.rev.sections))
        out = []
        for sec in order:
            if self.section_filter is not None and sec != self.section_filter:
                continue
            out += self.rev.section_lines(sec)
        return out

    def _rows(self) -> list[dict]:
        rows = []
        r = self.results
        pct = r.base.percent_items
        for ln in self._ordered_lines():
            lr = r.lines[ln.id]
            flags = []
            if ln.not_included:
                flags.append("not incl.")
            if ln.owner_furnished:
                flags.append("owner")
            if ln.is_allowance:
                flags.append("allow." + (f" {ln.tier.value}" if ln.allowance_id else ""))
            if ln.alternate:
                flags.append(f"Alt {ln.alternate}")
            if any(ln.id in a.removes for a in self.rev.alternates):
                flags.append("swapped")
            if catalog_differences(ln, self.cat):
                flags.append("catalog changed")
            if lr.errors:
                flags.append("error")
            basis = ln.price_basis.value + (f" ({ln.rate_key})" if ln.rate_key and ln.price_basis is PriceSource.RATE else "")
            qty_note = ""
            if ln.qty_var:
                qty_note = f" ={{{ln.qty_var}}}"
            elif lr.stock:
                qty_note = " (stock)"
            cost = pct.get(ln.id) if ln.is_percent else lr.cost
            if ln.is_percent and ln.alternate:
                cost = None
            rows.append({
                "id": ln.id, "code": ln.code, "section_name": self.section_name(ln.section),
                "title": ln.title, "notes": render(ln.notes, self.variables()) or ln.general_description,
                "performer": ln.performer.value, "unit": ln.unit,
                "qty": _num(lr.qty), "qty_locked": bool(ln.qty_var or lr.stock or ln.is_percent),
                "price": _num(lr.unit_price * 100 if ln.is_percent else lr.unit_price),
                "cost": money(cost) + qty_note if cost is not None else qty_note,
                "basis": basis, "flags": ", ".join(flags), "pct": ln.is_percent, "alt": ln.alternate,
                "excluded": ln.section not in self.rev.sections,
            })
        return rows

    INLINE_EDIT = {"title", "performer", "unit", "qty", "price"}

    def _dblclick(self, e) -> None:
        if not self.locked and e.args.get("colId") in self.INLINE_EDIT and not (e.args.get("colId") == "qty" and e.args["data"].get("qty_locked")):
            return  # double-click on an editable cell edits in place
        self.line_dialog(self.rev.line(e.args["data"]["id"]))

    def refresh_grid(self) -> None:
        rows = self._rows()
        for r in rows:
            r["last"] = r["id"] == self.last_edited
        if self._grid_filter_shown != self.section_filter:
            # section filter changed: column visibility changes too, so rebuild (scroll to top is expected)
            self._grid_filter_shown = self.section_filter
            for c in self.grid.options["columnDefs"]:
                if c["field"] == "section_name":
                    c["hide"] = self.section_filter is not None
            self.grid.options["rowData"] = rows
            self.grid.update()
            return
        # rows go straight to the grid API: assigning options would rebuild the grid and reset its scroll
        self.grid.run_grid_method("setGridOption", "rowData", rows)
        idx = next((i for i, r in enumerate(rows) if r["last"]), None)
        if idx is not None:
            self.grid.run_grid_method("ensureIndexVisible", idx)
            self.grid.run_row_method(self.last_edited, "setSelected", True)

    def mark_edited(self, line_id: str | None) -> None:
        self.last_edited = line_id

    def _cell_changed(self, e) -> None:
        ln = self.rev.line(e.args["data"]["id"])
        field, val = e.args["colId"], e.args.get("newValue")
        if ln is None:
            return
        try:
            if field == "title":
                ln.title = val or ln.title
            elif field == "performer":
                ln.performer = Performer(val or "")
            elif field == "unit":
                ln.unit = val
            elif field == "qty":
                ln.qty = to_decimal(val) or Decimal(0)
                ln.takeoff = None
            elif field == "price":
                p = to_decimal(val)
                if ln.is_percent:
                    ln.unit_price = p / 100 if p is not None else None
                else:
                    ln.unit_price = p
                    if ln.price_basis is PriceSource.RATE:
                        ln.price_basis = PriceSource.FIXED
                    elif ln.price_basis is PriceSource.ALLOWANCE:
                        ln.tier = LineTier.CUSTOM
                ln.price_var = None
        except (ValidationError, ValueError) as err:
            ui.notify(f"Not saved: {err}", type="negative")
        self.mark_edited(ln.id)
        self.save()

    async def _selected(self) -> Line | None:
        rows = await self.grid.get_selected_rows()
        if not rows:
            ui.notify("Select a line first.")
            return None
        return self.rev.line(rows[0]["id"])

    async def _edit_selected(self) -> None:
        ln = await self._selected()
        if ln:
            self.line_dialog(ln)

    async def _duplicate_selected(self) -> None:
        ln = await self._selected()
        if ln:
            copy = ln.model_copy(deep=True)
            copy.id = self.new_id(ln.section)
            self.rev.add_line(copy)
            copy.order = ln.order + 5
            self.mark_edited(copy.id)
            self.save()
            ui.notify(f"Duplicated {ln.id} as {copy.id}")

    async def _move_selected(self, d: int) -> None:
        ln = await self._selected()
        if ln:
            self.rev.move_line(ln.id, d)
            self.mark_edited(ln.id)
            self.save()

    async def _delete_selected(self) -> None:
        ln = await self._selected()
        if not ln:
            return
        with self.host, ui.dialog() as dlg, ui.card():
            ui.label(f"Delete line {ln.id} {ln.title}? Its ID is retired.")
            with ui.row():
                ui.button("Cancel", on_click=lambda: dlg.submit(False)).props("flat")
                ui.button("Delete", on_click=lambda: dlg.submit(True)).props("color=negative")
        if await dlg:
            self.rev.remove_line(ln.id)
            self.save()

    # ------------------------------------------------------------ sections panel
    @ui.refreshable_method
    def sections_panel(self) -> None:
        r = self.results
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Sections").classes("font-semibold")
            ui.button("All", on_click=lambda: self._filter(None)) \
                .props(f"dense {'unelevated' if self.section_filter is None else 'flat'} size=sm")
        ui.label("Checked sections print; order sets print order.").classes("text-xs text-gray-500")
        included = list(self.rev.sections)
        others = [s.number for s in self.cat.sections if s.number not in included]
        for num in included + others:
            on = num in included
            n_lines = len(self.rev.section_lines(num))
            with ui.row().classes("w-full items-center no-wrap gap-1 py-0") \
                    .style("background:#eef3f9;border-radius:4px" if self.section_filter == num else ""):
                cb = ui.checkbox(value=on, on_change=lambda e, n=num: self._toggle_section(n, e.value)).props("dense")
                if self.locked:
                    cb.disable()
                lbl = ui.label(self.section_name(num)).classes(
                    "text-sm grow cursor-pointer truncate " + ("" if on else "text-gray-400"))
                lbl.on("click", lambda n=num: self._filter(n))
                if on:
                    ui.label(money(r.base.section_total(num))).classes("text-xs text-gray-600")
                    if not self.locked:
                        ui.button(icon="expand_less", on_click=lambda n=num: self._move_section(n, -1)) \
                            .props("flat dense round size=xs")
                        ui.button(icon="expand_more", on_click=lambda n=num: self._move_section(n, 1)) \
                            .props("flat dense round size=xs")
                elif n_lines:
                    ui.label(f"{n_lines} hidden").classes("text-xs text-orange-700")

    def _filter(self, section: int | None) -> None:
        self.section_filter = section
        self.sections_panel.refresh()
        self.refresh_grid()

    def _toggle_section(self, num: int, on: bool) -> None:
        if on and num not in self.rev.sections:
            self.rev.sections.append(num)
        elif not on and num in self.rev.sections:
            self.rev.sections.remove(num)
        self.save()

    def _move_section(self, num: int, d: int) -> None:
        s = self.rev.sections
        i = s.index(num)
        j = i + d
        if 0 <= j < len(s):
            s[i], s[j] = s[j], s[i]
            self.save()

    # ------------------------------------------------------------ add lines
    def catalog_picker(self, alternate: int | None = None) -> None:
        rows = []
        for it in self.cat.items:
            if not it.active:
                continue
            price = self.cat.unit_price(it)
            rows.append({"code": it.code, "section": self.section_name(it.section), "title": it.title,
                         "unit": it.unit, "source": it.price_source.value,
                         "price": (f"{price * 100:.1f}%" if it.price_source is PriceSource.PERCENT
                                   else money(price)) if price is not None else "",
                         "description": it.description})
        with self.host, ui.dialog().props("maximized=false") as dlg, ui.card().classes("w-[1100px] max-w-full"):
            ui.label("Add from catalog" + (f" to Alt {alternate}" if alternate else "")).classes("text-lg font-semibold")
            ui.label("Tick one or more items. Each becomes a line in its own section; "
                     "the line keeps a copy of the catalog values.").classes("text-xs text-gray-500")
            flt = ui.input(placeholder="Search").props("dense clearable autofocus").classes("w-80")
            g = ui.aggrid({
                "columnDefs": [
                    {"field": "code", "headerName": "Code", "width": 80},
                    {"field": "section", "headerName": "Section", "width": 200},
                    {"field": "title", "headerName": "Title", "width": 220},
                    {"field": "unit", "headerName": "Unit", "width": 70},
                    {"field": "source", "headerName": "Source", "width": 90},
                    {"field": "price", "headerName": "Price", "width": 100},
                    {"field": "description", "headerName": "Description", "flex": 1, "tooltipField": "description"},
                ],
                "rowData": rows,
                "rowSelection": {"mode": "multiRow"},
                "rowHeight": 30,
            }, auto_size_columns=False).classes("w-full").style("height:60vh")
            flt.on_value_change(lambda e: g.run_grid_method("setGridOption", "quickFilterText", e.value or ""))

            async def add() -> None:
                sel = await g.get_selected_rows()
                if not sel:
                    ui.notify("Tick at least one item.")
                    return
                added = []
                for r in sel:
                    it = self.cat.item(r["code"])
                    ln = line_from_item(it, self.cat, self.new_id(it.section, it.code))
                    ln.alternate = alternate
                    self.rev.add_line(ln, by_code=True)
                    added.append(ln.id)
                dlg.close()
                self.mark_edited(added[-1] if added else None)
                self.save()
                ui.notify(f"Added {', '.join(added)}" + (f" to Alt {alternate}" if alternate else ""), type="positive")
                if alternate and len(added) == 1:
                    self.line_dialog(self.rev.line(added[0]))     # fill in the alternate's details right away

            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=dlg.close).props("flat")
                ui.button("Add selected", icon="playlist_add", on_click=add)
        dlg.open()

    def custom_line(self, alternate: int | None = None, section: int | None = None) -> None:
        sec = section or self.section_filter or (self.rev.sections[0] if self.rev.sections else self.cat.sections[0].number)
        ln = Line(id=self.new_id(sec), section=sec, title="New line", unit_price=Decimal(0), alternate=alternate)
        self.rev.add_line(ln)
        self.mark_edited(ln.id)
        self.save()
        self.line_dialog(ln)

    # ------------------------------------------------------------ line dialog
    def line_dialog(self, ln: Line | None) -> None:
        if ln is None:
            return
        cat, rev = self.cat, self.rev
        work = ln.model_copy(deep=True)
        var_names = sorted(self.variables())
        with self.host, ui.dialog() as dlg, ui.card().classes("w-[1000px] max-w-full"):
            with ui.row().classes("w-full items-center"):
                ui.label(f"Line {ln.id}" + (f"  (catalog {ln.code})" if ln.code else "  (custom)")) \
                    .classes("text-lg font-semibold")
                ui.space()
                diffs = catalog_differences(ln, cat)
                if diffs:
                    ui.label("Catalog changed: " + ", ".join(diffs)).classes("text-xs text-orange-700")

                    def pull() -> None:
                        changed = pull_update(ln, cat)
                        dlg.close()
                        self.mark_edited(ln.id)
                        self.save()
                        ui.notify(f"Pulled from catalog: {', '.join(changed)}", type="positive")
                    if not self.locked:
                        ui.button("Pull update", icon="sync", on_click=pull).props("dense outline")

            with ui.grid(columns=6).classes("w-full gap-x-3"):
                code_sel = ui.select({0: "- custom (no catalog item)",
                                      **{i.code: f"{i.code} {i.title}" for i in sorted(cat.items, key=lambda i: i.code)
                                         if i.active or i.code == work.code}},
                                     label="Catalog code", value=work.code or 0, with_input=True) \
                    .props("dense").classes("col-span-6")
                title = ui.input("Title", value=work.title).props("dense").classes("col-span-3")
                section = ui.select(keep_current({s.number: f"{s.number} {s.name}" for s in cat.sections}, work.section),
                                    label="Section", value=work.section).props("dense").classes("col-span-2")
                unit = ui.select(cat.unit_options(work.unit), label="Unit", value=work.unit).props("dense")
                performer = ui.select({p.value: p.value or "-" for p in Performer}, label="Performer (prints)",
                                      value=work.performer.value).props("dense").classes("col-span-2")
                from .crm_pages import contractor_dialog, vendor_names
                from ..crm import line_contractor
                cur = line_contractor(self.st.contractors, work)
                con_opts = {c.id: c.company for c in self.st.contractors.sorted() if c.active or (cur and c.id == cur.id)}
                with ui.row().classes("col-span-2 items-end gap-1 no-wrap"):
                    sub_sel = ui.select(con_opts, value=cur.id if cur else None, label="Contractor (internal)",
                                        with_input=True).props("dense clearable").classes("grow")

                    def new_con() -> None:
                        def done(c) -> None:
                            sub_sel.set_options({**sub_sel.options, c.id: c.company}, value=c.id)
                        contractor_dialog(None, done)
                    ui.button(icon="add", on_click=new_con).props("dense flat").tooltip("New contractor")
                alt = ui.select({0: "Base", **{a.number: f"Alt {a.number} only" for a in rev.alternates}},
                                label="Belongs to", value=work.alternate or 0).props("dense").classes("col-span-2")

            with ui.row().classes("w-full items-start no-wrap gap-4"):
                with ui.column().classes("w-1/2 gap-1"):
                    ui.label("General description (from catalog)").classes("text-xs text-gray-500")
                    gen_lbl = ui.label(work.general_description or "-").classes("text-sm whitespace-pre-line")
                    print_general = ui.switch("Print general description", value=work.print_general).props("dense")
                    notes = ui.textarea("Detail notes (prints; Markdown; {variables})", value=work.notes) \
                        .props("outlined autogrow").classes("w-full")
                    with ui.row().classes("gap-1 flex-wrap"):
                        for name in var_names:
                            ui.chip(name, on_click=lambda n=name: notes.set_value((notes.value or "") + f"{{{n}}}")) \
                                .props("dense outline clickable size=sm")
                with ui.column().classes("w-1/2 gap-1"):
                    ui.label("Preview").classes("text-xs text-gray-500")
                    preview = ui.markdown().classes("text-sm border rounded p-2 w-full min-h-[80px]")

                    def upd_preview() -> None:
                        parts = []
                        if print_general.value and work.general_description:
                            parts.append(work.general_description)
                        if notes.value:
                            parts.append(render(notes.value, self.variables()))
                        preview.set_content(md_breaks("\n\n".join(parts)))
                        missing = undefined_references(notes.value or "", self.variables())
                        warn_lbl.set_text(f"Undefined: {', '.join(sorted(missing))}" if missing else "")
                    warn_lbl = ui.label().classes("text-xs text-red-700")
                    notes.on_value_change(lambda _: upd_preview())
                    print_general.on_value_change(lambda _: upd_preview())
                    upd_preview()

            def change_code() -> None:
                # relink to another catalog item: title, section and general description follow the item;
                # quantity, price, notes and flags stay as entered
                new_code = int(code_sel.value or 0) or None
                if new_code == work.code:
                    return
                work.code = new_code
                item = cat.item(new_code) if new_code else None
                if item:
                    title.set_value(item.title)
                    section.set_value(item.section)
                    work.general_description = item.description
                else:
                    work.general_description = ""
                gen_lbl.set_text(work.general_description or "-")
                upd_preview()
            code_sel.on_value_change(lambda _: change_code())

            ui.separator()
            ui.label("Quantity").classes("font-semibold text-sm")
            with ui.grid(columns=6).classes("w-full gap-x-3 items-end"):
                qty = ui.number("Qty", value=_num(work.qty)).props("dense")
                qty_var = ui.select({"": "-", **{n: n for n in var_names}}, label="or bind to variable",
                                    value=work.qty_var or "").props("dense")
                takeoff = ui.number("or takeoff LF (stick goods)", value=_num(work.takeoff)).props("dense")
                stock = ui.select(keep_current({"": "-", **{s.key: s.name for s in cat.stock_classes}}, work.stock_class),
                                  label="Stock class", value=work.stock_class or "").props("dense")
                waste = ui.number("Waste % (blank = default)",
                                  value=_num(work.waste_pct * 100) if work.waste_pct is not None else None) \
                    .props("dense")
                stock_lbl = ui.label().classes("text-xs text-gray-600")

            ui.label("Price").classes("font-semibold text-sm mt-2")
            with ui.grid(columns=6).classes("w-full gap-x-3 items-end"):
                basis = ui.select({p.value: p.value for p in PriceSource}, label="Basis",
                                  value=work.price_basis.value).props("dense")
                rate = ui.select(keep_current({"": "-", **{r.key: f"{r.key} ${r.rate}" for r in cat.rates}}, work.rate_key),
                                 label="Rate", value=work.rate_key or "").props("dense")
                allow = ui.select(keep_current({"": "-", **{a.id: f"{a.category}: {a.description} ({a.unit} {a.low}-{a.high})"
                                                           for a in cat.allowances}}, work.allowance_id),
                                  label="Allowance range", value=work.allowance_id or "").props("dense") \
                    .classes("col-span-2")
                tier = ui.select({t.value: t.value for t in LineTier}, label="Tier", value=work.tier.value) \
                    .props("dense")
                price_shown = work.unit_price * 100 if (work.unit_price is not None and work.is_percent) else work.unit_price
                price = ui.number("Unit price ($, or % for percent)", value=_num(price_shown)).props("dense")
                price_var = ui.select({"": "-", **{n: n for n in var_names}}, label="or bind price to variable",
                                      value=work.price_var or "").props("dense").classes("col-span-2")
                tier_lbl = ui.label().classes("text-xs text-gray-600 col-span-4")

            def sync_price(source: str) -> None:
                b = PriceSource(basis.value)
                if source == "rate" and rate.value:
                    r = cat.rate(rate.value)
                    if r:
                        price.set_value(float(r.rate))
                        basis.set_value(PriceSource.RATE.value)
                if source in ("allow", "tier") and allow.value:
                    a = cat.allowance(allow.value)
                    if a:
                        if source == "allow":
                            work.allowance_low, work.allowance_high = a.low, a.high
                            unit.set_value(a.unit)
                        t = LineTier(tier.value)
                        tier_lbl.set_text(f"low ${work.allowance_low}  mid ${(work.allowance_low + work.allowance_high) / 2:.2f}"
                                          f"  high ${work.allowance_high}")
                        if t is not LineTier.CUSTOM:
                            work.tier = t
                            price.set_value(float(work.tier_price()))
                            if b is not PriceSource.ALLOWANCE:
                                basis.set_value(PriceSource.ALLOWANCE.value)

            rate.on_value_change(lambda _: sync_price("rate"))
            allow.on_value_change(lambda _: sync_price("allow"))
            tier.on_value_change(lambda _: sync_price("tier"))
            if work.allowance_low is not None and work.allowance_high is not None:
                mid = (work.allowance_low + work.allowance_high) / 2
                tier_lbl.set_text(f"low ${work.allowance_low}  mid ${mid:.2f}  high ${work.allowance_high}")

            def upd_stock() -> None:
                from ..calc import stock_round
                sc = cat.stock_classes
                cls = next((s for s in sc if s.key == stock.value), None)
                if takeoff.value and cls:
                    w = Decimal(str(waste.value)) / 100 if waste.value not in (None, "") else self.st.settings.default_waste_pct
                    res = stock_round(Decimal(str(takeoff.value)), w, cls.lengths_ft)
                    stock_lbl.set_text(f"need {res.need:.1f} LF: {res.describe()}")
                    if unit.value != "LF" and any(u.code == "LF" for u in cat.units):
                        unit.set_value("LF")
                else:
                    stock_lbl.set_text("")
            for el in (takeoff, stock, waste):
                el.on_value_change(lambda _: upd_stock())
            upd_stock()

            ui.separator()
            with ui.row().classes("w-full gap-4"):
                is_allow = ui.checkbox("Allowance (prints on proposal)", value=work.is_allowance)
                ni = ui.checkbox("Not included ($0 line)", value=work.not_included)
                of = ui.checkbox("Owner-furnished", value=work.owner_furnished)
                cu = ui.checkbox("Credit if unused", value=work.credit_if_unused)
            with ui.expansion("Internal (never prints)", icon="lock").classes("w-full"):
                with ui.grid(columns=4).classes("w-full gap-x-3"):
                    vnames = vendor_names()
                    vendor = ui.select(vnames + ([work.vendor] if work.vendor and work.vendor not in vnames else []),
                                       value=work.vendor or None, label="Vendor", with_input=True,
                                       new_value_mode="add-unique").props("dense clearable")
                    quote_ref = ui.input("Quote ref", value=work.quote_ref).props("dense")
                    quote_amt = ui.number("Quote amount", value=_num(work.quote_amount)).props("dense")
                internal = ui.textarea("Internal notes", value=work.internal_notes).props("dense autogrow") \
                    .classes("w-full")

            def save() -> None:
                try:
                    b = PriceSource(basis.value)
                    p = to_decimal(price.value)
                    if b is PriceSource.PERCENT and p is not None:
                        p = p / 100
                    new_section = int(section.value)
                    ln_id = ln.id
                    if new_section != ln.section:
                        ln_id = self.new_id(new_section, work.code)
                        for a in rev.alternates:
                            a.removes = [ln_id if x == ln.id else x for x in a.removes]
                    updated = work.model_copy(update=dict(
                        id=ln_id, section=new_section, title=(title.value or "").strip() or ln.title,
                        unit=unit.value, performer=Performer(performer.value),
                        contractor_id=sub_sel.value or None,
                        sub_name=(self.st.contractors.get(sub_sel.value).company if sub_sel.value else ""),
                        alternate=int(alt.value) or None, print_general=print_general.value,
                        notes=notes.value or "",
                        qty=to_decimal(qty.value) if qty.value not in (None, "") else Decimal(0),
                        qty_var=qty_var.value or None,
                        takeoff=to_decimal(takeoff.value), stock_class=stock.value or None,
                        waste_pct=(to_decimal(waste.value) / 100) if waste.value not in (None, "") else None,
                        price_basis=b, unit_price=p, rate_key=rate.value or None,
                        allowance_id=allow.value or None, tier=LineTier(tier.value),
                        price_var=price_var.value or None,
                        is_allowance=is_allow.value, not_included=ni.value, owner_furnished=of.value,
                        credit_if_unused=cu.value, vendor=vendor.value or "", quote_ref=quote_ref.value or "",
                        quote_amount=to_decimal(quote_amt.value), internal_notes=internal.value or "",
                    ))
                    Line.model_validate(updated.model_dump())
                except (ValidationError, ValueError, TypeError) as err:
                    ui.notify(f"Not saved: {err}", type="negative", multi_line=True)
                    return
                idx = rev.lines.index(ln)
                if updated.section != ln.section:
                    if updated.section not in rev.sections:
                        rev.sections.append(updated.section)
                    existing = rev.section_lines(updated.section)
                    updated.order = (existing[-1].order + 10) if existing else 10
                rev.lines[idx] = updated
                dlg.close()
                self.mark_edited(updated.id)
                self.save()

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Close" if self.locked else "Cancel", on_click=dlg.close).props("flat")
                if not self.locked:
                    ui.button("Save", icon="save", on_click=save)
        dlg.open()

    # ------------------------------------------------------------ variables
    def variables_tab(self) -> None:
        ui.label("Proposal variables").classes("font-semibold")
        ui.label("Use {name} in notes and boilerplate, or bind a line's quantity or price to a variable. "
                 "Changing a value here updates every place it is used.").classes("text-xs text-gray-500")

        def save_vars():
            self.save()
            builtin_tbl.refresh()

        EditableGrid(lambda: self.rev.variables,
                     [Col("name", "Name", width=200), Col("value", "Value", flex=1), Col("unit", "Unit", width=90),
                      Col("description", "Description", flex=2)],
                     save_vars, lambda: Variable(name=f"var{len(self.rev.variables) + 1}", value=""), height="32vh",
                     readonly=self.locked)

        @ui.refreshable
        def builtin_tbl() -> None:
            own = {v.name for v in self.rev.variables}
            rows = [{"name": k, "value": v, "source": "proposal" if k in own else
                     ("global" if any(g.name == k for g in self.st.settings.global_variables) else "built-in")}
                    for k, v in sorted(self.variables().items())]
            ui.label("All values in effect").classes("font-semibold mt-4")
            ui.table(columns=[{"name": "name", "label": "Name", "field": "name", "align": "left"},
                              {"name": "value", "label": "Value", "field": "value", "align": "left"},
                              {"name": "source", "label": "Source", "field": "source", "align": "left"}],
                     rows=rows, row_key="name").props("dense flat bordered").classes("w-full")
        builtin_tbl()

    # ------------------------------------------------------------ alternates
    @ui.refreshable_method
    def alternates_panel(self) -> None:
        r = self.results
        ui.label("Alternates").classes("font-semibold")
        ui.label("Each alternate removes base lines, adds its own lines, or both. Add lines here (or set Belongs to "
                 "in any line's form). Totals recompute percent items on each alternate's own subtotal.") \
            .classes("text-xs text-gray-500")
        base_lines = {ln.id: f"{ln.id} {ln.title} ({money(r.lines[ln.id].cost)})"
                      for ln in self._ordered_lines_all() if ln.alternate is None and not ln.is_percent}
        for alt in sorted(self.rev.alternates, key=lambda a: a.number):
            adds = [ln for ln in self.rev.lines if ln.alternate == alt.number]
            sc = r.alternates.get(alt.number)
            with ui.card().classes("w-full").style(f"border-left:6px solid {ALT_COLORS.get(alt.number, '#ccc')}"):
                with ui.row().classes("w-full items-center"):
                    ui.label(f"Alt {alt.number}").classes("text-lg font-semibold")
                    ui.label(alt.kind(bool(adds))).classes("text-xs uppercase text-gray-500")
                    ui.space()
                    if sc:
                        d = r.delta(alt.number)
                        ui.label(f"Subtotal {money(sc.subtotal)}  |  Total {money(sc.total)}  |  "
                                 f"{'+' if d >= 0 else '-'}{money(abs(d))} vs base").classes("text-sm")
                    if not self.locked:
                        ui.button(icon="delete", on_click=lambda a=alt: self._remove_alt(a)) \
                            .props("flat dense round color=negative")
                with ui.grid(columns=3).classes("w-full gap-x-3"):
                    ui.input("Name", value=alt.name).props("dense readonly" if self.locked else "dense") \
                        .on_value_change(lambda e, a=alt: (setattr(a, "name", e.value or ""), self._save_quiet()))
                    ui.input("Description (prints)", value=alt.description).props("dense readonly" if self.locked else "dense").classes("col-span-2") \
                        .on_value_change(lambda e, a=alt: (setattr(a, "description", e.value or ""), self._save_quiet()))
                ui.select(base_lines, multiple=True, value=[x for x in alt.removes if x in base_lines],
                          label="Removes these base lines",
                          on_change=lambda e, a=alt: (setattr(a, "removes", list(e.value or [])), self.save())) \
                    .props("dense use-chips" + (" readonly" if self.locked else "")).classes("w-full")
                with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                    ui.label("Adds:").classes("text-sm")
                    if not adds:
                        ui.label("none").classes("text-sm text-gray-500")
                    for ln in sorted(adds, key=lambda x: (x.section, x.order)):
                        ui.chip(f"{ln.id} {ln.title} ({money(r.lines[ln.id].cost)})", icon="edit",
                                removable=not self.locked, on_click=lambda ln=ln: self.line_dialog(ln)) \
                            .props("outline clickable").on("remove", lambda _, ln=ln: self._delete_alt_line(ln))
                if not self.locked:
                    with ui.row().classes("gap-2"):
                        ui.button("Add from catalog", icon="playlist_add",
                                  on_click=lambda a=alt: self.catalog_picker(alternate=a.number)).props("dense outline")
                        ui.button("Custom line", icon="add",
                                  on_click=lambda a=alt: self.custom_line(alternate=a.number, section=next(
                                      (self.rev.line(x).section for x in a.removes if self.rev.line(x)), None))) \
                            .props("dense outline")
                        ui.button("Copy removed lines", icon="content_copy",
                                  on_click=lambda a=alt: self._copy_removed(a)).props("dense flat") \
                            .tooltip("Start this alternate's version of each removed base line as an editable copy")
                    ui.label("Click a line to edit it; the x deletes it.").classes("text-xs text-gray-500")
        if len(self.rev.alternates) < MAX_ALTERNATES and not self.locked:
            ui.button("Add alternate", icon="add", on_click=self._add_alt).props("outline dense")
        if r.conflicts:
            ui.label("Mutually exclusive (remove the same base line): " +
                     ", ".join(f"Alt {a} / Alt {b}" for a, b in r.conflicts)).classes("text-sm text-orange-700 mt-2")
        if r.combinations:
            ui.label("Combinations").classes("font-semibold mt-3")
            ui.table(columns=[{"name": "n", "label": "Combination", "field": "n", "align": "left"},
                              {"name": "s", "label": "Subtotal", "field": "s", "align": "right"},
                              {"name": "t", "label": "Total", "field": "t", "align": "right"}],
                     rows=[{"n": c.name, "s": money(c.subtotal), "t": money(c.total)} for c in r.combinations],
                     row_key="n").props("dense flat bordered")

    def _copy_removed(self, alt: Alternate) -> None:
        src = [self.rev.line(lid) for lid in alt.removes if self.rev.line(lid)]
        if not src:
            ui.notify("Pick the base lines this alternate removes first.")
            return
        copies = []
        for ln in src:
            c = ln.model_copy(deep=True)
            c.id, c.alternate = self.new_id(ln.section, ln.code), alt.number
            self.rev.add_line(c)
            c.order = ln.order + 5
            copies.append(c)
        self.mark_edited(copies[-1].id)
        self.save()
        ui.notify(f"Copied into Alt {alt.number}: {', '.join(c.id for c in copies)}", type="positive")
        if len(copies) == 1:
            self.line_dialog(copies[0])

    async def _delete_alt_line(self, ln: Line) -> None:
        with self.host, ui.dialog() as dlg, ui.card():
            ui.label(f"Delete line {ln.id} {ln.title} from Alt {ln.alternate}?")
            with ui.row():
                ui.button("Cancel", on_click=lambda: dlg.submit(False)).props("flat")
                ui.button("Delete", on_click=lambda: dlg.submit(True)).props("color=negative")
        if await dlg:
            self.rev.remove_line(ln.id)
            self.save()
        else:
            self.alternates_panel.refresh()      # put the chip back

    def _ordered_lines_all(self) -> list[Line]:
        keep = self.section_filter
        self.section_filter = None
        try:
            return self._ordered_lines()
        finally:
            self.section_filter = keep

    def _save_quiet(self) -> None:
        if not self.locked:
            self.st.projects.save_revision(self.project.number, self.rev)

    def _add_alt(self) -> None:
        used = {a.number for a in self.rev.alternates}
        n = next(i for i in range(1, MAX_ALTERNATES + 1) if i not in used)
        self.rev.alternates.append(Alternate(number=n, name=f"Alternate {n}"))
        self.save()

    async def _remove_alt(self, alt: Alternate) -> None:
        with self.host, ui.dialog() as dlg, ui.card():
            ui.label(f"Delete Alt {alt.number}? Its own lines move back to the base proposal.")
            with ui.row():
                ui.button("Cancel", on_click=lambda: dlg.submit(False)).props("flat")
                ui.button("Delete", on_click=lambda: dlg.submit(True)).props("color=negative")
        if await dlg:
            for ln in self.rev.lines:
                if ln.alternate == alt.number:
                    ln.alternate = None
            self.rev.alternates.remove(alt)
            self.save()

    # ------------------------------------------------------------ issues
    def issues(self) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = [("error", e) for e in self.results.errors]
        v = self.variables()
        if not any(ln.section in self.rev.sections and not ln.is_percent for ln in self.rev.lines):
            out.append(("error", "The proposal has no priced lines"))
        for a, b in self.results.conflicts:
            out.append(("warn", f"Alt {a} and Alt {b} remove the same line; they cannot be combined"))
        from ..crm import insurance_warnings
        from ..proposal import WON_STATUSES
        from .crm_pages import project_contractor_ids
        ins = insurance_warnings(self.st.contractors, project_contractor_ids(self.project, self.rev))
        out += [("warn" if self.project.status in WON_STATUSES else "info", w) for w in ins]
        limit = self.st.settings.license_threshold
        if limit:
            # owner-supplied items count toward the project cost here
            totals = [("Total incl. owner-supplied", self.results.base.total_incl_owner)]
            totals += [(f"Alt {n} incl. owner-supplied", s.total_incl_owner)
                       for n, s in sorted(self.results.alternates.items())]
            totals += [(c.name, c.total_incl_owner) for c in self.results.combinations]
            over = [f"{name} ${t:,.2f}" for name, t in totals if t >= limit]
            if over:
                out.append(("warn", f"At or above the ${limit:,.0f} general contractor license threshold: "
                                    + ", ".join(over)))
        for ln in self.rev.lines:
            lr = self.results.lines[ln.id]
            if not ln.is_percent and not ln.not_included and not ln.owner_furnished and ln.section in self.rev.sections:
                if lr.qty == 0:
                    out.append(("warn", f"{ln.id} {ln.title}: quantity is 0"))
                elif ln.unit_price is None and not ln.price_var:
                    out.append(("warn", f"{ln.id} {ln.title}: no unit price"))
            miss = undefined_references(ln.notes, v)
            if miss:
                out.append(("error", f"{ln.id}: undefined variable(s) {', '.join(sorted(miss))} in notes"))
            d = catalog_differences(ln, self.cat)
            if d:
                out.append(("info", f"{ln.id}: catalog has changed ({', '.join(d)}); open the line to pull"))
            if ln.section not in self.rev.sections:
                out.append(("warn", f"{ln.id}: section {ln.section} is unchecked, line is excluded"))
            if (ln.price_basis is PriceSource.ALLOWANCE and ln.tier is LineTier.CUSTOM
                    and ln.allowance_low is not None and ln.unit_price is not None
                    and not ln.is_percent and not (ln.allowance_low <= ln.unit_price <= ln.allowance_high)):
                out.append(("warn", f"{ln.id}: price {money(ln.unit_price)} is outside its allowance range "
                                    f"{money(ln.allowance_low)} to {money(ln.allowance_high)}"))
        for b in self.rev.blocks:
            if b.on:
                miss = undefined_references(b.body, v)
                if miss:
                    out.append(("error", f"Boilerplate '{b.title or b.id}': undefined {', '.join(sorted(miss))}"))
        for sec in self.rev.sections:
            if not self.rev.section_lines(sec):
                out.append(("warn", f"Section {self.section_name(sec)} is checked but has no lines"))
        used = set()
        for ln in self.rev.lines:
            used |= {ln.qty_var, ln.price_var} - {None}
            used |= referenced(ln.notes)
        for b in self.rev.blocks:
            if b.on:
                used |= referenced(b.body)
        for pv in self.rev.variables:
            if pv.name in used and not pv.value.strip():
                out.append(("warn", f"Variable '{pv.name}' is empty; fill it in on the Variables tab"))
            if pv.name not in used:
                out.append(("info", f"Variable '{pv.name}' is not used anywhere"))
        return out

    @ui.refreshable_method
    def issues_panel(self) -> None:
        items = self.issues()
        if not items:
            ui.label("No issues.").classes("text-green-700")
            return
        icons = {"error": ("error", "text-red-700"), "warn": ("warning", "text-orange-700"),
                 "info": ("info", "text-blue-700")}
        for kind, msg in sorted(items, key=lambda x: ["error", "warn", "info"].index(x[0])):
            icon, cls = icons[kind]
            with ui.row().classes("items-center gap-2"):
                ui.icon(icon).classes(cls)
                ui.label(msg).classes("text-sm")

    # ------------------------------------------------------------ PDF
    def _logo(self) -> Path | None:
        lp = self.st.settings.company.logo_path
        return self.st.store.path(lp) if lp else None

    def _diff(self):
        prev = previous_issued(self.st.projects, self.project.number, self.rev)
        if prev is None:
            return None
        return revision_diff(prev, self.rev, self.st.settings, self.cat.stock_classes, self.project,
                             {s.number: s.name for s in self.cat.sections})

    def _document(self) -> dict:
        return build_document(self.project, self.rev, self.st.settings, self.cat, self.st.boilerplate,
                              self.results, diff=self._diff())

    async def preview(self) -> None:
        errors = [m for k, m in self.issues() if k == "error"]
        n = ui.notification("Rendering preview...", spinner=True, timeout=None)
        try:
            pages = await run.io_bound(compile_document, self._document(), self._logo(), "png", 80)
        except Exception as e:  # noqa: BLE001
            n.dismiss()
            ui.notify(f"Preview failed: {e}", type="negative", multi_line=True)
            return
        n.dismiss()
        with self.host, ui.dialog().props("maximized") as dlg, ui.card().classes("w-full h-full p-0"):
            with ui.row().classes("w-full items-center px-4 py-2").style(f"background:{BRAND};color:white"):
                ui.label(f"Preview: {pdf_filename(self.project, self.rev)}  ({len(pages)} pages)")
                if errors:
                    ui.label(f"{len(errors)} issue(s): see Issues tab").classes("text-orange-200")
                ui.space()
                ui.button("Export PDF", icon="picture_as_pdf",
                          on_click=lambda: (dlg.close(), self.export_pdf())).props("flat color=white")
                ui.button(icon="close", on_click=dlg.close).props("flat round color=white")
            with ui.scroll_area().classes("w-full grow").style("background:#80868b"):
                with ui.column().classes("w-full items-center gap-4 py-4"):
                    for png in pages:
                        ui.image("data:image/png;base64," + base64.b64encode(png).decode()) \
                            .classes("w-[850px] max-w-full shadow-lg bg-white")
        dlg.open()

    async def export_pdf(self, after_issue: bool = False) -> None:
        errors = [m for k, m in self.issues() if k == "error"]
        if errors and not after_issue:
            ui.notify(f"Exporting with {len(errors)} issue(s); see Issues tab.", type="warning")
        n = ui.notification("Building PDF...", spinner=True, timeout=None)
        try:
            pdf = await run.io_bound(compile_document, self._document(), self._logo(), "pdf")
        except Exception as e:  # noqa: BLE001
            n.dismiss()
            ui.notify(f"Export failed: {e}", type="negative", multi_line=True)
            return
        n.dismiss()
        folder = self.st.projects.project_dir(self.project.number) / "pdf"
        folder.mkdir(exist_ok=True)
        path = folder / pdf_filename(self.project, self.rev)
        try:
            path.write_bytes(pdf)
        except PermissionError:
            ui.notify(f"{path.name} is open in another program. Close it and export again.", type="negative")
            if after_issue:
                ui.navigate.to(f"/project/{self.project.number}?rev={self.rev.rev}")
            return
        reload = (lambda: ui.navigate.to(f"/project/{self.project.number}?rev={self.rev.rev}")) if after_issue else None
        with self.host, ui.dialog().props("persistent" if after_issue else "") as dlg, ui.card():
            ui.label(f"Rev {self.rev.rev} issued. PDF saved" if after_issue else "PDF saved") \
                .classes("text-lg font-semibold")
            ui.label(str(path)).classes("text-xs break-all")
            with ui.row():
                if sys.platform == "win32":
                    ui.button("Open PDF", icon="open_in_new", on_click=lambda: os.startfile(path))  # noqa: S606
                    ui.button("Open folder", icon="folder",
                              on_click=lambda: os.startfile(path.parent)).props("outline")  # noqa: S606
                else:
                    ui.button("Download", icon="download", on_click=lambda: ui.download.content(pdf, path.name))
                ui.button("Close", on_click=lambda: (dlg.close(), reload() if reload else None)).props("flat")
        dlg.open()

    # ------------------------------------------------------------ terms & options
    @ui.refreshable_method
    def terms_panel(self) -> None:
        rev, lib = self.rev, self.st.boilerplate
        with ui.card().classes("w-full"):
            ui.label("Document options").classes("font-semibold")
            with ui.row().classes("gap-6"):
                sw1 = ui.switch("Print 'Changes from previous revision' page", value=rev.print_changes,
                                on_change=lambda e: (setattr(rev, "print_changes", e.value), self._save_quiet()))
                sw2 = ui.switch("Print Schedule of Values summary", value=rev.print_sov,
                                on_change=lambda e: (setattr(rev, "print_sov", e.value), self._save_quiet()))
                if self.locked:
                    sw1.disable()
                    sw2.disable()
        ui.label("Terms and text in this proposal. Edits here change only this revision; the library under "
                 "Catalog > Boilerplate is untouched.").classes("text-xs text-gray-500 mt-3")
        headings = list(lib.headings) + sorted({b.heading for b in rev.blocks} - set(lib.headings))
        lib_ids = {b.id: b for b in lib.blocks}
        for heading in headings:
            blocks = sorted((b for b in rev.blocks if b.heading == heading), key=lambda b: b.order)
            missing = [b for b in lib.by_heading(heading) if b.id not in {x.id for x in rev.blocks}]
            on_count = sum(b.on for b in blocks)
            with ui.expansion(f"{heading} ({on_count} of {len(blocks)} on)").classes("w-full border rounded mb-2"):
                for b in blocks:
                    with ui.row().classes("w-full items-start no-wrap gap-3 py-1 border-b"):
                        sw = ui.switch(value=b.on, on_change=lambda e, b=b: self._block_set(b, "on", e.value))
                        if self.locked:
                            sw.disable()
                        with ui.column().classes("flex-1 gap-0"):
                            lb = lib_ids.get(b.id)
                            edited = lb is not None and (lb.body != b.body or lb.title != b.title)
                            ui.label((b.title or f"[{b.id}]") + ("  (edited for this proposal)" if edited else "")) \
                                .classes("font-semibold" + ("" if b.on else " text-gray-400"))
                            ui.label(render(b.body, self.variables())[:240]) \
                                .classes("text-xs text-gray-600 whitespace-pre-line")
                        if not self.locked:
                            ui.button(icon="arrow_upward", on_click=lambda b=b: self._block_move(b, -1)) \
                                .props("flat dense round")
                            ui.button(icon="arrow_downward", on_click=lambda b=b: self._block_move(b, 1)) \
                                .props("flat dense round")
                        ui.button(icon="visibility" if self.locked else "edit",
                                  on_click=lambda b=b: self._block_dialog(b, b.heading)).props("flat dense round")
                        if not self.locked:
                            ui.button(icon="delete", on_click=lambda b=b: self._block_remove(b)) \
                                .props("flat dense round color=negative")
                if not self.locked:
                    with ui.row().classes("gap-2 mt-1"):
                        ui.button("Custom block", icon="add",
                                  on_click=lambda h=heading: self._block_dialog(None, h)).props("flat dense")
                        if missing:
                            ui.select({b.id: b.title or b.id for b in missing}, label="Add from library",
                                      on_change=lambda e: self._block_add_library(e.value)) \
                                .props("dense outlined").classes("w-72")

    def _block_set(self, b: ProposalBlock, field: str, value) -> None:
        setattr(b, field, value)
        self.save(refresh_grid=False)
        self.terms_panel.refresh()

    def _block_move(self, b: ProposalBlock, d: int) -> None:
        sib = sorted((x for x in self.rev.blocks if x.heading == b.heading), key=lambda x: x.order)
        for n, x in enumerate(sib):
            x.order = (n + 1) * 10
        i = sib.index(b)
        j = i + d
        if 0 <= j < len(sib):
            sib[i].order, sib[j].order = sib[j].order, sib[i].order
            self.save(refresh_grid=False)
            self.terms_panel.refresh()

    def _block_remove(self, b: ProposalBlock) -> None:
        self.rev.blocks.remove(b)
        self.save(refresh_grid=False)
        self.terms_panel.refresh()

    def _block_add_library(self, block_id: str | None) -> None:
        lb = next((b for b in self.st.boilerplate.blocks if b.id == block_id), None)
        if lb is None:
            return
        order = max((b.order for b in self.rev.blocks if b.heading == lb.heading), default=0) + 10
        self.rev.blocks.append(ProposalBlock(id=lb.id, heading=lb.heading, title=lb.title, body=lb.body,
                                             on=True, order=order))
        self.save(refresh_grid=False)
        self.terms_panel.refresh()

    def _block_dialog(self, b: ProposalBlock | None, heading: str) -> None:
        lib = next((x for x in self.st.boilerplate.blocks if b is not None and x.id == b.id), None)
        with self.host, ui.dialog() as dlg, ui.card().classes("w-[920px] max-w-full"):
            ui.label(f"{heading}: {b.title if b else 'new block'}").classes("text-lg font-semibold")
            title = ui.input("Sub-heading", value=b.title if b else "").props(
                "dense readonly" if self.locked else "dense").classes("w-full")
            with ui.row().classes("w-full no-wrap gap-4"):
                body = ui.textarea(value=b.body if b else "").props(
                    "outlined autogrow" + (" readonly" if self.locked else "")).classes("w-1/2 font-mono text-sm")
                preview = ui.markdown().classes("w-1/2 border rounded p-2 text-sm")
            upd = lambda: preview.set_content(md_breaks(render(body.value or "", self.variables())))  # noqa: E731
            body.on_value_change(lambda _: upd())
            upd()

            def save() -> None:
                if b is None:
                    order = max((x.order for x in self.rev.blocks if x.heading == heading), default=0) + 10
                    bid, n = f"custom-{order}", 2
                    while any(x.id == bid for x in self.rev.blocks):
                        bid, n = f"custom-{order}-{n}", n + 1
                    self.rev.blocks.append(ProposalBlock(id=bid, heading=heading, title=title.value or "",
                                                         body=body.value or "", on=True, order=order))
                else:
                    b.title, b.body = title.value or "", body.value or ""
                dlg.close()
                self.save(refresh_grid=False)
                self.terms_panel.refresh()

            with ui.row().classes("w-full justify-end gap-2"):
                if lib is not None and not self.locked:
                    ui.button("Reset to library text",
                              on_click=lambda: (title.set_value(lib.title), body.set_value(lib.body))).props("flat")
                ui.button("Close" if self.locked else "Cancel", on_click=dlg.close).props("flat")
                if not self.locked:
                    ui.button("Save", icon="save", on_click=save)
        dlg.open()

    # ------------------------------------------------------------ revisions
    async def issue_dialog(self) -> None:
        items = self.issues()
        errors = [m for k, m in items if k == "error"]
        warns = [m for k, m in items if k == "warn"]
        diff = self._diff()
        contract = self.rev.is_contract
        with self.host, ui.dialog() as dlg, ui.card().classes("w-[720px] max-w-full"):
            ui.label(f"Issue Rev {self.rev.rev}" + (" (final, for signature)" if contract else "")) \
                .classes("text-lg font-semibold")
            ui.label("Issuing locks this revision, supersedes earlier ones and saves the PDF to the project's "
                     "pdf folder. Later changes need a new revision.").classes("text-sm")
            if diff is not None:
                d = diff.total_change
                ui.label(f"Compared with Rev {diff.old_rev}: {len(diff.changes)} line change(s), "
                         f"total {'+' if d >= 0 else '-'}{money(abs(d))} ({money(diff.old_total)} to "
                         f"{money(diff.new_total)}).").classes("text-sm")
            ui.label(f"Total Price: {money(self.results.base.total)}").classes("text-sm font-semibold")
            for m in errors:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("error").classes("text-red-700")
                    ui.label(m).classes("text-sm")
            for m in warns:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("warning").classes("text-orange-700")
                    ui.label(m).classes("text-sm")
            if not errors and not warns:
                ui.label("No issues found.").classes("text-sm text-green-700")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=lambda: dlg.submit(False)).props("flat")
                ui.button("Issue anyway" if errors else "Issue and save PDF", icon="lock",
                          on_click=lambda: dlg.submit(True)).props("color=negative" if errors else "")
        if not await dlg:
            return
        try:
            issue(self.st.projects, self.project, self.rev)
        except (RevisionError, PermissionError) as e:
            ui.notify(str(e), type="negative")
            return
        await self.export_pdf(after_issue=True)

    def new_revision(self) -> None:
        try:
            rev = create_revision(self.st.projects, self.project)
        except RevisionError as e:
            ui.notify(str(e), type="warning")
            return
        ui.navigate.to(f"/project/{self.project.number}?rev={rev.rev}")

    async def accept_dialog(self) -> None:
        from ..proposal import contract_revision
        alts = sorted(self.rev.alternates, key=lambda a: a.number)
        chosen: dict[int, bool] = {a.number: False for a in alts}
        with self.host, ui.dialog() as dlg, ui.card().classes("w-[620px] max-w-full"):
            ui.label(f"Finalize Rev {self.rev.rev}").classes("text-lg font-semibold")
            ui.label("Creates Rev 2.0, the final revision for signature. It is base only: the alternates the "
                     "client chose are merged into the base and the rest are dropped. Review it, issue it, "
                     "then Mark accepted once it is signed.").classes("text-sm")
            result = ui.label().classes("text-sm font-semibold")

            def update() -> None:
                sel = [n for n, v in chosen.items() if v]
                try:
                    preview = contract_revision(self.rev, sel)
                except ValueError as e:
                    result.set_text(str(e))
                    result.classes(replace="text-sm font-semibold text-red-700")
                    return
                total = calculate(preview, self.st.settings, self.cat.stock_classes, self.project).base.total
                result.set_text(f"Final total: {money(total)}")
                result.classes(replace="text-sm font-semibold")

            for a in alts:
                ui.checkbox(f"Alt {a.number}: {a.name}  ({money(self.results.alternates[a.number].total)} alone)",
                            on_change=lambda e, n=a.number: (chosen.__setitem__(n, e.value), update()))
            if not alts:
                ui.label("No alternates; the base proposal becomes the contract.").classes("text-sm")
            update()
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=lambda: dlg.submit(None)).props("flat")
                ui.button("Create Rev 2.0", icon="handshake",
                          on_click=lambda: dlg.submit([n for n, v in chosen.items() if v])).props("color=positive")
        sel = await dlg
        if sel is None:
            return
        try:
            rev = finalize(self.st.projects, self.project, sel)
        except RevisionError as e:
            ui.notify(str(e), type="negative")
            return
        ui.navigate.to(f"/project/{self.project.number}?rev={rev.rev}")

    async def mark_accepted_dialog(self) -> None:
        with self.host, ui.dialog() as dlg, ui.card():
            ui.label(f"Mark Rev {self.rev.rev} accepted?").classes("text-lg font-semibold")
            ui.label("Use this once the client has signed. The project status becomes Accepted and later "
                     "scope changes go through change orders.").classes("text-sm")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dlg.submit(False)).props("flat")
                ui.button("Mark accepted", icon="handshake", on_click=lambda: dlg.submit(True)) \
                    .props("color=positive")
        if not await dlg:
            return
        try:
            mark_accepted(self.st.projects, self.project, self.rev)
        except RevisionError as e:
            ui.notify(str(e), type="negative")
            return
        ui.navigate.to(f"/project/{self.project.number}?rev={self.rev.rev}")

    # ------------------------------------------------------------ project info
    def project_dialog(self) -> None:
        p, rev = self.project, self.rev
        with self.host, ui.dialog() as dlg, ui.card().classes("w-[520px]"):
            ui.label("Project info").classes("text-lg font-semibold")
            from .crm_pages import CustomerPicker
            picker = CustomerPicker(p.customer_id, p.site_address_id)
            name = ui.input("Project", value=p.project_name).props("dense").classes("w-full")
            with ui.input("Proposal date", value=rev.proposal_date.isoformat()).props("dense") as d:
                with ui.menu().props("no-parent-event") as menu:
                    ui.date().bind_value(d)
                with d.add_slot("append"):
                    ui.icon("edit_calendar").on("click", menu.open).classes("cursor-pointer")

            def save() -> None:
                try:
                    if not picker.apply(p):
                        return
                    p.project_name = name.value or p.project_name
                    if not self.locked:
                        rev.proposal_date = date.fromisoformat(d.value)
                except ValueError as e:
                    ui.notify(str(e), type="negative")
                    return
                self.save_project()
                dlg.close()
                if not self.locked:
                    self.save()

            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=dlg.close).props("flat")
                ui.button("Save", icon="save", on_click=save)
        dlg.open()


@ui.page("/project/{number}")
def editor_page(number: str, rev: str | None = None) -> None:
    try:
        ed = Editor(number, rev)
    except FileNotFoundError as e:
        layout("Project")
        ui.label(str(e)).classes("text-red-700")
        return
    ed.build()
