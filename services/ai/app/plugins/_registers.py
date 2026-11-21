"""Register lookups shared by the module plugins."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..context import ATTACHMENT_REGISTERS, AnalysisContext
from ..registries import KNF_FIRM_REGISTERS, KNF_OTHER_LICENSED, REGISTRIES, Match
from ..schemas import RegistryCheck
from ..scope import is_tfi_name
from .base import PluginFinding


def make_check(ctx: AnalysisContext, registry: str, subject: str, status: str, detail: str) -> RegistryCheck:
    label, url = REGISTRIES[registry]
    return RegistryCheck(
        registry=registry,
        label=label,
        url=url,
        subject=subject,
        status=status,
        detail=detail,
        snapshot_date=ctx.registries.snapshot(registry).snapshot_date,
    )


def registry_evidence(ctx: AnalysisContext, registry: str, subject: str, status_pl: str) -> str:
    label, url = REGISTRIES[registry]
    return ctx.evidence.registry(registry, subject, f"{label}: „{subject}” – {status_pl}", url)


@dataclass
class FirmLookup:
    name: str
    checks: list[RegistryCheck] = field(default_factory=list)
    listed: Match | None = None
    listed_in: list[str] = field(default_factory=list)
    similar: Match | None = None  # a registered entity with a similar name / the same brand
    warning: Match | None = None
    other_licence: Match | None = None  # e.g. a TFI: supervised by KNF, but not an investment firm
    other_licence_in: str | None = None
    evidence_ids: list[str] = field(default_factory=list)


def lookup_firm(ctx: AnalysisContext, name: str) -> FirmLookup:
    """Check one entity in the five KNF investment-firm registers and the public warnings."""
    cache = ctx.__dict__.setdefault("_firm_lookups", {})
    if name in cache:
        return cache[name]
    res = FirmLookup(name)
    for registry in KNF_FIRM_REGISTERS:
        match = ctx.registries.lookup(registry, name)
        if match and match.listed:
            detail = f"Dopasowano wpis: {match.entry['name']}"
            if match.entry.get("detail"):
                detail += f" ({match.entry['detail']})"
            if match.entry.get("synthetic"):
                detail += " [wpis fikcyjny, dane demonstracyjne]"
            res.checks.append(make_check(ctx, registry, name, "listed", detail))
            res.listed = res.listed or match
            res.listed_in.append(registry)
            res.evidence_ids.append(registry_evidence(ctx, registry, name, "figuruje"))
        else:
            detail = "Brak wpisu o tej nazwie"
            if match:
                detail += f"; nazwa podobna do wpisu: {match.entry['name']}"
                if res.similar is None or match.score > res.similar.score:
                    res.similar = match
            res.checks.append(make_check(ctx, registry, name, "not_listed", detail))
    for registry in KNF_OTHER_LICENSED:
        match = ctx.registries.lookup(registry, name)
        if match and match.listed:
            res.other_licence, res.other_licence_in = match, registry
            res.checks.append(make_check(ctx, registry, name, "listed", f"Dopasowano wpis: {match.entry['name']}"))
            res.evidence_ids.append(registry_evidence(ctx, registry, name, "figuruje"))
        elif is_tfi_name(name):
            status = (
                "not_checked"
                if _sample_miss(ctx, registry) or not ctx.registries.snapshot(registry).entries
                else "not_listed"
            )
            detail = "Nazwa wskazuje na TFI, a nie ma jej w rejestrze TFI" if status == "not_listed" else SAMPLE_DETAIL
            res.checks.append(make_check(ctx, registry, name, status, detail))
    if not res.listed and not res.other_licence:
        res.evidence_ids.append(registry_evidence(ctx, "knf_investment_firms", name, "brak wpisu"))
    res.evidence_ids.append(
        ctx.evidence.legal(
            "definicja firmy inwestycyjnej i wykaz rejestrów KNF (ustawa o obrocie instrumentami finansowymi)",
            "Rejestry firm inwestycyjnych KNF",
            ATTACHMENT_REGISTERS,
        )
    )

    warn = ctx.registries.lookup("knf_public_warnings", name)
    if not (warn and warn.listed) and ctx.host:
        for entry in ctx.registries.snapshot("knf_public_warnings").entries:
            if ctx.host in [a.lower() for a in entry.get("aliases", [])]:
                warn = Match(entry, 1.0, "alias")
    if warn and warn.listed:
        res.warning = warn
        res.checks.append(
            make_check(
                ctx,
                "knf_public_warnings",
                name,
                "warning_listed",
                f"{warn.entry['name']}: {warn.entry.get('detail', '')}".strip(": "),
            )
        )
        res.evidence_ids.append(registry_evidence(ctx, "knf_public_warnings", name, "wpis na liście ostrzeżeń"))
    else:
        if _sample_miss(ctx, "knf_public_warnings"):
            res.checks.append(make_check(ctx, "knf_public_warnings", name, "not_checked", SAMPLE_DETAIL))
        else:
            res.checks.append(
                make_check(ctx, "knf_public_warnings", name, "not_listed", "Brak wpisu na liście ostrzeżeń")
            )
    cache[name] = res
    return res


OUTSIDE_UKNF = " Informacja dla samorządu zawodowego (KIRP/KIDP), poza właściwością UKNF; nie wpływa na wynik."

SAMPLE_DETAIL = (
    "Migawka tego rejestru jest próbką (niepełną lub demonstracyjną); brak wpisu nie oznacza, że podmiotu "
    "nie ma w rejestrze. Sprawdź w rejestrze źródłowym."
)


def _sample_miss(ctx: AnalysisContext, registry: str) -> bool:
    """A lookup miss in a sample snapshot must not be reported against a real document."""
    return _partial(ctx, registry) and not ctx.context.synthetic


def _partial(ctx: AnalysisContext, registry: str) -> bool:
    meta = ctx.registries.snapshot(registry).meta
    return bool(meta.get("partial") or meta.get("synthetic_sample"))


def check_professionals(
    ctx: AnalysisContext, licence_from_text: str | None = None
) -> tuple[list[RegistryCheck], list[PluginFinding]]:
    """Verify declared professionals: investment adviser licence, legal adviser, tax adviser.

    Runs once per analysis (the first plugin that asks gets the result).
    """
    if ctx.__dict__.get("_professionals_done"):
        return [], []
    ctx.__dict__["_professionals_done"] = True
    declared = ctx.context.declared
    checks: list[RegistryCheck] = []
    findings: list[PluginFinding] = []

    licence = (declared.advisor_licence_no if declared else None) or licence_from_text
    if licence:
        reg = "knf_investment_advisors"
        entry = ctx.registries.lookup_number(reg, licence)
        subject = f"licencja doradcy inwestycyjnego nr {licence}"
        if entry:
            checks.append(make_check(ctx, reg, subject, "listed", f"Dopasowano wpis: {entry['name']}"))
            findings.append(
                PluginFinding(
                    "ADVISOR_LICENCE_VALID",
                    "info",
                    f"Deklarowana {subject} figuruje na liście doradców inwestycyjnych KNF.",
                    [registry_evidence(ctx, reg, subject, "figuruje")],
                    0.9,
                )
            )
        elif _sample_miss(ctx, reg):
            checks.append(make_check(ctx, reg, subject, "not_checked", SAMPLE_DETAIL))
        else:
            checks.append(make_check(ctx, reg, subject, "not_listed", "Numer licencji nie występuje na liście"))
            findings.append(
                PluginFinding(
                    "FAKE_LICENCE",
                    "high",
                    f"Deklarowana {subject} nie występuje na liście doradców inwestycyjnych KNF.",
                    [registry_evidence(ctx, reg, subject, "brak wpisu")],
                    0.85,
                    {"partial_snapshot": _partial(ctx, reg)},
                )
            )

    if declared and (declared.legal_adviser_name or declared.legal_adviser_no):
        reg = "kirp_legal_advisers"
        entry = ctx.registries.lookup_number(reg, declared.legal_adviser_no) if declared.legal_adviser_no else None
        if entry is None and declared.legal_adviser_name:
            match = ctx.registries.lookup(reg, declared.legal_adviser_name)
            entry = match.entry if match and match.listed else None
        subject = " / ".join(x for x in (declared.legal_adviser_name, declared.legal_adviser_no) if x)
        if entry is None and _sample_miss(ctx, reg):
            checks.append(make_check(ctx, reg, subject, "not_checked", SAMPLE_DETAIL))
        elif entry is None:
            checks.append(make_check(ctx, reg, subject, "not_listed", "Brak wpisu w rejestrze radców prawnych"))
            findings.append(
                PluginFinding(
                    "LEGAL_ADVISER_NOT_FOUND",
                    "info",
                    f"Radca prawny powołany w materiale ({subject}) nie figuruje w rejestrze KIRP." + OUTSIDE_UKNF,
                    [registry_evidence(ctx, reg, subject, "brak wpisu")],
                    0.75,
                    {"partial_snapshot": _partial(ctx, reg)},
                )
            )
        elif "nie wykonuje" in entry.get("status", "").lower():
            checks.append(make_check(ctx, reg, subject, "inactive", entry["status"]))
            findings.append(
                PluginFinding(
                    "LEGAL_ADVISER_INACTIVE",
                    "info",
                    f"Radca prawny powołany w materiale ({subject}) ma w rejestrze KIRP status „{entry['status']}”."
                    + OUTSIDE_UKNF,
                    [registry_evidence(ctx, reg, subject, entry["status"])],
                    0.9,
                )
            )
        else:
            checks.append(make_check(ctx, reg, subject, "listed", entry.get("status", "Wykonuje zawód")))
            findings.append(
                PluginFinding(
                    "LEGAL_ADVISER_ACTIVE",
                    "info",
                    f"Radca prawny powołany w materiale ({subject}) figuruje w rejestrze KIRP ze statusem "
                    f"„{entry.get('status', 'Wykonuje zawód')}”.",
                    [registry_evidence(ctx, reg, subject, "figuruje")],
                    0.9,
                )
            )

    if declared and declared.tax_adviser_no:
        reg = "kidp_tax_advisers"
        entry = ctx.registries.lookup_number(reg, declared.tax_adviser_no)
        subject = f"doradca podatkowy nr {declared.tax_adviser_no}"
        if entry is None and _sample_miss(ctx, reg):
            checks.append(make_check(ctx, reg, subject, "not_checked", SAMPLE_DETAIL))
        elif entry is None:
            checks.append(make_check(ctx, reg, subject, "not_listed", "Brak wpisu w rejestrze doradców podatkowych"))
            findings.append(
                PluginFinding(
                    "TAX_ADVISER_NOT_FOUND",
                    "info",
                    f"Deklarowany {subject} nie figuruje w rejestrze KIDP." + OUTSIDE_UKNF,
                    [registry_evidence(ctx, reg, subject, "brak wpisu")],
                    0.7,
                    {"partial_snapshot": _partial(ctx, reg)},
                )
            )
        elif entry.get("status", "listed").lower() not in {"listed", "czynny", "aktywny"}:
            checks.append(make_check(ctx, reg, subject, "inactive", entry["status"]))
            findings.append(
                PluginFinding(
                    "TAX_ADVISER_INACTIVE",
                    "info",
                    f"Deklarowany {subject} ma w rejestrze KIDP status „{entry['status']}”." + OUTSIDE_UKNF,
                    [registry_evidence(ctx, reg, subject, entry["status"])],
                    0.85,
                )
            )
        else:
            checks.append(make_check(ctx, reg, subject, "listed", f"Dopasowano wpis: {entry['name']}"))
    return checks, findings
