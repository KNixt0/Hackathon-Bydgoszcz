import { CircleAlert } from "lucide-react";
import { useState } from "react";
import { CASE_LABEL_LABEL, ESCALATION_PATH_LABEL, RESOLUTION_ACTION_LABEL, STATUS_LABEL } from "../../domain/labels";
import { availableActions, CLOSED, DEFAULT_ESCALATION_PATH, type WorkflowAction } from "../../domain/workflow";
import type { TransitionRequest, User } from "../../types/api";
import type { CaseLabel, Incident } from "../../types/incident";
import { Button } from "../ui/Button";
import { TransitionDialog, type TransitionInput } from "./TransitionDialog";

const LABELS: CaseLabel[] = ["unlabeled", "true_positive", "false_positive"];

interface Props {
  incident: Incident;
  user: User;
  busy?: boolean;
  /** Each resolves to null on success or a Polish error message. */
  onTransition: (body: TransitionRequest) => Promise<string | null>;
  onAssign: () => Promise<string | null>;
  onLabel: (label: CaseLabel) => Promise<string | null>;
}

/** The case workflow: where the case is, who has it, and the moves this user may make from here. */
export function WorkflowPanel({ incident, user, busy = false, onTransition, onAssign, onLabel }: Props) {
  const [pending, setPending] = useState<WorkflowAction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { status, workflow } = incident;
  const actions = availableActions(status, user.role, workflow.assigned_to, user.email);
  const closed = CLOSED.includes(status);
  const defaultPath = workflow.escalation_path ?? DEFAULT_ESCALATION_PATH[incident.primary_module];

  const direct = async (call: () => Promise<string | null>) => {
    setError(null);
    setError(await call());
  };
  const run = (action: WorkflowAction) => {
    const to = action.to;
    if (action.id === "assign") void direct(onAssign);
    else if (action.dialog) {
      setError(null);
      setPending(action);
    } else if (to) void direct(() => onTransition({ to }));
  };

  const confirm = async (input: TransitionInput) => {
    if (!pending?.to) return null;
    const failure = await onTransition({ to: pending.to, ...input });
    if (!failure) setPending(null);
    return failure;
  };

  return (
    <section className="csec workflow" data-testid="workflow" aria-labelledby="workflow-h">
      <h2 className="section-title" id="workflow-h" tabIndex={-1}>Postępowanie</h2>
      <dl className="kv workflow__facts">
        <dt>Status</dt>
        <dd><b>{STATUS_LABEL[status] ?? status}</b></dd>
        <dt>Prowadzi</dt>
        <dd data-testid="assignee">
          {workflow.assigned_to ? (
            workflow.assigned_to === user.email ? `${workflow.assigned_to} (Ty)` : workflow.assigned_to
          ) : <span className="muted">nikt, sprawa nieprzypisana</span>}
        </dd>
        {workflow.escalation_path && (
          <><dt>Ścieżka eskalacji</dt><dd>{ESCALATION_PATH_LABEL[workflow.escalation_path] ?? workflow.escalation_path}</dd></>
        )}
        {closed && workflow.resolution_action && (
          <><dt>Działanie końcowe</dt><dd>{RESOLUTION_ACTION_LABEL[workflow.resolution_action] ?? workflow.resolution_action}</dd></>
        )}
        {closed && workflow.resolution_note && (
          <><dt>Uzasadnienie</dt><dd>{workflow.resolution_note}</dd></>
        )}
      </dl>

      {status === "escalation_requested" && user.role !== "SUPERVISOR" && (
        <p className="workflow__wait">Wniosek czeka na decyzję kierownika.</p>
      )}
      {actions.length > 0 && (
        <div className="workflow__actions" role="group" aria-label="Działania w sprawie">
          {actions.map((a) => (
            <Button key={a.id} variant={a.primary ? "primary" : "default"} disabled={busy} onClick={() => run(a)}>
              {a.label}
            </Button>
          ))}
        </div>
      )}

      {error && <p className="form-error" role="alert"><CircleAlert aria-hidden="true" />{error}</p>}

      <div className="workflow__row">
        <label className="field workflow__label">
          <span className="field__label">Ocena trafności alarmu</span>
          <select className="select" value={workflow.label} disabled={busy} onChange={(e) => { const next = e.target.value as CaseLabel; void direct(() => onLabel(next)); }}>
            {LABELS.map((l) => <option key={l} value={l}>{CASE_LABEL_LABEL[l]}</option>)}
          </select>
        </label>
      </div>

      <TransitionDialog
        action={pending}
        defaultPath={defaultPath}
        defaultResolution={
          incident.follow_up?.outcome === "removed" ? "content_removed"
            : incident.follow_up?.outcome === "corrected" ? "content_corrected" : "evidence_report"
        }
        onCancel={() => setPending(null)}
        onConfirm={confirm}
      />
    </section>
  );
}
