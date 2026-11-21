"""Internal debate objects (richer than the contract's `Claim`)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..plugins import PluginFinding, PluginResult


@dataclass
class DebateClaim:
    id: str
    stance: str  # for | against
    text: str
    confidence: float
    evidence_ids: list[str]
    agent: str
    code: str  # finding code ("for") or mitigation key ("against")
    plugin: str | None = None
    finding: PluginFinding | None = None
    verdict: str = "upheld"
    critique: str | None = None
    origin: str = "engine"  # engine | llm


@dataclass
class AgentReport:
    agent: str
    role: str
    results: list[PluginResult] = field(default_factory=list)
    claims: list[DebateClaim] = field(default_factory=list)
    summary: str = ""
