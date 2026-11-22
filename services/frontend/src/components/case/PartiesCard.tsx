import { CircleCheck, CircleMinus, TriangleAlert, type LucideIcon } from "lucide-react";
import type { Entities, Party, RegistryCheck } from "../../types/incident";
import { REGISTRY_STATUS_LABEL } from "../../domain/labels";
import { Mark, type MarkTone } from "../ui/Mark";

const KIND_LABEL: Record<Party["kind"], string> = {
  investment_firm: "Firma inwestycyjna", advertiser: "Reklamujący", influencer: "Twórca internetowy", pr_agency: "Agencja PR",
  advisor: "Doradca", lawyer: "Prawnik", company: "Spółka", person: "Osoba",
};

interface Verification {
  key: string;
  tone: MarkTone;
  icon: LucideIcon;
  text: string;
  title: string;
}

/** Only the register results that change how the analyst reads this party; the full list is the register table. */
export function verifications(party: Party, checks: RegistryCheck[]): Verification[] {
  const name = party.name.toLowerCase();
  // Registers are searched by name or a shortened name, so match in both directions.
  const mine = checks.filter((c) => {
    const subject = c.subject.toLowerCase().trim();
    return subject.includes(name) || (subject.length >= 4 && name.includes(subject));
  });
  const licensed = mine.some((c) => c.status === "listed");
  const out: Verification[] = [];
  for (const c of mine) {
    const base = { key: `${c.registry}-${c.subject}`, title: `${c.label}: ${c.detail}` };
    if (c.status === "listed") out.push({ ...base, tone: "grn", icon: CircleCheck, text: `${REGISTRY_STATUS_LABEL.listed}: ${c.label}` });
    else if (c.status === "warning_listed") out.push({ ...base, tone: "red", icon: TriangleAlert, text: "Na liście ostrzeżeń publicznych KNF" });
    else if (c.status === "inactive") out.push({ ...base, tone: "amb", icon: TriangleAlert, text: `${REGISTRY_STATUS_LABEL.inactive}: ${c.label}` });
    else if (c.status === "not_listed" && c.registry === "knf_public_warnings") out.push({ ...base, tone: "ink", icon: CircleMinus, text: "Brak ostrzeżeń KNF" });
    else if (c.status === "not_listed" && c.registry === "uknf_cooperation_notice") out.push({ ...base, tone: "amb", icon: CircleMinus, text: "Brak zgłoszenia współpracy do UKNF" });
    else if (c.status === "not_listed" && c.registry === "knf_investment_firms" && !licensed) out.push({ ...base, tone: "amb", icon: CircleMinus, text: "Poza rejestrem firm inwestycyjnych" });
  }
  return out;
}

function PartyRow({ role, party, checks }: { role: string; party: Party; checks: RegistryCheck[] }) {
  const marks = verifications(party, checks);
  const meta = [party.handle, party.krs && `KRS ${party.krs}`, party.nip && `NIP ${party.nip}`, party.country && `kraj: ${party.country}`].filter(Boolean);
  return (
    <li className="party">
      <span className="party__role">{role}</span>
      <span className="party__name">{party.name}</span>
      {meta.length > 0 && <span className="party__meta">{meta.join(", ")}</span>}
      {marks.length > 0 && (
        <span className="party__marks">
          {marks.map((v) => <Mark key={v.key} tone={v.tone} icon={v.icon} title={v.title}>{v.text}</Mark>)}
        </span>
      )}
    </li>
  );
}

/** Who is involved, with the register results that matter next to each name. */
export function PartiesCard({ entities, registryChecks, inScope = true }: { entities: Entities; registryChecks: RegistryCheck[]; inScope?: boolean }) {
  const rows: { role: string; party: Party }[] = [];
  // outside UKNF's remit the advertised entity is not treated as an investment firm (contract v4 scope)
  if (entities.investment_firm) rows.push({ role: inScope ? "Firma inwestycyjna (reklamowana)" : "Podmiot reklamowany", party: entities.investment_firm });
  if (entities.advertiser && entities.advertiser.name !== entities.investment_firm?.name) rows.push({ role: "Publikujący materiał", party: entities.advertiser });
  for (const p of entities.others) rows.push({ role: KIND_LABEL[p.kind] ?? "Podmiot powiązany", party: p });
  if (rows.length === 0) return <p className="muted">Silnik nie ustalił podmiotów w tym materiale.</p>;
  return (
    <ul className="parties">
      {rows.map((r) => <PartyRow key={`${r.role}-${r.party.name}`} role={r.role} party={r.party} checks={registryChecks} />)}
    </ul>
  );
}
