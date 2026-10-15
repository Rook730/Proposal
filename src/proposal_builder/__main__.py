"""Start the app:  python -m proposal_builder [--browser] [--port N] [--data DIR]"""

from __future__ import annotations

import argparse
import os
import sys


def main() -> None:
    ap = argparse.ArgumentParser(prog="proposal_builder")
    ap.add_argument("--browser", action="store_true", help="open in a browser tab instead of a native window")
    ap.add_argument("--port", type=int, default=8731)
    ap.add_argument("--data", help="data folder (overrides saved setting for this run)")
    ap.add_argument("--no-show", action="store_true", help="do not open a window or tab (testing)")
    args, _ = ap.parse_known_args()

    if args.data:
        os.environ["PROPOSAL_DATA_DIR"] = args.data

    from nicegui import ui

    from .ui import pages  # noqa: F401  registers routes
    from .ui.state import get_state

    get_state()  # create/seed the data folder before the first request

    native = not args.browser and not args.no_show and sys.platform == "win32"
    ui.run(title="Kept Spec Proposal Builder", port=args.port, reload=False, native=native,
           window_size=(1400, 900) if native else None, show=not args.no_show,
           favicon="📐")


if __name__ == "__main__":
    main()
