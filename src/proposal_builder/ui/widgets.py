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

NAV_CATALOG = [
    ("Catalog items", "/items", "list_alt"),
    ("Sections", "/sections", "view_agenda"),
    ("Rates", "/rates", "schedule"),
    ("Price ranges", "/allowances", "straighten"),
    ("Units", "/units", "square_foot"),
    ("Stock lengths", "/stock", "carpenter"),
    ("Price references", "/prices", "forest"),
    ("Terms library", "/boilerplate", "article"),
]

NAV_CONTACTS = [
    ("Customers", "/customers", "people"),
    ("Contractors", "/contractors", "engineering"),
    ("Suppliers", "/suppliers", "local_shipping"),
]

NAV_SETTINGS = [("Settings", "/settings", "settings")]

NAV_GROUPS = [("Proposals", NAV_PROPOSALS), ("Catalog", NAV_CATALOG), ("Contacts", NAV_CONTACTS),
              ("", NAV_SETTINGS)]
NAV = NAV_CATALOG + NAV_CONTACTS + NAV_SETTINGS

BRAND = "#1F3A5F"


# Light and dark colors live in CSS classes (not inline styles) so the dark mode setting can switch them.
THEME_CSS = """
    .nicegui-content { padding: 16px 24px; }
    .ag-theme-quartz, .nicegui-aggrid { --ag-font-size: 13px; }
    .pb-strip { background: #ffffff; }
    .pb-issue:hover { background: rgba(31, 58, 95, 0.06); }
    .body--dark .pb-issue:hover { background: rgba(169, 196, 232, 0.10); }
    .pb-navsel { background: rgba(31, 58, 95, 0.08); }
    .body--dark .pb-navsel { background: rgba(169, 196, 232, 0.12); }
    .body--dark .pb-strip { background: #1d1d1d; border-color: #3a3a3a !important; }
    .pb-brand { color: #1F3A5F; }      .pb-red { color: #B00020; }
    .pb-green { color: #1B5E20; }      .pb-amber { color: #B26A00; }
    .pb-pct { background: #E6E8EB !important; }
    .pb-old { background: #FDEBD3 !important; color: #8A4B00; }
    .pb-alt1, .pb-altbg1 { background: #DCE8F7 !important; }
    .pb-alt2, .pb-altbg2 { background: #E3F1E8 !important; }
    .pb-alt3, .pb-altbg3 { background: #F6ECDD !important; }
    .pb-alt4, .pb-altbg4 { background: #ECE4F6 !important; }
    .pb-alt5, .pb-altbg5 { background: #F7E3E8 !important; }
    .pb-alt6, .pb-altbg6 { background: #DFF1F1 !important; }
    .pb-out { color: #9aa0a6; font-style: italic; }
    .pb-last { box-shadow: inset 4px 0 0 #E8A33D; }
    .pb-last .ag-cell { font-weight: 600; }
    .pb-warnbox { background: #FFF4E5; border: 1px solid #F0C36D; }
    .pb-selected { background: #eef3f9; border-radius: 4px; }
    .body--dark { --q-primary: #4C7DBD !important; }   /* white text 4.5:1; as text on dark 4:1 */
    .body--dark .q-header { --q-primary: #1F3A5F !important; }
    .body--dark .pb-brand { color: #A9C4E8; }  .body--dark .pb-red { color: #FF8A80; }
    .body--dark .pb-green { color: #81C784; }  .body--dark .pb-amber { color: #FFB74D; }
    .body--dark .pb-pct { background: #33373d !important; }
    .body--dark .pb-alt1, .body--dark .pb-altbg1 { background: #22344d !important; }
    .body--dark .pb-alt2, .body--dark .pb-altbg2 { background: #23392b !important; }
    .body--dark .pb-alt3, .body--dark .pb-altbg3 { background: #43361f !important; }
    .body--dark .pb-alt4, .body--dark .pb-altbg4 { background: #33284a !important; }
    .body--dark .pb-alt5, .body--dark .pb-altbg5 { background: #4a2832 !important; }
    .body--dark .pb-alt6, .body--dark .pb-altbg6 { background: #1f4242 !important; }
    .body--dark .pb-out { color: #8a9099; }
    .body--dark .pb-warnbox { background: #3b2f1a; border-color: #8a6a2a; }
    .body--dark .pb-selected { background: #2a3442; }
    .body--dark .text-gray-500, .body--dark .text-gray-600, .body--dark .text-gray-700 { color: #a0a6ad !important; }
"""

# Native window only: the right-click menu (turned on by native_menu) shows in text fields and on
# selected text, where it offers spelling suggestions and cut / copy / paste. Elsewhere it would
# offer Back and Refresh, which drop an open form, so it is suppressed there.
CONTEXT_MENU_JS = """<script>
document.addEventListener('contextmenu', function (e) {
  if (!window.pywebview) return;
  var t = e.target;
  if (t && t.closest && t.closest('input, textarea, [contenteditable=""], [contenteditable="true"]')) return;
  var sel = window.getSelection && window.getSelection();
  if (sel && String(sel).trim()) return;
  e.preventDefault();
}, true);
</script>"""


def layout(title: str, drawer: bool = True) -> None:
    ui.colors(primary=BRAND)
    from .state import get_state
    ui.dark_mode(value=bool(get_state().settings.dark_mode))
    ui.add_css(THEME_CSS)
    ui.add_head_html(CONTEXT_MENU_JS)
    with ui.header().classes("items-center py-2 px-4").style(f"background:{BRAND}"):
        ui.label("Proposal Builder").classes("text-lg font-semibold")
        ui.space()
        _saved_indicator()
        ui.label(title).classes("text-sm opacity-80")
        from .. import __version__
        ui.label(f"v{__version__}").classes("text-xs opacity-60")
        from .update_ui import header_slot
        header_slot()
    with ui.left_drawer(value=drawer, bordered=True).classes("p-0").props("width=210"):
        with ui.list().props("dense padding").classes("w-full"):
            for n, (group, items) in enumerate(NAV_GROUPS):
                if n:
                    ui.separator()
                if group:
                    ui.item_label(group).props("header").classes("text-xs uppercase")
                for label, path, icon in items:
                    with ui.item(on_click=lambda p=path: ui.navigate.to(p)).props("clickable") \
                            .classes("pb-navsel" if label == title else ""):
                        with ui.item_section().props("avatar"):
                            ui.icon(icon, size="xs")
                        with ui.item_section():
                            ui.item_label(label).classes("font-semibold" if label == title else "")


# ---------------------------------------------------------------- saved indicator


def _saved_indicator() -> None:
    """Small "Saved 6:41 PM" in the top bar, updated by every write to the data folder."""
    from .. import store
    lbl = ui.label("").classes("text-xs opacity-80 mr-3")
    lbl.set_visibility(False)
    ui.context.client.pb_saved_label = lbl
    if _flash_saved not in store.SAVE_HOOKS:
        store.SAVE_HOOKS.append(_flash_saved)


def _flash_saved(_path=None) -> None:
    try:
        client = ui.context.client
    except Exception:  # noqa: BLE001  no page context (startup, background thread)
        return
    lbl = getattr(client, "pb_saved_label", None)
    if lbl is not None:
        lbl.set_text(f"Saved {datetime.now():%I:%M %p}".replace(" 0", " "))
        lbl.set_visibility(True)


# ---------------------------------------------------------------- page frame


def page_title(title: str, help_text: str = "") -> None:
    """Title and one line of help at the top of every page."""
    ui.label(title).classes("text-xl font-semibold")
    if help_text:
        ui.label(help_text).classes("text-xs text-gray-500 mb-1")


def toolbar():
    """Row for a page's main button(s) and its filter box."""
    return ui.row().classes("w-full items-center gap-2 mb-2 no-wrap")


def filter_box(grid_getter, placeholder: str = "Filter"):
    inp = ui.input(placeholder=placeholder).props("dense clearable").classes("w-64")
    inp.on_value_change(lambda e: grid_getter().run_grid_method("setGridOption", "quickFilterText", e.value or ""))
    return inp


def list_grid(rows: list[dict], cols: list[dict], on_open, empty: str, height: str = "calc(100vh - 230px)",
              key: str = "id"):
    """Read-only list; double-click a row to open it."""
    g = ui.aggrid({"columnDefs": cols, "rowData": rows, "rowHeight": 32, "headerHeight": 36,
                   "rowSelection": {"mode": "singleRow", "checkboxes": False, "enableClickSelection": True},
                   "defaultColDef": {"resizable": True, "sortable": True, "filter": True},
                   "overlayNoRowsTemplate": no_rows(empty)},
                  auto_size_columns=False).classes("w-full").style(f"height:{height}")
    g.on("cellDoubleClicked", lambda e: on_open(e.args["data"][key]))
    return g


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


def warn(problems) -> None:
    """Show save warnings. Anything other than a list (e.g. a save callback that returns a refresh handle) is
    ignored, so a grid always redraws after a save."""
    if isinstance(problems, list) and problems:
        ui.notify("Saved with warnings: " + "; ".join(problems[:5])
                  + (" ..." if len(problems) > 5 else ""), type="warning", multi_line=True, timeout=8000)


# ---------------------------------------------------------------- dates and money

DATE_FMT = "%Y.%m.%d"          # one date format everywhere (matches the proposal)
MONEY_JS = ("p => (p.value === null || p.value === undefined || p.value === '') ? '' : "
            "(Number(p.value) < 0 ? '-$' : '$') + Math.abs(Number(p.value)).toLocaleString('en-US', "
            "{minimumFractionDigits: 2, maximumFractionDigits: 2})")
DATE_JS = "p => p.value ? String(p.value).slice(0, 10).replaceAll('-', '.') : ''"


def fmt_date(d: date | datetime | None) -> str:
    return d.strftime(DATE_FMT) if d else ""


def parse_date(s: Any) -> date | None:
    """2026.10.20, 2026-10-20, 10/20/2026 or 10/20 (this year); blank -> None."""
    if s in (None, ""):
        return None
    if isinstance(s, date):
        return s
    txt = str(s).strip()
    for fmt in (DATE_FMT, "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(txt[:10], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.strptime(f"{txt}/{date.today().year}", "%m/%d/%Y").date()
    except ValueError:
        raise ValueError(f"not a date: {txt!r} (use {date.today():%Y.%m.%d})") from None


def date_input(label: str, value: date | None, readonly: bool = False):
    """Text field showing 2026.10.20 with a calendar picker. Read it back with parse_date(x.value)."""
    inp = ui.input(label, value=fmt_date(value), placeholder=f"{date.today():%Y.%m.%d}").props(
        "dense" + (" readonly" if readonly else ""))
    if not readonly:
        with ui.menu().props("no-parent-event") as menu:
            ui.date(mask="YYYY.MM.DD").bind_value(inp).on_value_change(lambda _: menu.close())
        with inp.add_slot("append"):
            ui.icon("event").on("click", menu.open).classes("cursor-pointer")
    return inp


def no_rows(text: str) -> str:
    """AG Grid empty-state overlay."""
    return f'<span class="text-sm text-gray-500">{text}</span>'


# ---------------------------------------------------------------- editable grid


@dataclass
class Col:
    field: str
    header: str
    kind: str = "text"                  # text | number | money | bool | select | list | strlist | date | lookup
    options: list[str] = field(default_factory=list)
    width: int | None = None
    flex: int | None = None
    editable: bool = True
    lookup: dict[str, str] | None = None   # kind "lookup": stored id -> shown label
    cell_class: dict[str, str] | None = None   # AG Grid cellClassRules: css class -> JS function of params


class EditableGrid:
    """Grid over a list of pydantic models. Every cell edit is written back and saved."""

    def __init__(self, models: Callable[[], list[BaseModel]], cols: list[Col],
                 save: Callable[[], list[str] | None], new_model: Callable[[], BaseModel] | None = None,
                 height: str = "70vh", readonly: bool = False, empty: str = "",
                 on_cell: Callable[[BaseModel, str], None] | None = None):
        self.models, self.cols, self.save, self.new_model = models, cols, save, new_model
        self.on_cell = on_cell                 # called with (model, field) after a cell edit, before save
        self.readonly = readonly
        if readonly:
            self.cols = cols = [Col(**{**c.__dict__, "editable": False}) for c in cols]
        toolbar = ui.row().classes("gap-2 mb-2 items-center")
        toolbar.set_visibility(not readonly)
        with toolbar:
            if new_model:
                ui.button("Add row", icon="add", on_click=self.add).props("outline dense")
            self.del_btn = ui.button("Delete selected", icon="delete", on_click=self.delete) \
                .props("outline dense color=negative")
            self.del_btn.disable()             # enabled once rows are ticked
            self.filter = ui.input(placeholder="Filter").props("dense clearable").classes("w-64")
            self.filter.on_value_change(lambda e: self.grid.run_grid_method("setGridOption", "quickFilterText", e.value or ""))
        if not empty:
            empty = ("Nothing here yet. Use Add row to add one." if new_model and not readonly else "Nothing here yet.")
        self.grid = ui.aggrid({
            "columnDefs": [self._coldef(c) for c in cols],
            "rowData": self._rows(),
            "rowSelection": {"mode": "multiRow"},
            "rowHeight": 32, "headerHeight": 36,
            "stopEditingWhenCellsLoseFocus": True,
            "overlayNoRowsTemplate": no_rows(empty),
        }).classes("w-full").style(f"height:{height}")
        self.grid.on("cellValueChanged", self._changed)
        self.grid.on("selectionChanged", self._selection)
        self.grid.on("cellDoubleClicked", self._date_pick)

    async def _selection(self, _=None) -> None:
        rows = await self.grid.get_selected_rows()
        self.del_btn.set_enabled(bool(rows))

    def _date_pick(self, e) -> None:
        """Date cells open a calendar (2026.10.20) instead of the browser's own date field."""
        col = next((c for c in self.cols if c.field == e.args.get("colId")), None)
        data = e.args.get("data", {})
        models = self.models()
        if col is None or col.kind != "date" or not col.editable or data.get("_i") is None \
                or data["_i"] >= len(models):
            return
        model = models[data["_i"]]
        cur = getattr(model, col.field)
        with ui.dialog() as dlg, ui.card():
            ui.label(col.header).classes("font-semibold")
            picker = ui.date(value=fmt_date(cur) or None, mask="YYYY.MM.DD")

            def done(value) -> None:
                try:
                    setattr(model, col.field, parse_date(value))
                except (ValidationError, ValueError) as err:
                    ui.notify(f"Not saved: {err}", type="negative")
                    return
                dlg.close()
                warn(self.save() or [])
                self.refresh()
            with ui.row().classes("w-full justify-end"):
                ui.button("Clear", on_click=lambda: done(None)).props("flat")
                ui.button("Cancel", on_click=dlg.close).props("flat")
                ui.button("OK", on_click=lambda: done(picker.value))
        dlg.open()

    def _coldef(self, c: Col) -> dict:
        d: dict[str, Any] = {"field": c.field, "headerName": c.header, "editable": c.editable,
                             "filter": True, "sortable": True, "resizable": True}
        if c.width:
            d["width"] = c.width
        if c.flex:
            d["flex"] = c.flex
        if c.cell_class:
            d["cellClassRules"] = {f":{cls}": fn for cls, fn in c.cell_class.items()}
        if c.kind == "number":
            d["cellDataType"] = "number"
        elif c.kind == "money":
            d["cellDataType"] = "number"
            d["type"] = "rightAligned"
            d[":valueFormatter"] = MONEY_JS
        elif c.kind == "date":
            d["editable"] = False                  # double-click opens the calendar (_date_pick)
            d["cellDataType"] = "text"
            d[":valueFormatter"] = DATE_JS
        elif c.kind == "bool":
            d["cellDataType"] = "boolean"
        elif c.kind == "select":
            d["cellEditor"] = "agSelectCellEditor"
            d["cellEditorParams"] = {"values": c.options}
        elif c.kind == "lookup":
            d["cellEditor"] = "agSelectCellEditor"
            d["cellEditorParams"] = {"values": ["", *c.lookup.values()]}
        elif c.kind in ("list", "strlist"):
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
        if c.kind in ("number", "money"):
            return to_decimal(v)
        if c.kind == "list":
            return [to_decimal(x) for x in str(v or "").split(",") if x.strip()]
        if c.kind == "strlist":
            return [x.strip() for x in str(v or "").split(",") if x.strip()]
        if c.kind == "date":
            return parse_date(v)
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
        if self.on_cell is not None:
            self.on_cell(model, field_)
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
        self.del_btn.disable()
