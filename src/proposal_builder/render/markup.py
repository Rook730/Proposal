"""Convert the small Markdown subset used in notes and boilerplate into Typst markup.

Supported: paragraphs (blank line), line breaks (single newline), "- " bullets,
"1. " numbered items, **bold**, *italic*. Everything else is literal text.
"""

from __future__ import annotations

import re

_SPECIAL = set('\\#$*_`<>@[]~/="-+')
_BULLET = re.compile(r"^\s*[-*\u2022]\s+(.*)$")
_NUMBER = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
_INLINE = re.compile(r"\*\*(.+?)\*\*|(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")


def escape(text: str) -> str:
    return "".join("\\" + c if c in _SPECIAL else c for c in text)


def inline(text: str) -> str:
    out, pos = [], 0
    for m in _INLINE.finditer(text):
        out.append(escape(text[pos:m.start()]))
        if m.group(1) is not None:
            out.append("*" + escape(m.group(1)) + "*")
        else:
            out.append("_" + escape(m.group(2)) + "_")
        pos = m.end()
    out.append(escape(text[pos:]))
    return "".join(out)


def md_to_typst(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").strip()
    if not text:
        return ""
    paragraphs = re.split(r"\n\s*\n", text)
    out = []
    for para in paragraphs:
        lines = [ln.rstrip() for ln in para.split("\n") if ln.strip()]
        rendered: list[str] = []
        prev_plain = False
        for ln in lines:
            b, n = _BULLET.match(ln), _NUMBER.match(ln)
            if b:
                rendered.append("- " + inline(b.group(1)))
                prev_plain = False
            elif n:
                rendered.append(f"{n.group(1)}. " + inline(n.group(2)))
                prev_plain = False
            else:
                if prev_plain:
                    rendered[-1] += " \\"          # hard line break
                elif rendered:
                    rendered.append("")           # end list before text
                rendered.append(inline(ln.strip()))
                prev_plain = True
        out.append("\n".join(rendered))
    return "\n\n".join(out)
