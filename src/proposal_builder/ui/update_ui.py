"""Header button and dialog for in-app updates (see updater.py)."""

from __future__ import annotations

import webbrowser

from nicegui import app, run, ui

from .. import __version__, updater


@ui.refreshable
def update_badge() -> None:
    if updater.STATE.update_available:
        rel = updater.STATE.release
        ui.button(f"Update to v{rel.version}", icon="system_update", on_click=lambda: update_dialog(rel)) \
            .props("dense unelevated no-caps color=amber-7 text-color=black").classes("ml-3")


def header_slot() -> None:
    """Call inside the page header."""
    update_badge()
    if not updater.STATE.checked:
        ui.timer(5, update_badge.refresh, once=True)   # startup check is still running


async def check_now() -> None:
    st = await run.io_bound(updater.check)
    update_badge.refresh()
    if st.error:
        ui.notify(f"Could not check for updates: {st.error}", type="warning", multi_line=True)
    elif st.update_available:
        update_dialog(st.release)
    else:
        ui.notify(f"You have the latest version (v{__version__}).", type="positive")


def update_dialog(rel: updater.Release) -> None:
    can_self = updater.running_exe() is not None
    with ui.dialog() as dlg, ui.card().classes("w-[460px]"):
        ui.label(f"Update to v{rel.version}").classes("text-lg font-semibold")
        ui.label(f"You have v{__version__}. Your proposals and settings are stored in your data folder "
                 "and are not touched by an update.").classes("text-sm")
        if can_self:
            ui.label("The new version downloads (about 65 MB), then the app closes and reopens. "
                     "Changes are saved as you work, so nothing is lost.").classes("text-sm text-gray-600")
        else:
            ui.label("This copy cannot replace itself (it is the folder version or running from source). "
                     "Open the download page instead.").classes("text-sm text-gray-600")
        bar = ui.linear_progress(value=0, show_value=False).classes("w-full").style("visibility:hidden")
        status = ui.label().classes("text-xs text-gray-600")
        progress = {"got": 0, "total": None}

        def tick() -> None:
            if progress["total"]:
                bar.set_value(progress["got"] / progress["total"])
                status.set_text(f"{progress['got'] / 1e6:.0f} of {progress['total'] / 1e6:.0f} MB")
        timer = ui.timer(0.3, tick, active=False)

        async def go() -> None:
            btn.disable()
            bar.style("visibility:visible")
            timer.activate()
            try:
                exe = await run.io_bound(updater.update_to, rel,
                                         lambda g, t: progress.update(got=g, total=t))
            except Exception as err:  # noqa: BLE001
                timer.deactivate()
                status.set_text("")
                ui.notify(f"Update failed: {err}", type="negative", multi_line=True)
                btn.enable()
                return
            timer.deactivate()
            status.set_text("Restarting...")
            updater.relaunch(exe)
            ui.timer(1.0, app.shutdown, once=True)

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Not now", on_click=dlg.close).props("flat")
            if can_self:
                btn = ui.button("Download and restart", icon="system_update", on_click=go)
            else:
                btn = ui.button("Open download page", icon="open_in_new",
                                on_click=lambda: (webbrowser.open(rel.page), dlg.close()))
    dlg.open()
