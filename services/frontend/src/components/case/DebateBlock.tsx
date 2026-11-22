import { ShieldAlert, ShieldCheck } from "lucide-react";
import { formatPercent } from "../../domain/format";
import { ACTION_LABEL, CLAIM_VERDICT_LABEL } from "../../domain/labels";
import type { Claim, Debate, DebateRound, Recommendation } from "../../types/incident";
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
          <Icon aria-hidden="true" />{isFor ? "Za naruszeniem" : "Okoliczności łagodzące"}
        </h3>
        <span className="debate__count num">{claims.filter((c) => kept.has(c.id)).length} z {claims.length} utrzymanych</span>
      </div>
      {claims.length === 0 ? (
        <p className="muted">{isFor ? "Silnik nie utrzymał żadnego argumentu za naruszeniem." : "Silnik nie znalazł okoliczności łagodzących."}</p>
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

/**
 * WatchIt "Rekomendacja AI" (in the place of the former "Argumenty za i przeciw"): what the engine
 * recommends and why, then the arguments it kept. The full reasoning (every claim with the critic's
 * verdict, round by round) is folded under "Tok rozumowania" and closed by default.
 */
export function DebateBlock({ debate, recommendation }: { debate: Debate; recommendation: Recommendation }) {
  const empty = debate.claims.length === 0 && debate.rounds.length === 0 && !debate.arbiter_rationale;
  const kept = new Set([...debate.arguments_for, ...debate.arguments_against]);
  const byConfidence = (a: Claim, b: Claim) => b.confidence - a.confidence;
  const forClaims = debate.claims.filter((c) => c.stance === "for").sort(byConfidence);
  const againstClaims = debate.claims.filter((c) => c.stance === "against").sort(byConfidence);
  const keptFor = forClaims.filter((c) => kept.has(c.id));
  const keptAgainst = againstClaims.filter((c) => kept.has(c.id));
  return (
    <section className="csec" id="rekomendacja" aria-labelledby="rekomendacja-h">
      <h2 className="section-title" id="rekomendacja-h">Rekomendacja AI</h2>
      <div className="callout" data-testid="recommendation">
        <p className="callout__title">{ACTION_LABEL[recommendation.action] ?? recommendation.action}</p>
        {recommendation.label && recommendation.label !== ACTION_LABEL[recommendation.action] && <p className="reco__label">{recommendation.label}</p>}
        <p><span className="reco__next">Następne działanie:</span> {recommendation.next_step}</p>
        <p className="muted">Wynik automatycznej analizy wspierającej. Decyzję podejmuje analityk.</p>
      </div>
      {empty ? (
        <EmptyState compact title="Brak toku rozumowania" text="Dla tej sprawy silnik nie przeprowadził analizy argumentów. Ocena opiera się wyłącznie na regułach i rejestrach." />
      ) : (
        <>
          {debate.arbiter_rationale && (
            <div className="arbiter">
              <h3 className="subhead">Uzasadnienie</h3>
              <p className="arbiter__text">{debate.arbiter_rationale}</p>
            </div>
          )}
          <div className="debate">
            <Column stance="for" claims={keptFor} kept={kept} />
            <Column stance="against" claims={keptAgainst} kept={kept} />
          </div>
          <details className="reasoning" data-testid="reasoning">
            <summary className="reasoning__summary"><h3 className="subhead">Tok rozumowania</h3></summary>
            <p className="muted">Wszystkie argumenty rozważone przez silnik, także odrzucone, z oceną krytyka i przebiegiem kolejnych rund.</p>
            <div className="debate">
              <Column stance="for" claims={forClaims} kept={kept} />
              <Column stance="against" claims={againstClaims} kept={kept} />
            </div>
            {debate.rounds.length > 0 && (
              <ol className="rounds__grid">
                {groupRounds(debate.rounds).map(([n, entries]) => (
                  <li key={n} className="round">
                    <span className="round__n">Runda {n} z 3</span>
                    {entries.map((r, i) => (
                      <div key={`${r.agent}-${i}`} className="round__entry">
                        <p className="round__agent">{r.agent} <span className="round__role">{r.role}</span></p>
                        <p className="round__summary">{r.summary}</p>
                      </div>
                    ))}
                  </li>
                ))}
              </ol>
            )}
          </details>
        </>
      )}
    </section>
  );
}
