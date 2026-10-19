"""Shared PDF export and preview dialogs for non-proposal documents."""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

from nicegui import run, ui

from ..render.document import compile_document
from .widgets import BRAND


async def export_pdf(doc: dict, template: str, name: str, pdf_dir: Path, logo: Path | None) -> None:
    n = ui.notification("Building PDF...", spinner=True, timeout=None)
    try:
        pdf = await run.io_bound(compile_document, doc, logo, "pdf", 110, template)
    except Exception as e:  # noqa: BLE001
        n.dismiss()
        ui.notify(f"PDF failed: {e}", type="negative", multi_line=True)
        return
    n.dismiss()
    path = pdf_dir / name
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


async def preview_pdf(doc: dict, template: str, title: str, logo: Path | None) -> None:
    n = ui.notification("Rendering preview...", spinner=True, timeout=None)
    try:
        pages = await run.io_bound(compile_document, doc, logo, "png", 80, template)
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

