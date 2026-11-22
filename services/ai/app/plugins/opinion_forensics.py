"""Opinion forensics: is the wave of comments organic or manufactured?

Works on `context.comments`: opinion timeline, spike detection, account-age buckets, share
of accounts younger than 14 days, origin distribution, handle-pattern families
(e.g. "krypto_zysk" + digits) and near-duplicate texts (embedding similarity).
"""

from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict

from ..context import AnalysisContext, parse_date
from ..preprocess import cosine
from ..schemas import (
    Accounts,
    AgeBucket,
    Anomaly,
    Forensics,
    NamePattern,
    Origin,
    SampleAccount,
    TimelinePoint,
)
from .base import Plugin, PluginFinding, PluginResult

BUCKETS = ["<14d", "14–90d", "3–12m", "1–3y", ">3y"]
MIN_COMMENTS = 5  # below this no statistical statement is made
FRESH_SHARE_MEDIUM, FRESH_SHARE_HIGH = 0.3, 0.6
PATTERN_SHARE_MEDIUM, PATTERN_SHARE_HIGH = 0.25, 0.5
FOREIGN_SHARE = 0.5
LANG_COUNTRY = {"pl": "PL", "en": "", "de": "DE"}


def _bucket(age_days: float) -> str:
    if age_days < 14:
        return "<14d"
    if age_days < 90:
        return "14–90d"
    if age_days < 365:
        return "3–12m"
    if age_days < 3 * 365:
        return "1–3y"
    return ">3y"


def handle_stem(handle: str) -> tuple[str, bool]:
    """("krypto_zysk", True) for "@Krypto_Zysk4821": stem and whether digits were stripped."""
    h = handle.lower().lstrip("@")
    stem = re.sub(r"[\d_.\-]+$", "", h)
    return stem, stem != h and bool(re.search(r"\d", h[len(stem) :]))


class OpinionForensicsPlugin(Plugin):
    id = "opinion_forensics"
    module = None
    agent = "forensics"
    description = (
        "Analiza opinii i komentarzy: oś czasu, skoki aktywności, wiek kont, udział kont młodszych "
        "niż 14 dni, pochodzenie, rodziny podobnych nazw kont, powtarzalne treści."
    )

    def applies(self, ctx: AnalysisContext) -> bool:
        return bool(ctx.context.comments)

    def run(self, ctx: AnalysisContext) -> PluginResult:
        comments = ctx.context.comments
        total = len(comments)
        rows = []
        for c in comments:
            posted = parse_date(c.posted_at) or ctx.now
            created = parse_date(c.account_created)
            age = (posted - created).total_seconds() / 86400 if created else None
            rows.append((c, posted, age))

        # timeline
        per_day: dict[str, list] = defaultdict(list)
        for c, posted, age in rows:
            per_day[posted.date().isoformat()].append((c, age))
        timeline = []
        for day in sorted(per_day):
            items = per_day[day]
            ratings = [c.rating for c, _ in items if c.rating is not None]
            ages = [a for _, a in items if a is not None]
            timeline.append(
                TimelinePoint(
                    date=day,
                    count=len(items),
                    avg_rating=round(sum(ratings) / len(ratings), 2) if ratings else 0.0,
                    new_account_share=round(sum(a < 14 for a in ages) / len(ages), 3) if ages else 0.0,
                )
            )

        # accounts
        ages = [a for _, _, a in rows if a is not None]
        bucket_counts = Counter(_bucket(a) for a in ages)
        fresh_share = round(bucket_counts["<14d"] / len(ages), 3) if ages else 0.0
        origin_counts = Counter((c.country or "??").upper() for c, _, _ in rows)
        families: dict[str, list[str]] = defaultdict(list)
        for c, _, _ in rows:
            stem, numbered = handle_stem(c.handle)
            if numbered and len(stem) >= 3:
                families[stem].append(c.handle)
        patterns = [
            NamePattern(pattern=f"{stem}<cyfry>", count=len(handles), examples=sorted(handles)[:4])
            for stem, handles in sorted(families.items(), key=lambda kv: (-len(kv[1]), kv[0]))
            if len(handles) >= 3
        ]
        clustered = sum(p.count for p in patterns)

        # near-duplicate texts
        vectors = [ctx.embedder.embed(c.text) for c, _, _ in rows if len(c.text) >= 15][:200]
        dup = set()
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                if cosine(vectors[i], vectors[j]) >= ctx.embedder.duplicate_threshold:
                    dup.update((i, j))
        duplicate_share = len(dup) / len(vectors) if vectors else 0.0

        anomalies: list[Anomaly] = []
        findings: list[PluginFinding] = []
        enough = total >= MIN_COMMENTS

        counts = [p.count for p in timeline]
        if enough and len(counts) >= 3:
            median = statistics.median(counts)
            mean, sd = statistics.fmean(counts), statistics.pstdev(counts)
            for point in timeline:
                if point.count >= max(5, 3 * median, mean + 2 * sd) and point.count > median:
                    sev = "high" if point.new_account_share >= FRESH_SHARE_HIGH else "medium"
                    text = (
                        f"Skok liczby opinii {point.date}: {point.count} wobec mediany {median:.0f} dziennie; "
                        f"{point.new_account_share:.0%} z nich pochodzi z kont młodszych niż 14 dni."
                    )
                    anomalies.append(Anomaly(type="opinion_spike", severity=sev, description=text))
                    findings.append(
                        PluginFinding(
                            "OPINION_SPIKE",
                            sev,
                            text,
                            [],
                            0.8,
                            {"date": point.date, "new_account_share": point.new_account_share, "count": point.count},
                        )
                    )
                    break
        if enough and fresh_share >= FRESH_SHARE_MEDIUM:
            sev = "high" if fresh_share >= FRESH_SHARE_HIGH else "medium"
            text = (
                f"{fresh_share:.0%} komentarzy ({bucket_counts['<14d']} z {len(ages)}) pochodzi z kont "
                "założonych mniej niż 14 dni przed publikacją opinii."
            )
            if duplicate_share >= 0.3:
                text += f" {duplicate_share:.0%} treści to niemal identyczne powtórzenia."
            anomalies.append(Anomaly(type="fresh_account_cluster", severity=sev, description=text))
            findings.append(
                PluginFinding(
                    "FRESH_ACCOUNT_CLUSTER",
                    sev,
                    text,
                    [],
                    0.85,
                    {"share": fresh_share, "duplicate_share": duplicate_share},
                )
            )
        if enough and patterns and clustered / total >= PATTERN_SHARE_MEDIUM:
            sev = "high" if clustered / total >= PATTERN_SHARE_HIGH else "medium"
            names = ", ".join(f"{p.pattern} ({p.count})" for p in patterns[:3])
            text = f"{clustered} z {total} kont ma nazwy z tych samych rodzin „rdzeń + cyfry”: {names}."
            anomalies.append(Anomaly(type="name_pattern_cluster", severity=sev, description=text))
            findings.append(PluginFinding("NAME_PATTERN_CLUSTER", sev, text, [], 0.8, {"share": clustered / total}))
        # WatchIt: no "accounts from abroad" marker (origin inside / outside the EU is not shown).
        if findings:
            # attach the most telling accounts as evidence
            suspects = sorted((r for r in rows if r[2] is not None), key=lambda r: r[2])[:3]
            ev = [
                ctx.evidence.account(
                    c.handle,
                    f"Konto {c.handle}, założone {c.account_created[:10]}, kraj {c.country or '??'}: „{c.text[:120]}”",
                )
                for c, _, _ in suspects
            ]
            for f in findings:
                f.evidence_ids = ev
        elif enough:
            old_share = (bucket_counts["1–3y"] + bucket_counts[">3y"]) / len(ages) if ages else 0.0
            findings.append(
                PluginFinding(
                    "ORGANIC_OPINIONS",
                    "info",
                    f"Komentarze wyglądają na organiczne: {old_share:.0%} kont ma ponad rok, brak skoków aktywności i "
                    "rodzin podobnych nazw.",
                    [],
                    0.8,
                    {"old_share": old_share},
                )
            )

        ordered = sorted(rows, key=lambda r: (r[2] if r[2] is not None else 1e9, r[0].handle))
        forensics = Forensics(
            opinion_timeline=timeline,
            accounts=Accounts(
                total=total,
                share_younger_14d=fresh_share,
                age_buckets=[AgeBucket(bucket=b, count=bucket_counts.get(b, 0)) for b in BUCKETS],
                origins=[Origin(country=k, count=v) for k, v in origin_counts.most_common()],
                name_patterns=patterns,
            ),
            anomalies=anomalies,
            sample_accounts=[
                SampleAccount(
                    handle=c.handle, created_at=c.account_created, country=c.country or "??", text=c.text[:200]
                )
                for c, _, _ in ordered[:8]
            ],
        )
        return self.result(findings=findings, forensics=forensics)
