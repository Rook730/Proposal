"""Projects list, new project, import from Excel."""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import openpyxl
from nicegui import ui

from ..calc import calculate
from ..calc import DOCUMENT_VARIABLES, SPECIAL_PLACEHOLDERS, referenced, variable_map
from ..models import KS, PROFILE_SHORT, PROFILES, PriceSource, Variable
from ..proposal import WON_STATUSES, Project, ProjectStatus, Revision, default_blocks, line_from_item
from .state import get_state
from .widgets import filter_box, layout, no_rows, page_title, toolbar


def _project_rows(show_archived: bool = False, company: str = "") -> list[dict]:
    st = get_state()
    rows = []
    for p in st.projects.list_projects():
        if p.archived_on and not show_archived:
            continue
        if company and p.profile != company:
            continue
        revs = st.projects.list_revisions(p.number)
        total, state = "", ""
        try:
            rev = st.projects.load_revision(p.number)
            state = rev.state.value
            res = calculate(rev, st.settings_for(p.profile), st.catalog.stock_classes, p)
            total = f"${res.base.total:,.2f}"
        except Exception:  # noqa: BLE001 - list must render even if one file is bad
            pass
        rows.append({"number": p.number, "company": PROFILE_SHORT.get(p.profile, p.profile),
                     "client": p.client_name, "project": p.project_name,
                     "address": p.site_address,
                     "status": p.status.value + (" (archived)" if p.archived_on else ""),
                     "rev": f"{revs[-1]} {state}" if revs else "", "total": total})
    return rows


def new_project_dialog() -> None:
    st = get_state()
    s = st.settings
    projects = st.projects.list_projects()
    with ui.dialog() as dlg, ui.card().classes("w-[520px]"):
        ui.label("New project").classes("text-lg font-semibold")
        company = ui.toggle(dict(PROFILES), value=None).props("dense no-caps")
        ui.label("Which company is this proposal from? It cannot be changed later.").classes("text-xs text-gray-500")
        number = ui.input("Proposal #", value=s.next_proposal_number()).props("dense")
        from .crm_pages import CustomerPicker
        picker = CustomerPicker()
        name = ui.input("Project (e.g. Kitchen Renovation)").props("dense").classes("w-full")
        start = ui.select({"": "Blank"}, value="", label="Start from").props("dense").classes("w-full")
        ui.label("Copying keeps sections, lines, variables and terms choices from the latest revision "
                 "of that project. Prices stay as they were there; use Pull update on a line to refresh.") \
            .classes("text-xs text-gray-500")

        def company_changed(_=None) -> None:
            same = {p.number: f"{p.number} {p.client_name} {p.project_name}" for p in projects
                    if p.profile == company.value}
            blank = "Blank (percent items only)" if company.value == KS else "Blank"
            start.set_options({"": blank, **same}, value="")
        company.on_value_change(company_changed)

        def create() -> None:
            num = (number.value or "").strip()
            if not company.value:
                ui.notify("Pick the company first.", type="warning")
                return
            if not num or not (name.value or "").strip():
                ui.notify("Proposal # and project name are required.", type="warning")
                return
            profile = company.value
            p = Project(number=num, project_name=name.value.strip(), profile=profile)
            if not picker.apply(p):
                return
            if start.value:
                src = st.projects.load_revision(start.value)
                rev = Revision(sections=list(src.sections), lines=[ln.model_copy(deep=True) for ln in src.lines
                                                                   if ln.alternate is None],
                               variables=[v.model_copy() for v in src.variables],
                               blocks=[b.model_copy() for b in src.blocks], next_seq=dict(src.next_seq))
            else:
                rev = Revision(blocks=default_blocks(st.boilerplate_for(profile).blocks))
                for it in st.catalog.items_for(profile):
                    if it.active and it.price_source is PriceSource.PERCENT:
                        rev.add_line(line_from_item(it, st.catalog, rev.new_line_id(it.section)))
            # every {placeholder} the chosen terms use gets a proposal variable to fill in
            known = set(variable_map(p, rev, st.settings_for(profile))) | DOCUMENT_VARIABLES | SPECIAL_PLACEHOLDERS
            needed = sorted({n for b in rev.blocks if b.on for n in referenced(b.body)} - known)
            rev.variables += [Variable(name=n, value="", description="Used in the terms; fill in for this proposal")
                              for n in needed]
            try:
                st.projects.create(p, rev)
            except ValueError as e:
                ui.notify(str(e), type="negative")
                return
            if num == s.next_proposal_number():
                s.next_proposal_seq += 1
                st.save_settings()
            dlg.close()
            ui.navigate.to(f"/project/{num}")

        with ui.row().classes("w-full justify-end"):
            ui.button("Cancel", on_click=dlg.close).props("flat")
            ui.button("Create", icon="add", on_click=create)
    dlg.open()


def import_dialog(on_done) -> None:
    st = get_state()
    holder: dict = {}
    with ui.dialog() as dlg, ui.card().classes("w-[560px]"):
        ui.label("Import a proposal from the Excel workbook").classes("text-lg font-semibold")
        ui.label("Works with sheets built from the KS Proposal Template (e.g. \"26005 Proposal\"). "
                 "Totals are recalculated here; compare them with the sheet.").classes("text-xs text-gray-500")
        sheet = ui.select([], label="Sheet").props("dense").classes("w-full")
        sheet.disable()

        async def uploaded(e) -> None:
            data = await e.file.read()
            tmp = Path(tempfile.mkdtemp()) / "workbook.xlsx"
            tmp.write_bytes(data)
            holder["path"] = tmp
            names = [n for n in openpyxl.load_workbook(tmp, read_only=True).sheetnames if "Proposal" in n]
            sheet.set_options(names, value=names[-1] if names else None)
            sheet.enable()

        ui.upload(label="Workbook (.xlsx)", auto_upload=True, on_upload=uploaded) \
            .props('accept=".xlsx" flat bordered').classes("w-full")

        def run() -> None:
            from ..import_proposal import import_proposal_sheet
            if "path" not in holder or not sheet.value:
                ui.notify("Upload the workbook and choose a sheet.", type="warning")
                return
            try:
                p, rev = import_proposal_sheet(holder["path"], sheet.value, st.catalog, st.settings,
                                               st.boilerplate.blocks)
                st.projects.create(p, rev)
            except Exception as e:  # noqa: BLE001
                ui.notify(f"Import failed: {e}", type="negative", multi_line=True)
                return
            st.link_lists()   # the imported client becomes (or joins) a customer
            res = calculate(rev, st.settings, st.catalog.stock_classes, p)
            ui.notify(f"Imported {p.number}: {len(rev.lines)} lines, total ${res.base.total:,.2f}",
                      type="positive")
            dlg.close()
            on_done()

        with ui.row().classes("w-full justify-end"):
            ui.button("Cancel", on_click=dlg.close).props("flat")
            ui.button("Import", icon="upload_file", on_click=run)
    dlg.open()


@ui.page("/projects")
def projects_page() -> None:
    layout("Projects")

    st = get_state()

    def refresh() -> None:
        grid.options["rowData"] = _project_rows(show.value, company.value or "")
        grid.update()
        arch_btn.disable()
        del_btn.disable()

    async def selected():
        rows = await grid.get_selected_rows()
        if not rows:
            ui.notify("Select a project first (click its row).")
            return None
        return st.projects.load_project(rows[0]["number"])

    async def archive() -> None:
        p = await selected()
        if p is None:
            return
        if p.archived_on:
            p.archived_on = None
            ui.notify(f"{p.number} restored to the list.")
        else:
            if p.status not in (ProjectStatus.CLOSED, ProjectStatus.REJECTED, ProjectStatus.COMPLETED):
                with ui.dialog() as dlg, ui.card():
                    ui.label(f"{p.number} is {p.status.value}. Archive it anyway?")
                    with ui.row():
                        ui.button("Cancel", on_click=lambda: dlg.submit(False)).props("flat")
                        ui.button("Archive", on_click=lambda: dlg.submit(True))
                if not await dlg:
                    return
            p.archived_on = date.today()
            ui.notify(f"{p.number} archived. Turn on Show archived to see it.")
        st.projects.save_project(p)
        refresh()

    async def delete() -> None:
        p = await selected()
        if p is None:
            return
        with ui.dialog() as dlg, ui.card().classes("w-[460px]"):
            ui.label(f"Delete {p.number} {p.project_name}?").classes("text-lg font-semibold")
            ui.label("For mistakes and test projects. The folder (revisions, change orders, costs, PDFs) moves to "
                     "backups/deleted-projects in your data folder, so it can be recovered.").classes("text-sm")
            if p.status in WON_STATUSES:
                ui.label("This project was accepted. To keep its history out of the way, use Archive instead.") \
                    .classes("text-sm text-orange-700")
            confirm = ui.input(f"Type {p.number} to confirm").props("dense").classes("w-full")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dlg.submit(False)).props("flat")
                ui.button("Delete", icon="delete", on_click=lambda: dlg.submit(confirm.value == p.number)) \
                    .props("color=negative")
        if not await dlg:
            return
        try:
            dest = st.projects.delete(p.number)
        except (OSError, ValueError) as e:
            ui.notify(f"Delete failed: {e}", type="negative", multi_line=True)
            return
        s = st.settings
        if p.number == f"{s.proposal_year:02d}{s.next_proposal_seq - 1:03d}":
            s.next_proposal_seq -= 1          # the newest number was a test: hand it out again
            st.save_settings()
        ui.notify(f"Deleted {p.number}. Moved to {dest}", type="positive", multi_line=True)
        refresh()

    page_title("Projects", "Every proposal and its revisions. Double-click a project to open it; click once to select "
               "it for Archive or Delete.")
    with toolbar():
        ui.button("New project", icon="add", on_click=new_project_dialog).props("dense")
        ui.button("Import from Excel", icon="upload_file", on_click=lambda: import_dialog(refresh)) \
            .props("dense outline")
        filter_box(lambda: grid)
        company = ui.select({"": "Both companies", **PROFILES}, value="", on_change=lambda _: refresh()) \
            .props("dense options-dense").classes("w-56")
        show = ui.switch("Show archived", on_change=lambda _: refresh()).props("dense")
        ui.space()
        arch_btn = ui.button("Archive / restore", icon="inventory_2", on_click=archive).props("dense flat")
        del_btn = ui.button("Delete", icon="delete", on_click=delete).props("dense flat color=negative")
        for b in (arch_btn, del_btn):
            b.disable()            # enabled once a project is selected
    grid = ui.aggrid({
        "columnDefs": [
            {"field": "number", "headerName": "#", "width": 90, "sort": "desc"},
            {"field": "company", "headerName": "Company", "width": 120},
            {"field": "client", "headerName": "Client", "width": 200},
            {"field": "project", "headerName": "Project", "width": 220},
            {"field": "address", "headerName": "Address", "flex": 1},
            {"field": "status", "headerName": "Status", "width": 160},
            {"field": "rev", "headerName": "Rev", "width": 130},
            {"field": "total", "headerName": "Total Price", "width": 130, "type": "rightAligned"},
        ],
        "rowData": _project_rows(),
        "rowSelection": {"mode": "singleRow", "checkboxes": False, "enableClickSelection": True},
        "defaultColDef": {"sortable": True, "resizable": True, "filter": True},
        "rowHeight": 34,
        "overlayNoRowsTemplate": no_rows("No projects yet. Use New project, or Import from Excel."),
    }, auto_size_columns=False).classes("w-full").style("height:calc(100vh - 230px)")
    grid.on("cellDoubleClicked", lambda e: ui.navigate.to(f"/project/{e.args['data']['number']}"))

    async def selection(_=None) -> None:
        on = bool(await grid.get_selected_rows())
        arch_btn.set_enabled(on)
        del_btn.set_enabled(on)
    grid.on("selectionChanged", selection)


STATUS_OPTIONS = [s.value for s in ProjectStatus]
