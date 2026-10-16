"""Change orders, actual costs, payments and the final project ledger (milestone 5)."""

from __future__ import annotations

import base64
import os
import sys
from datetime import date
from decimal import Decimal

from nicegui import run, ui
from pydantic import ValidationError

from ..closeout import (
    ActualCost,
    ChangeOrder,
    ChangeOrderLog,
    COAction,
    COFunding,
    COItem,
    COStatus,
    PaidBy,
    Payment,
    Reconciliation,
    accepted_revision,
    build_ledger,
    contract_context,
    price_change_orders,
)
from ..render.closeout_docs import change_order_document, ledger_document, safe_name
from ..render.document import compile_document
from .state import get_state
from .widgets import BRAND, Col, EditableGrid, layout

ZERO = Decimal(0)


def money(v: Decimal | None) -> str:
    if v is None:
        return ""
    return f"-${abs(v):,.2f}" if v < 0 else f"${v:,.2f}"


class Closeout:
    def __init__(self, number: str):
        self.st = get_state()
        ps = self.st.projects
        self.project = ps.load_project(number)
        revs = [ps.load_revision(number, r) for r in ps.list_revisions(number)]
        self.rev = accepted_revision(revs)
        self.log: ChangeOrderLog = ps.load_change_orders(number)
        self.recon: Reconciliation = ps.load_reconciliation(number)
        self.contract = None
        if self.rev is not None:
            self.contract = contract_context(self.rev, self.st.settings, self.st.catalog.stock_classes, self.project)
        self.ledger = self._ledger()

    # ------------------------------------------------------------ plumbing
    def _ledger(self):
        return build_ledger(self.contract, self.log, self.recon) if self.contract else None

    def save(self) -> None:
        ps = self.st.projects
        ps.save_change_orders(self.project.number, self.log)
        ps.save_reconciliation(self.project.number, self.recon)
        self.ledger = self._ledger()
        self.tiles.refresh()
        self.co_list.refresh()
        self.line_summary.refresh()
        self.ledger_panel.refresh()

    def _logo(self):
        lp = self.st.settings.company.logo_path
        return self.st.store.path(lp) if lp else None

    def _pdf_dir(self):
        d = self.st.projects.project_dir(self.project.number) / "pdf"
        d.mkdir(exist_ok=True)
        return d

    async def _export(self, doc: dict, template: str, name: str) -> None:
        n = ui.notification("Building PDF...", spinner=True, timeout=None)
        try:
            pdf = await run.io_bound(compile_document, doc, self._logo(), "pdf", 110, template)
        except Exception as e:  # noqa: BLE001
            n.dismiss()
            ui.notify(f"PDF failed: {e}", type="negative", multi_line=True)
            return
        n.dismiss()
        path = self._pdf_dir() / name
        try:
            path.write_bytes(pdf)
        except PermissionError:
            ui.notify(f"{name} is open in another program. Close it and try again.", type="negative")
            return
        with ui.dialog() as dlg, ui.card():
            ui.label("PDF saved").classes("text-lg font-semibold")
            ui.label(str(path)).classes("text-xs break-all")
            with ui.row():
                if sys.platform == "win32":
                    ui.button("Open PDF", icon="open_in_new", on_click=lambda: os.startfile(path))  # noqa: S606
                else:
                    ui.button("Download", icon="download", on_click=lambda: ui.download.content(pdf, name))
                ui.button("Close", on_click=dlg.close).props("flat")
        dlg.open()

    async def _preview(self, doc: dict, template: str, title: str) -> None:
        n = ui.notification("Rendering preview...", spinner=True, timeout=None)
        try:
            pages = await run.io_bound(compile_document, doc, self._logo(), "png", 80, template)
        except Exception as e:  # noqa: BLE001
            n.dismiss()
            ui.notify(f"Preview failed: {e}", type="negative", multi_line=True)
            return
        n.dismiss()
        with ui.dialog().props("maximized") as dlg, ui.card().classes("w-full h-full p-0"):
            with ui.row().classes("w-full items-center px-4 py-2").style(f"background:{BRAND};color:white"):
                ui.label(title)
                ui.space()
                ui.button(icon="close", on_click=dlg.close).props("flat round color=white")
            with ui.scroll_area().classes("w-full grow").style("background:#80868b"):
                with ui.column().classes("w-full items-center gap-4 py-4"):
                    for png in pages:
                        ui.image("data:image/png;base64," + base64.b64encode(png).decode()) \
                            .classes("w-[850px] max-w-full shadow-lg bg-white")
        dlg.open()

    # ------------------------------------------------------------ page
    def build(self) -> None:
        p = self.project
        layout(f"{p.number} change orders & ledger", drawer=False)
        with ui.row().classes("w-full items-center gap-4"):
            ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to(f"/project/{p.number}")) \
                .props("flat round dense")
            with ui.column().classes("gap-0"):
                ui.label(f"{p.number}  {p.project_name}: change orders & ledger").classes("text-xl font-semibold")
                ui.label("  |  ".join(x for x in (p.client_name, p.site_address) if x)).classes("text-sm text-gray-600")
        if self.contract is None:
            with ui.card().classes("mt-4"):
                ui.label("No accepted revision yet.").classes("font-semibold")
                ui.label("Change orders and the ledger work from the accepted contract. In the proposal editor: "
                         "issue the final revision (Finalize, then issue 2.0) and use Mark accepted once the client "
                         "signs.").classes("text-sm")
            return
        self.tiles()
        with ui.tabs().props("dense inline-label align=left").classes("w-full border-b") as tabs:
            t_co = ui.tab("Change orders", icon="change_circle")
            t_act = ui.tab("Actual costs", icon="receipt_long")
            t_pay = ui.tab("Payments", icon="payments")
            t_led = ui.tab("Ledger", icon="balance")
        with ui.tab_panels(tabs, value=t_co).classes("w-full"):
            with ui.tab_panel(t_co):
                self.co_tab()
            with ui.tab_panel(t_act):
                self.actuals_tab()
            with ui.tab_panel(t_pay):
                self.payments_tab()
            with ui.tab_panel(t_led):
                self.ledger_panel()

    @ui.refreshable_method
    def tiles(self) -> None:
        lg, c = self.ledger, self.contract
        with ui.row().classes("w-full gap-3 my-2"):
            def tile(label, value, sub="", color=BRAND):
                with ui.card().classes("px-4 py-2 gap-0"):
                    ui.label(label).classes("text-xs uppercase text-gray-500")
                    ui.label(value).classes("text-lg font-semibold").style(f"color:{color}")
                    if sub:
                        ui.label(sub).classes("text-xs text-gray-500")
            tile("Contract", money(c.total), f"Rev {c.rev.rev}")
            tile("Change orders billed", money(lg.co_billed), f"{len(lg.approved)} approved")
            tile("Contingency left", money(lg.unused_contingency), f"of {money(c.contingency)}")
            tile("CO management left", money(lg.co_management_credit), f"of {money(c.co_management)}")
            tile("Line variance", money(lg.net_variance + lg.variance_markup), "incl. overhead and profit")
            tile("Final cost", money(lg.total_final))
            tile("Balance due", money(lg.balance_due), f"after {money(lg.payments_received)} received",
                 color="#B00020" if lg.balance_due > 0 else "#1B5E20")
            if lg.warnings:
                tile("Warnings", str(len(lg.warnings)), "see Ledger tab", color="#B26A00")

    # ------------------------------------------------------------ change orders
    def co_tab(self) -> None:
        with ui.row().classes("gap-2 items-center mb-2"):
            ui.button("New change order", icon="add", on_click=self.new_co).props("dense")
            ui.label(f"Price = direct cost change x (1 + {self.contract.markup_pct * 100:.0f}% overhead and profit). "
                     "Contingency-funded orders draw contingency at price; any overflow is billed. "
                     f"Management hours are drawn from the change order management allowance at "
                     f"{money(self.contract.mgmt_rate)}/HR; time beyond it is billed at that rate. "
                     "Only approved orders count in the ledger.").classes("text-xs text-gray-500")
        self.co_list()

    @ui.refreshable_method
    def co_list(self) -> None:
        pricing = price_change_orders(self.log, self.contract)
        if not self.log.orders:
            ui.label("No change orders yet.").classes("text-sm text-gray-600")
            return
        rows = []
        for o in sorted(self.log.orders, key=lambda o: o.number):
            pr = pricing[o.number]
            rows.append({"number": o.number, "title": o.title, "status": o.status.value, "funding": o.funding.value,
                         "requested": o.requested.isoformat(), "delta": money(pr.cost_delta), "price": money(pr.price),
                         "mgmt": f"{o.mgmt_hours.normalize():f} HR" if o.mgmt_hours else "",
                         "contingency": money(pr.from_contingency), "billed": money(pr.billed)})
        g = ui.aggrid({
            "columnDefs": [{"field": "number", "headerName": "CO #", "width": 110},
                           {"field": "title", "headerName": "Title", "flex": 1},
                           {"field": "status", "headerName": "Status", "width": 100},
                           {"field": "funding", "headerName": "Funding", "width": 170},
                           {"field": "requested", "headerName": "Requested", "width": 110},
                           {"field": "delta", "headerName": "Cost change", "width": 120, "type": "rightAligned"},
                           {"field": "price", "headerName": "Price", "width": 110, "type": "rightAligned"},
                           {"field": "contingency", "headerName": "From contingency", "width": 140, "type": "rightAligned"},
                           {"field": "mgmt", "headerName": "Mgmt time", "width": 100, "type": "rightAligned"},
                           {"field": "billed", "headerName": "Billed", "width": 110, "type": "rightAligned"}],
            "rowData": rows, "rowHeight": 32, "headerHeight": 36,
        }, auto_size_columns=False).classes("w-full").style("height:50vh")
        g.on("cellDoubleClicked", lambda e: self.co_dialog(self.log.get(e.args["data"]["number"])))
        ui.label("Double-click a change order to open it.").classes("text-xs text-gray-500")

    def new_co(self) -> None:
        co = ChangeOrder(number=self.log.next_number(self.project.number),
                         recommended_by=self.st.settings.recommended_by, items=[COItem()])
        self.log.orders.append(co)
        self.save()
        self.co_dialog(co)

    def co_dialog(self, co: ChangeOrder | None) -> None:
        if co is None:
            return
        locked = co.locked
        line_ids = [ln.id for ln in self.rev.lines]
        work = co.model_copy(deep=True)
        ro = "dense readonly" if locked else "dense"
        with ui.dialog() as dlg, ui.card().classes("w-[1100px] max-w-full"):
            with ui.row().classes("w-full items-center"):
                ui.label(f"Change order {co.number}").classes("text-lg font-semibold")
                ui.badge(co.status.value, color={"Draft": "grey-7", "Issued": "blue-8", "Approved": "green-8",
                                                  "Rejected": "red-8"}[co.status.value])
                ui.space()
                price_lbl = ui.label().classes("text-sm font-semibold")
            with ui.grid(columns=4).classes("w-full gap-x-3"):
                title = ui.input("Title", value=work.title).props(ro).classes("col-span-2")
                requested = ui.input("Requested date (YYYY-MM-DD)", value=work.requested.isoformat()).props(ro)
                funding = ui.select({f.value: f.value for f in COFunding}, label="Funding",
                                    value=work.funding.value).props(ro)
                hours = ui.number("Management hours (scoping, pricing, paperwork)",
                                  value=float(work.mgmt_hours) if work.mgmt_hours else None).props(ro)
            ui.label("Itemized changes at direct cost (no management time; log that as hours above). "
                     "Lines: proposal line IDs this change touches, comma separated.") \
                .classes("text-xs text-gray-500")

            def recompute() -> None:
                try:
                    tmp = self.log.model_copy(deep=True)
                    i = next(n for n, o in enumerate(tmp.orders) if o.number == co.number)
                    hrs = Decimal(str(hours.value)) if hours.value not in (None, "") else ZERO
                    tmp.orders[i] = work.model_copy(update={"funding": COFunding(funding.value), "mgmt_hours": hrs})
                    pr = price_change_orders(tmp, self.contract, include=(COStatus.APPROVED,))[co.number]
                except (ValidationError, ValueError, StopIteration):
                    return
                txt = f"Cost {money(pr.cost_delta)}  |  price {money(pr.price)}"
                if funding.value == COFunding.CONTINGENCY.value:
                    txt += f"  |  from contingency {money(pr.from_contingency)}"
                if pr.mgmt_hours:
                    txt += f"  |  mgmt {money(pr.mgmt_cost)} ({money(pr.mgmt_from_allowance)} from allowance)"
                txt += f"  |  billed {money(pr.billed)}"
                price_lbl.set_text(txt)
                bad = sorted({lid for it in work.items for lid in it.line_ids if lid not in line_ids})
                lines_warn.set_text(f"Unknown line IDs: {', '.join(bad)}" if bad else "")

            EditableGrid(lambda: work.items,
                         [Col("description", "Description (condition)", flex=2),
                          Col("action", "Action", "select", [a.value for a in COAction], width=100),
                          Col("change", "Change", flex=2),
                          Col("line_ids", "Lines", "strlist", width=110),
                          Col("original_cost", "Original cost", "number", width=120),
                          Col("final_cost", "Final cost", "number", width=110)],
                         lambda: recompute(), lambda: COItem(), height="22vh", readonly=locked)
            lines_warn = ui.label().classes("text-xs text-orange-700")
            funding.on_value_change(lambda _: recompute())
            hours.on_value_change(lambda _: recompute())
            with ui.grid(columns=3).classes("w-full gap-x-3"):
                sow = ui.textarea("SOW modifications", value=work.sow).props(ro + " autogrow")
                pay = ui.textarea("Payment impacts", value=work.payment_impacts).props(ro + " autogrow")
                sched = ui.textarea("Schedule impacts", value=work.schedule_impacts).props(ro + " autogrow")
                rec = ui.input("Recommended by", value=work.recommended_by).props(ro)
                appr = ui.input("Accepted and approved by", value=work.approved_by).props(ro)
            recompute()

            def collect() -> bool:
                try:
                    work.title = title.value or ""
                    work.requested = date.fromisoformat(requested.value.strip())
                    work.funding = COFunding(funding.value)
                    work.mgmt_hours = Decimal(str(hours.value)) if hours.value not in (None, "") else ZERO
                    work.sow, work.payment_impacts = sow.value or "", pay.value or ""
                    work.schedule_impacts = sched.value or ""
                    work.recommended_by, work.approved_by = rec.value or "", appr.value or ""
                except (ValidationError, ValueError) as e:
                    ui.notify(f"Not saved: {e}", type="negative")
                    return False
                return True

            def commit() -> None:
                i = self.log.orders.index(co)
                self.log.orders[i] = work
                self.save()

            def save() -> None:
                if collect():
                    commit()
                    dlg.close()

            def set_status(status: COStatus) -> None:
                if not collect():
                    return
                work.status = status
                if status is COStatus.APPROVED:
                    work.approved = date.today()
                commit()
                dlg.close()
                ui.notify(f"{co.number} {status.value.lower()}", type="positive")

            def delete() -> None:
                self.log.orders.remove(co)
                self.save()
                dlg.close()

            def doc() -> dict:
                collect()
                tmp = self.log.model_copy(deep=True)
                tmp.orders[[o.number for o in tmp.orders].index(co.number)] = work
                pr = price_change_orders(tmp, self.contract)[co.number]
                return change_order_document(self.project, self.contract, work, pr, self.st.settings)

            with ui.row().classes("w-full justify-end gap-2"):
                if not locked and co.status is COStatus.DRAFT:
                    ui.button("Delete", icon="delete", on_click=delete).props("flat color=negative")
                ui.button("Preview", icon="visibility",
                          on_click=lambda: self._preview(doc(), "co.typ", f"Change order {co.number}")) \
                    .props("outline")
                ui.button("Export PDF", icon="picture_as_pdf",
                          on_click=lambda: self._export(doc(), "co.typ",
                                                        safe_name(f"{co.number}_Change_Order.pdf"))).props("outline")
                ui.space()
                ui.button("Close" if locked else "Cancel", on_click=dlg.close).props("flat")
                if not locked:
                    if co.status is COStatus.DRAFT:
                        ui.button("Mark issued", on_click=lambda: set_status(COStatus.ISSUED)).props("outline")
                    ui.button("Reject", on_click=lambda: set_status(COStatus.REJECTED)).props("outline color=negative")
                    ui.button("Approve", icon="check", on_click=lambda: set_status(COStatus.APPROVED)) \
                        .props("color=positive")
                    ui.button("Save", icon="save", on_click=save)
        dlg.open()

    # ------------------------------------------------------------ actual costs
    def _contract_lines(self):
        return [ln for ln in self.rev.lines
                if not ln.is_percent and ln.section in self.rev.sections and ln.alternate is None]

    def actuals_tab(self) -> None:
        ui.label("Enter costs as they come in. Hourly lines can take hours instead of an amount (hours x the line "
                 "rate). Tick Unused to credit a line in full. Lines without actuals stay at their contract amount.") \
            .classes("text-xs text-gray-500")
        self.line_summary()
        ui.label("Cost entries").classes("font-semibold mt-3")
        ids = [ln.id for ln in self._contract_lines()]

        def new_entry() -> ActualCost:
            return ActualCost(line_id=ids[0], date=date.today())

        EditableGrid(lambda: self.recon.actuals,
                     [Col("line_id", "Line", "select", ids, width=90),
                      Col("date", "Date", "date", width=120),
                      Col("vendor", "Vendor / sub", width=180),
                      Col("description", "Description", flex=1),
                      Col("hours", "Hours", "number", width=90),
                      Col("amount", "Amount", "number", width=120),
                      Col("tax", "Tax", "number", width=90),
                      Col("paid_by", "Paid by", "select", [p.value for p in PaidBy], width=140)],
                     lambda: self.save(), new_entry, height="34vh")

    @ui.refreshable_method
    def line_summary(self) -> None:
        lg = self.ledger
        rows = []
        for lr in lg.lines:
            rows.append({"id": lr.line.id, "title": lr.line.title, "unit": lr.line.unit,
                         "budget": money(lr.budget), "actual": money(lr.actual) if lr.actual is not None else "",
                         "variance": money(lr.variance) if (lr.actual is not None or lr.unused) else "",
                         "client": money(lr.client_paid) if lr.client_paid else "", "unused": lr.unused,
                         "credit": "yes" if lr.line.credit_if_unused else ""})
        g = ui.aggrid({
            "columnDefs": [{"field": "id", "headerName": "Line", "width": 80},
                           {"field": "title", "headerName": "Item", "flex": 1},
                           {"field": "unit", "headerName": "Unit", "width": 70},
                           {"field": "budget", "headerName": "Budget", "width": 120, "type": "rightAligned"},
                           {"field": "actual", "headerName": "Actual", "width": 120, "type": "rightAligned"},
                           {"field": "variance", "headerName": "Variance", "width": 120, "type": "rightAligned"},
                           {"field": "client", "headerName": "Client paid", "width": 120, "type": "rightAligned"},
                           {"field": "credit", "headerName": "Credit if unused", "width": 130},
                           {"field": "unused", "headerName": "Unused", "width": 90, "editable": True,
                            "cellDataType": "boolean"}],
            "rowData": rows, "rowHeight": 30, "headerHeight": 34,
        }, auto_size_columns=False).classes("w-full").style("height:34vh")

        def changed(e) -> None:
            lid, val = e.args["data"]["id"], bool(e.args.get("newValue"))
            s = set(self.recon.unused_lines)
            (s.add if val else s.discard)(lid)
            self.recon.unused_lines = sorted(s, key=lambda x: tuple(int(p) for p in x.split(".")))
            self.save()
        g.on("cellValueChanged", changed)

    # ------------------------------------------------------------ payments
    def payments_tab(self) -> None:
        ui.label("Payments received by Kept Spec (draws). Invoicing itself happens in the other app.") \
            .classes("text-xs text-gray-500")
        EditableGrid(lambda: self.recon.payments,
                     [Col("draw", "Draw", width=120), Col("milestone", "Milestone", flex=1),
                      Col("date", "Date received", "date", width=140), Col("amount", "Amount", "number", width=140)],
                     lambda: self.save(),
                     lambda: Payment(draw=f"Draw {len(self.recon.payments) + 1}", date=date.today()), height="40vh")

    # ------------------------------------------------------------ ledger
    @ui.refreshable_method
    def ledger_panel(self) -> None:
        lg, c = self.ledger, self.contract
        with ui.row().classes("gap-2 mb-2"):
            ui.button("Preview ledger", icon="visibility",
                      on_click=lambda: self._preview(self._ledger_doc(), "ledger.typ", "Final project ledger")) \
                .props("outline dense")
            ui.button("Export ledger PDF", icon="picture_as_pdf",
                      on_click=lambda: self._export(self._ledger_doc(), "ledger.typ",
                                                    safe_name(f"{self.project.number}_Final_Project_Ledger.pdf"))) \
                .props("dense")
        for w in lg.warnings:
            with ui.row().classes("items-center gap-2"):
                ui.icon("warning").classes("text-orange-700")
                ui.label(w).classes("text-sm")
        rows = [("Original contract value", c.total), ("Plus: change orders billed", lg.co_billed),
                ("Plus: net line variance", lg.net_variance),
                ("Plus: overhead and profit on variance", lg.variance_markup),
                ("Less: unused contingency", -lg.unused_contingency)]
        rows.append(("Less: unused change order management", -lg.co_management_credit))
        rows += [("Total final project cost", lg.total_final),
                 ("Less: paid by the client directly", -lg.client_direct),
                 ("Less: payments received", -lg.payments_received),
                 ("Balance due" if lg.balance_due >= 0 else "Credit due to client", abs(lg.balance_due))]
        with ui.card().classes("w-[620px]"):
            for label, v in rows:
                bold = label.startswith(("Total", "Balance", "Credit"))
                with ui.row().classes("w-full justify-between border-b py-1"):
                    ui.label(label).classes("text-sm" + (" font-semibold" if bold else ""))
                    ui.label(money(v)).classes("text-sm" + (" font-semibold" if bold else ""))
        ui.textarea("Ledger note (prints at the end)", value=self.recon.note,
                    on_change=lambda e: (setattr(self.recon, "note", e.value or ""), self._save_quiet())) \
            .props("outlined autogrow").classes("w-[620px] mt-3")

    def _save_quiet(self) -> None:
        self.st.projects.save_reconciliation(self.project.number, self.recon)

    def _ledger_doc(self) -> dict:
        return ledger_document(self.project, self.ledger, self.recon, self.st.settings)


@ui.page("/project/{number}/closeout")
def closeout_page(number: str) -> None:
    try:
        Closeout(number).build()
    except FileNotFoundError as e:
        layout("Project")
        ui.label(str(e)).classes("text-red-700")

