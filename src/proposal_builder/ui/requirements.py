"""Convenient Enterprises requirements (ce-requirements section 8): the Requirements tab of a project, the intake
interview page and the requirement library page."""

from __future__ import annotations

import os
import sys

from nicegui import run, ui

from .. import ce_urs as U
from ..render.document import compile_document
from ..render.urs_document import (
    build_package,
    build_response_form,
    package_filename,
    response_filename,
    write_docx,
    write_response_docx,
)
from .state import get_state
from .widgets import Col, EditableGrid, layout, page_title

STATUS_LABELS = list(U.STATUSES.values())
STATUS_KEY = {v: k for k, v in U.STATUSES.items()}
KIND_LABELS = list(U.KINDS.values())
KIND_KEY = {v: k for k, v in U.KINDS.items()}


def company_info(settings) -> dict:
    c = settings.company
    return {"name": c.dba or c.legal_name, "legal": c.legal_name, "email": c.email, "phone": c.phone, "logo": ""}


def _open_buttons(paths) -> None:
    with ui.row():
        if sys.platform == "win32":
            for p in paths:
                ui.button(f"Open {p.suffix[1:].upper()}", icon="open_in_new",
                          on_click=lambda p=p: os.startfile(p)).props("outline")  # noqa: S606
            ui.button("Open folder", icon="folder",
                      on_click=lambda: os.startfile(paths[0].parent)).props("outline")  # noqa: S606
        else:
            for p in paths:
                ui.button(f"Download {p.suffix[1:].upper()}", icon="download",
                          on_click=lambda p=p: ui.download.content(p.read_bytes(), p.name)).props("outline")


class RequirementsPanel:
    """Requirements tab: the project's URS (ours from the library, or the client's entered by hand), compliance
    status and response per requirement, exports (URS/RFQ package, Response Form, questionnaire)."""

    def __init__(self, editor) -> None:
        self.ed = editor
        self.st = editor.st
        self.project = editor.project
        self.lib = self.st.requirements
        self.urs: U.ProjectUrs | None = self.st.projects.load_urs(self.project.number)
        self.grid = None
        self.panel()

    # ------------------------------------------------------------ data
    def save(self) -> None:
        if self.urs is not None:
            self.st.projects.save_urs(self.project.number, self.urs)
        self.ed._update_issue_badge()

    @property
    def folder(self):
        d = self.st.projects.project_dir(self.project.number) / "urs"
        d.mkdir(exist_ok=True)
        return d

    def _compliance_needed(self) -> bool:
        """Compliance statuses matter when we respond to a spec: the client's, or ours at URS-response depth."""
        from ..ce_models import URS
        return self.urs is not None and (self.urs.mode == U.CLIENT or self.ed.rev.depth == URS)

    # ------------------------------------------------------------ layout
    @ui.refreshable
    def panel(self) -> None:
        if self.urs is None:
            self._start()
            return
        u = self.urs
        ours = u.mode == U.OURS
        with ui.row().classes("items-center gap-2 w-full"):
            if ours:
                ui.label(f"URS/RFQ Rev {u.revision}: written by us from the requirement library") \
                    .classes("font-semibold")
            else:
                c = u.client
                ui.label("Client spec: " + " | ".join(x for x in (c.title, c.reference and f"Ref {c.reference}",
                                                                  c.revision and f"Rev {c.revision}", c.date) if x)
                         or "Client spec").classes("font-semibold")
            ui.space()
            ui.button("Document details", icon="tune", on_click=self.details_dialog).props("dense outline")
            if ours:
                ui.button("Interview", icon="quiz",
                          on_click=lambda: ui.navigate.to(f"/project/{self.project.number}/interview")) \
                    .props("dense outline")
                with ui.button("Questionnaire", icon="description").props("dense outline"):
                    with ui.menu():
                        ui.menu_item("Export Word questionnaire", on_click=self.export_questionnaire)
                        ui.menu_item("Import answered questionnaire", on_click=self.import_dialog)
                ui.button("Export URS/RFQ", icon="picture_as_pdf", on_click=self.export_package).props("dense")
            else:
                ui.button("New client revision", icon="history", on_click=self.client_revision_dialog) \
                    .props("dense outline")
            ui.button("Response Form", icon="assignment", on_click=self.export_response).props("dense")
        counts = U.summary(u)
        with ui.row().classes("gap-2 mt-1"):
            for k, n in counts.items():
                if n and (k or self._compliance_needed()):
                    ui.badge(f"{U.STATUSES[k]}: {n}", color="orange" if k == "" else
                             ("red" if k == "deviate" else "primary")).props("outline")
        ui.label("Double-click a heading to open the requirement. Status and response edit in place; Deviate and "
                 "Clarify rows go on the Response Form." + (" Turn sections off with the On column; the interview's "
                                                             "yes/no answers turn whole sections off too."
                                                             if ours else
                                                             " Numbers are the client's; type them as they appear."))\
            .classes("text-xs text-gray-500")
        with ui.row().classes("gap-1 mt-1"):
            ui.button("Add", icon="add", on_click=lambda: self.add_row()).props("dense flat")
            ui.button(icon="arrow_upward", on_click=lambda: self.move(-1)).props("dense flat").tooltip("Move up")
            ui.button(icon="arrow_downward", on_click=lambda: self.move(1)).props("dense flat").tooltip("Move down")
            ui.button(icon="format_indent_decrease", on_click=lambda: self.indent(-1)).props("dense flat") \
                .tooltip("Up a level")
            ui.button(icon="format_indent_increase", on_click=lambda: self.indent(1)).props("dense flat") \
                .tooltip("Down a level")
            ui.button(icon="delete", on_click=self.delete_row).props("dense flat color=negative").tooltip("Delete")
            if self._compliance_needed():
                ui.button("Comply to the rest", icon="done_all", on_click=self.comply_rest).props("dense flat") \
                    .tooltip("Every requirement with no status becomes Comply")
            ui.space()
            ui.button("Remove URS", icon="delete_forever", on_click=self.remove_urs).props("dense flat color=negative")
        self.grid = ui.aggrid({
            "columnDefs": [
                {"field": "num", "headerName": "#", "width": 80, "editable": not ours},
                {"field": "heading", "headerName": "Requirement", "flex": 2, "minWidth": 220,
                 ":cellStyle": "p => ({paddingLeft: ((p.data.level - 1) * 18 + 8) + 'px', "
                               "fontWeight: p.data.level === 1 ? '600' : '400', "
                               "color: p.data.live ? '' : '#9ca3af'})"},
                {"field": "kind", "headerName": "Kind", "width": 115},
                *([{"field": "on", "headerName": "On", "width": 70, "editable": True, "cellDataType": "boolean"}]
                  if ours else []),
                {"field": "status", "headerName": "Status", "width": 190, "editable": True,
                 "cellEditor": "agSelectCellEditor", "cellEditorParams": {"values": STATUS_LABELS},
                 ":cellStyle": "p => (p.value === 'Not answered' && p.data.need && p.data.kind !== 'Information' "
                               "&& p.data.live) "
                               "? {color: '#c2410c'} : (p.value === 'Deviate' ? {color: '#b91c1c', fontWeight: "
                               "'600'} : {})"},
                {"field": "response", "headerName": "Response (prints on the Response Form for Deviate/Clarify)",
                 "flex": 3, "minWidth": 260, "editable": True, "cellEditor": "agLargeTextCellEditor",
                 "cellEditorPopup": True, "tooltipField": "response"},
                {"field": "flags", "headerName": "", "width": 150},
            ],
            "rowData": self._rows(),
            "rowSelection": {"mode": "singleRow"},
            "rowHeight": 30, "headerHeight": 34, "stopEditingWhenCellsLoseFocus": True,
        }).classes("w-full").style("height:62vh")
        self.grid.on("cellValueChanged", self._changed)
        self.grid.on("cellDoubleClicked", self._dbl)

    def _rows(self) -> list[dict]:
        u = self.urs
        lib_bodies = {n.id: n.body for n in self.lib.nodes}
        need = self._compliance_needed()
        rows = []
        for i, (it, num, live) in enumerate(U.compliance_rows(u)):
            flags = []
            if it.review:
                flags.append("review")
            if it.changed:
                flags.append("changed")
            if it.source_id and it.source_body is not None and lib_bodies.get(it.source_id, it.source_body) \
                    != it.source_body:
                flags.append("library updated")
            rows.append({"_i": i, "num": num, "heading": it.heading or "(no heading)", "level": it.level,
                         "kind": U.KINDS.get(it.kind, it.kind), "on": it.on, "live": live, "need": need,
                         "status": U.STATUSES.get(it.status, ""), "response": it.response,
                         "flags": ", ".join(flags)})
        return rows

    def refresh_grid(self) -> None:
        if self.grid is not None:
            self.grid.options["rowData"] = self._rows()
            self.grid.update()

    def _changed(self, e) -> None:
        data, col, new = e.args.get("data", {}), e.args.get("colId"), e.args.get("newValue")
        i = data.get("_i")
        if i is None or i >= len(self.urs.items):
            return
        it = self.urs.items[i]
        if col == "status":
            it.status = STATUS_KEY.get(new, "")
            it.review = False
        elif col == "response":
            it.response = new or ""
            it.review = False
        elif col == "on":
            it.on = bool(new)
        elif col == "num":
            it.number = (new or "").strip()
        self.save()
        self.refresh_grid()

    def _dbl(self, e) -> None:
        if e.args.get("colId") in ("heading", "kind", "flags"):
            i = e.args.get("data", {}).get("_i")
            if i is not None and i < len(self.urs.items):
                self.item_dialog(self.urs.items[i])

    async def _selected(self) -> int | None:
        rows = await self.grid.get_selected_rows() if self.grid else []
        if not rows:
            ui.notify("Select a row first.")
            return None
        return rows[0]["_i"]

    # ------------------------------------------------------------ start
    def _start(self) -> None:
        ui.label("No requirements yet.").classes("text-lg font-semibold")
        ui.label("Write the URS for a client who has no spec (it starts from the requirement library and the "
                 "interview fills it in), or enter the client's own spec to respond to it.") \
            .classes("text-sm text-gray-600")
        with ui.row().classes("gap-4 mt-3 items-start"):
            with ui.card().classes("w-96"):
                ui.label("We write the URS/RFQ").classes("font-semibold")
                ui.label("Copy of the requirement library (Catalog > Requirement library). Answer the interview or "
                         "send the Word questionnaire, then export the URS/RFQ package for the client. Not billed; "
                         "the no-charge intake line (4090) notes it on the proposal.").classes("text-xs text-gray-600")
                ui.button("Start from the library", icon="playlist_add", on_click=self.start_ours).classes("mt-2")
            with ui.card().classes("w-96"):
                ui.label("Respond to the client's spec").classes("font-semibold")
                ui.label("Enter their requirements by hand using their section numbers (no import). Start blank, or "
                         "from the library tree when their spec follows our template.").classes("text-xs text-gray-600")
                title = ui.input("Spec title").props("dense").classes("w-full")
                with ui.row().classes("w-full gap-2 no-wrap"):
                    ref = ui.input("Reference #").props("dense").classes("flex-1")
                    rev = ui.input("Revision").props("dense").classes("w-20")
                    dt = ui.input("Date").props("dense").classes("w-28")
                tree = ui.checkbox("Start from the library tree")
                ui.button("Start", icon="edit_note",
                          on_click=lambda: self.start_client(title.value, ref.value, rev.value, dt.value,
                                                             tree.value)).classes("mt-2")

    def start_ours(self) -> None:
        self.urs = U.from_library(self.lib, self.project, self.lib.author)
        self.save()
        self._ensure_intake_line()
        self.panel.refresh()

    def start_client(self, title, ref, rev, dt, tree) -> None:
        self.urs = U.for_client_spec(title or "", ref or "", rev or "", dt or "", self.lib if tree else None)
        if not tree:
            self.urs.items.append(U.UrsItem(level=1, number="1", heading=""))
        self.save()
        self.panel.refresh()

    def _ensure_intake_line(self) -> None:
        """The no-charge requirements intake line (4090) notes the work on the proposal (decided 2026-11-03)."""
        ed = self.ed
        if ed.locked or any(ln.code == 4090 for ln in ed.rev.lines):
            return
        it = ed.cat.item(4090)
        if it is None:
            return
        from ..proposal import line_from_item
        ln = line_from_item(it, ed.cat, ed.new_id(it.section, 4090))
        ed.rev.add_line(ln)
        if it.section not in ed.rev.sections:
            ed.rev.sections.append(it.section)
        ed.save()
        ui.notify("Added the no-charge requirements intake line (4090) to the proposal.")

    async def remove_urs(self) -> None:
        with ui.dialog() as dlg, ui.card():
            ui.label("Remove this project's requirements and compliance responses?")
            ui.label("A backup of urs.json is kept in the backups folder.").classes("text-xs text-gray-500")
            with ui.row():
                ui.button("Cancel", on_click=lambda: dlg.submit(False)).props("flat")
                ui.button("Remove", on_click=lambda: dlg.submit(True)).props("color=negative")
        if not await dlg:
            return
        p = self.st.projects.project_dir(self.project.number) / "urs.json"
        if p.exists():
            self.st.store._backup(p)
            p.unlink()
        self.urs = None
        self.ed._update_issue_badge()
        self.panel.refresh()

    async def comply_rest(self) -> None:
        rows = [it for it, _, live in U.compliance_rows(self.urs) if live and not it.status
                and it.kind != "information"]
        if not rows:
            ui.notify("Every requirement already has a status.")
            return
        with ui.dialog() as dlg, ui.card():
            ui.label(f"Mark {len(rows)} requirement(s) with no status as Comply?")
            with ui.row():
                ui.button("Cancel", on_click=lambda: dlg.submit(False)).props("flat")
                ui.button("Comply", on_click=lambda: dlg.submit(True))
        if not await dlg:
            return
        for it in rows:
            it.status = "comply"
        self.save()
        self.panel.refresh()

    # ------------------------------------------------------------ row edits
    async def add_row(self) -> None:
        i = None
        if self.grid is not None:
            rows = await self.grid.get_selected_rows()
            i = rows[0]["_i"] if rows else None
        level = self.urs.items[i].level if i is not None else 1
        new = U.UrsItem(level=level, heading="New requirement",
                        kind="requirement")
        if i is None:
            self.urs.items.append(new)
        else:
            j = i + 1           # after the selected row and its children
            while j < len(self.urs.items) and self.urs.items[j].level > level:
                j += 1
            self.urs.items.insert(j, new)
        self.save()
        self.refresh_grid()
        self.item_dialog(new)

    async def move(self, d: int) -> None:
        i = await self._selected()
        if i is None:
            return
        items = self.urs.items
        j = i + d
        if 0 <= j < len(items):
            items[i], items[j] = items[j], items[i]
            self.save()
            self.refresh_grid()

    async def indent(self, d: int) -> None:
        i = await self._selected()
        if i is None:
            return
        it = self.urs.items[i]
        it.level = max(1, min(3, it.level + d))
        self.save()
        self.refresh_grid()

    async def delete_row(self) -> None:
        i = await self._selected()
        if i is None:
            return
        it = self.urs.items[i]
        with ui.dialog() as dlg, ui.card():
            ui.label(f"Delete '{it.heading or 'this row'}'?")
            if self.urs.mode == U.OURS:
                ui.label("To leave a section out of the URS, turn it off instead (On column).") \
                    .classes("text-xs text-gray-500")
            with ui.row():
                ui.button("Cancel", on_click=lambda: dlg.submit(False)).props("flat")
                ui.button("Delete", on_click=lambda: dlg.submit(True)).props("color=negative")
        if await dlg:
            self.urs.items.pop(i)
            self.save()
            self.refresh_grid()

    # ------------------------------------------------------------ dialogs
    def item_dialog(self, it: U.UrsItem) -> None:
        ours = self.urs.mode == U.OURS
        node = next((n for n in self.lib.nodes if n.id == it.source_id), None) if it.source_id else None
        with ui.dialog() as dlg, ui.card().style("width: 900px; max-width: 95vw"):
            with ui.row().classes("w-full gap-2 items-end no-wrap"):
                number = ui.input("Number", value=it.number,
                                  placeholder="automatic" if ours else "").props("dense").classes("w-28")
                level = ui.select({1: "Level 1", 2: "Level 2", 3: "Level 3"}, value=it.level).props("dense") \
                    .classes("w-28")
                heading = ui.input("Heading", value=it.heading).props("dense").classes("flex-1")
                kind = ui.select(U.KINDS, value=it.kind if it.kind in U.KINDS else "requirement", label="Kind") \
                    .props("dense").classes("w-40")
            body = ui.textarea("Text (Markdown: - bullets, **bold**, | tables |; [!note] is a template note, "
                               "{name} a variable)", value=it.body).props("outlined autogrow") \
                .classes("w-full font-mono text-xs")
            if node is not None and it.source_body is not None and node.body != it.source_body:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("update", color="orange")
                    ui.label("The library text has changed since this was copied.").classes("text-xs")
                    ui.button("Use library text", on_click=lambda: body.set_value(node.body)).props("dense flat")
            if ours:
                with ui.row().classes("w-full gap-3 items-center"):
                    on = ui.switch("Included", value=it.on)
                    applies = ui.select({t.key: t.key for t in self.lib.tags}, value=list(it.applies),
                                        multiple=True, label="Only when these interview answers are yes") \
                        .props("dense use-chips").classes("flex-1")
            ui.separator()
            with ui.row().classes("w-full gap-2 items-start no-wrap"):
                status = ui.select(U.STATUSES, value=it.status if it.status in U.STATUSES else "",
                                   label="Compliance").props("dense").classes("w-56")
                links = ui.input("Answered by (deliverable, BOM line, section of our proposal)",
                                 value=", ".join(it.links)).props("dense").classes("flex-1")
            response = ui.textarea("Response (Deviate: the proposed alternative; Clarify: the clarification)",
                                   value=it.response).props("outlined autogrow").classes("w-full")

            def done() -> None:
                text_changed = (heading.value or "") != it.heading or (body.value or "") != it.body
                it.number = (number.value or "").strip()
                it.level = int(level.value or 1)
                it.heading = heading.value or ""
                it.kind = kind.value or "requirement"
                if node is not None and body.value == node.body:
                    it.source_body = node.body
                it.body = body.value or ""
                if ours:
                    it.on = on.value
                    it.applies = list(applies.value or [])
                new_status = status.value or ""
                if new_status != it.status or (response.value or "") != it.response:
                    it.review = False
                it.status = new_status
                it.response = response.value or ""
                it.links = [x.strip() for x in (links.value or "").split(",") if x.strip()]
                if text_changed and not ours and (self.urs.client.revision or "") not in ("", "1.0", "A"):
                    it.changed, it.review = True, bool(it.status)
                self.save()
                dlg.close()
                self.refresh_grid()
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=dlg.close).props("flat")
                ui.button("Save", icon="save", on_click=done)
        dlg.open()

    def details_dialog(self) -> None:
        u = self.urs
        ours = u.mode == U.OURS
        with ui.dialog() as dlg, ui.card().style("width: 760px; max-width: 95vw"):
            ui.label("Document details").classes("text-lg font-semibold")
            f: dict = {}
            if ours:
                with ui.grid(columns=2).classes("w-full gap-x-4"):
                    for key, label in (("title", "Title"), ("subtitle", "Subtitle"), ("address_1", "Address line 1"),
                                       ("address_2", "Address line 2"), ("revision", "Revision"),
                                       ("month_year", "Month Year"), ("issued", "Issued for quotation"),
                                       ("due", "Quotation response due"), ("author", "Author"),
                                       ("document_number", "Document number")):
                        f[key] = ui.input(label, value=getattr(u, key)).props("dense")
                omit = ui.select({U.OMIT_NA: "Print 'Not applicable' (numbers stay)",
                                  U.OMIT_REMOVE: "Leave out (later sections renumber)"},
                                 value=u.omit, label="Sections turned off").props("dense").classes("w-96")
                ui.label("URS/RFQ revision history").classes("font-semibold mt-2")
                EditableGrid(lambda: u.history, [Col("revision", "Revision #", width=100),
                                                 Col("date", "Issue date", width=120),
                                                 Col("section", "Revised section", width=150),
                                                 Col("change", "Revisions made", flex=1)],
                             self.save, lambda: U.UrsRevisionRow(), height="22vh")
            else:
                c = u.client
                with ui.grid(columns=2).classes("w-full gap-x-4"):
                    for key, label in (("title", "Spec title"), ("reference", "Reference #"),
                                       ("revision", "Revision"), ("date", "Date")):
                        f["client." + key] = ui.input(label, value=getattr(c, key)).props("dense")
                    f["client.file"] = ui.input("File name in the project folder (reference only)",
                                                value=c.file).props("dense")
            ui.label("Response Form").classes("font-semibold mt-2")
            with ui.grid(columns=3).classes("w-full gap-x-4"):
                f["reference"] = ui.input("URS/RFQ reference #", value=u.reference).props("dense")
                f["completed_by"] = ui.input("Completed by", value=u.completed_by).props("dense")
                f["completed_date"] = ui.input("Completed date", value=u.completed_date).props("dense")

            def done() -> None:
                for key, el in f.items():
                    if key.startswith("client."):
                        setattr(u.client, key[7:], el.value or "")
                    else:
                        setattr(u, key, el.value or "")
                if ours:
                    u.omit = omit.value
                elif u.client.revision:
                    u.revision = u.client.revision
                self.save()
                dlg.close()
                self.panel.refresh()
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=dlg.close).props("flat")
                ui.button("Save", icon="save", on_click=done)
        dlg.open()

    def client_revision_dialog(self) -> None:
        with ui.dialog() as dlg, ui.card():
            ui.label("New client revision").classes("font-semibold")
            ui.label("The client sent a revised spec. Rows stay; every response is flagged for review until you "
                     "confirm it, and rows you edit from now on are marked changed.").classes("text-xs w-96")
            rev = ui.input("Revision", value="").props("dense")
            dt = ui.input("Date").props("dense")

            def done() -> None:
                if not (rev.value or "").strip():
                    ui.notify("Type the client's revision.")
                    return
                U.client_revision(self.urs, rev.value.strip(), dt.value or "")
                self.save()
                dlg.close()
                self.panel.refresh()
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=dlg.close).props("flat")
                ui.button("Apply", on_click=done)
        dlg.open()

    # ------------------------------------------------------------ exports
    def _company(self) -> dict:
        return company_info(self.ed.settings)

    async def _write(self, files: list[tuple[str, bytes]], title: str) -> None:
        paths = []
        try:
            for name, data in files:
                p = self.folder / name
                p.write_bytes(data)
                paths.append(p)
        except PermissionError:
            ui.notify("A file is open in another program. Close it and export again.", type="negative")
            return
        with self.ed.host, ui.dialog() as dlg, ui.card():
            ui.label(title).classes("text-lg font-semibold")
            for p in paths:
                ui.label(str(p)).classes("text-xs break-all")
            _open_buttons(paths)
            ui.button("Close", on_click=dlg.close).props("flat")
        dlg.open()

    async def export_package(self) -> None:
        open_items = U.open_answers(self.lib, self.urs)
        if open_items:
            ui.notify(f"Exporting with {len(open_items)} open question(s); see the Issues tab.", type="warning")
        n = ui.notification("Building URS/RFQ package...", spinner=True, timeout=None)
        try:
            doc = build_package(self.lib, self.urs, self.project, U.ISSUED, self._company())
            docx = await run.io_bound(write_docx, doc)
            pdf = await run.io_bound(compile_document, doc, None, "pdf", 110, "urs.typ")
        except Exception as e:  # noqa: BLE001
            n.dismiss()
            ui.notify(f"Export failed: {e}", type="negative", multi_line=True)
            return
        n.dismiss()
        await self._write([(package_filename(self.project, self.urs, "docx"), docx),
                           (package_filename(self.project, self.urs, "pdf"), pdf)], "URS/RFQ package saved")

    async def export_response(self) -> None:
        bad = [m for m in U.compliance_issues(self.urs) if "no response text" in m]
        if bad:
            ui.notify(f"{len(bad)} Deviate/Clarify row(s) have no response text.", type="warning")
        doc = build_response_form(self.lib, self.urs, self.project, U.ISSUED, company=self._company())
        try:
            docx = await run.io_bound(write_response_docx, doc)
            pdf = await run.io_bound(compile_document, doc, None, "pdf", 110, "urs.typ")
        except Exception as e:  # noqa: BLE001
            ui.notify(f"Export failed: {e}", type="negative", multi_line=True)
            return
        await self._write([(response_filename(self.project, self.urs, "docx"), docx),
                           (response_filename(self.project, self.urs, "pdf"), pdf)], "Response Form saved")

    async def export_questionnaire(self) -> None:
        from ..render.urs_questionnaire import write_questionnaire
        data = await run.io_bound(write_questionnaire, self.lib, self.urs, self.project,
                                  self.ed.settings.company.dba or "Convenient Enterprises")
        await self._write([(f"{self.project.number} Requirements questionnaire.docx", data)],
                          "Questionnaire saved")

    def import_dialog(self) -> None:
        from ..render.urs_questionnaire import read_questionnaire
        with ui.dialog() as dlg, ui.card():
            ui.label("Import answered questionnaire").classes("font-semibold")
            ui.label("Answers replace the ones on file; blank answers leave the current ones. Questions marked "
                     "\"Don't know\" stay open on the Issues tab.").classes("text-xs w-96")

            async def got(e) -> None:
                try:
                    data = await e.file.read() if hasattr(e, "file") else e.content.read()
                    answers, tags, dk = read_questionnaire(data)
                except Exception as err:  # noqa: BLE001
                    ui.notify(f"Could not read the file: {err}", type="negative")
                    return
                self.urs.answers.update(answers)
                self.urs.tags.update(tags)
                for k in dk:
                    self.urs.answers.pop(k, None)
                self.save()
                dlg.close()
                self.panel.refresh()
                ui.notify(f"Imported {len(answers)} answer(s) and {len(tags)} yes/no answer(s); "
                          f"{len(dk)} marked don't know.")
            ui.upload(on_upload=got, auto_upload=True, max_files=1).props('accept=".docx"').classes("w-96")
            ui.button("Close", on_click=dlg.close).props("flat")
        dlg.open()


# ---------------------------------------------------------------- interview page

@ui.page("/project/{number}/interview")
def interview_page(number: str, topic: int = 0) -> None:
    layout(f"{number} interview")
    st = get_state()
    try:
        project = st.projects.load_project(number)
    except (FileNotFoundError, OSError):
        ui.label("Project not found.")
        return
    lib = st.requirements
    urs = st.projects.load_urs(number)
    if urs is None or urs.mode != U.OURS:
        ui.label("Start the URS from the library first (Requirements tab).")
        return
    topics = U.interview(lib, urs)
    vals = U.values(lib, urs, project)
    topic = max(0, min(topic, len(topics) - 1))
    t, questions = topics[topic]

    def save() -> None:
        st.projects.save_urs(number, urs)

    with ui.row().classes("items-center gap-3 w-full"):
        ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to(f"/project/{number}")).props("flat round")
        ui.label(f"{project.number} {project.project_name}: requirements interview").classes("text-lg font-semibold")
    ui.linear_progress(value=(topic + 1) / len(topics), show_value=False).classes("w-full")
    with ui.row().classes("gap-1 flex-wrap"):
        for i, (tt, _) in enumerate(topics):
            ui.button(tt.title, on_click=lambda i=i: ui.navigate.to(f"/project/{number}/interview?topic={i}")) \
                .props("dense " + ("unelevated" if i == topic else "flat"))
    ui.label(t.title).classes("text-xl font-semibold mt-3")
    ui.label("Answers save as you type. Blank answers print the template text (blue in the URS) and stay open "
             "on the Issues tab.").classes("text-xs text-gray-500")
    with ui.column().classes("w-full max-w-3xl gap-3 mt-2"):
        for q in questions:
            with ui.card().classes("w-full"):
                ui.label(q.text).classes("font-semibold")
                if q.example:
                    ui.label(f"Example: {q.example}").classes("text-xs text-gray-500 italic")
                if q.kind == "tag":
                    cur = urs.tags.get(q.key)
                    val = "yes" if cur is True else ("no" if cur is False else "dk")

                    def set_tag(e, key=q.key) -> None:
                        if e.value == "dk":
                            urs.tags.pop(key, None)
                        else:
                            urs.tags[key] = e.value == "yes"
                        save()
                    ui.toggle({"yes": "Yes", "no": "No", "dk": "Don't know"}, value=val, on_change=set_tag) \
                        .props("dense no-caps")
                else:
                    var = lib.variable(q.key)
                    cur = urs.answers.get(q.key, "")

                    def set_var(e, key=q.key) -> None:
                        v = (e.value or "").strip("\n")
                        if v.strip():
                            urs.answers[key] = v
                        else:
                            urs.answers.pop(key, None)
                        save()
                    placeholder = U._sub(var.default, vals) if var and "[" not in var.default else ""
                    if q.type == "list":
                        ui.textarea(value=cur, placeholder=placeholder or "One per line",
                                    on_change=set_var).props("outlined autogrow dense").classes("w-full")
                    elif q.type == "choice" and q.choices:
                        ui.select(q.choices, value=cur or None, on_change=set_var).props("dense").classes("w-64")
                    else:
                        ui.input(value=cur, placeholder=placeholder, on_change=set_var).props("dense") \
                            .classes("w-full")
    with ui.row().classes("gap-2 mt-4"):
        if topic > 0:
            ui.button("Back", icon="chevron_left",
                      on_click=lambda: ui.navigate.to(f"/project/{number}/interview?topic={topic - 1}")) \
                .props("outline")
        if topic < len(topics) - 1:
            ui.button("Next", icon="chevron_right",
                      on_click=lambda: ui.navigate.to(f"/project/{number}/interview?topic={topic + 1}"))
        else:
            ui.button("Done", icon="check", on_click=lambda: ui.navigate.to(f"/project/{number}"))


# ---------------------------------------------------------------- library page

@ui.page("/requirements")
def library_page() -> None:
    layout("Requirement library")
    st = get_state()
    lib = st.requirements
    page_title("Requirement library", "Convenient Enterprises URS/RFQ Template as sections, with the variables and "
               "yes/no questions the intake interview and Word questionnaire ask. A project's URS is a copy; edits "
               "here never change it (its rows show 'library updated').")

    def save() -> None:
        st.save_requirements()

    with ui.row().classes("gap-2"):
        async def template() -> None:
            doc = build_package(lib, None, company=company_info(st.settings_for("ce")))
            docx = await run.io_bound(write_docx, doc)
            pdf = await run.io_bound(compile_document, doc, None, "pdf", 110, "urs.typ")
            folder = st.store.root / "profiles" / "ce" / "exports"
            folder.mkdir(parents=True, exist_ok=True)
            paths = []
            for name, data in (("URS-RFQ Template.docx", docx), ("URS-RFQ Template.pdf", pdf)):
                p = folder / name
                try:
                    p.write_bytes(data)
                except PermissionError:
                    ui.notify(f"{name} is open in another program.", type="negative")
                    return
                paths.append(p)
            with ui.dialog() as dlg, ui.card():
                ui.label("Blank template saved").classes("font-semibold")
                for p in paths:
                    ui.label(str(p)).classes("text-xs break-all")
                _open_buttons(paths)
                ui.button("Close", on_click=dlg.close).props("flat")
            dlg.open()
        ui.button("Export blank template", icon="description", on_click=template).props("outline")

    with ui.tabs() as tabs:
        t_nodes = ui.tab("Sections")
        t_vars = ui.tab("Variables and questions")
        t_tags = ui.tab("Yes/no questions")
        t_doc = ui.tab("Front matter")
    with ui.tab_panels(tabs, value=t_nodes).classes("w-full"):
        with ui.tab_panel(t_nodes):
            ui.label("Level 1 to 3 sections in print order. Applies: the yes/no questions (tags) that must not be "
                     "answered no. Edit the text in the project, or here for every new project.") \
                .classes("text-xs text-gray-500")

            def node_rows():
                items = [U.UrsItem(level=n.level, numbered=n.numbered) for n in lib.nodes]
                return list(zip(lib.nodes, U.numbers(items), strict=True))

            grid = ui.aggrid({
                "columnDefs": [
                    {"field": "num", "headerName": "#", "width": 80},
                    {"field": "heading", "headerName": "Heading", "flex": 2,
                     ":cellStyle": "p => ({paddingLeft: ((p.data.level - 1) * 18 + 8) + 'px'})"},
                    {"field": "kind", "headerName": "Kind", "width": 120},
                    {"field": "applies", "headerName": "Applies when", "width": 160},
                    {"field": "on", "headerName": "On", "width": 70},
                    {"field": "text", "headerName": "Text", "flex": 3},
                ],
                "rowData": [], "rowHeight": 28}).classes("w-full").style("height:64vh")

            def refresh():
                grid.options["rowData"] = [{"_i": i, "num": num, "heading": n.heading, "level": n.level,
                                            "kind": U.KINDS.get(n.kind, n.kind), "applies": ", ".join(n.applies),
                                            "on": "yes" if n.on else "no",
                                            "text": n.body.replace("\n", " ")[:160]}
                                           for i, (n, num) in enumerate(node_rows())]
                grid.update()
            refresh()

            def edit(e) -> None:
                i = e.args.get("data", {}).get("_i")
                if i is None:
                    return
                n = lib.nodes[i]
                with ui.dialog() as dlg, ui.card().style("width: 900px; max-width: 95vw"):
                    with ui.row().classes("w-full gap-2 no-wrap items-end"):
                        heading = ui.input("Heading", value=n.heading).props("dense").classes("flex-1")
                        kind = ui.select(U.KINDS, value=n.kind, label="Kind").props("dense").classes("w-40")
                        on = ui.switch("On by default", value=n.on)
                    applies = ui.select({t.key: t.key for t in lib.tags}, value=list(n.applies), multiple=True,
                                        label="Applies when").props("dense use-chips").classes("w-full")
                    body = ui.textarea("Text", value=n.body).props("outlined autogrow") \
                        .classes("w-full font-mono text-xs")

                    def done() -> None:
                        n.heading, n.kind, n.on = heading.value or "", kind.value, on.value
                        n.applies, n.body = list(applies.value or []), body.value or ""
                        save()
                        dlg.close()
                        refresh()
                    with ui.row().classes("w-full justify-end"):
                        ui.button("Cancel", on_click=dlg.close).props("flat")
                        ui.button("Save", icon="save", on_click=done)
                dlg.open()
            grid.on("cellDoubleClicked", edit)
        with ui.tab_panel(t_vars):
            ui.label("Each {name} in the text. The question is asked in the interview and the questionnaire; the "
                     "default prints when unanswered (text in brackets prints blue and stays open).") \
                .classes("text-xs text-gray-500")
            EditableGrid(lambda: lib.variables,
                         [Col("name", "Name", width=150), Col("type", "Type", "select", list(U.VAR_TYPES), width=90),
                          Col("topic", "Topic", "select", [t.key for t in lib.topics], width=120),
                          Col("question", "Question", flex=3), Col("example", "Example", flex=1),
                          Col("default", "Default", flex=2)],
                         save, lambda: U.UrsVariable(name="new_variable"), height="62vh")
        with ui.tab_panel(t_tags):
            EditableGrid(lambda: lib.tags,
                         [Col("key", "Tag", width=130), Col("topic", "Topic", "select", [t.key for t in lib.topics],
                                                            width=130), Col("question", "Question", flex=1)],
                         save, lambda: U.UrsTag(key="new_tag"), height="40vh")
        with ui.tab_panel(t_doc):
            ui.input("Author (footer)", value=lib.author,
                     on_change=lambda e: (setattr(lib, "author", e.value or ""), save())).classes("w-80")
            ui.textarea("Instructions page (blank template only)", value=lib.instructions,
                        on_change=lambda e: (setattr(lib, "instructions", e.value or ""), save())) \
                .props("outlined autogrow").classes("w-full")
            ui.textarea("Confidential information (cover)", value=lib.confidentiality,
                        on_change=lambda e: (setattr(lib, "confidentiality", e.value or ""), save())) \
                .props("outlined autogrow").classes("w-full")
            ui.textarea("Response Form instructions", value=lib.response_instructions,
                        on_change=lambda e: (setattr(lib, "response_instructions", e.value or ""), save())) \
                .props("outlined autogrow").classes("w-full")
