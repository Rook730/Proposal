"""Start the app:  python -m proposal_builder [--browser] [--port N] [--data DIR] [--self-test]"""

from __future__ import annotations

import argparse
import multiprocessing
import os
import socket
import sys
from pathlib import Path

from .native_menu import install as _install_native_menu

DEFAULT_PORT = 8731

# Runs in the native window's child process too (it imports this module before opening the window).
_install_native_menu()


def _free_port(preferred: int) -> int:
    """The preferred port if free, else any free port (a second copy of the app still starts)."""
    for port in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    return preferred


def _icon():
    from importlib import resources
    p = resources.files("proposal_builder") / "assets" / "icon.png"
    return Path(str(p)) if p.is_file() else "📐"


def _frozen_dir() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()


def main() -> None:
    multiprocessing.freeze_support()
    # A windowed .exe has no console: give libraries somewhere to write.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")  # noqa: SIM115
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")  # noqa: SIM115

    ap = argparse.ArgumentParser(prog="proposal_builder")
    ap.add_argument("--browser", action="store_true", help="open in a browser tab instead of a native window")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--data", help="data folder (overrides saved setting for this run)")
    ap.add_argument("--no-show", action="store_true", help="do not open a window or tab (testing)")
    ap.add_argument("--self-test", action="store_true", help="check data, calculation and PDF output, then exit")
    ap.add_argument("--apply-update", metavar="URL", help=argparse.SUPPRESS)  # CI check of the self-update path
    args, _ = ap.parse_known_args()

    if args.apply_update:
        from . import updater
        exe = updater.update_to(updater.Release(version="test", tag="test", exe_url=args.apply_update,
                                                exe_size=None, page=""))
        updater.relaunch(exe, ("--self-test",))
        sys.exit(0)

    if args.self_test:
        from .selftest import run_self_test
        ok, report = run_self_test()
        try:
            (_frozen_dir() / "selftest.log").write_text(report, encoding="utf-8")
        except OSError:
            pass
        print(report)
        sys.exit(0 if ok else 1)

    if args.data:
        os.environ["PROPOSAL_DATA_DIR"] = args.data

    from nicegui import ui

    from . import __version__
    from .ui import closeout, crm_pages, editor, pages, projects, summary_page  # noqa: F401  registers routes
    from .ui.state import get_state

    get_state()  # create/seed the data folder before the first request

    import threading

    from nicegui import app

    from . import updater
    updater.cleanup_old()  # leftover from the previous version after a self-update
    app.on_startup(lambda: threading.Thread(target=updater.check, daemon=True).start())

    native = not args.browser and not args.no_show and sys.platform == "win32"
    ui.run(title=f"Kept Spec Proposal Builder {__version__}", port=_free_port(args.port), reload=False,
           native=native, window_size=(1400, 900) if native else None, show=not args.no_show,
           favicon=_icon(), show_welcome_message=False)


if __name__ == "__main__":
    main()
