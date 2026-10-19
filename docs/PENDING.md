# Pending changes (next release: 1.5.0)

Collected until Nick says to release. Status: [ ] open, [~] built, not released, [x] released.

1. [~] Income tab: Kept Spec, Convenient Woodworking and Combined columns with Share of Price, Estimate/Actual toggle. Rows not tied to a performer (overhead, profit, change order management, change order and variance overhead and profit) count as Kept Spec. Income by option shows the split too.
2. [~] Income summary page (left menu): timeframe presets or from/to, status filter (default Accepted, In-Process, Completed, Closed), Estimate/Actual, one row per project with totals, win/loss/open counts and win rate, CSV export (saved to the data folder's exports/ and downloaded). Projects are placed by acceptance date; never-accepted proposals by issue date.
   - Projects now record an acceptance date (Mark accepted, or setting an accepted-type status) and a close date.
   - New status Closed. "Close project" on the change orders & ledger page (warns about balance due and open change orders) makes change orders, costs and payments read-only; Reopen sets Completed.
3. [ ] Catalog: Customers. Fields: name, contacts (several: spouse, property manager...), phone/email per contact, mailing address, several addresses (site picked per project from a dropdown), lead source, notes, linked projects. Project picker on New project / Project info. Existing projects linked by matching names. Later: follow-up flags.
4. [ ] Catalog: Contractors (company, trades, contact, phone, email, license number/type, insurance expiry, W-9, rating, notes, linked projects/lines). Lines and change order items pick a contractor instead of typing the internal sub name. Warning when a contractor with lapsed insurance is on an accepted project.
5. [ ] Catalog: Suppliers, own page (name, contact, phone, email, account number, website, notes). Vendor fields pick from it.
6. [ ] Sub quote package: PDF of the lines assigned to one contractor (title, description, notes, unit, quantity; no prices; no client name), project info header. Export only.
7. [ ] Quote comparison: log quotes from several contractors for the same scope; PDF comparison for the client (separate from the proposal). Winner entered manually on the lines.
