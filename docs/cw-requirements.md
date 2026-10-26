# Convenient Woodworking profile: requirements draft

Version 0.4 | 2026-10-26 | Owner: Nick (stages 1 and 2 in 1.8.0, stage 3 in 1.9.0)
Source: intake answers (claude/proposal-builder-cw-intake.md) and follow-ups F1 to F18. Open items are in section 16. Summary in docs/requirements.md section 16.

## 1. Purpose and scope

Add Convenient Woodworking (CW) proposals to Proposal Builder as a second company profile.

- **Kept Spec Advisors (KS):** project management. Subs and trades on site.
- **Convenient Woodworking (CW):** building or restoring a physical thing.

**CW job types in scope**
- Shop-built pieces, including production runs for businesses (e.g. 25017 boxes).
- Built-ins installed in a client's home (e.g. 25021).
- Restoration and refurbishment of client-owned items (e.g. 26003, 26004).

**Out of scope**
- Wholesale and consignment pricing (future update).
- Online store.
- Production status tracking.
- Closeout ledger for CW.
- Actual-hours calibration (later stage, after the profile is in use).

## 2. Profiles

- `Project.profile`: `ks` or `cw`. Set at creation; New project asks every time. Cannot be changed afterwards.
- **Shared:** catalog (sections tagged KS, CW or both), units, customers, contractors, suppliers, numbering (one YYNNN sequence), updater, Windows build.
- **Per profile:** settings (company identity, payment rules, pricing policy, defaults), terms library, How to read text, rates, PDF template.
- **Projects list:** both companies, with a Company column and filter.
- **App name:** "Proposal Builder" in the window title, exe name and `%APPDATA%` folder. The settings folder is migrated once on first start. The data folder is unchanged.
- **Data layout:** Kept Spec files stay at the data folder root (`settings.json`, `boilerplate.json`), so nothing is moved. Versions before 1.8.0 cannot read the folder once 1.8.0 or later has saved to it (unknown fields are rejected); update every computer that uses it. `profiles/cw/` holds the CW `settings.json`, `boilerplate.json` and `logo.svg`, created on first start. Shared values are read from the root `settings.json`. (Changed during stage 1 from moving KS files into `profiles/ks/`.)

## 3. CW identity

- Legal line: Convenient Enterprises LLC dba Convenient Woodworking.
- 224 Rutledge Rd, Fletcher, NC 28732 | 423.218.6067 | Nick@ConvenientWoodworking.com
- Logo: Textmark SVG.
- Colors: dark gold #A87B20 and black #000000.

## 4. Catalog

- Each section is tagged KS, CW or both. The catalog picker shows sections for the project's profile.
- **GC sections (100 to 1400):** KS.
- **Restoration sections (2000 to 2690):** CW. Imported from the Items sheet with typos fixed (mecahnical, refinsh). Fixed EA prices; qty = fixture count. Any restoration line can optionally carry a build sheet.
- **CW-only items:** codes from 3000.
- **Units added:** BF, SHT, PC, SET (PR exists).
- **Piece templates:** a catalog item with a build sheet and size variables (e.g. box W x D x H). Adding one copies its build sheet into the line (snapshot rule).

## 5. Price reference tables (Catalog > Price references)

| Table | Fields | Seed |
|---|---|---|
| Lumber | species, grade, thickness (4/4 to 16/4), surfacing, $/BF (rough, nominal thickness), supplier, price date, notes | Costing Wood rows 21 to 48 |
| Sheet goods | product, core/face, thickness, sheet W x L, $/sheet, supplier, date | Costing Wood rows 3 to 19, less Shop Made |
| Dimensional | class, size, length, $/stick (uses stock-length rounding) | Costing Wood rows 50 to 97, corrected |
| Veneer | species, thickness, $/SF, supplier, date | empty |
| Hardware | name, supplier, part number, unit, $/unit, date | empty (McMaster PNs from 25017 as placeholders) |
| Finishes | product, type, container size, $/container, coverage SF, coats, recoat time, cure days | empty |
| Outsourced | service, supplier/contractor, basis, typical price | empty |

**Global values (CW settings)**

| Setting | Value |
|---|---|
| Shop rate | $75/hr, all phases (design, milling, joinery and machining, assembly, sanding, finishing, hardware and fitting, crating, delivery and install) |
| Yield tiers (multiplier on net BF) | Low 1.25, Medium 1.5, High 1.8 |
| Rough thickness map | 3/4 from 4/4, 1 from 5/4, 1-1/4 from 6/4, 1-3/4 from 8/4, 2-3/4 from 12/4 (editable) |
| Overhead | 15% default (15 to 20%). Covers machines, consumables, tooling, material handling. |
| Profit | separate percent; 10% placeholder until set |
| Rush | per proposal, 20 to 50% |
| Rounding | unit price rounded up to the next $5 |
| Delivery | free within 1 hour of 224 Rutledge Rd (as built: a $0 Delivery line; no project checkbox needed); beyond, round-trip miles beyond the zone x $0.725 (IRS 2026 rate) plus drive time beyond the zone at $35/hr; crating as a line item |
| Storage of client property | $/SF of footprint per month, starting 15 days after notice of completion; printed in terms |

No machine-rate, consumables or material-markup tables: these are inside overhead.

**Seed corrections from Costing Wood:**
- Row 32 is missing its formula.
- Pressure-treated prices out of order (2x6x10, 2x8x16) to be checked.
- SPF vs SYP labels to be assigned.
- Shop Made plywood dropped.

## 6. Build sheet (internal, never printed)

Any line can have a build sheet; CW piece lines normally do. Price basis "Built".

**Setup (once per line):** hours by phase (design, drawings, jigs, CNC programming), plus one-time materials.

**Per unit:**
- **Lumber:** parts (name, qty, finished T x W x L, species, yield tier). Rough thickness from the map; BF x yield x $/BF. Or BF entered directly.
- **Sheet goods:** parts (qty, W x L) or sheet count; whole or fractional sheets.
- **Dimensional:** takeoff with stock-length rounding.
- **Veneer:** SF x $/SF, substrate as a lumber or sheet goods part.
- **Hardware:** item x qty.
- **Finish:** SF x coats x $/SF per coat (from container price and coverage).
- **Outsourced:** quote amount.
- **Labor:** hours by phase.

**Calculation**
```
cost       = setup + qty x (materials + outsourced + hours x shop rate)
line price = cost x (1 + overhead % + profit %)      flat, not compounded, like KS percent items
unit price = ceiling(line price / qty, $5)
line total = unit price x qty
```

- The client sees title, notes, unit, qty, unit price and cost. Build sheet, overhead and profit are hidden.
- The internal view shows cost, overhead, profit, effective $/hr and the qty-1 vs qty-N unit price.
- Snapshot rule: reference prices are copied when the line is added. Lines that differ from current prices show an indicator with "pull update".
- Check: 25018 side table with about $100 materials and 33 hours at 15% overhead gives about $3,000 before profit.

## 7. Proposal PDF

KS structure with CW identity:

1. **Intro page:** logo header, proposal #, date, revision; client block (person, or company with contact), site address, project, PO number when set. Cover letter: project-specific text plus boilerplate blocks (marketing paragraph, broad spec overview of species, finish and joinery, notes and clarifications).
2. **How to read this proposal** plus the units table (CW text).
3. **Sections:**
   - Shop-built and built-in work: one section per piece, created in the proposal. Each holds the piece line(s) and its install hours.
   - Restoration: catalog sections (Metalcraft, Woodcraft ...).
   - Delivery & Installation (project level): delivery, mileage, crating.
   - Line notes carry specifics (finishes used, hardware PNs) for future reference.
4. **Totals:** Subtotal, Rush (own line, % of subtotal), Sales tax (county and rate), Total. Then each alternate: Alternate Subtotal, Rush, Tax, Alternate Total.
5. **Signature:** client only.
6. **Payment schedule and payment terms.**
7. **Terms** (CW library).
8. **Appendix:** images and drawings in a grid with captions, each tied to its piece section.

Not printed: Prepared by, valid-until date, slogan, cash discount (none offered).

## 8. Alternates

- Same as KS: swap, add, deduct; combinations; "offer together" switch per pair.
- Species, finish and size options are swap alternates.
- Limit raised from 3 to 6, both profiles.
- Printed blue with alternate totals including tax.

## 9. Sales tax

- **Per proposal:**
  - taxable switch: default on for CW, off for KS
  - county picked from a list with rates (Henderson 6.75%, Buncombe 7.00%, editable in Settings > Lists)
- **Base:** the whole proposal (lines, delivery, install, rush, crating). Restoration is taxed (the 26003 and 26004 treatment is not carried forward).
- **No E-589CI handling for CW.** Note: built-ins permanently attached may be real property contracts; confirm with your accountant.

## 10. Payment

- **Deposit:** 25% of the Total (incl. tax) when under $500; 60% at $500 and over. Thresholds and percents are CW settings.
- **Balance:** due at delivery, or at completion of installation.
- **Deposit is applied to costs.** On cancellation the client owes materials purchased + hours worked x shop rate, plus 15% on those. Deposit above that is refunded; any shortfall is billed.
- 3% fee on PayPal and Venmo payments: noted in payment terms, applied at invoice.
- No returns.

## 11. Workflow

- Revisions, alternates and change orders on all CW jobs.
- **Not used for CW:** closeout ledger, contingency, change order management, retainage, license threshold check.
- **Acceptance** is design signoff. Changes after acceptance go through change orders.
- **Change order price:** build sheet delta priced with the section 6 formula, plus tax.
- **Placeholders:** TBD and other placeholders block Issue with no "Issue anyway", in both profiles.
- **Client property:**
  - Project fields: received date, condition notes.
  - Storage charge per terms.
- **Lead time:** default 10 to 12 weeks for custom work, as a variable in the terms.

## 12. Customers

- Customer type: Person or Company. A company has an optional contact person; both print.
- PO number field on the project, printed in the header block.

## 13. Income

- CW income: everything except materials and outsourced cost. Overhead and profit count as CW income.
- The CW column and Income summary pick up CW projects by profile.

## 14. CW terms library (to draft)

- Payment schedule and deposit
- Cancellation (materials + time + 15%)
- Card and app payment fee
- Lead time and scheduling
- Rush and hard deadlines
- Design signoff and changes after acceptance
- Delivery, installation and mileage
- Crating and freight
- Client property in our care and storage charges
- Natural variation of wood (from website warranty)
- Wood movement and finish care
- Warranty (1 year, from website warranty, corrected entity name)
- No returns
- Scope clarifications and exclusions
- Proposal validity

## 15. Stages

1. **Profile plumbing (released in 1.8.0):**
   - `Project.profile` and the CW profile folder.
   - Section tags.
   - Company column and filter.
   - Rename to Proposal Builder.
   - KS behavior unchanged.
2. **CW proposals (built 2026-10-25, released in 1.8.0):**
   - CW settings and identity.
   - Price reference tables, build sheets and pricing policy.
   - Piece sections.
   - Tax by county, deposit rule.
   - Customer type and PO number.
   - CW PDF template, How to read and terms library.
3. **Remaining CW features (released in 1.9.0):**
   - Restoration import.
   - Image appendix.
   - Client property fields and storage.
   - Veneer.
   - Alternate limit 6.
   - Placeholder hard block.
4. **Later:** actual hours by phase for calibration; wholesale.

## 16. Open

- Profit percent default.
- Storage rate: $2.00/SF per month, $25 minimum, 15 free days are the 1.9.0 defaults (Settings); confirm.
- Box job inputs: 1/2" prefinished maple ply price, McMaster hardware prices (1647A34 handles, 1766A2 latches, 1608A42 piano hinge), engraving method and time, setup and per-box hours.
