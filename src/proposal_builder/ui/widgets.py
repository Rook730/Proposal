"""Shared layout and an editable AG Grid helper."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from nicegui import ui
from pydantic import BaseModel, ValidationError

NAV_PROPOSALS = [
    ("Projects", "/projects", "folder_open"),
    ("Income summary", "/summary", "insights"),
]

NAV = [
    ("Catalog items", "/items", "list_alt"),
    ("Sections", "/sections", "view_agenda"),
    ("Rates", "/rates", "schedule"),
    ("Price ranges", "/allowances", "straighten"),
    ("Units", "/units", "square_foot"),
    ("Stock lengths", "/stock", "carpenter"),
    ("Boilerplate", "/boilerplate", "article"),
    ("Customers", "/customers", "people"),
    ("Contractors", "/contractors", "engineering"),
    ("Suppliers", "/suppliers", "local_shipping"),
    ("Settings", "/settings", "settings"),
]

BRAND = "#1F3A5F"


# Light and dark colors live in CSS classes (not inline styles) so the dark mode setting can switch them.
THEME_CSS = """
    .nicegui-content { padding: 16px 24px; }
    .ag-theme-quartz, .nicegui-aggrid { --ag-font-size: 13px; }
    .pb-brand { color: #1F3A5F; }      .pb-red { color: #B00020; }
    .pb-green { color: #1B5E20; }      .pb-amber { color: #B26A00; }
    .pb-pct { background: #E6E8EB !important; }
    .pb-alt1, .pb-altbg1 { background: #DCE8F7 !important; }
    .pb-alt2, .pb-altbg2 { background: #E3F1E8 !important; }
    .pb-alt3, .pb-altbg3 { background: #F6ECDD !important; }
    .pb-out { color: #9aa0a6; font-style: italic; }
    .pb-last { box-shadow: inset 4px 0 0 #E8A33D; }
    .pb-last .ag-cell { font-weight: 600; }
    .pb-warnbox { background: #FFF4E5; border: 1px solid #F0C36D; }
    .pb-selected { background: #eef3f9; border-radius: 4px; }
    .body--dark { --q-primary: #8FB3E0 !important; }
    .body--dark .q-header { --q-primary: #1F3A5F !important; }
    .body--dark .bg-primary.text-white { color: #0E1B2C !important; }
    .body--dark .pb-brand { color: #A9C4E8; }  .body--dark .pb-red { color: #FF8A80; }
    .body--dark .pb-green { color: #81C784; }  .body--dark .pb-amber { color: #FFB74D; }
    .body--dark .pb-pct { background: #33373d !important; }
    .body--dark .pb-alt1, .body--dark .pb-altbg1 { background: #22344d !important; }
    .body--dark .pb-alt2, .body--dark .pb-altbg2 { background: #23392b !important; }
    .body--dark .pb-alt3, .body--dark .pb-altbg3 { background: #43361f !important; }
    .body--dark .pb-out { color: #8a9099; }
    .body--dark .pb-warnbox { background: #3b2f1a; border-color: #8a6a2a; }
    .body--dark .pb-selected { background: #2a3442; }
    .body--dark .text-gray-500, .body--dark .text-gray-600, .body--dark .text-gray-700 { color: #a0a6ad !important; }
"""


def layout(title: str, drawer: bool = True) -> None:
    ui.colors(primary=BRAND)
    from .state import get_state
    ui.dark_mode(value=bool(get_state().settings.dark_mode))
    ui.add_css(THEME_CSS)
    with ui.header().classes("items-center py-2 px-4").style(f"background:{BRAND}"):
        ui.label("Kept Spec Proposal Builder").classes("text-lg font-semibold")
        ui.space()
        ui.label(title).classes("text-sm opacity-80")
        from .. import __version__
        ui.label(f"v{__version__}").classes("text-xs opacity-60")
        from .update_ui import header_slot
        header_slot()
    with ui.left_drawer(value=drawer, bordered=True).classes("p-0").props("width=210"):
        with ui.list().props("dense padding").classes("w-full"):
            ui.item_label("Proposals").props("header").classes("text-xs uppercase")
            for label, path, icon in NAV_PROPOSALS:
                with ui.item(on_click=lambda p=path: ui.navigate.to(p)).props("clickable"):
                    with ui.item_section().props("avatar"):
                        ui.icon(icon, size="xs")
                    with ui.item_section():
                        ui.item_label(label).classes("font-semibold" if label == title else "")
            ui.separator()
            ui.item_label("Catalog").props("header").classes("text-xs uppercase")
            for label, path, icon in NAV:
                with ui.item(on_click=lambda p=path: ui.navigate.to(p)).props("clickable"):
                    with ui.item_section().props("avatar"):
                        ui.icon(icon, size="xs")
                    with ui.item_section():
                        ui.item_label(label).classes("font-semibold" if label == title else "")


def keep_current(options: dict, value) -> dict:
    """Select options that still include the saved value(s), so a form opens after a catalog entry was
    renamed or deleted (the stale value shows as "missing" and can be changed)."""
    vals = value if isinstance(value, list) else [value]
    missing = {v: f"{v} (missing)" for v in vals if v not in (None, "") and v not in options}
    return {**missing, **options}


# ---------------------------------------------------------------- conversions


def to_decimal(v: Any) -> Decimal | None:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v).replace("$", "").replace(",", "").strip())
    except InvalidOperation:
        raise ValueError(f"not a number: {v!r}")


def to_json(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if hasattr(v, "value"):          # Enum
        return v.value
    return v


def warn(problems: list[str]) -> None:
    if problems:
        ui.notify("Saved with warnings: " + "; ".join(problems[:5])
                  + (" ..." if len(problems) > 5 else ""), type="warning", multi_line=True, timeout=8000)


# ---------------------------------------------------------------- editable grid


@dataclass
class Col:
    field: str
    header: str
    kind: str = "text"                  # text | number | bool | select | list | strlist | date
    options: list[str] = field(default_factory=list)
    width: int | None = None
    flex: int | None = None
    editable: bool = True
    lookup: dict[str, str] | None = None   # kind "lookup": stored id -> shown label


class EditableGrid:
    """Grid over a list of pydantic models. Every cell edit is written back and saved."""

    def __init__(self, models: Callable[[], list[BaseModel]], cols: list[Col],
                 save: Callable[[], list[str] | None], new_model: Callable[[], BaseModel] | None = None,
                 height: str = "70vh", readonly: bool = False):
        self.models, self.cols, self.save, self.new_model = models, cols, save, new_model
        self.readonly = readonly
        if readonly:
            self.cols = cols = [Col(**{**c.__dict__, "editable": False}) for c in cols]
        toolbar = ui.row().classes("gap-2 mb-2")
        toolbar.set_visibility(not readonly)
        with toolbar:
            if new_model:
                ui.button("Add row", icon="add", on_click=self.add).props("outline dense")
            ui.button("Delete selected", icon="delete", on_click=self.delete).props("outline dense color=negative")
            self.filter = ui.input(placeholder="Filter").props("dense clearable").classes("w-64")
            self.filter.on_value_change(lambda e: self.grid.run_grid_method("setGridOption", "quickFilterText", e.value or ""))
        self.grid = ui.aggrid({
            "columnDefs": [self._coldef(c) for c in cols],
            "rowData": self._rows(),
            "rowSelection": {"mode": "multiRow"},
            "rowHeight": 32, "headerHeight": 36,
            "stopEditingWhenCellsLoseFocus": True,
        }).classes("w-full").style(f"height:{height}")
        self.grid.on("cellValueChanged", self._changed)

    def _coldef(self, c: Col) -> dict:
        d: dict[str, Any] = {"field": c.field, "headerName": c.header, "editable": c.editable,
                             "filter": True, "sortable": True, "resizable": True}
        if c.width:
            d["width"] = c.width
        if c.flex:
            d["flex"] = c.flex
        if c.kind == "number":
            d["cellDataType"] = "number"
        elif c.kind == "bool":
            d["cellDataType"] = "boolean"
        elif c.kind == "select":
            d["cellEditor"] = "agSelectCellEditor"
            d["cellEditorParams"] = {"values": c.options}
        elif c.kind == "lookup":
            d["cellEditor"] = "agSelectCellEditor"
            d["cellEditorParams"] = {"values": ["", *c.lookup.values()]}
        elif c.kind in ("list", "strlist", "date"):
            d["cellDataType"] = "text"
        return d

    def _rows(self) -> list[dict]:
        rows = []
        for i, m in enumerate(self.models()):
            r = {"_i": i}
            for c in self.cols:
                v = getattr(m, c.field)
                if c.kind == "lookup":
                    r[c.field] = c.lookup.get(v, "") if v else ""
                else:
                    r[c.field] = ", ".join(str(x) for x in v) if c.kind in ("list", "strlist") else to_json(v)
            rows.append(r)
        return rows

    def refresh(self) -> None:
        self.grid.options["rowData"] = self._rows()
        self.grid.update()

    def _convert(self, c: Col, v: Any) -> Any:
        if c.kind == "number":
            return to_decimal(v)
        if c.kind == "list":
            return [to_decimal(x) for x in str(v or "").split(",") if x.strip()]
        if c.kind == "strlist":
            return [x.strip() for x in str(v or "").split(",") if x.strip()]
        if c.kind == "date":
            return date.fromisoformat(str(v).strip()[:10]) if v not in (None, "") else None
        if c.kind == "lookup":
            return next((k for k, label in c.lookup.items() if label == v), None) if v else None
        return v

    def _changed(self, e) -> None:
        data = e.args.get("data", {})
        field_ = e.args.get("colId")
        col = next((c for c in self.cols if c.field == field_), None)
        models = self.models()
        if col is None or data.get("_i") is None or data["_i"] >= len(models):
            return
        model = models[data["_i"]]
        try:
            setattr(model, field_, self._convert(col, e.args.get("newValue")))
        except (ValidationError, ValueError) as err:
            ui.notify(f"Not saved: {err}", type="negative", multi_line=True)
            self.refresh()
            return
        warn(self.save() or [])

    def add(self) -> None:
        if not self.new_model:
            return
        try:
            self.models().append(self.new_model())
        except (ValidationError, ValueError) as err:
            ui.notify(str(err), type="negative")
            return
        warn(self.save() or [])
        self.refresh()

    async def delete(self) -> None:
        rows = await self.grid.get_selected_rows()
        if not rows:
            ui.notify("Select rows first (checkbox column).")
            return
        idx = sorted({r["_i"] for r in rows}, reverse=True)
        models = self.models()
        with ui.dialog() as dlg, ui.card():
            ui.label(f"Delete {len(idx)} row(s)?")
            with ui.row():
                ui.button("Cancel", on_click=lambda: dlg.submit(False)).props("flat")
                ui.button("Delete", on_click=lambda: dlg.submit(True)).props("color=negative")
        if not await dlg:
            return
        for i in idx:
            del models[i]
        warn(self.save() or [])
        self.refresh()
