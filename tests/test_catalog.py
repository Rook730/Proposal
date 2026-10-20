import json
import os
from decimal import Decimal
from importlib import resources
from pathlib import Path

import pytest

from proposal_builder.models import (
    Boilerplate,
    Catalog,
    CatalogItem,
    PriceSource,
    Settings,
    Tier,
)
from proposal_builder.store import MAX_BACKUPS, DataStore


def seed(name: str) -> str:
    return (resources.files("proposal_builder") / "seed" / name).read_text(encoding="utf-8")


@pytest.fixture
def catalog() -> Catalog:
    return Catalog.model_validate_json(seed("catalog.json"))


# ---------------------------------------------------------------- seed content


def test_seed_files_validate():
    Settings.model_validate_json(seed("settings.json"))
    Boilerplate.model_validate_json(seed("boilerplate.json"))
    Catalog.model_validate_json(seed("catalog.json"))


def test_seed_catalog_has_no_integrity_problems(catalog):
    assert catalog.validate_refs() == []


def test_seed_catalog_scope(catalog):
    codes = {i.code for i in catalog.items}
    assert len(catalog.sections) == 14
    assert max(codes) < 2000, "lamp restoration items must be dropped"
    assert {1121, 1141, 1142, 1143, 1144, 1171} <= codes, "new allowance items"
    assert len(codes) == len(catalog.items), "codes are unique"
    assert any(u.code == "PR" for u in catalog.units)


def test_seed_catalog_fixes(catalog):
    assert "utility connection" in catalog.item(450).description.lower()
    assert catalog.item(450).description != catalog.item(410).description


def test_percent_items(catalog):
    pct = {i.code: i.price for i in catalog.items if i.price_source is PriceSource.PERCENT}
    assert pct == {130: Decimal("0.005"), 1310: Decimal("0.05"), 1320: Decimal("0.05"),
                   1410: Decimal("0.05"), 1420: Decimal("0.1")}
    assert sum(pct.values()) == Decimal("0.255")


def test_rate_resolution(catalog):
    assert catalog.unit_price(catalog.item(210)) == Decimal("75")
    assert catalog.unit_price(catalog.item(626)) == Decimal("95")
    assert catalog.unit_price(catalog.item(330)) == Decimal("35")


def test_allowance_resolution(catalog):
    tile = catalog.item(1121)
    first = catalog.allowance(tile.allowance_ids[0])
    assert catalog.unit_price(tile) == first.high          # default tier = high
    assert catalog.unit_price(tile, Tier.LOW) == first.low
    assert first.mid == ((first.low + first.high) / 2).quantize(Decimal("0.01"))


def test_stock_lengths(catalog):
    trim = next(s for s in catalog.stock_classes if s.key == "trim")
    assert trim.lengths_ft == [Decimal(x) for x in (8, 10, 12, 16, 20)]
    assert catalog.item(940).stock_class == "trim"


def test_validate_refs_flags_problems(catalog):
    catalog.items.append(CatalogItem(code=210, section=999, title="dup", unit="ZZ"))
    problems = " | ".join(catalog.validate_refs())
    assert "duplicate item code 210" in problems
    assert "unknown section 999" in problems
    assert "unknown unit ZZ" in problems


def test_rate_item_requires_rate_key():
    with pytest.raises(ValueError):
        CatalogItem(code=1, section=100, title="x", price_source=PriceSource.RATE)


def test_boilerplate_groups():
    bp = Boilerplate.model_validate_json(seed("boilerplate.json"))
    titles = {b.title for b in bp.by_heading("Payment Schedule")}
    assert titles == {"Contract Execution / Mobilization", "Construction Progress Payments",
                      "Allowances & Change Orders", "Substantial Completion", "Final Payment"}
    assert len(bp.by_heading("Scope Clarifications & Exclusions")) == 12
    assert all(b.body for b in bp.blocks)
    validity = next(b for b in bp.blocks if b.title == "Proposal Validity")
    assert "{validity_days}" in validity.body


# ---------------------------------------------------------------- storage


def test_store_seed_and_roundtrip(tmp_path: Path):
    ds = DataStore(tmp_path / "data")
    assert not ds.is_initialized()
    assert set(ds.initialize_from_seed()) == {"settings.json", "catalog.json", "boilerplate.json", "logo.png"}
    assert ds.is_initialized()
    assert ds.initialize_from_seed() == []          # never overwrites silently

    cat = ds.load_catalog()
    cat.item(1180).title = "Countertop (edited)"
    ds.save_catalog(cat)
    assert ds.load_catalog().item(1180).title == "Countertop (edited)"
    assert len(list(ds.backup_dir.glob("catalog.*.json"))) == 1


def test_store_skips_identical_save(tmp_path: Path):
    ds = DataStore(tmp_path)
    ds.initialize_from_seed()
    ds.save_catalog(ds.load_catalog())
    assert not ds.backup_dir.exists() or not list(ds.backup_dir.glob("catalog.*"))


def test_backup_rotation(tmp_path: Path):
    ds = DataStore(tmp_path)
    ds.initialize_from_seed()
    s = ds.load_settings()
    for n in range(MAX_BACKUPS + 5):
        s.validity_days = 100 + n
        ds.save_settings(s)
    assert len(list(ds.backup_dir.glob("settings.*.json"))) == MAX_BACKUPS
    assert ds.load_settings().validity_days == 100 + MAX_BACKUPS + 4


def test_saved_json_is_readable(tmp_path: Path):
    ds = DataStore(tmp_path)
    ds.initialize_from_seed()
    data = json.loads(ds.path("catalog.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == 1


# ---------------------------------------------------------------- importer


@pytest.mark.skipif(not os.environ.get("PROPOSAL_XLSX"), reason="set PROPOSAL_XLSX to the workbook path")
def test_importer_matches_seed():
    from proposal_builder.importer import import_workbook
    s, c, b = import_workbook(Path(os.environ["PROPOSAL_XLSX"]))
    assert c.model_dump() == Catalog.model_validate_json(seed("catalog.json")).model_dump()
    assert b.model_dump() == Boilerplate.model_validate_json(seed("boilerplate.json")).model_dump()


def test_migration_updates_only_untouched_text():
    from proposal_builder.migrations import OLD_1320, OLD_GRAY, migrate_library
    cat = Catalog.model_validate_json(seed("catalog.json"))
    bp = Boilerplate.model_validate_json(seed("boilerplate.json"))
    new_1320 = cat.item(1320).description
    cat.item(1320).description = OLD_1320
    next(b for b in bp.blocks if b.id == "gray-lines").body = OLD_GRAY
    assert migrate_library(cat, bp) == (True, True)
    assert cat.item(1320).description == new_1320
    cat.item(1320).description = "my own wording"
    assert migrate_library(cat, bp) == (False, False)
    assert cat.item(1320).description == "my own wording"


def test_unit_rename_and_missing_unit_options():
    from importlib import resources
    from proposal_builder.models import Catalog
    cat = Catalog.model_validate_json((resources.files("proposal_builder") / "seed" / "catalog.json").read_text())
    users = cat.unit_users("EA")
    assert users
    n = cat.rename_unit("EA", "EACH")
    assert n == len(users) and not cat.unit_users("EA") and len(cat.unit_users("EACH")) == n
    opts = cat.unit_options("EACH")                     # "EACH" is not in Units yet
    assert list(opts)[0] == "EACH" and "not in Units" in opts["EACH"]
    assert "LF" in opts and cat.unit_options("LF") == {u.code: u.code for u in cat.units}
