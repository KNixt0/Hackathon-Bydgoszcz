"""Per-document analysis state shared by plugins and debate agents.

`AnalysisContext` bundles the preprocessed page, the enrichment context, the registers, the
evidence book and lazily computed text facts (profit claims, risk warnings, ...).
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from functools import cached_property
from urllib.parse import urlparse

from . import lexicon as lx
from .preprocess import Embedder, Page, Sentence, cosine
from .registries import KNF_FIRM_REGISTERS, RegistryStore, core_name, normalize_name
from .schemas import BBox, Context, Document, Evidence, Party, Span

ATTACHMENT_RULES = "ZASÓB DLA UCZESTNIKÓW - InvestWatch - kryteria oceny informacji o ryzyku.docx"
ATTACHMENT_REGISTERS = "Załącznik do Tematu 1 Wyzwanie KNF HackNation.docx"
ATTACHMENT_ART76 = "Załącznik do tematu 3 Wyzwanie KNF HackNation 2026.docx"
ART_76 = "art. 76 ustawy o obrocie instrumentami finansowymi"
SOCIAL_PLATFORMS = {"youtube", "instagram", "facebook", "tiktok", "x"}


def parse_date(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)


class EvidenceBook:
    """Collects evidence items; quote evidence is always cut out of the source text."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.items: list[Evidence] = []
        self._index: dict[tuple, str] = {}

    def _add(self, key: tuple, **fields) -> str:
        if key in self._index:
            return self._index[key]
        ev_id = f"e{len(self.items) + 1}"
        self.items.append(Evidence(id=ev_id, **fields))
        self._index[key] = ev_id
        return ev_id

    def quote(self, start: int, end: int, label: str) -> str:
        """Evidence for text[start:end], trimmed to whole words and a readable length."""
        start, end = self._trim(start, end)
        return self._add(
            ("quote", start, end),
            kind="quote",
            label=label,
            quote=self.text[start:end],
            span=Span(start=start, end=end),
        )

    def visual_quote(self, start: int, end: int, label: str, bbox: BBox, storage_key: str | None) -> str:
        """Quote evidence located on an archived screenshot (contract v3: `bbox` + `storage_key`)."""
        start, end = self._trim(start, end)
        return self._add(
            ("vquote", start, end, bbox.viewport, bbox.x, bbox.y, label),
            kind="quote",
            label=label,
            quote=self.text[start:end],
            span=Span(start=start, end=end),
            bbox=bbox,
            storage_key=storage_key or None,
        )

    def _trim(self, start: int, end: int) -> tuple[int, int]:
        start, end = max(0, start), min(len(self.text), end)
        while start < end and self.text[start].isspace():
            start += 1
        while end > start and self.text[end - 1].isspace():
            end -= 1
        if end - start > 320:
            end = start + 320
            while end > start + 200 and not self.text[end - 1].isspace():
                end -= 1
            end = len(self.text[:end].rstrip())
        if end <= start:
            raise ValueError("empty quote")
        return start, end

    def legal(self, legal_ref: str, label: str, attachment: str) -> str:
        return self._add(("legal", legal_ref), kind="legal", label=label, legal_ref=legal_ref, attachment=attachment)

    def registry(self, registry: str, subject: str, label: str, url: str) -> str:
        return self._add(("registry", registry, subject), kind="registry", label=label, url=url or None)

    def account(self, handle: str, label: str) -> str:
        return self._add(("account", handle), kind="account", label=label)

    def krs(self, company: str, label: str) -> str:
        return self._add(("krs", company), kind="krs", label=label)

    def url(self, url: str, label: str) -> str:
        return self._add(("url", url), kind="url", label=label, url=url)

    def archive(self, storage_key: str, label: str) -> str:
        return self._add(("archive", storage_key), kind="archive", label=label, storage_key=storage_key)

    def ids(self) -> set[str]:
        return {e.id for e in self.items}

    def get(self, ev_id: str) -> Evidence | None:
        return next((e for e in self.items if e.id == ev_id), None)


@dataclass
class Hit:
    start: int
    end: int
    kind: str
    sentence: Sentence


@dataclass
class Facts:
    risk: list[Hit] = field(default_factory=list)  # one per risk sentence (span = sentence)
    risk_refs: list[Hit] = field(default_factory=list)
    profit_claims: list[Hit] = field(default_factory=list)
    guarantees: list[Hit] = field(default_factory=list)
    historical: list[Hit] = field(default_factory=list)  # sentences with past results
    forecasts: list[Hit] = field(default_factory=list)
    tax: list[Hit] = field(default_factory=list)
    supervisor: list[Hit] = field(default_factory=list)
    comparisons: list[Hit] = field(default_factory=list)
    ad_markers: list[Hit] = field(default_factory=list)
    ad_negations: list[Hit] = field(default_factory=list)
    independence: list[Hit] = field(default_factory=list)
    cta: list[Hit] = field(default_factory=list)


def negated(sentence: Sentence, abs_start: int, window: int = 32) -> bool:
    rel = abs_start - sentence.start
    return bool(lx.NEGATION_BEFORE.search(sentence.folded[max(0, rel - window) : rel]))


def _hits(
    sentences: list[Sentence],
    pattern: re.Pattern[str],
    kind: str,
    *,
    skip_negated: bool = False,
    first_only: bool = False,
) -> list[Hit]:
    out = []
    for s in sentences:
        for m in pattern.finditer(s.folded):
            if skip_negated and negated(s, s.start + m.start()):
                continue
            out.append(Hit(s.start + m.start(), s.start + m.end(), kind, s))
            if first_only:
                break
    return out


def extract_facts(page: Page, embedder: Embedder) -> Facts:
    facts = Facts()
    sentences = page.sentences
    prototypes = [embedder.embed(p) for p in lx.RISK_PROTOTYPES]
    risk_ids: set[int] = set()
    warning_ids: set[int] = set()  # historical / forecast disclaimers are not claims either
    for s in sentences:
        f = s.folded
        if lx.HIST_WARNING.search(f) or lx.FORECAST_WARNING.search(f):
            warning_ids.add(id(s))
        if lx.NO_RISK_CLAIM.search(f) and not lx.RISK_STANDARD.search(f):
            continue  # "bez ryzyka" is a safety claim, never a warning
        kind = None
        if lx.RISK_STANDARD.search(f):
            kind = "standard"
        elif (m := lx.RISK_GENERIC.search(f)) and not (lx.RISK_REFERENCE.search(f) and len(f) < 60):
            kind = "generic"
            if negated(s, s.start + m.start(), 12) and not f[m.start() :].startswith("nie "):
                kind = None
        elif lx.RISK_STEM.search(f) and len(f) > 25 and not lx.RISK_REFERENCE.search(f):
            vec = embedder.embed(s.text)
            if max(cosine(vec, p) for p in prototypes) >= embedder.similar_threshold:
                kind = "soft"
        if kind:
            facts.risk.append(Hit(s.start, s.end, kind, s))
            risk_ids.add(id(s))
        elif lx.RISK_REFERENCE.search(f):
            facts.risk_refs.append(Hit(s.start, s.end, "reference", s))

    plain = [s for s in sentences if id(s) not in risk_ids and id(s) not in warning_ids]
    facts.guarantees = _hits(plain, lx.GUARANTEE, "guarantee", skip_negated=True)
    facts.guarantees += _hits(plain, lx.NO_RISK_CLAIM, "no_risk", skip_negated=True)
    facts.profit_claims = _hits(plain, lx.PROFIT_CLAIM, "profit", skip_negated=True) + facts.guarantees
    facts.profit_claims.sort(key=lambda h: h.start)

    for s in plain:
        f = s.folded
        past = lx.PAST_MARKER.search(f)
        if past and lx.FIGURE.search(f) and not re.search(r"\b(?:zaloz\w+|istniej\w+|dzial\w+) (?:w|od) 20", f):
            facts.historical.append(Hit(s.start, s.end, "historical", s))
        elif lx.FORECAST.search(f) and not negated(s, s.start + lx.FORECAST.search(f).start(), 14):
            facts.forecasts.append(Hit(s.start, s.end, "forecast", s))
    facts.tax = _hits(sentences, lx.TAX_REF, "tax", first_only=True)
    facts.supervisor = _hits(sentences, lx.SUPERVISOR_REF, "supervisor", first_only=True)
    facts.comparisons = _hits(plain, lx.COMPARISON, "comparison", first_only=True)
    facts.ad_negations = _hits(sentences, lx.AD_NEGATION, "ad_negation")
    neg_spans = [(h.start, h.end) for h in facts.ad_negations]
    facts.ad_markers = [
        h
        for h in _hits(sentences, lx.AD_MARKER, "ad_marker")
        if not any(a <= h.start < b or a < h.end <= b for a, b in neg_spans)
    ]
    facts.independence = _hits(sentences, lx.INDEPENDENCE_CLAIM, "independence")
    facts.cta = _hits(sentences, lx.CALL_TO_ACTION, "cta", first_only=True)
    return facts


_NAME_TOKEN = r"(?:[A-ZŁŚŻŹĆÓ0-9][\w&./\-]*|[a-z][A-ZŁŚŻŹĆÓ][\w&./\-]*|&|i|of|and|de)"
_LEGAL_NAME = re.compile(rf"((?:{_NAME_TOKEN} ){{1,6}}?{lx.LEGAL_FORM_RE})(?![\w])")
_SERVICE_NAME = re.compile(
    r"((?:[A-ZŁŚŻŹĆÓ][\w&\-]+ ){1,3}(?:Wealth Management|Family Office|Asset Management|Capital|Investments?|"
    r"Invest|Consulting|Advisory|Partners|Finance|Trading|Markets|Group|Brokers?|Securities))\b"
)
_LEADING_NOISE = {
    "firma",
    "spółka",
    "broker",
    "platforma",
    "w",
    "z",
    "dla",
    "nasz",
    "nasza",
    "oferta",
    "marka",
    "do",
    "od",
    "przez",
    "na",
    "że",
    "to",
    "a",
    "i",
    "oraz",
    "administratorem",
    "jest",
    "usługi",
    "świadczy",
    "podmiot",
    "copyright",
    "©",
    "wydawca",
    "właścicielem",
    "operator",
    "operatorem",
    "partner",
}


def legal_names_in_text(text: str) -> list[tuple[int, int, str]]:
    """Company names with a legal form ("Aurum Capital Ltd", "XTB S.A.") found in the text."""
    out = []
    for m in _LEGAL_NAME.finditer(text):
        start, name = m.start(1), m.group(1)
        words = name.split()
        while len(words) > 2 and words[0].lower().strip(".,:") in _LEADING_NOISE:
            start += len(words[0]) + 1
            words = words[1:]
        name = text[start : m.end(1)]
        if len(words) >= 2:
            out.append((start, m.end(1), name))
    return out


@dataclass
class ResolvedEntities:
    firm: Party | None = None
    advertiser: Party | None = None
    others: list[Party] = field(default_factory=list)
    third_party: bool = False  # the publisher is someone else than the firm
    firm_mentions: list[tuple[int, int]] = field(default_factory=list)
    firm_source: str = "none"  # context | register | text | none
    official_name_span: tuple[int, int] | None = None  # full legal name present in the text
    registered_brands: list[tuple[int, int, dict]] = field(default_factory=list)


def _same_entity(a: str, b: str) -> bool:
    """Two names denote the same entity: equal without legal form, or equal brand core.

    Containment counts only for multi-word cores ("Kormoran Fikcyjny" in "DM Kormoran
    Fikcyjny"); a single shared word is not enough.
    """
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    ca, cb = core_name(a), core_name(b)
    if not ca or not cb:
        return False
    if ca == cb:
        return True
    ta, tb = set(ca.split()), set(cb.split())
    small, big = (ta, set(nb.split())) if len(ta) <= len(tb) else (tb, set(na.split()))
    return len(small) >= 2 and small <= big


def firm_node_ids(graph, firm_name: str | None) -> list[str]:
    """Graph nodes that represent the analysed firm: by explicit role, else by name."""
    if graph is None:
        return []
    by_role = [n.id for n in graph.nodes if (n.meta or {}).get("role") == "investment_firm"]
    if by_role or not firm_name:
        return by_role
    wanted = normalize_name(firm_name)
    exact = [n.id for n in graph.nodes if n.type == "company" and normalize_name(n.label) == wanted]
    return exact or [n.id for n in graph.nodes if n.type == "company" and _same_entity(n.label, firm_name)]


class AnalysisContext:
    def __init__(
        self, document: Document, context: Context, page: Page, registries: RegistryStore, embedder: Embedder
    ) -> None:
        self.document = document
        self.context = context
        self.page = page
        self.registries = registries
        self.embedder = embedder
        self.evidence = EvidenceBook(page.text)
        self.now = parse_date(document.fetched_at) or dt.datetime.now(dt.UTC)
        self.host = (urlparse(document.url).hostname or "").lower().removeprefix("www.")

    @cached_property
    def facts(self) -> Facts:
        return extract_facts(self.page, self.embedder)

    @cached_property
    def scope(self):  # -> schemas.Scope
        from .scope import assess_scope

        return assess_scope(self)

    @cached_property
    def entities(self) -> ResolvedEntities:
        return self._resolve_entities()

    # ------------------------------------------------------------------ helpers
    def quote(self, hit_or_start, end: int | None = None, label: str = "Cytat ze źródła") -> str:
        if isinstance(hit_or_start, Hit):
            return self.evidence.quote(hit_or_start.sentence.start, hit_or_start.sentence.end, label)
        return self.evidence.quote(hit_or_start, end, label)

    def quote_sentence(self, pos: int, label: str) -> str:
        s = self.page.sentence_at(pos)
        return self.evidence.quote(s.start, s.end, label) if s else self.evidence.quote(pos, pos + 80, label)

    def find_name(self, name: str) -> list[tuple[int, int]]:
        """All occurrences of a name (or its legal-form-free variant) in the text."""
        spans: list[tuple[int, int]] = []
        for variant in dict.fromkeys([name, re.sub(rf"\s*{lx.LEGAL_FORM_RE}\s*$", "", name).strip()]):
            if len(variant) < 3:
                continue
            for m in re.finditer(rf"(?<!\w){re.escape(variant)}(?!\w)", self.page.text, flags=re.I):
                if not any(a <= m.start() and m.end() <= b for a, b in spans):
                    spans.append((m.start(), m.end()))
        return sorted(spans)

    def _resolve_entities(self) -> ResolvedEntities:
        res = ResolvedEntities()
        text, doc, ctx = self.page.text, self.document, self.context
        res.registered_brands = self.registries.brands_in_text("knf_investment_firms", text, self.page.folded)
        legal_names = legal_names_in_text(text)
        author = doc.author.name if doc.author and doc.author.name else None

        firm_company = next((c for c in ctx.companies if c.role == "investment_firm"), None)
        if firm_company:
            res.firm = Party(
                name=firm_company.name, kind="investment_firm", krs=firm_company.krs, country=firm_company.country
            )
            res.firm_source = "context"
        elif res.registered_brands:
            counts: dict[str, int] = {}
            for _, _, entry in res.registered_brands:
                counts[entry["name"]] = counts.get(entry["name"], 0) + 1
            # Prefer an explicitly identified publisher when its legal name matches a
            # register hit. Footer references to other firms do not outrank that identity.
            publisher_matches = [name for name in counts if author and _same_entity(name, author)]
            best = max(publisher_matches or counts, key=lambda name: counts[name])
            res.firm = Party(name=best, kind="investment_firm")
            res.firm_source = "register"
        else:
            candidates = [n for _, _, n in legal_names if not (author and _same_entity(n, author))]
            if not candidates:
                candidates = [
                    m.group(1)
                    for m in _SERVICE_NAME.finditer(text)
                    if not (author and _same_entity(m.group(1), author))
                ]
            if candidates:
                res.firm = Party(name=candidates[0], kind="investment_firm")
                res.firm_source = "text"

        if res.firm:
            res.firm_mentions = self.find_name(res.firm.name)
            for a, b, entry in res.registered_brands:
                if _same_entity(entry["name"], res.firm.name) and (a, b) not in res.firm_mentions:
                    res.firm_mentions.append((a, b))
            res.firm_mentions.sort()
            for a, b, name in legal_names:
                if _same_entity(name, res.firm.name):
                    res.official_name_span = (a, b)
                    break
        elif legal_names:
            res.official_name_span = legal_names[0][:2]

        adv_company = next((c for c in ctx.companies if c.role == "advertiser"), None)
        social = doc.platform in SOCIAL_PLATFORMS
        if author:
            res.advertiser = Party(
                name=author,
                kind="influencer" if social else "advertiser",
                handle=doc.author.handle,
                url=doc.author.url,
            )
        elif adv_company:
            res.advertiser = Party(
                name=adv_company.name, kind="advertiser", krs=adv_company.krs, country=adv_company.country
            )
        if res.firm and res.advertiser:
            res.third_party = not _same_entity(res.firm.name, res.advertiser.name)
        elif res.firm and adv_company:
            res.third_party = not _same_entity(res.firm.name, adv_company.name)

        seen = {p.name for p in (res.firm, res.advertiser) if p}
        for c in ctx.companies:
            if c.name not in seen:
                kind = "pr_agency" if c.role == "pr_agency" else "company"
                res.others.append(Party(name=c.name, kind=kind, krs=c.krs, country=c.country))
                seen.add(c.name)
        declared = ctx.declared
        if declared and declared.legal_adviser_name and declared.legal_adviser_name not in seen:
            res.others.append(Party(name=declared.legal_adviser_name, kind="lawyer"))
        return res

    # ------------------------------------------------------------------ registers
    def firm_register_matches(self, name: str) -> dict[str, object]:
        """Lookup of one name in the five KNF investment-firm registers."""
        return {reg: self.registries.lookup(reg, name) for reg in KNF_FIRM_REGISTERS}
