"""Terms blocks added after the workbook import (approved 2026-10-18).

The importer applies these on top of the workbook text so a regenerated seed keeps them.
"""
PT = "Payment Terms & Contract Cancellation"
SC = "Scope Clarifications & Exclusions"
HR = "How to read this proposal"

NEW = {
    "hourly-rates": (HR, "Hourly Rates",
        "Hourly work performed by Kept Spec Advisors and Convenient Woodworking on this proposal, "
        "including any Change Order work, is billed at the following rates.\n\n{rates_table}", 35),
    "lien-waivers": (PT, "Lien Waivers",
        "With the final invoice, Kept Spec Advisors provides final lien waivers from itself and from each "
        "subcontractor and supplier paid under this Agreement. Partial lien waivers for a progress payment "
        "are available on request.", 15),
    "payment-term-contract-cancellation-or-termination": (PT, "Contract Cancellation or Termination",
        "Either party may terminate this Agreement by written notice if the other party materially breaches it "
        "and does not cure the breach within seven (7) days after receiving written notice of it. Nonpayment "
        "is a material breach. Client may also cancel this Agreement for any reason by written notice.\n\n"
        "In the event of any cancellation or termination:\n"
        "- Client shall pay for all hours worked, services rendered, and materials purchased or ordered up to "
        "the effective date of termination (see Materials and Special Orders below).\n"
        "- No refunds shall be issued for time already spent, whether billed hourly, as part of General "
        "Conditions, Management/Supervision, or lump-sum line items that include labor or time-based services.\n"
        "- Payments received beyond the amounts owed are refunded to Client after final reconciliation.", 30),
    "insurance": (PT, "Insurance", "Certificates of insurance are available upon request.", 60),
    "dispute-resolution": (PT, "Dispute Resolution",
        "This Agreement is governed by the laws of the State of North Carolina. If a dispute arises, the parties "
        "will first try to resolve it directly. If it is not resolved within thirty (30) days, the parties will "
        "attempt mediation before either party starts litigation, with mediation costs shared equally. Venue for "
        "any mediation or litigation is the county in which the project is located.", 70),
    "scope-clarif-permits-inspections": (SC, "Permits & Inspections",
        "Permits required for the work are obtained before the related work begins. Trade permits (electrical, "
        "plumbing, gas, mechanical) are obtained by the licensed subcontractor performing that work. Permit fees "
        "are billed at actual cost unless listed as a line item. Kept Spec Advisors coordinates and attends "
        "required inspections, and no work is covered or concealed until it has passed any required inspection.",
        75),
}
ALLOWANCE_SENTENCE = ("Any selection over its allowance is required to be approved by the client in writing "
                      "before it will be ordered by the contractor.")



def apply(blocks: list) -> None:
    """Add or replace the blocks above in a list of BoilerplateBlock."""
    from .models import BoilerplateBlock
    by_id = {b.id: i for i, b in enumerate(blocks)}
    for bid, (heading, title, body, order) in NEW.items():
        blk = BoilerplateBlock(id=bid, heading=heading, title=title, body=body, order=order)
        if bid in by_id:
            blocks[by_id[bid]] = blk
        else:
            blocks.append(blk)
    for b in blocks:
        if b.id == "allowances" and ALLOWANCE_SENTENCE not in b.body:
            b.body = b.body.rstrip() + " " + ALLOWANCE_SENTENCE
