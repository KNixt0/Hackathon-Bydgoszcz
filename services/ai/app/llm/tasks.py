"""What the optional LLM may do, and the guards around it.

(a) rewrite the arbiter rationale in natural Polish: accepted only if it introduces no
    number that is absent from the deterministic rationale,
(b) propose extra claims: each must carry a quote, and is accepted only if that quote is an
    exact substring of the source text (same grounding check as for the engine's claims).
"""

from __future__ import annotations

import json
import re

from ..context import AnalysisContext
from ..debate.critic import grounding_error
from ..debate.models import DebateClaim
from .ollama import OllamaClient

MAX_SOURCE_CHARS = 6000
MAX_LLM_CLAIMS = 3
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")

REWRITE_SYSTEM = (
    "Jesteś analitykiem nadzoru finansowego. Przeredaguj podane uzasadnienie na zwięzły, naturalny język polski "
    "(3-5 zdań). Nie dodawaj żadnych nowych faktów, liczb ani ocen. Zachowaj wynik i rekomendację."
)
CLAIMS_SYSTEM = (
    "Jesteś analitykiem nadzoru finansowego. Wskaż w tekście reklamy lub oferty fragmenty, które mogą naruszać "
    "zasady rzetelnej informacji o ryzyku albo świadczyć o doradztwie inwestycyjnym bez zezwolenia. Odpowiedz "
    'wyłącznie JSON-em: {"claims": [{"text": "krótka teza po polsku", "quote": "DOSŁOWNY cytat z tekstu"}]}. '
    "Cytat musi być skopiowany znak po znaku. Jeżeli nic nie znajdujesz, zwróć pustą listę."
)


async def rewrite_rationale(client: OllamaClient, rationale: str) -> str | None:
    text = await client.generate(rationale, REWRITE_SYSTEM)
    if not text or not (40 <= len(text) <= 1500):
        return None
    allowed = set(_NUMBER.findall(rationale))
    if any(n not in allowed for n in _NUMBER.findall(text)):
        return None  # the model changed or invented a figure
    return text


async def propose_claims(
    client: OllamaClient, ctx: AnalysisContext, existing: list[DebateClaim], next_id
) -> list[DebateClaim]:
    raw = await client.generate(ctx.page.text[:MAX_SOURCE_CHARS], CLAIMS_SYSTEM, json_mode=True)
    if not raw:
        return []
    try:
        items = json.loads(raw).get("claims", [])
    except (json.JSONDecodeError, AttributeError):
        return []
    known_quotes = {
        ctx.evidence.get(e).quote
        for c in existing
        for e in c.evidence_ids
        if ctx.evidence.get(e) is not None and ctx.evidence.get(e).kind == "quote"
    }
    accepted: list[DebateClaim] = []
    for item in items if isinstance(items, list) else []:
        if len(accepted) >= MAX_LLM_CLAIMS or not isinstance(item, dict):
            break
        text, quote = str(item.get("text", "")).strip(), str(item.get("quote", "")).strip()
        start = ctx.page.text.find(quote) if len(quote) >= 12 else -1
        if not text or start < 0:
            continue  # ungrounded: the quote is not in the source, the claim is dropped
        if any(quote in k or k in quote for k in known_quotes if k):
            continue  # already covered by an engine claim
        ev_id = ctx.evidence.quote(start, start + len(quote), "Cytat wskazany przez model językowy")
        claim = DebateClaim(
            id=f"c{next(next_id)}",
            stance="for",
            text=text[:300],
            confidence=0.5,
            evidence_ids=[ev_id],
            agent="Model językowy (Ollama)",
            code="LLM_CLAIM",
            origin="llm",
            verdict="weakened",
            critique="Teza zaproponowana przez model językowy; cytat zweryfikowany w źródle. Nie wpływa na wynik "
            "liczbowy, wymaga oceny analityka.",
        )
        if grounding_error(ctx.evidence, claim.evidence_ids) is None:
            accepted.append(claim)
    return accepted
