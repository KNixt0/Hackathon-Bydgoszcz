"""Three-round debate: parallel specialists -> critic -> arbiter."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ..context import AnalysisContext
from ..plugins import Plugin
from ..schemas import Claim, Debate, DebateRound
from .agents import AGENT_CLASSES, claim_counter
from .arbiter import Arbiter, Verdict
from .critic import Critic, World
from .models import AgentReport, DebateClaim

RULE_BASED = "agent regułowy"


@dataclass
class DebateOutcome:
    reports: list[AgentReport]
    against: list[DebateClaim]
    verdict: Verdict
    world: World
    critic_summary: str
    extra_claims: list[DebateClaim]

    def all_claims(self) -> list[DebateClaim]:
        return [c for r in self.reports for c in r.claims] + self.extra_claims + self.against

    def to_schema(self, rationale: str | None = None, model: str | None = None) -> Debate:
        """model: name of the language model, set only when it actually wrote part of the result.

        The debate agents are rule-based; their roles say so, and only the rounds a model really took
        part in name it.
        """
        rounds = [
            DebateRound(
                round=1,
                agent=r.agent,
                role=f"{RULE_BASED}: {r.role}",
                summary=r.summary,
                claim_ids=[c.id for c in r.claims],
            )
            for r in self.reports
        ]
        if self.extra_claims:
            rounds.append(
                DebateRound(
                    round=1,
                    agent=f"Model językowy ({model or 'Ollama'})",
                    role="Dodatkowe tezy modelu, przyjmowane tylko po weryfikacji cytatu w źródle",
                    summary=f"Zaproponowane tezy: {len(self.extra_claims)}.",
                    claim_ids=[c.id for c in self.extra_claims],
                )
            )
        rounds.append(
            DebateRound(
                round=2,
                agent=Critic.name,
                role=f"{RULE_BASED}: {Critic.role}",
                summary=self.critic_summary,
                claim_ids=[c.id for c in self.against],
            )
        )
        v = self.verdict
        rounds.append(
            DebateRound(
                round=3,
                agent=Arbiter.name,
                role=f"{RULE_BASED}: {Arbiter.role}"
                + (f"; uzasadnienie zredagował model {model}" if model and rationale else ""),
                summary=v.summary,
                claim_ids=v.arguments_for + v.arguments_against,
            )
        )
        return Debate(
            rounds=rounds,
            claims=[
                Claim(
                    id=c.id,
                    stance=c.stance,
                    text=c.text,
                    confidence=round(c.confidence, 2),
                    evidence_ids=c.evidence_ids,
                    verdict=c.verdict,
                    critique=c.critique,
                )
                for c in self.all_claims()
            ],
            arguments_for=v.arguments_for,
            arguments_against=v.arguments_against,
            arbiter_rationale=rationale or v.rationale,
        )


async def run_debate(ctx: AnalysisContext, plugins: list[Plugin]) -> DebateOutcome:
    ids = claim_counter()
    agents = [cls(plugins) for cls in AGENT_CLASSES]
    # Round 1: the specialists work concurrently and do not see each other's claims.
    reports = list(await asyncio.gather(*(agent.run(ctx, ids) for agent in agents)))
    # Round 2: cross-critique.
    critic = Critic()
    against, critic_summary, world = critic.review(ctx, reports, ids)
    # Round 3: arbitration and aggregation.
    verdict = Arbiter().decide(reports, against)
    return DebateOutcome(reports, against, verdict, world, critic_summary, [])
