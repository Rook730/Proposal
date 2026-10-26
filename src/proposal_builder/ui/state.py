"""In-process application state: one data folder, loaded once, saved on every edit."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..crm import ContractorBook, CustomerBook, SupplierBook, add_from_sub_names, link_projects
from ..models import KS, PROFILES, Boilerplate, Catalog, Settings
from ..store import DataStore, ProjectStore, resolve_data_dir, share_settings


@dataclass
class AppState:
    store: DataStore
    settings: Settings = field(init=False)          # Kept Spec settings + the shared ones
    catalog: Catalog = field(init=False)
    boilerplate: Boilerplate = field(init=False)    # Kept Spec terms library
    profile_settings: dict[str, Settings] = field(init=False)      # other profiles
    profile_boilerplate: dict[str, Boilerplate] = field(init=False)
    customers: CustomerBook = field(init=False)
    contractors: ContractorBook = field(init=False)
    suppliers: SupplierBook = field(init=False)

    def __post_init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        # copies missing seed files only (never overwrites), e.g. the logo for older data folders
        self.store.initialize_from_seed()
        self.settings = self.store.load_settings()
        self.catalog = self.store.load_catalog()
        self.boilerplate = self.store.load_boilerplate()
        from ..migrations import migrate_library
        cat_changed, bp_changed = migrate_library(self.catalog, self.boilerplate)
        if cat_changed:
            self.store.save_catalog(self.catalog)
        if bp_changed:
            self.store.save_boilerplate(self.boilerplate)
        self.profile_settings, self.profile_boilerplate = {}, {}
        for key in PROFILES:
            if key != KS:
                self.profile_settings[key] = self.store.load_settings(key)
                self.profile_boilerplate[key] = self.store.load_boilerplate(key)
        self.customers = self.store.load_book("customers.json", CustomerBook)
        self.contractors = self.store.load_book("contractors.json", ContractorBook)
        self.suppliers = self.store.load_book("suppliers.json", SupplierBook)
        self._link_lists()
        if not self.settings.company.logo_path and self.store.path("logo.png").exists():
            self.settings.company.logo_path = "logo.png"
            self.save_settings()

    def link_lists(self) -> None:
        self._link_lists()

    def _link_lists(self) -> None:
        """Projects typed before the customer list existed get linked by client name; sub names become
        contractors. Revisions are not modified (issued ones are write-once)."""
        ps = self.projects
        try:
            projects = ps.list_projects()
        except OSError:
            return
        changed = link_projects(self.customers, projects)
        for p in changed:
            ps.save_project(p)
        if changed:
            self.save_customers()
        names = set()
        for p in projects:
            for r in ps.list_revisions(p.number):
                try:
                    names |= {ln.sub_name for ln in ps.load_revision(p.number, r).lines if ln.sub_name}
                except (OSError, ValueError):
                    continue
        if add_from_sub_names(self.contractors, names):
            self.save_contractors()

    def save_customers(self) -> None:
        self.store.save("customers.json", self.customers)

    def save_contractors(self) -> None:
        self.store.save("contractors.json", self.contractors)

    def save_suppliers(self) -> None:
        self.store.save("suppliers.json", self.suppliers)

    @property
    def projects(self) -> ProjectStore:
        return ProjectStore(self.store)

    def save_catalog(self) -> list[str]:
        """Save and return integrity warnings (saved regardless)."""
        self.store.save_catalog(self.catalog)
        return self.catalog.validate_refs()

    # -- per profile
    def settings_for(self, profile: str = KS) -> Settings:
        """The profile's settings; shared values (numbering, lists, performers...) are the Kept Spec ones."""
        if profile == KS or profile not in self.profile_settings:
            return self.settings
        return share_settings(self.profile_settings[profile], self.settings)

    def boilerplate_for(self, profile: str = KS) -> Boilerplate:
        if profile == KS or profile not in self.profile_boilerplate:
            return self.boilerplate
        return self.profile_boilerplate[profile]

    def save_settings(self, profile: str = KS) -> None:
        """Save a profile's settings. Shared values always save with the Kept Spec file."""
        self.store.save_settings(self.settings)
        if profile != KS and profile in self.profile_settings:
            self.store.save_settings(self.settings_for(profile), profile)

    def save_boilerplate(self, profile: str = KS) -> None:
        self.store.save_boilerplate(self.boilerplate_for(profile), profile)


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
