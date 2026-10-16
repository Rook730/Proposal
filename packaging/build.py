"""Build the standalone app with PyInstaller.

    python packaging/build.py            # one-file executable (Windows: "KeptSpec Proposal Builder.exe")
    python packaging/build.py --onedir   # folder build, faster start, zip it to share

Run from the repo root with the project installed (pip install -e .[native] pyinstaller).
Output goes to dist/. The build is checked with --self-test afterwards.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import nicegui

ROOT = Path(__file__).resolve().parents[1]
NAME = "KeptSpec Proposal Builder"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--onedir", action="store_true")
    ap.add_argument("--console", action="store_true", help="keep a console window (debugging)")
    args = ap.parse_args()

    sep = os.pathsep
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--name", NAME,
        "--onedir" if args.onedir else "--onefile",
        "--icon", str(ROOT / "packaging" / "icon.ico"),
        "--add-data", f"{Path(nicegui.__file__).parent}{sep}nicegui",
        "--collect-data", "proposal_builder",
        "--collect-submodules", "proposal_builder",
        "--collect-all", "typst",
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT / "build"),
    ]
    if sys.platform == "win32":
        cmd += ["--collect-all", "webview", "--collect-all", "clr_loader", "--collect-all", "pythonnet"]
    if not args.console:
        cmd.append("--windowed")
    cmd.append(str(ROOT / "packaging" / "launcher.py"))
    print(" ".join(f'"{c}"' if " " in c else c for c in cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT)

    exe = ROOT / "dist" / (NAME if not args.onedir else f"{NAME}/{NAME}")
    if sys.platform == "win32":
        exe = exe.with_name(exe.name + ".exe")
    print(f"built {exe}", flush=True)
    r = subprocess.run([str(exe), "--self-test"], capture_output=True, text=True, timeout=600)
    log = exe.parent / "selftest.log"
    report = log.read_text(encoding="utf-8") if log.exists() else (r.stdout + r.stderr)
    print(report)
    return 0 if r.returncode == 0 and "SELF-TEST PASSED" in report else 1


if __name__ == "__main__":
    sys.exit(main())
