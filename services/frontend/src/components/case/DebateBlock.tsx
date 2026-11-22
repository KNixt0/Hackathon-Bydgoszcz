import { ShieldAlert, ShieldCheck } from "lucide-react";
import { formatPercent } from "../../domain/format";
import { CLAIM_VERDICT_LABEL } from "../../domain/labels";
import type { Claim, Debate, DebateRound } from "../../types/incident";
import { EmptyState } from "../ui/States";
import { EvidenceChips } from "./EvidenceChips";

export function ClaimCard({ claim, counted }: { claim: Claim; counted: boolean }) {
  return (
    <li className={`claim claim--${claim.verdict}`} data-testid="claim">
      <p className="claim__text">{claim.text}</p>
      <p className="claim__meta">
        <span className={`claim__verdict claim__verdict--${claim.verdict}`}>Krytyk: {CLAIM_VERDICT_LABEL[claim.verdict] ?? claim.verdict}</span>
        <span className="num" title="Pewność argumentu po krytyce">pewność {formatPercent(claim.confidence)}</span>
        {!counted && <span>nieuwzględniony w ocenie końcowej</span>}
      </p>
      {claim.critique && <p className="claim__critique"><b>Uwaga krytyka:</b> {claim.critique}</p>}
      <EvidenceChips ids={claim.evidence_ids} />
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
        <span className="debate__count num">{claims.filter((c) => kept.has(c.id)).length} z {claims.length} utrzymanych</span>
      </div>
      {claims.length === 0 ? (
        <p className="muted">{isFor ? "Analiza nie wykazała argumentów za naruszeniem." : "Analiza nie wykazała okoliczności łagodzących."}</p>
      ) : (
        <ul className="claims">
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

/** The agents' debate: incriminating and mitigating claims side by side, the critic's verdict on each, then the arbiter. */
export function DebateBlock({ debate }: { debate: Debate }) {
  const empty = debate.claims.length === 0 && debate.rounds.length === 0 && !debate.arbiter_rationale;
  const kept = new Set([...debate.arguments_for, ...debate.arguments_against]);
  const byConfidence = (a: Claim, b: Claim) => b.confidence - a.confidence;
  const forClaims = debate.claims.filter((c) => c.stance === "for").sort(byConfidence);
  const againstClaims = debate.claims.filter((c) => c.stance === "against").sort(byConfidence);
  return (
    <div className="recommendation-arguments">
      {empty ? (
        <EmptyState compact title="Brak dodatkowych argumentów" text="Dla tej sprawy silnik nie przygotował argumentów. Ocena opiera się wyłącznie na regułach i rejestrach." />
      ) : (
        <>
          {debate.arbiter_rationale && (
            <div className="arbiter">
              <h3 className="subhead">Uzasadnienie</h3>
              <p className="arbiter__text">{debate.arbiter_rationale}</p>
            </div>
          )}
          <div className="debate">
            <Column stance="for" claims={forClaims} kept={kept} />
            <Column stance="against" claims={againstClaims} kept={kept} />
          </div>
          {debate.rounds.length > 0 && (
            <details className="rounds disclosure">
              <summary>Tok rozumowania</summary>
              <ol className="rounds__grid">
                {groupRounds(debate.rounds).map(([n, entries]) => (
                  <li key={n} className="round">
                    <span className="round__n">Etap {n} z 3</span>
                    {entries.map((r, i) => (
                      <div key={`${r.agent}-${i}`} className="round__entry">
                        <p className="round__agent">{r.agent} <span className="round__role">{r.role}</span></p>
                        <p className="round__summary">{r.summary}</p>
                      </div>
                    ))}
                  </li>
                ))}
              </ol>
            </details>
          )}
        </>
      )}
    </div>
  );
}
