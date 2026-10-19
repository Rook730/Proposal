"""Income across projects for a timeframe (the Summary page).

A project's date is its acceptance date. Projects that were never accepted use the date the
latest revision was issued, or its proposal date, so open and lost proposals can still be
counted in the same window.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .calc import calculate
from .closeout import accepted_revision, build_ledger, contract_context
from .income import CW, KS, IncomeReport, contract_report, estimate_report
from .models import Catalog, Settings
from .proposal import WON_STATUSES, Project, ProjectStatus, Revision

ZERO = Decimal(0)


@dataclass
class ProjectIncome:
    project: Project
    when: date
    basis: str                          # "accepted", "issued", "proposal date"
    total_price: Decimal
    report: IncomeReport
    contract_rev: str | None            # accepted revision, if any

    @property
    def won(self) -> bool:
        return self.project.status in WON_STATUSES

    @property
    def lost(self) -> bool:
        return self.project.status is ProjectStatus.REJECTED

    def amount(self, kind: str, entity: str | None = None) -> Decimal | None:
        return self.report.total(kind, entity)

    def share(self, kind: str, entity: str | None = None) -> Decimal | None:
        return self.report.share(kind, entity)


def _project_date(project: Project, revs: list[Revision], acc: Revision | None) -> tuple[date, str]:
    if project.accepted_on:
        return project.accepted_on, "accepted"
    if acc is not None:
        return (acc.issued_at.date() if acc.issued_at else acc.proposal_date), "accepted"
    issued = [r for r in revs if r.issued_at]
    if issued:
        return issued[-1].issued_at.date(), "issued"
    return (revs[-1].proposal_date if revs else project.created), "proposal date"


def project_income(ps, project: Project, settings: Settings, catalog: Catalog) -> ProjectIncome | None:
    names = ps.list_revisions(project.number)
    if not names:
        return None
    revs = [ps.load_revision(project.number, r) for r in names]
    acc = accepted_revision(revs)
    when, basis = _project_date(project, revs, acc)
    if acc is not None:
        contract = contract_context(acc, settings, catalog.stock_classes, project)
        ledger = build_ledger(contract, ps.load_change_orders(project.number),
                              ps.load_reconciliation(project.number))
        rep = contract_report(ledger, settings)
        return ProjectIncome(project, when, basis, contract.total, rep, acc.rev)
    latest = revs[-1]
    res = calculate(latest, settings, catalog.stock_classes, project)
    rep = estimate_report(latest, res, res.base, settings)
    return ProjectIncome(project, when, basis, res.base.total, rep, None)


def all_project_income(ps, settings: Settings, catalog: Catalog) -> list[ProjectIncome]:
    out = []
    for p in ps.list_projects():
        try:
            pi = project_income(ps, p, settings, catalog)
        except Exception:  # noqa: BLE001  one broken project must not hide the rest
            continue
        if pi is not None:
            out.append(pi)
    return out


def in_window(rows: list[ProjectIncome], start: date | None, end: date | None) -> list[ProjectIncome]:
    return [r for r in rows if (start is None or r.when >= start) and (end is None or r.when <= end)]


@dataclass
class Pipeline:
    proposals: int
    proposed_value: Decimal
    won: int
    won_value: Decimal
    lost: int
    lost_value: Decimal
    open: int
    open_value: Decimal

    @property
    def win_rate(self) -> Decimal | None:
        decided = self.won + self.lost
        return Decimal(self.won) / decided if decided else None

    @property
    def win_rate_value(self) -> Decimal | None:
        decided = self.won_value + self.lost_value
        return self.won_value / decided if decided else None


def pipeline(rows: list[ProjectIncome]) -> Pipeline:
    """Outcome of every proposal in the window that has been issued at least once."""
    sent = [r for r in rows if r.project.status is not ProjectStatus.DRAFT]
    won = [r for r in sent if r.won]
    lost = [r for r in sent if r.lost]
    open_ = [r for r in sent if not r.won and not r.lost]
    s = lambda xs: sum((r.total_price for r in xs), ZERO)  # noqa: E731
    return Pipeline(len(sent), s(sent), len(won), s(won), len(lost), s(lost), len(open_), s(open_))


def to_csv(rows: list[ProjectIncome], kind: str) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Project", "Client", "Name", "Status", "Date", "Date basis", "Total Price",
                f"Kept Spec ({kind})", f"Convenient Woodworking ({kind})", f"Combined ({kind})", "Share"])
    for r in rows:
        k = kind if (kind == "estimate" or r.report.actual_total is not None) else "estimate"
        share = r.share(k)
        w.writerow([r.project.number, r.project.client_name, r.project.project_name, r.project.status.value,
                    r.when.isoformat(), r.basis, f"{r.total_price:.2f}",
                    f"{r.amount(k, KS):.2f}", f"{r.amount(k, CW):.2f}", f"{r.amount(k):.2f}",
                    f"{share * 100:.1f}%" if share is not None else ""])
    return buf.getvalue()

