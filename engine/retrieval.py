"""Tiny keyword-match retrieval over the advice bank / content pack.

Deliberately not an embedding-based retriever. Reasons, in order:
  1. There isn't enough content yet (a few dozen chunks) for embedding
     search to beat keyword match on precision.
  2. An embedding model is another model to load into an already-tight
     RAM budget on an old phone, for a benefit that doesn't show up until
     content volume is much larger.
  3. Keyword match over a labeled, curated chunk set is easy to audit —
     you can see exactly why a chunk was picked, which matters when a
     wrong retrieval could surface wrong crop-protection advice.

Swap this for a real embedding retriever once the content pack is large
enough that keyword collisions become a real problem — the interface
(`Retriever.search(query) -> list[Chunk]`) is written so that swap doesn't
touch any caller.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


_HEADING_RE = re.compile(r"^### (.+)$", re.MULTILINE)
_FIELD_RE = re.compile(r"^(\w[\w ]*?):\s*(.+)$", re.MULTILINE)


@dataclass
class Chunk:
    title: str
    body: str
    fields: dict = field(default_factory=dict)
    keywords: set = field(default_factory=set)
    source_file: str = ""

    def score(self, query_terms: set) -> float:
        hay = self.keywords | {w.lower() for w in self.title.split()}
        if not query_terms:
            return 0.0
        overlap = len(hay & query_terms)
        return overlap / max(1, len(query_terms))


def _tokenize(text: str) -> set:
    return {w for w in re.findall(r"[a-zA-Z0-9']+", text.lower()) if len(w) > 2}


def parse_markdown_bank(path: Path) -> list[Chunk]:
    """Split a bank file on `### Heading` lines into retrieval chunks.

    Each chunk may carry a metadata line directly under the heading like:
        classifier_label: Tomato___Early_blight
    or:
        class: 8 | subject: Maths | topic: linear_equations
        keywords: linear equation, solve for x, balance method
    All such `key: value` lines (and `key: v1 | key2: v2` combos) become
    `fields`, and any `keywords:` field is additionally split on commas
    and folded into the match set alongside the heading words.
    """
    text = path.read_text(encoding="utf-8")
    headings = list(_HEADING_RE.finditer(text))
    chunks: list[Chunk] = []
    for i, m in enumerate(headings):
        title = m.group(1).strip()
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[start:end].strip()

        fields: dict = {}
        # metadata lines sit in the first few lines of the body, possibly
        # combined on one line with " | " separators
        meta_lines = []
        rest_lines = []
        in_meta = True
        for line in body.splitlines():
            if in_meta and (":" in line) and len(line) < 300 and not line.startswith("**"):
                meta_lines.append(line)
            else:
                in_meta = False
                rest_lines.append(line)
        for line in meta_lines:
            for part in line.split("|"):
                if ":" in part:
                    k, v = part.split(":", 1)
                    fields[k.strip().lower()] = v.strip()

        keywords = _tokenize(title)
        if "keywords" in fields:
            keywords |= {w.strip().lower() for w in fields["keywords"].split(",") if w.strip()}
        if "classifier_label" in fields:
            keywords |= _tokenize(fields["classifier_label"].replace("_", " "))

        clean_body = "\n".join(rest_lines).strip() or body
        chunks.append(Chunk(title=title, body=clean_body, fields=fields,
                             keywords=keywords, source_file=path.name))
    return chunks


class Retriever:
    def __init__(self, bank_paths: list[Path]):
        self.chunks: list[Chunk] = []
        for p in bank_paths:
            self.chunks.extend(parse_markdown_bank(p))

    def by_classifier_label(self, label: str) -> Chunk | None:
        for c in self.chunks:
            if c.fields.get("classifier_label") == label:
                return c
        return None

    def search(self, query: str, top_k: int = 1, min_score: float = 0.15) -> list[Chunk]:
        terms = _tokenize(query)
        scored = [(c.score(terms), c) for c in self.chunks]
        scored = [(s, c) for s, c in scored if s >= min_score]
        scored.sort(key=lambda sc: sc[0], reverse=True)
        return [c for _, c in scored[:top_k]]


if __name__ == "__main__":
    import sys
    bank_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "advice_bank"
    r = Retriever(sorted(bank_dir.glob("*.md")))
    print(f"loaded {len(r.chunks)} chunks from {bank_dir}")
    if len(sys.argv) > 2:
        q = " ".join(sys.argv[2:])
        for c in r.search(q, top_k=3):
            print(f"\n--- {c.title} ({c.source_file}) ---")
            print(c.body[:200])
