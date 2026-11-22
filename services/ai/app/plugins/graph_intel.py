"""Company / person graph intelligence (KRS-style relations) and company financial flags.

Path-finding over `context.graph`: the plugin searches simple paths between the firm side
(the firm and companies tied to it by ownership) and the publisher of the material, and
flags the ones that run through people or a PR agency, e.g.
board member of the parent company -> PR agency -> influencer.
"""

from __future__ import annotations

from collections import defaultdict

from ..context import AnalysisContext, _same_entity, firm_node_ids, parse_date
from ..schemas import Financials, FlaggedPath, Graph, GraphEdge, GraphNode, Statement
from .base import Plugin, PluginFinding, PluginResult

MAX_PATH_EDGES = 5
PERSONAL_TIES = {"board_member", "owner", "beneficial_owner", "employs", "related"}
OWNERSHIP = {"owner", "beneficial_owner"}
EDGE_PL = {
    "board_member": "członek zarządu",
    "owner": "właściciel",
    "beneficial_owner": "beneficjent rzeczywisty",
    "employs": "zatrudnienie",
    "contract": "umowa",
    "promotes": "promuje",
    "related": "powiązanie",
    "publishes": "publikuje",
}
EEA = {
    "PL",
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
    "IS",
    "LI",
    "NO",
}
MIN_SHARE_CAPITAL_PLN = 5000


class GraphIntelPlugin(Plugin):
    id = "graph_intel"
    module = None
    agent = "graph"
    description = (
        "Graf powiązań kapitałowo-osobowych (KRS/CRBR/umowy): wyszukiwanie ścieżek firma → osoby → "
        "agencja PR → influencer oraz flagi finansowe spółki (wiek, kapitał, sprawozdania)."
    )

    def applies(self, ctx: AnalysisContext) -> bool:
        graph = ctx.context.graph
        return bool((graph and graph.nodes) or ctx.context.companies)

    def run(self, ctx: AnalysisContext) -> PluginResult:
        findings: list[PluginFinding] = []
        graph = self._graph(ctx, findings)
        financials = self._financials(ctx, findings)
        return self.result(findings=findings, graph=graph, financials=financials)

    # ------------------------------------------------------------------ graph
    def _graph(self, ctx: AnalysisContext, findings: list[PluginFinding]) -> Graph | None:
        raw = ctx.context.graph
        if not raw or not raw.nodes:
            return None
        nodes = {n.id: n for n in raw.nodes}
        edges = [e for e in raw.edges if e.source in nodes and e.target in nodes]
        adjacency: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for i, e in enumerate(edges):
            adjacency[e.source].append((e.target, i))
            adjacency[e.target].append((e.source, i))

        ent = ctx.entities
        firm_nodes = firm_node_ids(raw, ent.firm.name if ent.firm else None)
        targets = [
            n.id
            for n in raw.nodes
            if n.type == "influencer" or (ent.advertiser and _same_entity(n.label, ent.advertiser.name))
        ]
        targets = [t for t in targets if t not in firm_nodes]

        flagged: list[tuple[list[str], list[int]]] = []
        for target in targets:
            best = None
            for start in firm_nodes:
                for path_nodes, path_edges in _simple_paths(adjacency, start, target, MAX_PATH_EDGES):
                    if not _is_hidden_tie(path_nodes, path_edges, nodes, edges):
                        continue
                    if best is None or len(path_edges) < len(best[1]):
                        best = (path_nodes, path_edges)
            if best:
                flagged.append(best)

        suspicious_edges = {i for _, path_edges in flagged for i in path_edges}
        out_paths = []
        for path_nodes, path_edges in flagged:
            steps = [nodes[path_nodes[0]].label]
            for node_id, edge_i in zip(path_nodes[1:], path_edges, strict=True):
                steps.append(f"({EDGE_PL[edges[edge_i].type]}) {nodes[node_id].label}")
            description = " → ".join(steps)
            out_paths.append(FlaggedPath(node_ids=path_nodes, description=description))
            via_pr = any(nodes[n].type == "pr_agency" for n in path_nodes[1:-1])
            ev = [ctx.evidence.krs(description, f"Ścieżka powiązań: {description}")]
            findings.append(
                PluginFinding(
                    "PR_CONFLICT_PATH" if via_pr else "PERSONAL_TIE_PATH",
                    "high" if via_pr else "medium",
                    "Graf powiązań ujawnia nieujawnioną w materiale ścieżkę między firmą a promującym ją twórcą: "
                    f"{description}.",
                    ev,
                    0.8 if via_pr else 0.65,
                    {"path": path_nodes},
                )
            )
        if targets and firm_nodes and not flagged:
            findings.append(
                PluginFinding(
                    "NO_HIDDEN_TIES",
                    "info",
                    "Graf powiązań nie wykazuje ukrytych powiązań osobowych ani kapitałowych między firmą a twórcą "
                    "publikacji.",
                    [],
                    0.8,
                )
            )
        return Graph(
            nodes=[GraphNode(id=n.id, type=n.type, label=n.label, meta=n.meta) for n in raw.nodes],
            edges=[
                GraphEdge(
                    source=e.source,
                    target=e.target,
                    type=e.type,
                    label=e.label or EDGE_PL[e.type],
                    suspicious=i in suspicious_edges,
                )
                for i, e in enumerate(edges)
            ],
            flagged_paths=out_paths,
        )

    # ------------------------------------------------------------------ financials
    def _financials(self, ctx: AnalysisContext, findings: list[PluginFinding]) -> Financials | None:
        companies = ctx.context.companies
        company = next((c for c in companies if c.role == "investment_firm"), None)
        if company is None:
            return None
        flags: list[str] = []
        age_months = None
        incorporated = parse_date(company.incorporated_on)
        if incorporated:
            age_months = max(
                0,
                (ctx.now.year - incorporated.year) * 12
                + ctx.now.month
                - incorporated.month
                - (1 if ctx.now.day < incorporated.day else 0),
            )
        ev = [
            ctx.evidence.krs(
                company.name,
                f"Dane rejestrowe spółki {company.name}" + (f" (KRS {company.krs})" if company.krs else ""),
            )
        ]
        if age_months is not None and age_months < 12:
            flags.append("Spółka młodsza niż 12 miesięcy")
            findings.append(
                PluginFinding(
                    "COMPANY_YOUNG", "low", f"Spółka „{company.name}” działa od {age_months} miesięcy.", ev, 0.9
                )
            )
        if company.share_capital_pln is not None and company.share_capital_pln <= MIN_SHARE_CAPITAL_PLN:
            flags.append(f"Minimalny kapitał zakładowy ({company.share_capital_pln:,.0f} zł)".replace(",", " "))
            findings.append(
                PluginFinding(
                    "LOW_SHARE_CAPITAL",
                    "low",
                    f"Kapitał zakładowy spółki „{company.name}” to {company.share_capital_pln:,.0f} zł (ustawowe "
                    "minimum).".replace(",", " "),
                    ev,
                    0.9,
                )
            )
        filed = [s for s in company.statements if s.filed]
        known_facts = incorporated or company.statements or company.share_capital_pln is not None
        if known_facts and not filed:
            flags.append("Brak pełnego sprawozdania finansowego")
            findings.append(
                PluginFinding(
                    "NO_FINANCIAL_STATEMENTS",
                    "low",
                    f"Spółka „{company.name}” nie złożyła dotąd pełnego sprawozdania finansowego.",
                    ev,
                    0.85,
                )
            )
        # WatchIt: no marker based on whether the entity comes from inside or outside the EU / EEA
        # (requirement 1: such "unknown origin" markers are removed from the interface).
        return Financials(
            company=company.name,
            krs=company.krs,
            incorporated_on=company.incorporated_on,
            age_months=age_months,
            share_capital_pln=company.share_capital_pln,
            statements=[
                Statement(year=s.year, revenue_pln=s.revenue_pln, net_result_pln=s.net_result_pln, filed=s.filed)
                for s in company.statements
            ],
            flags=flags,
        )


def _simple_paths(adjacency: dict[str, list[tuple[str, int]]], start: str, goal: str, max_edges: int):
    """Depth-first enumeration of simple paths (no repeated node) up to `max_edges`."""
    stack = [(start, [start], [])]
    while stack:
        node, path_nodes, path_edges = stack.pop()
        if node == goal and path_edges:
            yield path_nodes, path_edges
            continue
        if len(path_edges) >= max_edges:
            continue
        for neighbour, edge_i in adjacency[node]:
            if neighbour not in path_nodes:
                stack.append((neighbour, [*path_nodes, neighbour], [*path_edges, edge_i]))


def _is_hidden_tie(path_nodes: list[str], path_edges: list[int], nodes: dict, edges: list) -> bool:
    """A path is a hidden tie when it runs through an intermediary and a personal/ownership link.

    The direct commercial relation (firm -contract/promotes-> publisher) is the disclosed,
    expected one and is not flagged.
    """
    if len(path_edges) < 2:
        return False
    types = [edges[i].type for i in path_edges]
    intermediaries = [nodes[n] for n in path_nodes[1:-1]]
    if any(n.type == "ad" for n in intermediaries):
        return False
    has_personal = any(t in PERSONAL_TIES for t in types)
    via_person_or_pr = any(n.type in {"person", "pr_agency"} for n in intermediaries)
    return has_personal and via_person_or_pr
