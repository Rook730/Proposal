"""Customers, contractors and suppliers (stored in the data folder, shared by all projects).

customers.json, contractors.json and suppliers.json are created empty when missing. Projects,
proposal lines and change order items refer to them by id and also keep the display text
(client name, site address, sub name) so printed documents never depend on these lists.
"""

from __future__ import annotations

import re
import uuid
from datetime import date, timedelta

from pydantic import BaseModel, ConfigDict, Field

INSURANCE_WARN_DAYS = 30


class _Model(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).casefold()


# ---------------------------------------------------------------- customers


class Contact(_Model):
    name: str = ""
    role: str = ""                       # Spouse, Property manager, ...
    phone: str = ""
    email: str = ""


class Address(_Model):
    id: str = Field(default_factory=new_id)
    label: str = ""                      # Home, Rental on Elm St, ...
    address: str = ""


class Customer(_Model):
    id: str = Field(default_factory=new_id)
    name: str                            # as printed on proposals, e.g. "Kim and Pam Hotch"
    contacts: list[Contact] = Field(default_factory=list)
    addresses: list[Address] = Field(default_factory=list)
    mailing_address_id: str | None = None
    source: str = ""                     # how they found you
    notes: str = ""
    created: date = Field(default_factory=date.today)
    active: bool = True

    def address(self, address_id: str | None) -> Address | None:
        return next((a for a in self.addresses if a.id == address_id), None)

    def find_address(self, text: str) -> Address | None:
        return next((a for a in self.addresses if _norm(a.address) == _norm(text)), None)

    def add_address(self, text: str, label: str = "") -> Address:
        a = self.find_address(text)
        if a is None:
            a = Address(label=label, address=text.strip())
            self.addresses.append(a)
        return a

    @property
    def primary(self) -> Contact | None:
        return self.contacts[0] if self.contacts else None


class CustomerBook(_Model):
    schema_version: int = 1
    customers: list[Customer] = Field(default_factory=list)

    def get(self, cid: str | None) -> Customer | None:
        return next((c for c in self.customers if c.id == cid), None)

    def find(self, name: str) -> Customer | None:
        return next((c for c in self.customers if _norm(c.name) == _norm(name)), None)

    def sorted(self) -> list[Customer]:
        return sorted(self.customers, key=lambda c: _norm(c.name))


def link_projects(book: CustomerBook, projects: list) -> list:
    """Attach projects without a customer to one with the same name (created if needed).

    The project's site address is added to the customer and selected. Returns changed projects.
    """
    changed = []
    for p in projects:
        if p.customer_id or not p.client_name.strip():
            continue
        cust = book.find(p.client_name)
        if cust is None:
            cust = Customer(name=p.client_name.strip(), created=p.created)
            book.customers.append(cust)
        if p.site_address.strip():
            addr = cust.add_address(p.site_address)
            p.site_address_id = addr.id
            if cust.mailing_address_id is None:
                cust.mailing_address_id = addr.id
        p.customer_id = cust.id
        changed.append(p)
    return changed


# ---------------------------------------------------------------- contractors and suppliers


class Contractor(_Model):
    id: str = Field(default_factory=new_id)
    company: str
    trades: list[str] = Field(default_factory=list)
    contact: str = ""
    phone: str = ""
    email: str = ""
    license_no: str = ""
    license_type: str = ""
    insurance_expiry: date | None = None
    w9_on_file: bool = False
    rating: int | None = None            # 1-5
    notes: str = ""
    active: bool = True

    def insurance_status(self, today: date | None = None) -> str:
        """"ok", "expiring" (within 30 days), "expired" or "unknown"."""
        if self.insurance_expiry is None:
            return "unknown"
        today = today or date.today()
        if self.insurance_expiry < today:
            return "expired"
        if self.insurance_expiry <= today + timedelta(days=INSURANCE_WARN_DAYS):
            return "expiring"
        return "ok"


class ContractorBook(_Model):
    schema_version: int = 1
    contractors: list[Contractor] = Field(default_factory=list)

    def get(self, cid: str | None) -> Contractor | None:
        return next((c for c in self.contractors if c.id == cid), None)

    def find(self, company: str) -> Contractor | None:
        return next((c for c in self.contractors if _norm(c.company) == _norm(company)), None)

    def sorted(self) -> list[Contractor]:
        return sorted(self.contractors, key=lambda c: _norm(c.company))


class Supplier(_Model):
    id: str = Field(default_factory=new_id)
    name: str
    contact: str = ""
    phone: str = ""
    email: str = ""
    account_no: str = ""
    website: str = ""
    notes: str = ""
    active: bool = True


class SupplierBook(_Model):
    schema_version: int = 1
    suppliers: list[Supplier] = Field(default_factory=list)

    def get(self, sid: str | None) -> Supplier | None:
        return next((s for s in self.suppliers if s.id == sid), None)

    def find(self, name: str) -> Supplier | None:
        return next((s for s in self.suppliers if _norm(s.name) == _norm(name)), None)

    def sorted(self) -> list[Supplier]:
        return sorted(self.suppliers, key=lambda s: _norm(s.name))


def add_from_sub_names(book: ContractorBook, names) -> bool:
    """Create contractors for sub names typed on lines before the contractor list existed."""
    changed = False
    for n in sorted(n for n in names if n):
        if n.strip() and book.find(n) is None:
            book.contractors.append(Contractor(company=n.strip()))
            changed = True
    return changed


def line_contractor(book: ContractorBook, ln) -> Contractor | None:
    """The contractor on a proposal line or change order item (by id, else by the typed sub name)."""
    return book.get(getattr(ln, "contractor_id", None)) or (book.find(ln.sub_name) if getattr(ln, "sub_name", "") else None)


def insurance_warnings(book: ContractorBook, contractor_ids: set[str], today: date | None = None) -> list[str]:
    out = []
    for cid in sorted(contractor_ids):
        c = book.get(cid)
        if c is None:
            continue
        st = c.insurance_status(today)
        if st == "expired":
            out.append(f"{c.company}: insurance expired {c.insurance_expiry:%Y.%m.%d}")
        elif st == "expiring":
            out.append(f"{c.company}: insurance expires {c.insurance_expiry:%Y.%m.%d}")
        elif st == "unknown":
            out.append(f"{c.company}: no insurance expiry date on file")
    return out
