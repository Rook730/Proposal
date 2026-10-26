"""Spelling check for the printed text of a proposal (Issues tab).

Uses pyspellchecker's offline English word list plus BUILTIN_WORDS (trade terms) and the words the
user adds in Settings. ALL-CAPS words (GFCI, LVP) and words with inner capitals (QuietCool) are
skipped, as are {variables}, web addresses and email addresses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from .calc import VAR_RE

# Trade and local terms missing from the general dictionary. Lowercase.
BUILTIN_WORDS = frozenset("""
asheville backdraft backer backerboard backorder backorders backsplash backsplashes bullnose buncombe
caulked caulking cfm countertop countertops demo demoed drywalled ductless ductwork durock eave
etc fletcher ft gal grouted hardie hardieboard hardiplank haul hendersonville incl lf lvt misc mo multi
onsite passthrough pre precon preconstruction prehung punchlist qty ramboard reinstall reinstalled
schluter shiplap sq subfloor subfloors templated templating trex underlayment undermount
walkthrough walkthroughs wk wks hr hrs approx sf ea ln mt romex ditra kerdi
prefinished venmo paypal signoff sapwood heartwood hardwax tenon tenons dovetail dovetails dowel dowels
mdf plywood veneer veneered crating reuleaux haywood
""".split())

_PROTECT = re.compile(VAR_RE.pattern + r"|https?://\S+|www\.\S+|\S+@\S+\.\S+|\]\([^)]*\)")
_WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")


@lru_cache(maxsize=1)
def _checker():
    from spellchecker import SpellChecker
    return SpellChecker()


def available() -> bool:
    try:
        _checker()
        return True
    except Exception:  # noqa: BLE001  missing package or word list: skip the check
        return False


@dataclass(frozen=True)
class Place:
    kind: str          # "project", "line", "general", "alternate", "block"
    ref: str           # line id, alternate number, block id ("" for project)
    field: str         # attribute name on the object
    label: str         # shown to the user, e.g. "3.02 notes"


@dataclass
class Finding:
    word: str                                  # as first seen (case kept)
    places: list[Place] = field(default_factory=list)

    @property
    def key(self) -> str:
        return self.word.lower()

    def where(self, limit: int = 4) -> str:
        labels = list(dict.fromkeys(p.label for p in self.places))
        more = len(labels) - limit
        return ", ".join(labels[:limit]) + (f" and {more} more" if more > 0 else "")


def _segments(text: str):
    """(is_text, chunk): chunks outside {variables}, links and addresses are checkable."""
    pos = 0
    for m in _PROTECT.finditer(text):
        if m.start() > pos:
            yield True, text[pos:m.start()]
        yield False, m.group(0)
        pos = m.end()
    if pos < len(text):
        yield True, text[pos:]


def _base(w: str) -> str:
    w = w.replace("’", "'")
    return re.sub(r"'s$", "", w, flags=re.IGNORECASE)


def _checkable(w: str) -> bool:
    if len(w) < 2:
        return False
    if w.isupper():
        return False                      # acronyms: GFCI, LVP
    return not any(c.isupper() for c in w[1:])   # QuietCool, iPhone


def words_in(text: str) -> list[str]:
    out = []
    for ok, chunk in _segments(text or ""):
        if ok:
            out += [b for w in _WORD.findall(chunk) if _checkable(b := _base(w))]
    return out


def text_fields(project, rev) -> list[tuple[Place, str]]:
    """The text that prints on the proposal, with where it lives."""
    out: list[tuple[Place, str]] = [(Place("project", "", "project_name", "Project name"), project.project_name)]
    for ln in rev.lines:
        if ln.section not in rev.sections:
            continue
        out.append((Place("line", ln.id, "title", f"{ln.id} title"), ln.title))
        if ln.print_general and ln.general_description:
            out.append((Place("general", ln.id, "general_description", f"{ln.id} catalog description"),
                        ln.general_description))
        out.append((Place("line", ln.id, "notes", f"{ln.id} notes"), ln.notes))
    for a in rev.alternates:
        out.append((Place("alternate", str(a.number), "name", f"Alt {a.number} name"), a.name))
        out.append((Place("alternate", str(a.number), "description", f"Alt {a.number} description"),
                    a.description))
    for b in rev.blocks:
        if b.on:
            name = b.title or b.heading
            out.append((Place("block", b.id, "title", f"Terms: {name} (title)"), b.title))
            out.append((Place("block", b.id, "body", f"Terms: {name}"), b.body))
    return [(p, t) for p, t in out if t and t.strip()]


def check(project, rev, extra_words=()) -> list[Finding]:
    """Unknown words, in order of first appearance."""
    known = BUILTIN_WORDS | {w.strip().lower() for w in extra_words if w.strip()}
    found: dict[str, Finding] = {}
    for place, text in text_fields(project, rev):
        for w in words_in(text):
            k = w.lower()
            if k in known:
                continue
            f = found.get(k)
            if f is None:
                found[k] = f = Finding(w)
            if place not in f.places:
                f.places.append(place)
    if not found:
        return []
    unknown = _checker().unknown(list(found))
    return [f for k, f in found.items() if k in unknown]


@lru_cache(maxsize=4096)
def suggestions(word: str, n: int = 3) -> tuple[str, ...]:
    sc = _checker()
    cands = sc.candidates(word.lower()) or set()
    best = sorted(cands, key=lambda c: (-sc.word_usage_frequency(c), c))[:n]
    return tuple(_match_case(word, c) for c in best)


def _match_case(original: str, new: str) -> str:
    if original[:1].isupper():
        return new[:1].upper() + new[1:]
    return new[:1].lower() + new[1:]


def replace_word(text: str, old: str, new: str) -> tuple[str, int]:
    """Replace whole-word `old` (any case) with `new`, matching the case of each occurrence's first
    letter. {variables}, links and addresses are left alone. Returns (text, count)."""
    pat = re.compile(r"(?<![A-Za-z])" + re.escape(old) + r"(?![A-Za-z])", re.IGNORECASE)
    count = 0

    def sub(m):
        nonlocal count
        count += 1
        return _match_case(m.group(0), new)

    parts = [pat.sub(sub, chunk) if ok else chunk for ok, chunk in _segments(text or "")]
    return "".join(parts), count


def apply_fix(project, rev, finding: Finding, new: str, catalog=None, boilerplate=None) -> dict[str, int]:
    """Replace the word everywhere it was found in this revision. Catalog descriptions are fixed in
    the catalog item too (the line keeps an exact copy), and terms blocks in the library when the
    library text has the same word. Returns counts per place kind ("project", "line", ...,
    "catalog", "library")."""
    counts: dict[str, int] = {}

    def fix(obj, attr, kind):
        if obj is None:
            return
        text, n = replace_word(getattr(obj, attr), finding.word, new)
        if n:
            setattr(obj, attr, text)
            counts[kind] = counts.get(kind, 0) + n

    for p in finding.places:
        if p.kind == "project":
            fix(project, p.field, "project")
        elif p.kind in ("line", "general"):
            ln = rev.line(p.ref)
            fix(ln, p.field, p.kind)
            if p.kind == "general" and ln is not None and catalog is not None and ln.code is not None:
                fix(catalog.item(ln.code), "description", "catalog")
        elif p.kind == "alternate":
            fix(next((a for a in rev.alternates if str(a.number) == p.ref), None), p.field, "alternate")
        elif p.kind == "block":
            fix(next((b for b in rev.blocks if b.id == p.ref), None), p.field, "block")
            if boilerplate is not None:
                fix(next((b for b in boilerplate.blocks if b.id == p.ref), None), p.field, "library")
    return counts
