import { Gavel, MessagesSquare, ShieldCheck, ShieldAlert } from "lucide-react";
import { formatPercent } from "../../domain/format";
import { CLAIM_VERDICT_LABEL } from "../../domain/labels";
import type { Claim, Debate, DebateRound } from "../../types/incident";
import { Badge, type Tone } from "../ui/Badge";
import { EmptyState } from "../ui/States";
import { EvidenceChips } from "./EvidenceChips";

const VERDICT_TONE: Record<Claim["verdict"], Tone> = { upheld: "accent", weakened: "orange", rejected: "neutral" };

export function ClaimCard({ claim, counted }: { claim: Claim; counted: boolean }) {
  return (
    <li className={`claim claim--${claim.verdict}`} data-testid="claim">
      <div className="claim__top">
        <Badge tone={VERDICT_TONE[claim.verdict] ?? "neutral"}>Krytyk: {CLAIM_VERDICT_LABEL[claim.verdict] ?? claim.verdict}</Badge>
        <span className="conf" title="Pewność argumentu po krytyce">
          <span className="conf__bar" aria-hidden="true"><i style={{ width: `${Math.round(claim.confidence * 100)}%` }} /></span>
          <span className="num">pewność {formatPercent(claim.confidence)}</span>
        </span>
      </div>
      <p className="claim__text">{claim.text}</p>
      {claim.critique && <p className="claim__critique"><b>Krytyk:</b> {claim.critique}</p>}
      <EvidenceChips ids={claim.evidence_ids} />
      {!counted && <p className="muted" style={{ fontSize: "var(--fs-sm)" }}>Nieuwzględniony w ocenie końcowej.</p>}
    </li>
  );
}

function Column({ stance, claims, kept }: { stance: Claim["stance"]; claims: Claim[]; kept: Set<string> }) {
  const isFor = stance === "for";
  const Icon = isFor ? ShieldAlert : ShieldCheck;
  return (
    <div className="debate__col" data-testid={`debate-${stance}`}>
      <div className="debate__head">
        <h3 className={`debate__title debate__title--${stance}`}>
          <Icon aria-hidden="true" />{isFor ? "Za naruszeniem" : "Przeciw: okoliczności łagodzące"}
        </h3>
        <span className="muted num" style={{ fontSize: "var(--fs-sm)" }}>{claims.filter((c) => kept.has(c.id)).length} z {claims.length} utrzymanych</span>
      </div>
      {claims.length === 0 ? (
        <p className="muted">{isFor ? "Agenci nie sformułowali argumentów za naruszeniem." : "Agenci nie znaleźli okoliczności łagodzących."}</p>
      ) : (
        <ul style={{ display: "grid", gap: 8 }}>
          {claims.map((c) => <ClaimCard key={c.id} claim={c} counted={kept.has(c.id)} />)}
        </ul>
      )}
    </div>
  );
}

function groupRounds(rounds: DebateRound[]): [number, DebateRound[]][] {
  const map = new Map<number, DebateRound[]>();
  for (const r of rounds) map.set(r.round, [...(map.get(r.round) ?? []), r]);
  return [...map.entries()].sort((a, b) => a[0] - b[0]);
}

/** Block 3: the agents' debate. Incriminating and mitigating claims side by side, the critic's verdict on each, then the arbiter. */
export function DebateBlock({ debate }: { debate: Debate }) {
  const empty = debate.claims.length === 0 && debate.rounds.length === 0 && !debate.arbiter_rationale;
  const kept = new Set([...debate.arguments_for, ...debate.arguments_against]);
  const byConfidence = (a: Claim, b: Claim) => b.confidence - a.confidence;
  const forClaims = debate.claims.filter((c) => c.stance === "for").sort(byConfidence);
  const againstClaims = debate.claims.filter((c) => c.stance === "against").sort(byConfidence);
  return (
    <section className="panel block" id="argumenty" aria-labelledby="argumenty-h">
      <header className="panel__head">
        <h2 className="panel__title" id="argumenty-h"><span className="block__n">3</span>Argumenty „za” i „przeciw”</h2>
      </header>
      {empty ? (
        <EmptyState icon={<MessagesSquare />} title="Brak debaty agentów" text="Dla tej sprawy silnik nie przeprowadził debaty. Ocena opiera się wyłącznie na regułach i rejestrach." />
      ) : (
        <>
          {debate.arbiter_rationale && (
            <div className="arbiter">
              <span className="arbiter__icon" aria-hidden="true"><Gavel /></span>
              <div>
                <h3 className="arbiter__title">Uzasadnienie arbitra</h3>
                <p className="arbiter__text">{debate.arbiter_rationale}</p>
              </div>
            </div>
          )}
          <div className="debate">
            <Column stance="for" claims={forClaims} kept={kept} />
            <Column stance="against" claims={againstClaims} kept={kept} />
          </div>
          {debate.rounds.length > 0 && (
            <div className="rounds">
              <h3 className="subhead">Przebieg debaty</h3>
              <ol className="rounds__grid">
                {groupRounds(debate.rounds).map(([n, entries]) => (
                  <li key={n} className="round">
                    <span className="round__n">Runda {n} z 3</span>
                    {entries.map((r, i) => (
                      <div key={`${r.agent}-${i}`} className="round__entry">
                        <p className="round__agent">{r.agent}</p>
                        <p className="round__role">{r.role}</p>
                        <p className="round__summary">{r.summary}</p>
                      </div>
                    ))}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </>
      )}
    </section>
  );
}
