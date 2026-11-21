import { STATUS_LABEL } from "../../domain/labels";
import type { Status } from "../../types/incident";
import { Button } from "../ui/Button";

const STEPS: { key: string; label: string; statuses: Status[] }[] = [
  { key: "new", label: "Nowe", statuses: ["new"] },
  { key: "in_review", label: "W analizie", statuses: ["in_review"] },
  { key: "escalated", label: "Eskalowane", statuses: ["escalated"] },
  { key: "closed", label: "Zamknięte", statuses: ["closed_violation", "closed_ok"] },
];

const NEXT: Record<Status, { status: Status; label: string; primary?: boolean }[]> = {
  new: [{ status: "in_review", label: "Podejmij analizę", primary: true }, { status: "closed_ok", label: "Zamknij: bez naruszeń" }],
  in_review: [
    { status: "escalated", label: "Eskaluj", primary: true },
    { status: "closed_violation", label: "Zamknij: naruszenie" },
    { status: "closed_ok", label: "Zamknij: bez naruszeń" },
  ],
  escalated: [{ status: "closed_violation", label: "Zamknij: naruszenie", primary: true }, { status: "closed_ok", label: "Zamknij: bez naruszeń" }],
  closed_violation: [{ status: "in_review", label: "Otwórz ponownie" }],
  closed_ok: [{ status: "in_review", label: "Otwórz ponownie" }],
};

interface Props {
  status: Status;
  onChange: (next: Status) => void;
  busy?: boolean;
}

/** Case pipeline: where the case is and the moves available from here. */
export function StatusStepper({ status, onChange, busy = false }: Props) {
  const current = STEPS.findIndex((s) => s.statuses.includes(status));
  return (
    <div>
      <ol className="stepper" aria-label="Etap sprawy">
        {STEPS.map((s, i) => (
          <li key={s.key} className={`step${i < current ? " step--done" : i === current ? " step--current" : ""}`} aria-current={i === current ? "step" : undefined}>
            <span className="step__bar" aria-hidden="true" />
            <span>{i === current ? STATUS_LABEL[status] : s.label}</span>
          </li>
        ))}
      </ol>
      <div className="stepper-actions" style={{ marginTop: 10 }}>
        {NEXT[status].map((n) => (
          <Button key={n.status} size="sm" variant={n.primary ? "primary" : "default"} disabled={busy} onClick={() => onChange(n.status)}>
            {n.label}
          </Button>
        ))}
      </div>
    </div>
  );
}
