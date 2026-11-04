"""Opening a data folder that a sync service (Proton Drive) is still downloading: never seed over files the
folder should already have; wait, then say what is missing (2.0.1)."""

from pathlib import Path

import pytest

from proposal_builder import store as store_mod
from proposal_builder.store import DataFolderError, DataStore
from proposal_builder.ui.state import AppState


@pytest.fixture(autouse=True)
def no_wait(monkeypatch):
    monkeypatch.setattr(store_mod, "SYNC_WAIT_SECONDS", 0)


def _folder(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    AppState(DataStore(root))          # a full folder, as on the first PC
    return root


def test_new_folder_is_seeded(tmp_path: Path):
    root = _folder(tmp_path)
    assert (root / "profiles/ce/boilerplate.json").exists() and (root / "catalog.json").exists()


def test_known_company_file_missing_is_waited_for_not_recreated(tmp_path: Path):
    root = _folder(tmp_path)
    (root / "profiles/ce/boilerplate.json").unlink()          # not downloaded yet on this PC
    with pytest.raises(DataFolderError) as err:
        AppState(DataStore(root))
    assert err.value.missing == ["profiles/ce/boilerplate.json"]
    assert not (root / "profiles/ce/boilerplate.json").exists()
    assert "still be downloading" in str(err.value)
    DataStore(root).initialize_from_seed(repair=True)          # the files really were deleted
    AppState(DataStore(root))


def test_shared_file_missing_is_not_recreated(tmp_path: Path):
    root = _folder(tmp_path)
    (root / "catalog.json").unlink()
    with pytest.raises(DataFolderError) as err:
        DataStore(root).initialize_from_seed()
    assert err.value.missing == ["catalog.json"] and not (root / "catalog.json").exists()


def test_company_new_to_the_folder_is_still_seeded(tmp_path: Path):
    """A 1.10.1 folder (no Convenient Enterprises yet) gets its files on the first 2.0 start."""
    root = _folder(tmp_path)
    import json
    s = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    s["migrations"] = [m for m in s["migrations"] if m != "ce-performer"]
    (root / "settings.json").write_text(json.dumps(s), encoding="utf-8")
    for f in (root / "profiles/ce").iterdir():
        f.unlink()
    AppState(DataStore(root))
    assert (root / "profiles/ce/boilerplate.json").exists()


def test_requirement_library_made_elsewhere_is_waited_for(tmp_path: Path):
    root = _folder(tmp_path)
    st = AppState(DataStore(root))
    assert st.requirements.nodes and "ce-requirements" in st.settings.migrations
    (root / "profiles/ce/requirements.json").unlink()
    with pytest.raises(DataFolderError):
        _ = AppState(DataStore(root)).requirements
