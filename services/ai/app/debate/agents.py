"""Round 1: three specialised agents work in parallel and emit claims with evidence."""

from __future__ import annotations

import itertools
from collections.abc import Iterator

from ..context import AnalysisContext
from ..plugins import Plugin
from .models import AgentReport, DebateClaim


class Agent:
    key = ""  # matches Plugin.agent
    name = ""
    role = ""

    def __init__(self, plugins: list[Plugin]) -> None:
        self.plugins = [p for p in plugins if p.agent == self.key]

    async def run(self, ctx: AnalysisContext, ids: Iterator[int]) -> AgentReport:
        report = AgentReport(agent=self.name, role=self.role)
        for plugin in self.plugins:
            if not plugin.applies(ctx):
                continue
            result = plugin.run(ctx)
            report.results.append(result)
            for finding in result.findings:
                if finding.severity == "info":
                    continue
                report.claims.append(
                    DebateClaim(
                        id=f"c{next(ids)}",
                        stance="for",
                        text=finding.text,
                        confidence=finding.confidence,
                        evidence_ids=list(finding.evidence_ids),
                        agent=self.name,
                        code=finding.code,
                        plugin=result.plugin,
                        finding=finding,
                    )
                )
        report.summary = self.summarise(report)
        return report

    def summarise(self, report: AgentReport) -> str:
        ran = ", ".join(r.plugin for r in report.results) or "brak danych wejściowych"
        return f"Uruchomione analizy: {ran}. Zgłoszone tezy o naruszeniach: {len(report.claims)}."


class RegulatoryAdvertisingAgent(Agent):
    key = "regulatory"
    name = "Agent regulacyjno-reklamowy"
    role = "Moduły 1–3: reguły informacji o ryzyku, rejestry KNF/KIRP/KIDP, art. 76 ustawy o obrocie"

    def summarise(self, report: AgentReport) -> str:
        rules = next((r.rules for r in report.results if r.rules), None)
        failed = [r.id for r in rules or [] if r.status == "fail"]
        parts = [f"Uruchomione moduły: {', '.join(r.plugin for r in report.results)}."]
        if rules:
            parts.append(f"Naruszone kryteria: {', '.join(failed) if failed else 'brak'}.")
        parts.append(f"Zgłoszone tezy: {len(report.claims)}.")
        return " ".join(parts)


class GraphInvestigator(Agent):
    key = "graph"
    name = "Śledczy KRS / grafu powiązań"
    role = "Powiązania kapitałowo-osobowe, agencje PR, kondycja i wiek spółki"

    def summarise(self, report: AgentReport) -> str:
        if not report.results:
            return "Brak danych o powiązaniach i spółkach w kontekście sprawy."
        graph = report.results[0].graph
        paths = len(graph.flagged_paths) if graph else 0
        return (
            f"Przeanalizowano graf powiązań ({len(graph.nodes) if graph else 0} węzłów); oznaczone ścieżki: "
            f"{paths}. Zgłoszone tezy: {len(report.claims)}."
        )


class OpinionForensicsAgent(Agent):
    key = "forensics"
    name = "Agent analizy opinii"
    role = "Autentyczność komentarzy: skoki aktywności, wiek i pochodzenie kont, wzorce nazw"

    def summarise(self, report: AgentReport) -> str:
        if not report.results or not report.results[0].forensics:
            return "Brak komentarzy do analizy."
        acc = report.results[0].forensics.accounts
        return (
            f"Przeanalizowano {acc.total} komentarzy; {acc.share_younger_14d:.0%} z kont młodszych niż 14 dni. "
            f"Zgłoszone tezy: {len(report.claims)}."
        )


AGENT_CLASSES = [RegulatoryAdvertisingAgent, GraphInvestigator, OpinionForensicsAgent]


def claim_counter() -> Iterator[int]:
    return itertools.count(1)
