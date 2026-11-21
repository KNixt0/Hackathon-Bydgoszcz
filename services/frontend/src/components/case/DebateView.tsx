import { formatPercent } from "../../domain/format";
import { CLAIM_VERDICT_LABEL } from "../../domain/labels";
import type { Claim, Debate } from "../../types/incident";
import { Badge } from "../ui/Badge";
import { EvidenceChips } from "./EvidenceChips";

function ClaimCard({ claim }: { claim: Claim }) {
  const tone = claim.verdict === "upheld" ? "green" : claim.verdict === "weakened" ? "orange" : "neutral";
  return (
    <li className={`claim claim--${claim.stance}${claim.verdict === "rejected" ? " claim--rejected" : ""}`}>
      <div className="claim__top">
        <Badge tone={tone}>{CLAIM_VERDICT_LABEL[claim.verdict]}</Badge>
        <span className="muted">pewność <span className="num">{formatPercent(claim.confidence)}</span></span>
      </div>
      <p>{claim.text}</p>
      {claim.critique && <p className="claim__critique"><strong>Krytyka:</strong> {claim.critique}</p>}
      <EvidenceChips ids={claim.evidence_ids} />
    </li>
  );
}

export function DebateView({ debate }: { debate: Debate }) {
  const byId = new Map(debate.claims.map((c) => [c.id, c]));
  const forClaims = debate.claims.filter((c) => c.stance === "for");
  const againstClaims = debate.claims.filter((c) => c.stance === "against");
  const kept = (ids: string[]) => ids.filter((id) => byId.has(id)).length;
  return (
    <div className="stack">
      {debate.rounds.length > 0 && (
        <ol className="rounds" aria-label="Przebieg debaty">
          {debate.rounds.map((r, i) => (
            <li key={i} className="round">
              <span className="round__n">Runda {r.round}</span>
              <strong>{r.agent}</strong> <span className="muted">· {r.role}</span>
              <p>{r.summary}</p>
            </li>
          ))}
        </ol>
      )}
      <div className="grid-2">
        <section aria-label="Argumenty za naruszeniem">
          <h3 className="subhead subhead--red">Za naruszeniem ({kept(debate.arguments_for)} utrzymanych z {forClaims.length})</h3>
          {forClaims.length ? <ul className="claims">{forClaims.map((c) => <ClaimCard key={c.id} claim={c} />)}</ul> : <p className="muted">Brak argumentów.</p>}
        </section>
        <section aria-label="Argumenty przeciw naruszeniu">
          <h3 className="subhead subhead--green">Okoliczności łagodzące ({kept(debate.arguments_against)} utrzymanych z {againstClaims.length})</h3>
          {againstClaims.length ? <ul className="claims">{againstClaims.map((c) => <ClaimCard key={c.id} claim={c} />)}</ul> : <p className="muted">Brak argumentów.</p>}
        </section>
      </div>
      {debate.arbiter_rationale && (
        <section className="arbiter" aria-label="Uzasadnienie rozstrzygnięcia">
          <h3 className="subhead">Rozstrzygnięcie arbitra</h3>
          <p>{debate.arbiter_rationale}</p>
        </section>
      )}
    </div>
  );
}
