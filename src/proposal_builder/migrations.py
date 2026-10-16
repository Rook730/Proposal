"""Small, safe updates to an existing data folder's library when a seed text changes.

A text is replaced only when it still matches the old seed exactly, so anything the
user edited is left alone. Saved proposals are never touched (snapshot rule).
"""

from __future__ import annotations

from importlib import resources

from .models import Boilerplate, Catalog

OLD_1320 = ("5% allowance for the project management relating to change orders that may arise during the course "
            "of this project. \n*This amount to be deducted from the final invoice if no change orders are issued.")
OLD_GRAY = ("These have a percentage unit price: builder’s risk, contingency, change order management, overhead "
            "and profit. They are not part of the subtotal. Each is calculated as a percentage of the subtotal and "
            "added to reach the Total Price. Unused contingency is credited on the final invoice.")


def _seed_catalog() -> Catalog:
    return Catalog.model_validate_json((resources.files("proposal_builder") / "seed" / "catalog.json")
                                       .read_text(encoding="utf-8"))


def _seed_boilerplate() -> Boilerplate:
    return Boilerplate.model_validate_json((resources.files("proposal_builder") / "seed" / "boilerplate.json")
                                           .read_text(encoding="utf-8"))


def migrate_library(catalog: Catalog, boilerplate: Boilerplate) -> tuple[bool, bool]:
    """Returns (catalog_changed, boilerplate_changed)."""
    cat_changed = bp_changed = False
    item = catalog.item(1320)
    if item is not None and item.description == OLD_1320:
        new = _seed_catalog().item(1320)
        if new is not None:
            item.description = new.description
            cat_changed = True
    blk = next((b for b in boilerplate.blocks if b.id == "gray-lines"), None)
    if blk is not None and blk.body == OLD_GRAY:
        new = next((b for b in _seed_boilerplate().blocks if b.id == "gray-lines"), None)
        if new is not None:
            blk.body = new.body
            bp_changed = True
    return cat_changed, bp_changed
