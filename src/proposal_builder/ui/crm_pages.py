"""Contacts pages: Customers, Contractors, Suppliers."""

from __future__ import annotations

from nicegui import ui

from ..crm import Contact, Contractor, Customer, Supplier, line_contractor
from ..proposal import WON_STATUSES
from .state import get_state
from .widgets import (
    Col,
    EditableGrid,
    date_input,
    filter_box,
    fmt_date,
    keep_current,
    layout,
    list_grid,
    page_title,
    parse_date,
    toolbar,
)

INS_COLOR = {"expired": "#B00020", "expiring": "#B26A00", "unknown": "#80868b", "ok": ""}


def _list_page(title: str, help_text: str, new_label: str, new_icon: str, on_new, table, holder: dict) -> None:
    """Shared frame for the contacts pages: title, help, toolbar (New + filter + hint), grid.
    table(holder) builds the grid and stores it in holder["grid"] for the filter box."""
    page_title(title, help_text)
    with toolbar():
        ui.button(new_label, icon=new_icon, on_click=on_new).props("dense")
        filter_box(lambda: holder["grid"])
        ui.space()
        ui.label("Double-click a row to open it.").classes("text-xs text-gray-500")
    table(holder)


# ---------------------------------------------------------------- customers


def _customer_projects(cid: str) -> list:
    return [p for p in get_state().projects.list_projects() if p.customer_id == cid]


@ui.page("/customers")
def customers_page() -> None:
    layout("Customers")
    st = get_state()

    @ui.refreshable
    def table(holder: dict) -> None:
        counts: dict[str, int] = {}
        for p in st.projects.list_projects():
            if p.customer_id:
                counts[p.customer_id] = counts.get(p.customer_id, 0) + 1
        rows = []
        for c in st.customers.sorted():
            pc = c.primary
            mail = c.address(c.mailing_address_id)
            rows.append({"id": c.id, "name": c.name, "contact": pc.name if pc else "", "phone": pc.phone if pc else "",
                         "email": pc.email if pc else "", "address": (mail.address if mail else "").replace("\n", ", "),
                         "projects": counts.get(c.id, 0), "source": c.source, "active": "Yes" if c.active else "No"})
        holder["grid"] = list_grid(rows, [
            {"field": "name", "headerName": "Customer", "width": 210},
            {"field": "contact", "headerName": "Primary contact", "width": 160},
            {"field": "phone", "headerName": "Phone", "width": 130},
            {"field": "email", "headerName": "Email", "width": 190},
            {"field": "address", "headerName": "Mailing address", "flex": 1, "minWidth": 180},
            {"field": "projects", "headerName": "Projects", "width": 100, "type": "rightAligned"},
            {"field": "source", "headerName": "How they found you", "width": 160},
            {"field": "active", "headerName": "Active", "width": 100}],
            lambda cid: customer_dialog(st.customers.get(cid), lambda *_: table.refresh(holder)),
            "No customers yet. Use New customer, or pick one when you create a project.")

    holder: dict = {}
    _list_page("Customers", "One entry per client, with as many contacts and addresses as needed. A project "
               "picks its customer and site address in Project info.", "New customer", "person_add",
               lambda: customer_dialog(None, lambda *_: table.refresh(holder)), table, holder)


def customer_dialog(cust: Customer | None, on_saved, preset_name: str = "") -> None:
    st = get_state()
    is_new = cust is None
    work = (cust.model_copy(deep=True) if cust else Customer(name=preset_name or ""))
    with ui.dialog() as dlg, ui.card().classes("w-[1000px] max-w-full"):
        ui.label("New customer" if is_new else work.name).classes("text-lg font-semibold")
        with ui.grid(columns=4).classes("w-full gap-x-3"):
            name = ui.input("Name (as printed on proposals)", value=work.name,
                            placeholder="e.g. Kim and Pam Hotch").props("dense").classes("col-span-2")
            source = ui.select(keep_current({x: x for x in st.settings.lists.lead_sources}, work.source),
                               value=work.source or None, label="How they found you", with_input=True,
                               new_value_mode="add-unique").props("dense clearable")
            with ui.column().classes("gap-0"):
                company = ui.checkbox("Company", value=work.is_company) \
                    .tooltip("A business: proposals print the company name with Attn: the first contact")
                active = ui.checkbox("Active", value=work.active)
        ui.label("Contacts (the first one is the primary contact)").classes("font-semibold text-sm mt-2")
        EditableGrid(lambda: work.contacts,
                     [Col("name", "Name", flex=1),
                      Col("role", "Role", "select", ["", *st.settings.lists.contact_roles], width=150),
                      Col("phone", "Phone", width=150), Col("email", "Email", flex=1)],
                     lambda: None, lambda: Contact(), height="20vh")
        ui.label("Addresses (each project picks its site from these)").classes("font-semibold text-sm mt-2")
        EditableGrid(lambda: work.addresses,
                     [Col("label", "Label", "select", ["", *st.settings.lists.address_labels], width=180),
                      Col("address", "Address", flex=1)],
                     lambda: mailing.set_options(_addr_opts(work), value=mailing.value), lambda: _new_addr(),
                     height="18vh")
        mailing = ui.select(_addr_opts(work), value=work.mailing_address_id or "", label="Mailing address") \
            .props("dense").classes("w-96")
        notes = ui.textarea("Notes", value=work.notes).props("dense autogrow").classes("w-full")
        if not is_new:
            projs = _customer_projects(work.id)
            if projs:
                ui.label("Projects").classes("font-semibold text-sm mt-2")
                with ui.row().classes("gap-2 flex-wrap"):
                    for p in projs:
                        ui.chip(f"{p.number} {p.project_name} ({p.status.value})", icon="folder_open",
                                on_click=lambda p=p: ui.navigate.to(f"/project/{p.number}")).props("clickable outline")

        def save() -> None:
            work.name = (name.value or "").strip() or work.name
            if not work.name:
                ui.notify("Enter the customer's name.", type="warning")
                return
            work.source, work.notes, work.active = source.value or "", notes.value or "", active.value
            work.is_company = bool(company.value)
            work.mailing_address_id = mailing.value or None
            other = st.customers.find(work.name)
            if other is not None and other.id != work.id:
                ui.notify(f"A customer named {work.name} already exists.", type="warning")
                return
            if is_new:
                st.customers.customers.append(work)
            else:
                idx = st.customers.customers.index(cust)
                st.customers.customers[idx] = work
                _sync_projects(work)
            st.save_customers()
            dlg.close()
            on_saved(work)

        async def delete() -> None:
            if _customer_projects(work.id):
                ui.notify("This customer has projects; mark it inactive instead.", type="warning")
                return
            st.customers.customers.remove(cust)
            st.save_customers()
            dlg.close()
            on_saved(None)

        with ui.row().classes("w-full justify-end gap-2"):
            if not is_new:
                ui.button("Delete", icon="delete", on_click=delete).props("flat color=negative")
            ui.space()
            ui.button("Cancel", on_click=dlg.close).props("flat")
            ui.button("Save", icon="save", on_click=save)
    dlg.open()


def _new_addr():
    from ..crm import Address
    return Address(label="Site")


def _addr_opts(c: Customer) -> dict:
    return {"": "-", **{a.id: (a.label + ": " if a.label else "") + a.address.replace("\n", ", ") for a in c.addresses}}


def _sync_projects(cust: Customer) -> None:
    """Customer renamed or an address edited: keep linked projects' printed text in step (drafts too)."""
    st = get_state()
    for p in _customer_projects(cust.id):
        changed = False
        if p.client_name != cust.name:
            p.client_name, changed = cust.name, True
        a = cust.address(p.site_address_id)
        if a and p.site_address != a.address:
            p.site_address, changed = a.address, True
        if changed:
            st.projects.save_project(p)


# ---------------------------------------------------------------- contractors


def contractor_usage(cid: str) -> list[tuple[str, str, list[str]]]:
    """[(project number, project name, line ids or CO numbers)] where the contractor appears."""
    st = get_state()
    ps, book = st.projects, st.contractors
    out = []
    for p in ps.list_projects():
        revs = ps.list_revisions(p.number)
        if not revs:
            continue
        rev = ps.load_revision(p.number, revs[-1])
        ids = [ln.id for ln in rev.lines if (c := line_contractor(book, ln)) and c.id == cid]
        log = ps.load_change_orders(p.number)
        ids += [o.number for o in log.orders if any(it.contractor_id == cid for it in o.items)]
        if ids:
            out.append((p.number, p.project_name, ids))
    return out


def project_contractor_ids(project, rev) -> set[str]:
    """Contractors on a project's revision lines and change order items."""
    st = get_state()
    ids = {c.id for ln in rev.lines if (c := line_contractor(st.contractors, ln))}
    for o in st.projects.load_change_orders(project.number).orders:
        ids |= {it.contractor_id for it in o.items if it.contractor_id}
    return ids


@ui.page("/contractors")
def contractors_page() -> None:
    layout("Contractors")
    st = get_state()

    @ui.refreshable
    def table(holder: dict) -> None:
        rows = []
        for c in st.contractors.sorted():
            ins = c.insurance_status()
            rows.append({"id": c.id, "company": c.company, "trades": ", ".join(c.trades), "contact": c.contact,
                         "phone": c.phone, "email": c.email,
                         "license": " ".join(x for x in (c.license_type, c.license_no) if x),
                         "insurance": (fmt_date(c.insurance_expiry) if c.insurance_expiry else "none on file")
                         + ("" if ins in ("ok", "unknown") else f" ({ins})"),
                         "ins": ins, "w9": "Yes" if c.w9_on_file else "", "rating": "★" * (c.rating or 0),
                         "active": "Yes" if c.active else "No"})
        holder["grid"] = list_grid(rows, [
            {"field": "company", "headerName": "Company", "width": 190},
            {"field": "trades", "headerName": "Trades", "width": 150},
            {"field": "contact", "headerName": "Contact", "width": 130},
            {"field": "phone", "headerName": "Phone", "width": 120},
            {"field": "email", "headerName": "Email", "flex": 1, "minWidth": 150},
            {"field": "license", "headerName": "License", "width": 120},
            {"field": "insurance", "headerName": "Insurance expiry", "width": 170,
             ":cellStyle": "p => ({expired: {color: '#B00020', fontWeight: 600}, "
                           "expiring: {color: '#B26A00', fontWeight: 600}, "
                           "unknown: {color: '#80868b'}})[p.data.ins] || null"},
            {"field": "w9", "headerName": "W-9", "width": 70},
            {"field": "rating", "headerName": "Rating", "width": 90},
            {"field": "active", "headerName": "Active", "width": 100}],
            lambda cid: contractor_dialog(st.contractors.get(cid), lambda *_: table.refresh(holder)),
            "No contractors yet. Use New contractor, or the + beside Contractor on a line.")

    holder: dict = {}
    _list_page("Contractors", "Subcontractors. Proposal lines and change order items pick from this list. Insurance "
               "that has lapsed or lapses within 30 days is flagged here and on accepted projects.",
               "New contractor", "engineering",
               lambda: contractor_dialog(None, lambda *_: table.refresh(holder)), table, holder)


def contractor_dialog(con: Contractor | None, on_saved, preset_name: str = "") -> None:
    st = get_state()
    is_new = con is None
    work = con.model_copy(deep=True) if con else Contractor(company=preset_name or "")
    with ui.dialog() as dlg, ui.card().classes("w-[860px] max-w-full"):
        ui.label("New contractor" if is_new else work.company).classes("text-lg font-semibold")
        with ui.grid(columns=4).classes("w-full gap-x-3"):
            company = ui.input("Company", value=work.company, placeholder="e.g. Sparky Electric").props("dense") \
                .classes("col-span-2")
            trade_opts = list(dict.fromkeys([*st.settings.lists.trades, *work.trades]))
            trades = ui.select(trade_opts, value=list(work.trades), label="Trades", multiple=True, with_input=True,
                               new_value_mode="add-unique").props("dense use-chips").classes("col-span-2")
            contact = ui.input("Contact", value=work.contact).props("dense")
            phone = ui.input("Phone", value=work.phone).props("dense")
            email = ui.input("Email", value=work.email).props("dense").classes("col-span-2")
            lic_type = ui.input("License type", value=work.license_type).props("dense")
            lic_no = ui.input("License number", value=work.license_no).props("dense")
            ins = date_input("Insurance expiry", work.insurance_expiry)
            rating = ui.select({0: "-", 1: "★", 2: "★★", 3: "★★★", 4: "★★★★", 5: "★★★★★"}, value=work.rating or 0,
                               label="Rating").props("dense")
            w9 = ui.checkbox("W-9 on file", value=work.w9_on_file)
            active = ui.checkbox("Active", value=work.active)
        notes = ui.textarea("Notes", value=work.notes).props("dense autogrow").classes("w-full")
        if not is_new:
            used = contractor_usage(work.id)
            if used:
                ui.label("Used on").classes("font-semibold text-sm mt-2")
                for num, pname, ids in used:
                    with ui.row().classes("items-center gap-2"):
                        ui.link(f"{num} {pname}", f"/project/{num}")
                        ui.label(", ".join(ids)).classes("text-xs text-gray-600")

        def save() -> None:
            try:
                work.company = (company.value or "").strip() or work.company
                if not work.company:
                    raise ValueError("enter the company name")
                work.trades = [t.strip() for t in (trades.value or []) if t.strip()]
                work.contact, work.phone, work.email = contact.value or "", phone.value or "", email.value or ""
                work.license_type, work.license_no = lic_type.value or "", lic_no.value or ""
                work.insurance_expiry = parse_date(ins.value)
                work.rating = int(rating.value) or None
                work.w9_on_file, work.active, work.notes = w9.value, active.value, notes.value or ""
            except ValueError as err:
                ui.notify(f"Not saved: {err}", type="negative")
                return
            other = st.contractors.find(work.company)
            if other is not None and other.id != work.id:
                ui.notify(f"A contractor named {work.company} already exists.", type="warning")
                return
            if is_new:
                st.contractors.contractors.append(work)
            else:
                st.contractors.contractors[st.contractors.contractors.index(con)] = work
            st.save_contractors()
            dlg.close()
            on_saved(work)

        def delete() -> None:
            if contractor_usage(work.id):
                ui.notify("This contractor is on projects; mark it inactive instead.", type="warning")
                return
            st.contractors.contractors.remove(con)
            st.save_contractors()
            dlg.close()
            on_saved(None)

        with ui.row().classes("w-full justify-end gap-2"):
            if not is_new:
                ui.button("Delete", icon="delete", on_click=delete).props("flat color=negative")
            ui.space()
            ui.button("Cancel", on_click=dlg.close).props("flat")
            ui.button("Save", icon="save", on_click=save)
    dlg.open()


# ---------------------------------------------------------------- suppliers


@ui.page("/suppliers")
def suppliers_page() -> None:
    layout("Suppliers")
    st = get_state()

    @ui.refreshable
    def table(holder: dict) -> None:
        rows = [{"id": s.id, "name": s.name, "contact": s.contact, "phone": s.phone, "email": s.email,
                 "account": s.account_no, "website": s.website, "active": "Yes" if s.active else "No"}
                for s in st.suppliers.sorted()]
        holder["grid"] = list_grid(rows, [
            {"field": "name", "headerName": "Supplier", "width": 210},
            {"field": "contact", "headerName": "Contact", "width": 150},
            {"field": "phone", "headerName": "Phone", "width": 130},
            {"field": "email", "headerName": "Email", "flex": 1, "minWidth": 160},
            {"field": "account", "headerName": "Account #", "width": 130},
            {"field": "website", "headerName": "Website", "width": 190},
            {"field": "active", "headerName": "Active", "width": 100}],
            lambda sid: supplier_dialog(st.suppliers.get(sid), lambda *_: table.refresh(holder)),
            "No suppliers yet. Use New supplier.")

    holder: dict = {}
    _list_page("Suppliers", "Material and equipment vendors. Vendor fields on lines and actual costs pick from "
               "suppliers and contractors.", "New supplier", "add_business",
               lambda: supplier_dialog(None, lambda *_: table.refresh(holder)), table, holder)


def supplier_dialog(sup: Supplier | None, on_saved) -> None:
    st = get_state()
    is_new = sup is None
    work = sup.model_copy(deep=True) if sup else Supplier(name="")
    with ui.dialog() as dlg, ui.card().classes("w-[760px] max-w-full"):
        ui.label("New supplier" if is_new else work.name).classes("text-lg font-semibold")
        with ui.grid(columns=4).classes("w-full gap-x-3"):
            name = ui.input("Name", value=work.name, placeholder="e.g. Lowe's Pro Desk").props("dense") \
                .classes("col-span-2")
            contact = ui.input("Contact", value=work.contact).props("dense")
            phone = ui.input("Phone", value=work.phone).props("dense")
            email = ui.input("Email", value=work.email).props("dense").classes("col-span-2")
            account = ui.input("Account #", value=work.account_no).props("dense")
            active = ui.checkbox("Active", value=work.active)
            website = ui.input("Website", value=work.website).props("dense").classes("col-span-4")
        notes = ui.textarea("Notes", value=work.notes).props("dense autogrow").classes("w-full")

        def save() -> None:
            work.name = (name.value or "").strip()
            if not work.name:
                ui.notify("Enter the supplier's name.", type="warning")
                return
            other = st.suppliers.find(work.name)
            if other is not None and other.id != work.id:
                ui.notify(f"A supplier named {work.name} already exists.", type="warning")
                return
            work.contact, work.phone, work.email = contact.value or "", phone.value or "", email.value or ""
            work.account_no, work.website, work.notes = account.value or "", website.value or "", notes.value or ""
            work.active = active.value
            if is_new:
                st.suppliers.suppliers.append(work)
            else:
                st.suppliers.suppliers[st.suppliers.suppliers.index(sup)] = work
            st.save_suppliers()
            dlg.close()
            on_saved(work)

        def delete() -> None:
            st.suppliers.suppliers.remove(sup)
            st.save_suppliers()
            dlg.close()
            on_saved(None)

        with ui.row().classes("w-full justify-end gap-2"):
            if not is_new:
                ui.button("Delete", icon="delete", on_click=delete).props("flat color=negative")
            ui.space()
            ui.button("Cancel", on_click=dlg.close).props("flat")
            ui.button("Save", icon="save", on_click=save)
    dlg.open()


def vendor_names() -> list[str]:
    """Supplier and contractor names for vendor pickers."""
    st = get_state()
    names = [s.name for s in st.suppliers.sorted() if s.active] + [c.company for c in st.contractors.sorted() if c.active]
    return list(dict.fromkeys(names))


def won(project) -> bool:
    return project.status in WON_STATUSES


# ---------------------------------------------------------------- picker used by New project / Project info


class CustomerPicker:
    """Customer + site address selects. apply(project) writes ids and the printed text."""

    def __init__(self, customer_id: str | None = None, address_id: str | None = None):
        st = get_state()
        self.st = st
        with ui.row().classes("w-full items-end gap-2 no-wrap"):
            self.cust = ui.select(self._cust_opts(customer_id), value=customer_id or None, label="Customer", with_input=True) \
                .props("dense clearable").classes("grow")
            ui.button(icon="person_add", on_click=self._new_customer).props("dense flat").tooltip("New customer")
        with ui.row().classes("w-full items-end gap-2 no-wrap"):
            self.addr = ui.select(self._addr_opts(), value=address_id or None, label="Site address") \
                .props("dense clearable").classes("grow")
            ui.button(icon="add_location_alt", on_click=self._new_address).props("dense flat").tooltip("Add address")
        self.cust.on_value_change(lambda _: self._customer_changed())

    def _cust_opts(self, keep: str | None = None) -> dict:
        return {c.id: c.name for c in self.st.customers.sorted() if c.active or c.id == keep}

    def _addr_opts(self) -> dict:
        c = self.customer
        return {a.id: (a.label + ": " if a.label else "") + a.address.replace("\n", ", ") for a in c.addresses} if c else {}

    @property
    def customer(self) -> Customer | None:
        cid = getattr(self, "cust", None) and self.cust.value
        return self.st.customers.get(cid) if cid else None

    def _customer_changed(self) -> None:
        c = self.customer
        opts = self._addr_opts()
        first = c.mailing_address_id if (c and c.mailing_address_id in opts) else next(iter(opts), None)
        self.addr.set_options(opts, value=first)


    def _new_customer(self) -> None:
        def done(c: Customer) -> None:
            self.cust.set_options(self._cust_opts(c.id), value=c.id)
            self._customer_changed()
        customer_dialog(None, done)

    def _new_address(self) -> None:
        c = self.customer
        if c is None:
            ui.notify("Pick or create a customer first.")
            return
        with ui.dialog() as dlg, ui.card().classes("w-[420px]"):
            ui.label(f"New address for {c.name}").classes("font-semibold")
            label = ui.select(self.st.settings.lists.address_labels, label="Label", with_input=True,
                              new_value_mode="add-unique").props("dense clearable").classes("w-full")
            text = ui.textarea("Address").props("dense autogrow").classes("w-full")

            def add() -> None:
                if not (text.value or "").strip():
                    return
                a = c.add_address(text.value, label.value or "")
                if c.mailing_address_id is None:
                    c.mailing_address_id = a.id
                self.st.save_customers()
                self.addr.set_options(self._addr_opts(), value=a.id)
                dlg.close()
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=dlg.close).props("flat")
                ui.button("Add", on_click=add)
        dlg.open()

    def apply(self, project) -> bool:
        c = self.customer
        if c is None:
            ui.notify("Pick a customer (or create one with the + button).", type="warning")
            return False
        a = c.address(self.addr.value)
        project.customer_id, project.client_name = c.id, c.name
        project.attention = (c.primary.name if c.primary else "") if c.is_company else ""
        project.site_address_id = a.id if a else None
        project.site_address = a.address if a else ""
        return True
