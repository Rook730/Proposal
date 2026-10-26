"""In-app updates from GitHub Releases.

Only the one-file .exe updates itself. Windows lets a running .exe be renamed but not
overwritten, so the update:
  1. downloads the new .exe next to the current one as "<name>.new",
  2. renames the running .exe to "<name>.old" and "<name>.new" to the original name,
  3. starts the new .exe and closes this one.
The new copy deletes the leftover ".old" on start. Data lives outside the program folder,
so nothing else changes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from . import __version__

REPO = "Rook730/Proposal"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
TIMEOUT = 8


@dataclass
class Release:
    version: str            # "1.3.0"
    tag: str                # "v1.3.0"
    exe_url: str | None
    exe_size: int | None
    page: str


def parse_version(v: str) -> tuple[int, ...]:
    parts = []
    for p in v.strip().lstrip("vV").split("."):
        digits = "".join(ch for ch in p if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer(candidate: str, current: str = __version__) -> bool:
    return parse_version(candidate) > parse_version(current)


def release_from_json(data: dict) -> Release:
    tag = data.get("tag_name", "")
    exe = next((a for a in data.get("assets", []) if a.get("name", "").lower().endswith(".exe")), None)
    return Release(version=tag.lstrip("vV"), tag=tag,
                   exe_url=exe.get("browser_download_url") if exe else None,
                   exe_size=exe.get("size") if exe else None,
                   page=data.get("html_url") or RELEASES_PAGE)


def latest_release() -> Release:
    req = urllib.request.Request(API_LATEST, headers={"Accept": "application/vnd.github+json",
                                                      "User-Agent": f"ProposalBuilder/{__version__}"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310  fixed https URL
        return release_from_json(json.load(r))


# ---------------------------------------------------------------- self-replacement


def running_exe() -> Path | None:
    """The one-file .exe this process runs from, or None (source run or folder build)."""
    if not getattr(sys, "frozen", False):
        return None
    exe = Path(sys.executable)
    meipass = Path(getattr(sys, "_MEIPASS", exe.parent))
    # one-file builds unpack to a temp folder; the folder build runs from beside the .exe
    if exe.suffix.lower() != ".exe" or exe.parent in meipass.parents or meipass == exe.parent:
        return None
    return exe


def cleanup_old(exe: Path | None = None) -> None:
    exe = exe or running_exe()
    if exe is None:
        return
    for leftover in (exe.with_name(exe.name + ".old"), exe.with_name(exe.name + ".new")):
        try:
            leftover.unlink(missing_ok=True)
        except OSError:
            pass  # still locked by the old process; next start removes it


def download(url: str, dest: Path, expected_size: int | None = None, progress=None) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": f"ProposalBuilder/{__version__}"})
    tmp = dest.with_name(dest.name + ".part")
    got = 0
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:  # noqa: S310
        total = expected_size or int(r.headers.get("Content-Length") or 0) or None
        while chunk := r.read(1 << 20):
            f.write(chunk)
            got += len(chunk)
            if progress:
                progress(got, total)
    if expected_size and got != expected_size:
        tmp.unlink(missing_ok=True)
        raise OSError(f"download incomplete ({got} of {expected_size} bytes)")
    os.replace(tmp, dest)


def swap_in(exe: Path, new_file: Path) -> None:
    """Replace the running exe with new_file (same folder). Keeps the old one as .old."""
    old = exe.with_name(exe.name + ".old")
    try:
        old.unlink(missing_ok=True)
    except OSError:
        pass
    os.replace(exe, old)          # renaming a running .exe is allowed on Windows
    try:
        os.replace(new_file, exe)
    except OSError:
        os.replace(old, exe)      # put the original back
        raise


def relaunch(exe: Path, args: tuple[str, ...] = ()) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("_PYI", "_MEIPASS"))}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"   # the new exe unpacks fresh instead of reusing ours
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([str(exe), *args], env=env, cwd=str(exe.parent), close_fds=True,  # noqa: S603
                     creationflags=flags)


def update_to(release: Release, progress=None) -> Path:
    """Download and swap in the release's exe. Returns the exe path to relaunch."""
    exe = running_exe()
    if exe is None:
        raise RuntimeError("This copy cannot update itself (it is not the one-file .exe).")
    if not release.exe_url:
        raise RuntimeError(f"Release {release.tag} has no .exe attached.")
    new_file = exe.with_name(exe.name + ".new")
    download(release.exe_url, new_file, release.exe_size, progress)
    swap_in(exe, new_file)
    return exe


# ---------------------------------------------------------------- app-wide state


@dataclass
class CheckState:
    checked: bool = False
    release: Release | None = None
    error: str = ""

    @property
    def update_available(self) -> bool:
        return self.release is not None and is_newer(self.release.version)


STATE = CheckState()


def check() -> CheckState:
    """Ask GitHub for the latest release. Never raises; offline just means no update shown."""
    try:
        STATE.release, STATE.error = latest_release(), ""
    except Exception as err:  # noqa: BLE001  network, proxy, rate limit, bad JSON
        STATE.error = str(err)
    STATE.checked = True
    return STATE
