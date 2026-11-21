"""Plugin (strategy) interface.

A plugin inspects one document through `AnalysisContext` and returns findings plus any
structured output it owns (rule rows, register checks, graph, forensics, financials).
Adding a module = adding one file to this package with a `Plugin` subclass; the registry in
`plugins/__init__.py` discovers it automatically.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..context import AnalysisContext
from ..schemas import Financials, Forensics, Graph, RegistryCheck, RuleResult


@dataclass
class PluginFinding:
    code: str  # also the key into scoring.weights.FINDING_WEIGHTS
    severity: str  # high | medium | low | info
    text: str  # Polish, user-facing
    evidence_ids: list[str] = field(default_factory=list)
    confidence: float = 0.8  # how sure the detector is, before the critic looks at it
    data: dict = field(default_factory=dict)  # machine-readable details for the critic


@dataclass
class PluginResult:
    plugin: str
    module: int | None
    findings: list[PluginFinding] = field(default_factory=list)
    rules: list[RuleResult] | None = None
    registry_checks: list[RegistryCheck] = field(default_factory=list)
    graph: Graph | None = None
    forensics: Forensics | None = None
    financials: Financials | None = None


class Plugin(ABC):
    id: str = ""
    module: int | None = None  # 1 | 2 | 3, or None for cross-cutting intelligence plugins
    description: str = ""
    agent: str = "regulatory"  # which round-1 debate agent runs this plugin

    def applies(self, ctx: AnalysisContext) -> bool:
        return True

    @abstractmethod
    def run(self, ctx: AnalysisContext) -> PluginResult: ...

    def result(self, **kwargs) -> PluginResult:
        return PluginResult(plugin=self.id, module=self.module, **kwargs)
