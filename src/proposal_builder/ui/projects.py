"""Projects list, new project, import from Excel."""

from __future__ import annotations

import tempfile
from pathlib import Path

import openpyxl
from nicegui import ui

from ..calc import calculate
from ..calc import DOCUMENT_VARIABLES, SPECIAL_PLACEHOLDERS, referenced, variable_map
from ..models import PriceSource, Variable
from ..proposal import Project, ProjectStatus, Revision, default_blocks, line_from_item
from .state import get_state
from .widgets import layout


def _project_rows() -> list[dict]:
    st = get_state()
    rows = []
    for p in st.projects.list_projects():
        revs = st.projects.list_revisions(p.number)
        total, state = "", ""
        try:
            rev = st.projects.load_revision(p.number)
            state = rev.state.value
            res = calculate(rev, st.settings, st.catalog.stock_classes, p)
            total = f"${res.base.total:,.2f}"
        except Exception:  # noqa: BLE001 - list must render even if one file is bad
            pass
        rows.append({"number": p.number, "client": p.client_name, "project": p.project_name,
                     "address": p.site_address, "status": p.status.value,
                     "rev": f"{revs[-1]} {state}" if revs else "", "total": total})
    return rows


def new_project_dialog() -> None:
    st = get_state()
    s = st.settings
    with ui.dialog() as dlg, ui.card().classes("w-[520px]"):
        ui.label("New project").classes("text-lg font-semibold")
        number = ui.input("Proposal #", value=s.next_proposal_number()).props("dense")
        client = ui.input("Client").props("dense").classes("w-full")
        address = ui.input("Site address").props("dense").classes("w-full")
        name = ui.input("Project (e.g. Kitchen Renovation)").props("dense").classes("w-full")
        existing = {p.number: f"{p.number} {p.client_name} {p.project_name}" for p in st.projects.list_projects()}
        start = ui.select({"": "Blank (percent items only)", **existing}, value="",
                          label="Start from").props("dense").classes("w-full")
        ui.label("Copying keeps sections, lines, variables and boilerplate choices from the latest revision "
                 "of that project. Prices stay as they were there; use Pull update on a line to refresh.") \
            .classes("text-xs text-gray-500")

        def create() -> None:
            num = (number.value or "").strip()
            if not num or not (name.value or "").strip():
                ui.notify("Proposal # and project name are required.", type="warning")
                return
            p = Project(number=num, client_name=client.value or "", site_address=address.value or "",
                        project_name=name.value.strip())
            if start.value:
                src = st.projects.load_revision(start.value)
                rev = Revision(sections=list(src.sections), lines=[ln.model_copy(deep=True) for ln in src.lines
                                                                   if ln.alternate is None],
                               variables=[v.model_copy() for v in src.variables],
                               blocks=[b.model_copy() for b in src.blocks], next_seq=dict(src.next_seq))
            else:
                rev = Revision(blocks=default_blocks(st.boilerplate.blocks))
                for it in st.catalog.items:
                    if it.active and it.price_source is PriceSource.PERCENT:
                        rev.add_line(line_from_item(it, st.catalog, rev.new_line_id(it.section)))
            # every {placeholder} the chosen terms use gets a proposal variable to fill in
            known = set(variable_map(p, rev, s)) | DOCUMENT_VARIABLES | SPECIAL_PLACEHOLDERS
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

    def refresh() -> None:
        grid.options["rowData"] = _project_rows()
        grid.update()

    with ui.row().classes("gap-2 mb-2 items-center"):
        ui.button("New project", icon="add", on_click=new_project_dialog).props("dense")
        ui.button("Import from Excel", icon="upload_file", on_click=lambda: import_dialog(refresh)) \
            .props("dense outline")
        ui.label("Double-click a project to open it.").classes("text-xs text-gray-500")
    grid = ui.aggrid({
        "columnDefs": [
            {"field": "number", "headerName": "#", "width": 90, "sort": "desc"},
            {"field": "client", "headerName": "Client", "width": 200},
            {"field": "project", "headerName": "Project", "width": 220},
            {"field": "address", "headerName": "Address", "flex": 1},
            {"field": "status", "headerName": "Status", "width": 120},
            {"field": "rev", "headerName": "Rev", "width": 130},
            {"field": "total", "headerName": "Total", "width": 130, "type": "rightAligned"},
        ],
        "rowData": _project_rows(),
        "defaultColDef": {"sortable": True, "resizable": True, "filter": True},
        "rowHeight": 34,
    }, auto_size_columns=False).classes("w-full").style("height:75vh")
    grid.on("cellDoubleClicked", lambda e: ui.navigate.to(f"/project/{e.args['data']['number']}"))


STATUS_OPTIONS = [s.value for s in ProjectStatus]
