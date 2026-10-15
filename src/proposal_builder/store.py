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

    # -- typed accessors
    def load_settings(self) -> Settings:
        return self.load("settings.json", Settings)

    def save_settings(self, s: Settings) -> None:
        self.save("settings.json", s)

    def load_catalog(self) -> Catalog:
        return self.load("catalog.json", Catalog)

    def save_catalog(self, c: Catalog) -> None:
        self.save("catalog.json", c)

    def load_boilerplate(self) -> Boilerplate:
        return self.load("boilerplate.json", Boilerplate)

    def save_boilerplate(self, b: Boilerplate) -> None:
        self.save("boilerplate.json", b)
