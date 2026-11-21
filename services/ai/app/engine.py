"""The analysis pipeline: preprocess -> debate (plugins, critic, arbiter) -> one `Analysis`."""

from __future__ import annotations

import itertools
import time

from . import __version__
from .config import Settings
from .context import SOCIAL_PLATFORMS, AnalysisContext
from .debate import DebateOutcome, run_debate
from .llm import OllamaClient, propose_claims, rewrite_rationale
from .plugins import get_plugins
from .preprocess import build_embedder, preprocess
from .registries import RegistryStore
from .rules import run_rules
from .schemas import (
    Analysis,
    Context,
    Document,
    EngineInfo,
    Entities,
    Finding,
    Graph,
    ModuleResult,
    RegistryCheck,
    Source,
)
from .scoring import plugin_weight

PLATFORM_PL = {
    "web": "strona WWW",
    "youtube": "YouTube",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "tiktok": "TikTok",
    "x": "X",
    "google_ads": "Google Ads",
    "sample": "próbka",
}
LEVEL_SUMMARY = {
    "green": "Nie stwierdzono istotnych naruszeń",
    "orange": "Materiał budzi wątpliwości i wymaga wyjaśnienia",
    "red": "Wysokie ryzyko naruszenia",
}


class Engine:
    def __init__(self, settings: Settings, registries: RegistryStore | None = None) -> None:
        self.settings = settings
        self.registries = registries or RegistryStore(settings.data_dir, settings.demo_overlay)
        self.embedder = build_embedder(settings.embeddings_backend, settings.ollama_url, settings.ollama_embed_model)
        self.plugins = get_plugins()
        self.llm = OllamaClient(settings)

    async def analyze(self, document: Document, context: Context | None = None) -> Analysis:
        started = time.perf_counter()
        context = context or Context()
        page = preprocess(document.html, document.text, document.title, document.language)
        ctx = AnalysisContext(document, context, page, self.registries, self.embedder)
        outcome = await run_debate(ctx, list(self.plugins.values()))

        llm_used = False
        rationale = None
        if await self.llm.available():
            ids = itertools.count(len(outcome.all_claims()) + 1)
            extra = await propose_claims(self.llm, ctx, outcome.all_claims(), ids)
            if extra:
                outcome.extra_claims = extra
                llm_used = True
            rationale = await rewrite_rationale(self.llm, outcome.verdict.rationale)
            llm_used = llm_used or rationale is not None

        return self._assemble(ctx, outcome, rationale, llm_used, started)

    # ------------------------------------------------------------------ assembly
    def _assemble(
        self, ctx: AnalysisContext, outcome: DebateOutcome, rationale: str | None, llm_used: bool, started: float
    ) -> Analysis:
        doc, context, page, verdict = ctx.document, ctx.context, ctx.page, outcome.verdict
        results = [res for report in outcome.reports for res in report.results]
        by_plugin = {res.plugin: res for res in results}

        # primary module: the caller's hint if that module produced findings, else the strongest module
        module_strength = {
            res.module: plugin_weight(res.plugin) * verdict.plugin_scores[res.plugin]
            for res in results
            if res.module is not None and res.findings
        }
        if context.module_hint in module_strength:
            primary = context.module_hint
        else:
            primary = max(module_strength, key=lambda m: (module_strength[m], -m)) if module_strength else 2

        claim_by_finding = {id(c.finding): c for c in outcome.all_claims() if c.finding is not None}
        module_results = []
        for res in results:
            if not res.findings:
                continue
            module_results.append(
                ModuleResult(
                    module=res.module or primary,
                    plugin=res.plugin,
                    score=verdict.plugin_scores[res.plugin],
                    weight=plugin_weight(res.plugin),
                    findings=[
                        Finding(
                            code=f.code,
                            severity=f.severity,
                            text=f.text,
                            evidence_ids=list(dict.fromkeys(f.evidence_ids)),
                        )
                        for f in res.findings
                        if not (
                            id(f) in claim_by_finding
                            and claim_by_finding[id(f)].verdict == "rejected"
                            and claim_by_finding[id(f)].critique.startswith("Odrzucono: brak ugruntowania")
                        )
                    ],
                )
            )
        modules = sorted({m.module for m in module_results}) or [primary]

        rules = next((res.rules for res in results if res.rules), None) or run_rules(ctx)
        checks: list[RegistryCheck] = []
        seen = set()
        for res in results:
            for check in res.registry_checks:
                key = (check.registry, check.subject)
                if key not in seen:
                    seen.add(key)
                    checks.append(check)
        graph_res, forensic_res = by_plugin.get("graph_intel"), by_plugin.get("opinion_forensics")
        graph = (graph_res.graph if graph_res and graph_res.graph else None) or Graph(
            nodes=[], edges=[], flagged_paths=[]
        )

        if doc.archive.html_key:
            ctx.evidence.archive(doc.archive.html_key, "Zarchiwizowany kod HTML materiału")
        if doc.archive.screenshot_key:
            ctx.evidence.archive(doc.archive.screenshot_key, "Zarchiwizowany zrzut ekranu")
        ctx.evidence.url(doc.url, "Adres analizowanego materiału")

        ent = ctx.entities
        score = verdict.breakdown.risk_score
        failed = [r.id for r in rules if r.status == "fail"]
        return Analysis(
            title=self._title(ctx, primary),
            summary=self._summary(outcome, failed),
            modules=modules,
            primary_module=primary,
            risk_score=score,
            compliance_score=round(100.0 - score, 1),
            risk_level=verdict.level,
            synthetic=bool(context.synthetic),
            ground_truth=context.ground_truth,
            demo_case=context.demo_case,
            source=Source(
                platform=doc.platform,
                url=doc.url,
                fetched_at=doc.fetched_at,
                language=page.language,
                content_hash=page.content_hash,
                text=page.text,
                archive=doc.archive,
            ),
            entities=Entities(investment_firm=ent.firm, advertiser=ent.advertiser, others=ent.others),
            module_results=module_results,
            rules=rules,
            registry_checks=checks,
            graph=graph,
            forensics=forensic_res.forensics if forensic_res else None,
            financials=graph_res.financials if graph_res else None,
            debate=outcome.to_schema(rationale),
            evidence=ctx.evidence.items,
            recommendation=verdict.recommendation,
            engine=EngineInfo(
                version=__version__,
                plugins=[r.plugin for r in results],
                llm_used=llm_used,
                model=self.llm.model if llm_used else None,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            ),
        )

    @staticmethod
    def _title(ctx: AnalysisContext, primary: int) -> str:
        ent, doc = ctx.entities, ctx.document
        firm = ent.firm.name if ent.firm else None
        where = PLATFORM_PL[doc.platform]
        if primary == 3:
            return f"Oferta doradztwa inwestycyjnego: {firm or ctx.host or 'podmiot nieustalony'}"
        if primary == 1 and firm and ent.advertiser:
            kind = "u twórcy" if doc.platform in SOCIAL_PLATFORMS else "w serwisie"
            return f"Reklama {firm} {kind} „{ent.advertiser.name}” ({where})"
        return f"Informacja o ryzyku w materiale {firm or ctx.host or 'bez wskazanej firmy'} ({where})"

    @staticmethod
    def _summary(outcome: DebateOutcome, failed: list[str]) -> str:
        v = outcome.verdict
        kept = {c.id: c for c in outcome.all_claims()}
        first = f"{LEVEL_SUMMARY[v.level]} (ryzyko {v.breakdown.risk_score:.0f}/100)."
        if not v.arguments_for:
            return f"{first} Żadna teza o naruszeniu nie utrzymała się po weryfikacji."
        top = kept[v.arguments_for[0]].text
        rules = f" Naruszone kryteria informacji o ryzyku: {', '.join(failed)}." if failed else ""
        return f"{first} Najpoważniejsze ustalenie: {top}{rules}"
