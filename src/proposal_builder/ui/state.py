"""In-process application state: one data folder, loaded once, saved on every edit."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..models import Boilerplate, Catalog, Settings
from ..store import DataStore, ProjectStore, resolve_data_dir


@dataclass
class AppState:
    store: DataStore
    settings: Settings = field(init=False)
    catalog: Catalog = field(init=False)
    boilerplate: Boilerplate = field(init=False)

    def __post_init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        if not self.store.is_initialized():
            self.store.initialize_from_seed()
        self.settings = self.store.load_settings()
        self.catalog = self.store.load_catalog()
        self.boilerplate = self.store.load_boilerplate()

    @property
    def projects(self) -> ProjectStore:
        return ProjectStore(self.store)

    def save_catalog(self) -> list[str]:
        """Save and return integrity warnings (saved regardless)."""
        self.store.save_catalog(self.catalog)
        return self.catalog.validate_refs()

    def save_settings(self) -> None:
        self.store.save_settings(self.settings)

    def save_boilerplate(self) -> None:
        self.store.save_boilerplate(self.boilerplate)


_state: AppState | None = None


def get_state() -> AppState:
    global _state
    if _state is None:
        _state = AppState(DataStore(resolve_data_dir()))
    return _state


def set_data_dir(path: Path) -> AppState:
    global _state
    _state = AppState(DataStore(path))
    return _state
