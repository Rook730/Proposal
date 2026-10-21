"""Content checks for the Issues tab and the Issue dialog: $0 lines, leftover placeholders,
Allowance wording against the Allowance flag, lines added twice, and blank project info.
Each returns (kind, message) with kind "error", "warn" or "info"."""

from __future__ import annotations

import re
from collections import defaultdict

from .spelling import text_fields

PLACEHOLDER = re.compile(
    r"(?<![A-Za-z])(?:TBD|TBA|TODO)(?![A-Za-z])"     # to be determined
    r"|(?<![A-Za-z0-9])[Xx]{2,}(?![A-Za-z0-9])"       # XX, $XXX
    r"|\?{2,}"                                       # ??
    r"|\[\s*\]",                                     # [ ]
    re.IGNORECASE)
_ALLOWANCE_START = re.compile(r"^\W*allowance\b", re.IGNORECASE)


def _printed(rev, ln) -> bool:
    return ln.section in rev.sections


def zero_lines(rev, results) -> list[tuple[str, str]]:
    out = []
    for ln in rev.lines:
        if not _printed(rev, ln) or ln.is_percent or ln.not_included or ln.owner_furnished:
            continue
        lr = results.lines.get(ln.id)
        if lr is None or lr.qty == 0 or (ln.unit_price is None and not ln.price_var):
            continue                     # quantity 0 / no price are reported separately
        if lr.cost == 0:
            out.append(("warn", f"{ln.id} {ln.title}: prices at $0 but is not marked Not included (the terms "
                                "say a $0 line is not included); enter a price or mark it Not included"))
    return out


def placeholders(project, rev) -> list[tuple[str, str]]:
    out = []
    for place, text in text_fields(project, rev):
        found = list(dict.fromkeys(m.group(0) for m in PLACEHOLDER.finditer(text)))
        if found:
            out.append(("warn", f"{place.label}: placeholder {', '.join(found)} left in the text"))
    for v in rev.variables:
        found = list(dict.fromkeys(m.group(0) for m in PLACEHOLDER.finditer(v.value or "")))
        if found:
            out.append(("warn", f"Variable '{v.name}': placeholder {', '.join(found)} in its value"))
    return out


def _body_start(ln) -> str:
    """The text printed right after the "Allowance." label."""
    if ln.print_general and ln.general_description.strip():
        return ln.general_description
    return ln.notes or ""


def allowance_wording(rev) -> list[tuple[str, str]]:
    out = []
    for ln in rev.lines:
        if not _printed(rev, ln) or ln.is_percent:
            continue
        says = bool(_ALLOWANCE_START.match(_body_start(ln)))
        if ln.is_allowance and says:
            out.append(("info", f"{ln.id} {ln.title}: description starts with \"Allowance\" and the Allowance flag "
                                "also prints \"Allowance.\"; remove the word from the description"))
        elif not ln.is_allowance and (says or re.match(r"^\W*allowance\s+for\b", ln.title, re.IGNORECASE)):
            out.append(("info", f"{ln.id} {ln.title}: worded as an allowance but the Allowance flag is off"))
    return out


def duplicate_lines(rev) -> list[tuple[str, str]]:
    """Lines with the same title and notes in one section (and the same alternate): added twice."""
    groups: dict[tuple, list] = defaultdict(list)
    for ln in rev.lines:
        if _printed(rev, ln):
            groups[(ln.section, ln.alternate, ln.title.strip().lower(), (ln.notes or "").strip().lower())].append(ln)
    out = []
    for lines in groups.values():
        if len(lines) > 1:
            ids = ", ".join(ln.id for ln in lines)
            out.append(("warn", f"{ids} {lines[0].title}: same title and notes in one section; added twice?"))
    return out


def project_info(project, customers) -> list[tuple[str, str]]:
    out = []
    if not project.client_name.strip():
        out.append(("warn", "Project info: client name is blank"))
    if not project.site_address.strip():
        out.append(("warn", "Project info: site address is blank"))
    cust = customers.get(project.customer_id) if customers is not None else None
    if project.customer_id is None:
        out.append(("info", "Project info: not linked to a customer"))
    elif cust is not None and not any(c.phone.strip() or c.email.strip() for c in cust.contacts):
        out.append(("info", f"Customer {cust.name}: no contact with a phone or email"))
    return out


def content_checks(project, rev, results, customers=None) -> list[tuple[str, str]]:
    return (project_info(project, customers) + zero_lines(rev, results) + placeholders(project, rev)
            + allowance_wording(rev) + duplicate_lines(rev))
