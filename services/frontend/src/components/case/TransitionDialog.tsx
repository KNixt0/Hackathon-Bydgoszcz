import * as Dialog from "@radix-ui/react-dialog";
import { CircleAlert, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { ESCALATION_PATH_LABEL, ESCALATION_PATHS, RESOLUTION_ACTION_LABEL } from "../../domain/labels";
import type { WorkflowAction } from "../../domain/workflow";
import type { EscalationPath, ResolutionAction } from "../../types/incident";
import { Button } from "../ui/Button";

export interface TransitionInput {
  reason?: string;
  escalation_path?: EscalationPath;
  resolution_action?: ResolutionAction;
}

interface Props {
  action: WorkflowAction | null;
  defaultPath: EscalationPath;
  /** Module 3 cases offer the warning-list request first. */
  defaultResolution: ResolutionAction;
  onCancel: () => void;
  /** Resolves to null on success or an error message to show in the dialog. */
  onConfirm: (input: TransitionInput) => Promise<string | null>;
}

const RESOLUTIONS: ResolutionAction[] = ["evidence_report", "warning_list_request", "enhanced_monitoring"];

/** Asks for what the step needs (reason, escalation path, resolution action) before it is sent. */
export function TransitionDialog({ action, defaultPath, defaultResolution, onCancel, onConfirm }: Props) {
  const spec = action?.dialog;
  return (
    <Dialog.Root open={Boolean(spec)} onOpenChange={(open) => { if (!open) onCancel(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        {action && spec && (
          <Dialog.Content
            className="dialog" data-testid="transition-dialog"
            // start in the reason field (Radix would focus the first control, the path select)
            onOpenAutoFocus={(e) => {
              const reason = document.getElementById("transition-reason");
              if (reason) {
                e.preventDefault();
                reason.focus();
              }
            }}
          >
            <DialogForm key={action.id} action={action} defaultPath={defaultPath} defaultResolution={defaultResolution} onConfirm={onConfirm} />
          </Dialog.Content>
        )}
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function DialogForm({ action, defaultPath, defaultResolution, onConfirm }: Omit<Props, "action" | "onCancel"> & { action: WorkflowAction }) {
  const spec = action.dialog;
  const [reason, setReason] = useState("");
  const [path, setPath] = useState<EscalationPath>(defaultPath);
  const [resolution, setResolution] = useState<ResolutionAction>(defaultResolution);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (!spec) return null;
  const required = spec.reason === "required";

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (required && !reason.trim()) {
      setError("Uzasadnienie jest wymagane: zostanie zapisane w historii decyzji.");
      return;
    }
    setBusy(true);
    setError(null);
    const failure = await onConfirm({
      ...(reason.trim() ? { reason: reason.trim() } : {}),
      ...(spec.escalationPath ? { escalation_path: path } : {}),
      ...(spec.resolutionAction ? { resolution_action: resolution } : {}),
    });
    setBusy(false);
    if (failure) setError(failure);
  };

  return (
    <form onSubmit={submit} noValidate>
      <div className="dialog__head">
        <div>
          <Dialog.Title className="dialog__title">{spec.title}</Dialog.Title>
          <Dialog.Description className="dialog__desc">{spec.description}</Dialog.Description>
        </div>
        <Dialog.Close asChild>
          <Button variant="ghost" iconOnly aria-label="Zamknij"><X aria-hidden="true" /></Button>
        </Dialog.Close>
      </div>
      <div className="dialog__body">
        {spec.escalationPath && (
          <label className="field">
            <span className="field__label">Ścieżka eskalacji</span>
            <select className="select" value={path} onChange={(e) => setPath(e.target.value as EscalationPath)}>
              {ESCALATION_PATHS.map((p) => <option key={p} value={p}>{ESCALATION_PATH_LABEL[p]}</option>)}
            </select>
          </label>
        )}
        {spec.resolutionAction && (
          <label className="field">
            <span className="field__label">Działanie końcowe</span>
            <select className="select" value={resolution} onChange={(e) => setResolution(e.target.value as ResolutionAction)}>
              {RESOLUTIONS.map((r) => <option key={r} value={r}>{RESOLUTION_ACTION_LABEL[r]}</option>)}
            </select>
          </label>
        )}
        <label className="field">
          <span className="field__label">Uzasadnienie{required ? " (wymagane)" : " (opcjonalnie)"}</span>
          <textarea
            id="transition-reason" className="input textarea" rows={4} maxLength={2000} value={reason}
            aria-required={required || undefined} aria-invalid={error ? true : undefined} aria-describedby={error ? "transition-error" : undefined}
            onChange={(e) => { setReason(e.target.value); if (error) setError(null); }}
          />
        </label>
        {error && <p className="form-error" id="transition-error" role="alert"><CircleAlert aria-hidden="true" />{error}</p>}
      </div>
      <div className="dialog__foot">
        <Dialog.Close asChild><Button>Anuluj</Button></Dialog.Close>
        <Button type="submit" variant="primary" disabled={busy}>{busy ? "Zapisywanie…" : spec.confirm}</Button>
      </div>
    </form>
  );
}
