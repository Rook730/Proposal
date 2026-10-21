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
OLD_ALLOWANCES = ("Allowance items are budget amounts for Client selections. Actual cost is billed as incurred and "
                  "reconciled on the final invoice. Overhead and profit percentages apply to the net allowance "
                  "variance, whether an overage (billed) or underage (credited).")
OLD_ZERO = ("A line showing $0 is one of two things:\n\nWork that is not included in this proposal, listed so the "
            "scope is clear.\nAn owner-furnished item, which you purchase directly. We show it so the coordination "
            "and installation scope is clear.")
# 1.6.2: a $0 line is included at no charge; Not included lines say so in the Cost column
OLD_ZERO_2 = ("A line showing $0 is work that is not included in this proposal, listed so the scope is clear.\n\n"
              "Owner-supplied items are purchased directly by you. We list them so the coordination and installation "
              "scope is clear. When an estimated cost is known it is shown in parentheses; it is not part of the "
              "subtotal or Total Price. The Total *Incl. Owner-supplied items line adds these costs to show the full "
              "project cost.")


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
    # 1.5.1: overhead and profit apply to the variance on every line (cost-plus), not only allowances
    blk = next((b for b in boilerplate.blocks if b.id == "scope-clarif-allowances"), None)
    if blk is not None and blk.body == OLD_ALLOWANCES:
        from .added_terms import NEW
        from .models import BoilerplateBlock
        blk.body = NEW["scope-clarif-allowances"][2]
        if not any(b.id == "scope-clarif-actual-cost" for b in boilerplate.blocks):
            heading, title, body, order = NEW["scope-clarif-actual-cost"]
            boilerplate.blocks.append(BoilerplateBlock(id="scope-clarif-actual-cost", heading=heading,
                                                       title=title, body=body, order=order))
        bp_changed = True
    blk = next((b for b in boilerplate.blocks if b.id == "zero-lines"), None)
    if blk is not None and blk.body in (OLD_ZERO, OLD_ZERO_2):
        from .added_terms import NEW
        _, title, body, _ = NEW["zero-lines"]
        blk.title, blk.body = title, body
        bp_changed = True
    return cat_changed, bp_changed
