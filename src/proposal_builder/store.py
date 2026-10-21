"""File-based storage.

Layout under the data folder (a Proton Drive synced folder in production):

    settings.json
    catalog.json
    boilerplate.json
    projects/<number>_<name>/...      (milestone 2+)
    backups/<file>.<timestamp>.json

Writes are atomic (temp file + os.replace) so a sync client never sees a
half-written file. The previous version of a file is copied to backups/
before every overwrite; the newest MAX_BACKUPS per file are kept.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime
from importlib import resources
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .models import Boilerplate, Catalog, Settings

MAX_BACKUPS = 50
APP_DIR_NAME = "KeptSpecProposal"
DEFAULT_DATA_DIR_NAME = "KeptSpec Proposals"

T = TypeVar("T", bound=BaseModel)

SEED_ASSETS = ["logo.png"]

FILES: dict[str, type[BaseModel]] = {
    "settings.json": Settings,
    "catalog.json": Catalog,
    "boilerplate.json": Boilerplate,
}


# ---------------------------------------------------------------- config


def config_path() -> Path:
    base = os.environ.get("APPDATA") or os.path.join(Path.home(), ".config")
    return Path(base) / APP_DIR_NAME / "config.json"


def resolve_data_dir() -> Path:
    """PROPOSAL_DATA_DIR env var > config file > ~/KeptSpec Proposals."""
    env = os.environ.get("PROPOSAL_DATA_DIR")
    if env:
        return Path(env)
    cfg = config_path()
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            if data.get("data_dir"):
                return Path(data["data_dir"])
        except (OSError, ValueError):
            pass
    return Path.home() / DEFAULT_DATA_DIR_NAME


def save_data_dir(path: Path) -> None:
    cfg = config_path()
    cfg.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(cfg, json.dumps({"data_dir": str(path)}, indent=2))


# ---------------------------------------------------------------- io helpers


# called after every successful write (the app shows a "Saved" time in the top bar)
SAVE_HOOKS: list = []


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    for hook in SAVE_HOOKS:
        try:
            hook(path)
        except Exception:  # noqa: BLE001  a display hook must never break a save
            pass


def dump_model(model: BaseModel) -> str:
    return model.model_dump_json(indent=2) + "\n"


class DataStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    # -- paths
    def path(self, name: str) -> Path:
        return self.root / name

    @property
    def backup_dir(self) -> Path:
        return self.root / "backups"

    @property
    def projects_dir(self) -> Path:
        return self.root / "projects"

    # -- lifecycle
    def is_initialized(self) -> bool:
        return all(self.path(n).exists() for n in FILES)

    def initialize_from_seed(self, overwrite: bool = False) -> list[str]:
        """Copy packaged seed files into the data folder. Returns files written."""
        self.root.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(exist_ok=True)
        written = []
        seed = resources.files("proposal_builder") / "seed"
        for name in FILES:
            dest = self.path(name)
            if dest.exists() and not overwrite:
                continue
            text = (seed / name).read_text(encoding="utf-8")
            FILES[name].model_validate_json(text)  # refuse a broken seed
            if dest.exists():
                self._backup(dest)
            _atomic_write(dest, text)
            written.append(name)
        for name in SEED_ASSETS:
            dest = self.path(name)
            if not dest.exists():
                dest.write_bytes((seed / name).read_bytes())
                written.append(name)
        return written

    # -- generic load/save
    def load(self, name: str, cls: type[T]) -> T:
        return cls.model_validate_json(self.path(name).read_text(encoding="utf-8"))

    def save(self, name: str, model: BaseModel) -> None:
        text = dump_model(model)
        dest = self.path(name)
        if dest.exists():
            if dest.read_text(encoding="utf-8") == text:
                return
            self._backup(dest)
        _atomic_write(dest, text)

    def _backup(self, src: Path) -> Path:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        dest = self.backup_dir / f"{src.stem}.{stamp}{src.suffix}"
        shutil.copy2(src, dest)
        old = sorted(self.backup_dir.glob(f"{src.stem}.*{src.suffix}"))
        for p in old[:-MAX_BACKUPS]:
            p.unlink(missing_ok=True)
        return dest

    def backup_zip(self) -> Path:
        """Zip the whole data folder (except backups/) into backups/full-<timestamp>.zip."""
        import zipfile
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dest = self.backup_dir / f"full-{stamp}.zip"
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(self.root.rglob("*")):
                if f.is_file() and self.backup_dir not in f.parents and not f.name.startswith("."):
                    z.write(f, f.relative_to(self.root).as_posix())
        return dest

    # -- typed accessors
    def load_settings(self) -> Settings:
        return self.load("settings.json", Settings)

    def save_settings(self, s: Settings) -> None:
        self.save("settings.json", s)

    def load_catalog(self) -> Catalog:
        return self.load("catalog.json", Catalog)

    def save_catalog(self, c: Catalog) -> None:
        self.save("catalog.json", c)

    def load_book(self, name: str, cls: type[T]) -> T:
        """Optional list files (customers, contractors, suppliers): empty when missing."""
        return self.load(name, cls) if self.path(name).exists() else cls()

    def load_boilerplate(self) -> Boilerplate:
        return self.load("boilerplate.json", Boilerplate)

    def save_boilerplate(self, b: Boilerplate) -> None:
        self.save("boilerplate.json", b)


# ---------------------------------------------------------------- projects


def _rev_key(rev: str) -> tuple[int, ...]:
    return tuple(int(p) for p in rev.split(".") if p.isdigit())


class ProjectStore:
    """projects/<number>_<name>/project.json and rev_<rev>.json files."""

    def __init__(self, store: DataStore):
        self.store = store

    @property
    def root(self) -> Path:
        return self.store.projects_dir

    def project_dir(self, number: str) -> Path | None:
        if not self.root.exists():
            return None
        for d in sorted(self.root.iterdir()):
            if d.is_dir() and (d.name == number or d.name.startswith(number + "_")) and (d / "project.json").exists():
                return d
        return None

    def list_projects(self):
        from .proposal import Project
        out = []
        if self.root.exists():
            for f in sorted(self.root.glob("*/project.json")):
                try:
                    out.append(Project.model_validate_json(f.read_text(encoding="utf-8")))
                except ValueError:
                    continue
        return sorted(out, key=lambda p: p.number, reverse=True)

    def delete(self, number: str) -> Path:
        """Move a project folder to backups/deleted-projects/ (recoverable by moving it back)."""
        d = self.project_dir(number)
        if d is None:
            raise ValueError(f"project {number} not found")
        trash = self.store.backup_dir / "deleted-projects"
        trash.mkdir(parents=True, exist_ok=True)
        dest = trash / f"{d.name}_{datetime.now():%Y%m%d-%H%M%S}"
        shutil.move(str(d), str(dest))
        return dest

    def create(self, project, revision) -> Path:
        if self.project_dir(project.number):
            raise ValueError(f"project {project.number} already exists")
        d = self.root / project.folder_name
        d.mkdir(parents=True, exist_ok=False)
        self.save_project(project, d)
        self.save_revision(project.number, revision)
        return d

    def load_project(self, number: str):
        from .proposal import Project
        d = self.project_dir(number)
        if d is None:
            raise FileNotFoundError(f"project {number} not found")
        return Project.model_validate_json((d / "project.json").read_text(encoding="utf-8"))

    def save_project(self, project, folder: Path | None = None) -> None:
        d = folder or self.project_dir(project.number)
        if d is None:
            raise FileNotFoundError(f"project {project.number} not found")
        self._save(d / "project.json", project)

    def list_revisions(self, number: str) -> list[str]:
        d = self.project_dir(number)
        if d is None:
            return []
        revs = [p.stem[len("rev_"):] for p in d.glob("rev_*.json")]
        return sorted(revs, key=_rev_key)

    def load_revision(self, number: str, rev: str | None = None):
        from .proposal import Revision
        revs = self.list_revisions(number)
        if not revs:
            raise FileNotFoundError(f"project {number} has no revisions")
        rev = rev or revs[-1]
        d = self.project_dir(number)
        return Revision.model_validate_json((d / f"rev_{rev}.json").read_text(encoding="utf-8"))

    def save_revision(self, number: str, revision, allow_locked: bool = False) -> None:
        """Issued revisions are write-once: saving over one needs allow_locked (state changes only)."""
        d = self.project_dir(number)
        if d is None:
            raise FileNotFoundError(f"project {number} not found")
        path = d / f"rev_{revision.rev}.json"
        if path.exists() and not allow_locked:
            from .proposal import Revision
            on_disk = Revision.model_validate_json(path.read_text(encoding="utf-8"))
            if on_disk.locked:
                raise PermissionError(f"revision {revision.rev} is {on_disk.state.value.lower()} and locked")
        self._save(path, revision)

    def _save(self, path: Path, model: BaseModel) -> None:
        text = dump_model(model)
        if path.exists():
            if path.read_text(encoding="utf-8") == text:
                return
            backup_dir = self.store.backup_dir / "projects" / path.parent.name
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            shutil.copy2(path, backup_dir / f"{path.stem}.{stamp}{path.suffix}")
            old = sorted(backup_dir.glob(f"{path.stem}.*{path.suffix}"))
            for p in old[:-MAX_BACKUPS]:
                p.unlink(missing_ok=True)
        _atomic_write(path, text)

    # -- change orders and reconciliation (one file each per project)
    def load_change_orders(self, number: str):
        from .closeout import ChangeOrderLog
        p = self.project_dir(number) / "change_orders.json"
        return ChangeOrderLog.model_validate_json(p.read_text(encoding="utf-8")) if p.exists() else ChangeOrderLog()

    def save_change_orders(self, number: str, log) -> None:
        self._save(self.project_dir(number) / "change_orders.json", log)

    def load_quotes(self, number: str):
        from .quotes import QuoteLog
        p = self.project_dir(number) / "quotes.json"
        return QuoteLog.model_validate_json(p.read_text(encoding="utf-8")) if p.exists() else QuoteLog()

    def save_quotes(self, number: str, log) -> None:
        self._save(self.project_dir(number) / "quotes.json", log)

    def load_reconciliation(self, number: str):
        from .closeout import Reconciliation
        p = self.project_dir(number) / "reconciliation.json"
        return Reconciliation.model_validate_json(p.read_text(encoding="utf-8")) if p.exists() else Reconciliation()

    def save_reconciliation(self, number: str, recon) -> None:
        self._save(self.project_dir(number) / "reconciliation.json", recon)
