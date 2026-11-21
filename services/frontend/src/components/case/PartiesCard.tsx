import { BadgeCheck, Building2, CircleAlert, CircleHelp, Megaphone, UserRound, type LucideIcon } from "lucide-react";
import type { Entities, Party, RegistryCheck } from "../../types/incident";
import { REGISTRY_STATUS_LABEL } from "../../domain/labels";
import { Badge, type Tone } from "../ui/Badge";

const KIND_LABEL: Record<Party["kind"], string> = {
  investment_firm: "Firma inwestycyjna", advertiser: "Reklamujący", influencer: "Influencer", pr_agency: "Agencja PR",
  advisor: "Doradca", lawyer: "Prawnik", company: "Spółka", person: "Osoba",
};

const STATUS_TONE: Record<RegistryCheck["status"], Tone> = {
  listed: "green", not_listed: "neutral", warning_listed: "red", inactive: "orange", not_checked: "neutral",
};

function iconFor(kind: Party["kind"]): LucideIcon {
  if (kind === "influencer" || kind === "advertiser") return Megaphone;
  if (kind === "person" || kind === "advisor" || kind === "lawyer") return UserRound;
  return Building2;
}

interface Verification {
  key: string;
  tone: Tone;
  icon: LucideIcon;
  text: string;
  title: string;
}

/** Only the register results that change how the analyst reads this party; the full list lives in the matrix tab. */
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
    if (c.status === "listed") out.push({ ...base, tone: STATUS_TONE.listed, icon: BadgeCheck, text: `${REGISTRY_STATUS_LABEL.listed}: ${c.label}` });
    else if (c.status === "warning_listed") out.push({ ...base, tone: "red", icon: CircleAlert, text: "Na liście ostrzeżeń publicznych KNF" });
    else if (c.status === "inactive") out.push({ ...base, tone: "orange", icon: CircleAlert, text: `${REGISTRY_STATUS_LABEL.inactive}: ${c.label}` });
    else if (c.status === "not_listed" && c.registry === "knf_public_warnings") out.push({ ...base, tone: "neutral", icon: CircleHelp, text: "Brak ostrzeżeń KNF" });
    else if (c.status === "not_listed" && c.registry === "uknf_cooperation_notice") out.push({ ...base, tone: "orange", icon: CircleAlert, text: "Brak zgłoszenia współpracy do UKNF" });
    else if (c.status === "not_listed" && c.registry === "knf_investment_firms" && !licensed) out.push({ ...base, tone: "orange", icon: CircleAlert, text: "Poza rejestrem firm inwestycyjnych" });
  }
  return out;
}

function PartyRow({ role, party, checks }: { role: string; party: Party; checks: RegistryCheck[] }) {
  const Icon = iconFor(party.kind);
  const badges = verifications(party, checks);
  return (
    <li className="party">
      <span className="party__avatar" aria-hidden="true"><Icon /></span>
      <div className="party__body">
        <p className="party__role">{role}</p>
        <p className="party__name">{party.name}</p>
        <p className="party__meta">
          {party.handle && <span>{party.handle}</span>}
          {party.krs && <span>KRS {party.krs}</span>}
          {party.nip && <span>NIP {party.nip}</span>}
          {party.country && <span>Kraj: {party.country}</span>}
        </p>
        {badges.length > 0 && (
          <div className="party__badges">
            {badges.map((v) => (
              <Badge key={v.key} tone={v.tone} title={v.title}><v.icon aria-hidden="true" />{v.text}</Badge>
            ))}
          </div>
        )}
      </div>
    </li>
  );
}

/** Who is involved, with register verification badges next to each name. */
export function PartiesCard({ entities, registryChecks }: { entities: Entities; registryChecks: RegistryCheck[] }) {
  const rows: { role: string; party: Party }[] = [];
  if (entities.investment_firm) rows.push({ role: "Firma inwestycyjna (reklamowana)", party: entities.investment_firm });
  if (entities.advertiser && entities.advertiser.name !== entities.investment_firm?.name) rows.push({ role: "Publikujący materiał", party: entities.advertiser });
  for (const p of entities.others) rows.push({ role: KIND_LABEL[p.kind] ?? "Podmiot powiązany", party: p });
  if (rows.length === 0) return <p className="muted">Silnik nie ustalił podmiotów w tym materiale.</p>;
  return (
    <ul>
      {rows.map((r) => <PartyRow key={`${r.role}-${r.party.name}`} role={r.role} party={r.party} checks={registryChecks} />)}
    </ul>
  );
}
