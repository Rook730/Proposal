import json
from decimal import Decimal
from importlib import resources
from pathlib import Path

import pytest

from proposal_builder.closeout import (
    ActualCost,
    ChangeOrder,
    ChangeOrderLog,
    COFunding,
    COItem,
    COStatus,
    PaidBy,
    Payment,
    Reconciliation,
    build_ledger,
    contract_context,
    price_change_orders,
)
from proposal_builder.models import Catalog, Settings
from proposal_builder.proposal import Project, Revision, contract_revision as make_contract

FIXTURE = Path(__file__).parent / "fixtures" / "26005_anon.json"
D = Decimal


def seed(name):
    return (resources.files("proposal_builder") / "seed" / name).read_text(encoding="utf-8")


@pytest.fixture
def contract():
    settings = Settings.model_validate_json(seed("settings.json"))
    catalog = Catalog.model_validate_json(seed("catalog.json"))
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rev = make_contract(Revision.model_validate(data["revision"]), [])      # base only, 41,186.59
    return contract_context(rev, settings, catalog.stock_classes, Project.model_validate(data["project"]))


def co(n, delta, funding, status=COStatus.APPROVED, hours=0):
    return ChangeOrder(number=f"26005-{n:02d}", funding=funding, status=status, mgmt_hours=D(hours),
                       items=[COItem(description="x", original_cost=D(0), final_cost=D(delta))])


def test_contract_context(contract):
    assert contract.total == D("41186.59")
    assert contract.markup_pct == D("0.15")
    assert contract.contingency == D("1640.90") and contract.co_management == D("1640.90")
    assert contract.mgmt_rate == D(75)                                     # contract PM rate


def test_change_order_pricing_and_contingency(contract):
    log = ChangeOrderLog(orders=[
        co(1, 350, COFunding.CLIENT),
        co(2, 1200, COFunding.CONTINGENCY),
        co(3, 300, COFunding.CONTINGENCY),
        co(4, 500, COFunding.ABSORBED),
        co(5, 999, COFunding.CONTINGENCY, COStatus.DRAFT),
    ])
    p = price_change_orders(log, contract)
    assert (p["26005-01"].price, p["26005-01"].billed) == (D("402.50"), D("402.50"))
    assert (p["26005-02"].price, p["26005-02"].from_contingency, p["26005-02"].billed) == (D("1380.00"), D("1380.00"), 0)
    assert (p["26005-03"].from_contingency, p["26005-03"].billed) == (D("260.90"), D("84.10"))
    assert p["26005-04"].billed == 0 and p["26005-04"].price == D("575.00")
    assert p["26005-05"].from_contingency == 0 and p["26005-05"].billed == p["26005-05"].price   # draft: nothing left


def test_ledger(contract):
    log = ChangeOrderLog(orders=[co(1, 350, COFunding.CLIENT), co(2, 1200, COFunding.CONTINGENCY),
                                 co(3, 300, COFunding.CONTINGENCY), co(4, 500, COFunding.ABSORBED)])
    recon = Reconciliation(
        actuals=[ActualCost(line_id="11.04", vendor="Hardware", amount=D(850), tax=D(50), paid_by=PaidBy.CLIENT),
                 ActualCost(line_id="6.01", hours=D(5)),                    # 5 HR x $75
                 ActualCost(line_id="1.01")],                               # blank entry: ignored
        unused_lines=["11.03"],
        payments=[Payment(draw="1", amount=D("10296.65")), Payment(draw="2", amount=D(15000))],
    )
    lg = build_ledger(contract, log, recon)
    assert lg.co_billed == D("486.60")
    assert lg.contingency_used == D("1640.90") and lg.unused_contingency == 0
    assert lg.co_management_credit == D("1640.90")                         # no management hours logged
    assert lg.net_variance == D(-705)                                      # +120 +75 -900
    assert lg.variance_markup == D("-105.75")
    assert lg.total_final == D("39221.54")
    assert lg.client_direct == D(900)
    assert lg.balance_due == D("13024.89")
    assert {lr.line.id for lr in lg.lines_with_activity} == {"11.04", "6.01", "11.03"}


def test_ledger_without_change_orders_credits_contingency_and_management(contract):
    lg = build_ledger(contract, ChangeOrderLog(), Reconciliation())
    assert lg.unused_contingency == D("1640.90") and lg.co_management_credit == D("1640.90")
    assert lg.total_final == D("41186.59") - D("3281.80")
    assert any("credit-if-unused" in w for w in lg.warnings)              # painting lines have no actuals


def test_next_number():
    log = ChangeOrderLog(orders=[ChangeOrder(number="26005-01"), ChangeOrder(number="26005-03")])
    assert log.next_number("26005") == "26005-02"


def test_management_hours_draw_allowance(contract):
    log = ChangeOrderLog(orders=[co(1, 350, COFunding.CLIENT, hours=2),          # 150 from allowance
                                 co(2, 100, COFunding.CLIENT, hours=20),         # 1500: 1490.90 left, 9.10 billed
                                 co(3, 100, COFunding.ABSORBED, hours=4),        # 300 beyond allowance, absorbed
                                 co(4, 100, COFunding.CLIENT, COStatus.DRAFT, hours=50)])
    p = price_change_orders(log, contract)
    assert (p["26005-01"].mgmt_cost, p["26005-01"].mgmt_from_allowance, p["26005-01"].mgmt_billed) == \
        (D("150.00"), D("150.00"), 0)
    assert p["26005-01"].billed == D("402.50")                              # work only, management from allowance
    assert (p["26005-02"].mgmt_from_allowance, p["26005-02"].mgmt_billed) == (D("1490.90"), D("9.10"))
    assert p["26005-02"].billed == D("115.00") + D("9.10")
    assert (p["26005-03"].mgmt_billed, p["26005-03"].billed) == (0, 0)
    lg = build_ledger(contract, log, Reconciliation())
    assert lg.mgmt_used == D("1640.90") and lg.co_management_credit == 0
    assert lg.co_billed == D("402.50") + D("124.10")


def test_partial_management_use_is_credited(contract):
    lg = build_ledger(contract, ChangeOrderLog(orders=[co(1, 350, COFunding.CLIENT, hours=3)]), Reconciliation())
    assert lg.mgmt_used == D("225.00") and lg.co_management_credit == D("1415.90")


def test_license_threshold_warning(contract):
    assert contract.license_threshold == D(40000)
    lg = build_ledger(contract, ChangeOrderLog(), Reconciliation())
    assert any("license threshold" in w for w in lg.warnings)              # 41,186.59 >= 40,000
    contract.license_threshold = D(0)
    assert not any("license threshold" in w for w in build_ledger(contract, ChangeOrderLog(), Reconciliation()).warnings)
