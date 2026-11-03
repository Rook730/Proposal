"""Convenient Enterprises requirements engine (ce-requirements section 8): requirement library, project URS,
intake answers, compliance matrix.

The library (profiles/ce/requirements.json) starts from seed/ce/requirements.md, the URS/RFQ Template as a
tree of requirement nodes with variables, tags and intake questions. A project's URS (urs.json in the project
folder) is either a copy of the library (we write the spec) or the client's own requirements entered by hand
(we respond to it). Every row then carries a compliance status and response; Deviate and Clarify rows make the
Response Form.

Only Convenient Enterprises projects have a URS; 1.10.1 never opens them, so these files are free of the
shared-file contract.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date
from importlib import resources

from pydantic import Field

from .base import SavedModel

KINDS = {"requirement": "Requirement", "instruction": "Instruction", "data": "Data", "information": "Information"}
STATUSES = {"": "Not answered", "comply": "Comply", "clarify": "Comply with clarification", "deviate": "Deviate",
            "na": "N/A", "info": "Information only", "client": "By client"}
FORM_STATUSES = ("deviate", "clarify")       # rows that go on the Response Form
TEXT_STATUSES = ("deviate", "clarify")       # rows that need response text
VAR_TYPES = {"text": "Text", "list": "List (one per line)", "number": "Number", "choice": "Choice", "yesno": "Yes / no"}
OURS, CLIENT = "ours", "client"
OMIT_NA, OMIT_REMOVE = "na", "remove"
TEMPLATE, ISSUED = "template", "issued"


def new_id() -> str:
    return uuid.uuid4().hex[:10]


# ---------------------------------------------------------------- library

class UrsTopic(SavedModel):
    key: str
    title: str


class UrsTag(SavedModel):
    """A yes/no question that turns sections on or off (a node applies when all its tags are not 'no')."""
    key: str
    question: str = ""
    topic: str = ""


class UrsVariable(SavedModel):
    """A blank in the library text ({name}) with its intake question. Unanswered, the default prints."""
    name: str
    type: str = "text"
    topic: str = ""
    question: str = ""
    example: str = ""
    default: str = ""
    choices: list[str] = Field(default_factory=list)


class ReqNode(SavedModel):
    """One section of the library: heading (levels 1 to 3) and body text."""
    id: str = Field(default_factory=new_id)
    level: int = 1
    heading: str = ""
    body: str = ""
    kind: str = "requirement"
    applies: list[str] = Field(default_factory=list)
    numbered: bool = True
    on: bool = True
    pagebreak: bool = False


FRONT_INSTRUCTIONS = """**Instructions**

**All blue text contained in brackets [ ] is present for clarification only and should be deleted in the final revision of this URS/RFQ document.**

**All sections/items in this template may not apply to your current need. Sections may be deleted or left as-is and conveyed to the Supplier that certain sections are not applicable.**

**"Document Version History and Approvals" are for major Template updates**

**"URS/RFQ Revision History" should document the changes made to the URS/RFQ document after discussions with Supplier**

**Before final printing/sharing update page numbers in Table of Contents by clicking the "Table of Contents" title and then "Update Table"**

**Per section 1.3, a completed CDA/NDA is required before sending any drawings/ documentation/information regarding our process.**

**Please delete this page**"""

CONFIDENTIALITY = ("The information contained in this document and any other correspondence written or verbal pertaining "
                   "to this project is confidential information and the property of {company}. The confidential "
                   "information may be used only for the purpose of this project and will not be disclosed by you to "
                   "any third party or used for any other purpose without the prior written consent of {company}. Any "
                   "use of this information by you constitutes acceptance of these terms.")

RESPONSE_INSTRUCTIONS = ("Instructions: The Provider shall include this completed form with their quotation to identify "
                         "any deviations or corrections to specific requirements within the specific revision of the "
                         "URS/RFQ document noted above. Include the section number from the URS/RFQ document in the "
                         "left column and the proposed deviation or correction in the right. Add additional pages as "
                         "needed.")


class RequirementLibrary(SavedModel):
    schema_version: int = 1
    topics: list[UrsTopic] = Field(default_factory=list)
    tags: list[UrsTag] = Field(default_factory=list)
    variables: list[UrsVariable] = Field(default_factory=list)
    nodes: list[ReqNode] = Field(default_factory=list)
    # template document control (printed in template exports only)
    approvers: list[list[str]] = Field(default_factory=lambda: [["Person", "Mfg Engineering Mgr"],
                                                                ["Person", "Facilities Mgr"],
                                                                ["Person", "EHS Mgr"]])
    versions: list[list[str]] = Field(default_factory=lambda: [["A", "2/26/2019", "N/A", "Initial Release"]])
    instructions: str = FRONT_INSTRUCTIONS
    confidentiality: str = CONFIDENTIALITY
    response_instructions: str = RESPONSE_INSTRUCTIONS
    author: str = "Nick Matney"

    def variable(self, name: str) -> UrsVariable | None:
        return next((v for v in self.variables if v.name == name), None)

    def tag(self, key: str) -> UrsTag | None:
        return next((t for t in self.tags if t.key == key), None)


_ATTR = re.compile(r"\s*\{((?:\s*(?:kind|applies)=\S+|\s*unnumbered|\s*off|\s*pagebreak)+)\s*\}\s*$")


def _heading_attrs(text: str) -> tuple[str, dict]:
    m = _ATTR.search(text)
    if not m:
        return text.strip(), {}
    attrs: dict = {}
    for part in m.group(1).split():
        k, _, v = part.partition("=")
        attrs[k] = v if v else True
    return text[:m.start()].strip(), attrs


def parse_library(text: str) -> RequirementLibrary:
    """Read the library source (seed/ce/requirements.md, format in its header)."""
    lib = RequirementLibrary()
    lines = text.replace("\r\n", "\n").split("\n")
    node: ReqNode | None = None
    body: list[str] = []
    i = 0

    def close() -> None:
        if node is not None:
            node.body = "\n".join(body).strip("\n")

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("%%"):
            i += 1
            continue
        m = re.match(r"^::: (topic|tag|var) (\S+)\s*$", ln)
        if m:
            kind, key = m.groups()
            fields: dict[str, str] = {}
            i += 1
            current = None
            while i < len(lines) and lines[i].strip() != ":::":
                row = lines[i]
                fm = re.match(r"^(\w+):\s?(.*)$", row)
                if fm and not row.startswith(" "):
                    current = fm.group(1)
                    fields[current] = fm.group(2)
                elif current:
                    fields[current] = (fields[current] + "\n" + row[2:]).lstrip("\n")
                i += 1
            i += 1
            if kind == "topic":
                lib.topics.append(UrsTopic(key=key, title=fields.get("title", key)))
            elif kind == "tag":
                lib.tags.append(UrsTag(key=key, question=fields.get("question", ""), topic=fields.get("topic", "")))
            else:
                lib.variables.append(UrsVariable(name=key, type=fields.get("type", "text"),
                                                 topic=fields.get("topic", ""), question=fields.get("question", ""),
                                                 example=fields.get("example", ""),
                                                 default=fields.get("default", "").strip("\n"),
                                                 choices=[c.strip() for c in fields.get("choices", "").split("|")
                                                          if c.strip()]))
            continue
        hm = re.match(r"^(#{1,3}) (.+)$", ln)
        if hm:
            close()
            heading, attrs = _heading_attrs(hm.group(2))
            node = ReqNode(level=len(hm.group(1)), heading=heading,
                           kind=str(attrs.get("kind", "requirement")),
                           applies=[t for t in str(attrs.get("applies", "")).split(",") if t],
                           numbered="unnumbered" not in attrs, on="off" not in attrs,
                           pagebreak="pagebreak" in attrs)
            lib.nodes.append(node)
            body = []
            i += 1
            continue
        if node is not None:
            body.append(ln)
        i += 1
    close()
    return lib


def default_library() -> RequirementLibrary:
    text = (resources.files("proposal_builder") / "seed" / "ce" / "requirements.md").read_text(encoding="utf-8")
    return parse_library(text)


# ---------------------------------------------------------------- project URS

class UrsItem(SavedModel):
    """A requirement in a project's URS: a library section copied in, or a client requirement entered by hand."""
    id: str = Field(default_factory=new_id)
    source_id: str | None = None         # library node it was copied from
    source_body: str | None = None       # library text when copied (library updated indicator)
    level: int = 1
    number: str = ""                     # client numbering; empty = automatic outline number
    heading: str = ""
    body: str = ""
    kind: str = "requirement"
    applies: list[str] = Field(default_factory=list)
    numbered: bool = True
    pagebreak: bool = False
    on: bool = True
    changed: bool = False                # client requirement edited after a client revision was entered
    review: bool = False                 # compliance needs review (client revision)
    status: str = ""
    response: str = ""
    links: list[str] = Field(default_factory=list)   # what in the proposal answers it (free text: "Deliverable 3")


class UrsRevisionRow(SavedModel):
    revision: str = ""
    date: str = ""
    section: str = ""
    change: str = ""


class ClientSpec(SavedModel):
    """The client's own document, when we respond to their spec (attached for reference, not parsed)."""
    title: str = ""
    reference: str = ""
    revision: str = ""
    date: str = ""
    file: str = ""                       # file name in the project folder, if attached


class ProjectUrs(SavedModel):
    schema_version: int = 1
    mode: str = OURS                     # ours: we write the URS from the library; client: their spec, entered
    omit: str = OMIT_NA                  # sections turned off: printed "Not applicable" (keeps numbers) or removed
    title: str = ""
    subtitle: str = ""
    address_1: str = ""
    address_2: str = ""
    revision: str = "1.0"
    month_year: str = ""
    issued: str = ""
    due: str = ""
    author: str = ""
    document_number: str = "Not Assigned"
    reference: str = ""                  # URS/RFQ reference number (Response Form)
    completed_by: str = ""               # Response Form
    completed_date: str = ""
    answers: dict[str, str] = Field(default_factory=dict)
    tags: dict[str, bool] = Field(default_factory=dict)
    history: list[UrsRevisionRow] = Field(default_factory=list)
    client: ClientSpec = Field(default_factory=ClientSpec)
    items: list[UrsItem] = Field(default_factory=list)

    def item(self, item_id: str) -> UrsItem | None:
        return next((x for x in self.items if x.id == item_id), None)


def from_library(lib: RequirementLibrary, project, author: str = "") -> ProjectUrs:
    """A new URS that we write for the client, copied from the library (snapshot rule)."""
    lines = [x.strip() for x in (getattr(project, "site_address", "") or "").split("\n") if x.strip()]
    urs = ProjectUrs(mode=OURS, title=getattr(project, "project_name", "") or "", author=author or lib.author,
                     address_1=lines[0] if lines else "", address_2=", ".join(lines[1:]),
                     month_year=date.today().strftime("%B %Y"),
                     history=[UrsRevisionRow(revision="1.0", date=date.today().strftime("%m/%d/%Y").lstrip("0"),
                                             section="N/A", change="Original Release to Provider")])
    for n in lib.nodes:
        urs.items.append(UrsItem(source_id=n.id, source_body=n.body, level=n.level, heading=n.heading, body=n.body,
                                 kind=n.kind, applies=list(n.applies), numbered=n.numbered, pagebreak=n.pagebreak,
                                 on=n.on, status="info" if n.kind == "information" else ""))
    return urs


def for_client_spec(title: str = "", reference: str = "", revision: str = "", spec_date: str = "",
                    lib: RequirementLibrary | None = None) -> ProjectUrs:
    """A URS for responding to the client's own spec: blank, or the library tree to edit and renumber."""
    urs = ProjectUrs(mode=CLIENT, client=ClientSpec(title=title, reference=reference, revision=revision,
                                                    date=spec_date),
                     reference=reference, revision=revision or "1.0")
    if lib is not None:
        nums = numbers([UrsItem(level=n.level, numbered=n.numbered) for n in lib.nodes])
        for n, num in zip(lib.nodes, nums, strict=True):
            urs.items.append(UrsItem(source_id=n.id, source_body=n.body, level=n.level, heading=n.heading,
                                     body=n.body, kind=n.kind, number=num, numbered=n.numbered,
                                     status="info" if n.kind == "information" else ""))
    return urs


def client_revision(urs: ProjectUrs, revision: str, rev_date: str = "") -> None:
    """The client issued a new revision of their spec: rows stay, every compliance status is flagged for review
    until confirmed, and rows edited from now on are marked changed."""
    urs.client.revision, urs.revision = revision, revision
    if rev_date:
        urs.client.date = rev_date
    for it in urs.items:
        it.changed = False
        it.review = bool(it.status) and it.kind != "information"


# ---------------------------------------------------------------- numbering and applicability

def effective_on(items: list[UrsItem], tags: dict[str, bool]) -> list[bool]:
    """Whether each row prints as a live section: on, its tags not answered 'no', and its parent live."""
    out, stack = [], []          # stack of (level, live)
    for it in items:
        while stack and stack[-1][0] >= it.level:
            stack.pop()
        parent = all(live for _, live in stack)
        live = parent and it.on and all(tags.get(t) is not False for t in it.applies)
        out.append(live)
        stack.append((it.level, live))
    return out


def numbers(items: list[UrsItem], live: list[bool] | None = None, omit: str = OMIT_NA) -> list[str]:
    """Outline numbers ("3", "3.3", "3.3.1") from levels. Rows with a number typed in keep it. With omit=remove,
    rows that are not live take no number (later sections move up)."""
    counters = [0, 0, 0, 0]
    out = []
    for i, it in enumerate(items):
        if it.number:
            out.append(it.number)
            parts = [int(p) for p in re.findall(r"\d+", it.number)][:3]
            for k, p in enumerate(parts):
                counters[k] = p
            for k in range(len(parts), 4):
                counters[k] = 0
            continue
        if not it.numbered or (omit == OMIT_REMOVE and live is not None and not live[i]):
            out.append("")
            continue
        lvl = max(1, min(3, it.level))
        counters[lvl - 1] += 1
        for k in range(lvl, 4):
            counters[k] = 0
        out.append(".".join(str(c) for c in counters[:lvl]))
    return out


def number_key(num: str) -> tuple:
    """Sort key for section numbers: "3.10" after "3.9"; text parts sort after numbers."""
    return tuple((0, int(p)) if p.isdigit() else (1, p) for p in re.split(r"[.\s]+", num.strip()) if p)


# ---------------------------------------------------------------- variables and text

VAR_RE = re.compile(r"\{([a-z_][a-z0-9_]*)\}")
COND_OPEN = re.compile(r"^\{\?(!?)([a-z_][a-z0-9_]*)\}\s*$")
COND_CLOSE = re.compile(r"^\{/\?\}\s*$")
NOTE_RE = re.compile(r"\[!([^\]]*)\]")
BLANK_RE = re.compile(r"\[(?!!)([^\]]*)\]")


def values(lib: RequirementLibrary, urs: ProjectUrs, project=None) -> dict[str, str]:
    """Variable values for printing: answers, else the project's own data, else the library default."""
    out = {v.name: v.default for v in lib.variables}
    if project is not None:
        out["company"] = getattr(project, "client_name", "") or "[COMPANY]"
    else:
        out.setdefault("company", "[COMPANY]")
    out.update({k: v for k, v in urs.answers.items() if str(v).strip()})
    return out


def answered(urs: ProjectUrs, name: str) -> bool:
    return bool(str(urs.answers.get(name, "")).strip())


def expand(body: str, vals: dict[str, str], tags: dict[str, bool], list_vars: set[str], show_all: bool) -> str:
    """Resolve conditionals, list variables and variables in a body. show_all keeps both branches of a
    conditional whose tag is unanswered (template export); otherwise an unanswered tag keeps both too, and the
    Issues tab flags it."""
    out: list[str] = []
    keep = [True]
    for ln in body.split("\n"):
        m = COND_OPEN.match(ln.strip())
        if m:
            neg, tag = m.groups()
            v = tags.get(tag)
            k = True if v is None else (v is False if neg else v is True)
            keep.append(keep[-1] and k)
            continue
        if COND_CLOSE.match(ln.strip()):
            if len(keep) > 1:
                keep.pop()
            continue
        if not keep[-1]:
            continue
        lm = re.match(r"^(\s*)- \{([a-z_][a-z0-9_]*)\}\s*$", ln)
        if lm and lm.group(2) in list_vars:
            indent = lm.group(1)
            for row in str(vals.get(lm.group(2), "")).split("\n"):
                if not row.strip():
                    continue
                extra = len(row) - len(row.lstrip(" "))
                out.append(f"{indent}{' ' * extra}- {_sub(row.strip(), vals)}")
            continue
        out.append(_sub(ln, vals))
    return "\n".join(out)


def _sub(text: str, vals: dict[str, str]) -> str:
    # one pass, then a second for defaults that hold variables (need_reasons mentions {plant})
    for _ in range(2):
        text = VAR_RE.sub(lambda m: str(vals.get(m.group(1), m.group(0))), text)
    return text


def used_variables(text: str) -> set[str]:
    return set(VAR_RE.findall(text or ""))


def blanks(text: str) -> list[str]:
    """Fill-in blanks left in printed text ("[ ]", "[ADDRESS]"), not template notes."""
    return BLANK_RE.findall(text or "")


# ---------------------------------------------------------------- intake

@dataclass
class Question:
    kind: str            # "tag" or "var"
    key: str
    text: str
    example: str = ""
    type: str = "yesno"
    choices: list[str] = field(default_factory=list)


def interview(lib: RequirementLibrary, urs: ProjectUrs) -> list[tuple[UrsTopic, list[Question]]]:
    """Intake questions by topic. A variable is asked only if some live section uses it (or none does: intake-only
    variables such as target date and budget); tag questions are always asked."""
    live = effective_on(urs.items, urs.tags) if urs.items else []
    used: dict[str, bool] = {}
    for it, on in zip(urs.items, live, strict=False):
        for name in used_variables(it.body):
            used[name] = used.get(name, False) or on
    # list defaults may mention other variables
    by_topic: dict[str, list[Question]] = {t.key: [] for t in lib.topics}
    for t in lib.tags:
        by_topic.setdefault(t.topic, []).append(Question("tag", t.key, t.question))
    for v in lib.variables:
        if not v.question or (v.name in used and not used[v.name]):
            continue
        by_topic.setdefault(v.topic, []).append(Question("var", v.name, v.question, v.example, v.type, v.choices))
    topics = {t.key: t for t in lib.topics}
    out = []
    for key, qs in by_topic.items():
        if qs:
            out.append((topics.get(key) or UrsTopic(key=key, title=key.title()), qs))
    return out


def open_answers(lib: RequirementLibrary, urs: ProjectUrs) -> list[str]:
    """Questions still open (unanswered tag, or a variable left at a bracketed default): Issues tab."""
    out = []
    live = effective_on(urs.items, urs.tags)
    used = set()
    for it, on in zip(urs.items, live, strict=True):
        if on:
            used |= used_variables(it.body)
    for t in lib.tags:
        if t.key not in urs.tags and any(t.key in it.applies or f"{{?{t.key}}}" in it.body or f"{{?!{t.key}}}" in it.body
                                         for it in urs.items):
            out.append(t.question)
    for v in lib.variables:
        if v.name in used and not answered(urs, v.name) and "[" in v.default:
            out.append(v.question)
    return out


# ---------------------------------------------------------------- compliance

@dataclass
class ResponseRow:
    number: str
    heading: str
    status: str
    text: str


def compliance_rows(urs: ProjectUrs) -> list[tuple[UrsItem, str, bool]]:
    """(item, number, live) for every row, in document order."""
    live = effective_on(urs.items, urs.tags)
    return list(zip(urs.items, numbers(urs.items, live, urs.omit), live, strict=True))


def response_form_rows(urs: ProjectUrs) -> list[ResponseRow]:
    """Deviate and Clarify rows, by section number, for the Response Form."""
    rows = [ResponseRow(num, it.heading, it.status, it.response.strip())
            for it, num, live in compliance_rows(urs) if live and it.status in FORM_STATUSES]
    rows.sort(key=lambda r: number_key(r.number) if r.number else ((2, r.heading),))
    for r in rows:
        if r.status == "clarify" and r.text and not r.text.lower().startswith("clarification"):
            r.text = "Clarification: " + r.text
    return rows


def compliance_issues(urs: ProjectUrs) -> list[str]:
    """Unanswered requirements, Deviate/Clarify without text, rows awaiting review after a client revision."""
    out = []
    unanswered = [num or it.heading for it, num, live in compliance_rows(urs)
                  if live and it.kind != "information" and not it.status]
    if unanswered:
        out.append(f"{len(unanswered)} requirement(s) have no compliance status: " + ", ".join(unanswered[:8])
                   + (" ..." if len(unanswered) > 8 else ""))
    for it, num, live in compliance_rows(urs):
        if live and it.status in TEXT_STATUSES and not it.response.strip():
            out.append(f"{num or it.heading}: {STATUSES[it.status]} with no response text")
    review = [num or it.heading for it, num, live in compliance_rows(urs) if live and it.review]
    if review:
        out.append(f"Client revision {urs.client.revision or urs.revision}: {len(review)} response(s) to review: "
                   + ", ".join(review[:8]) + (" ..." if len(review) > 8 else ""))
    return out


def summary(urs: ProjectUrs) -> dict[str, int]:
    counts = {k: 0 for k in STATUSES}
    for it, _, live in compliance_rows(urs):
        if live:
            counts[it.status if it.status in counts else ""] += 1
    return counts


def leftover_blanks(lib: RequirementLibrary, urs: ProjectUrs, project=None) -> list[tuple[str, int]]:
    """(section, count) of fill-in blanks still in live sections once variables are filled (Issues tab)."""
    vals = values(lib, urs, project)
    list_vars = {v.name for v in lib.variables if v.type == "list"}
    out = []
    for it, num, live in compliance_rows(urs):
        if not live:
            continue
        text = NOTE_RE.sub("", expand(it.body, vals, urs.tags, list_vars, False))
        n = len(blanks(text))
        if n:
            out.append((num or it.heading, n))
    return out
