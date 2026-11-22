import type { EscalationPath, ModuleId, Role, Status } from "../types/incident";

/** Mirrors the server's transition table (contract v3); the server enforces it, the UI only offers what is allowed. */
export const TRANSITIONS: Record<Status, Status[]> = {
  new: ["in_review"],
  in_review: ["escalation_requested", "awaiting_correction", "resolved", "false_positive"],
  escalation_requested: ["escalated", "in_review"],
  escalated: ["awaiting_correction", "resolved", "false_positive"],
  awaiting_correction: ["resolved", "in_review", "escalation_requested"],
  resolved: [],
  false_positive: [],
};

export const CLOSED: Status[] = ["resolved", "false_positive"];

export const DEFAULT_ESCALATION_PATH: Record<ModuleId, EscalationPath> = {
  1: "THIRD_PARTY_ADVERTISING",
  2: "RISK_INFORMATION",
  3: "UNLICENSED_ACTIVITY",
};

export type ActionId =
  | "assign" | "start" | "request_escalation" | "approve_escalation" | "reject_escalation"
  | "withdraw_escalation" | "close_violation" | "close_false_positive"
  | "record_intervention" | "close_after_follow_up" | "reopen_review";

export interface WorkflowAction {
  id: ActionId;
  label: string;
  /** Target status; absent for "assign". */
  to?: Status;
  primary?: boolean;
  /** What the confirmation dialog asks for; absent = no dialog. */
  dialog?: {
    title: string;
    description: string;
    reason: "required" | "optional";
    escalationPath?: boolean;
    resolutionAction?: boolean;
    /** Contract v4: ask for the follow-up deadline (awaiting_correction). */
    followUpDays?: boolean;
    confirm: string;
  };
}

const ACTIONS: Record<Exclude<ActionId, "assign">, WorkflowAction> = {
  start: { id: "start", label: "Rozpocznij weryfikację", to: "in_review", primary: true },
  request_escalation: {
    id: "request_escalation", label: "Wnioskuj o eskalację", to: "escalation_requested", primary: true,
    dialog: {
      title: "Wniosek o eskalację", description: "Kierownik zatwierdzi albo odrzuci wniosek. Wskaż ścieżkę, którą sprawa ma pójść dalej.",
      reason: "optional", escalationPath: true, confirm: "Wyślij wniosek",
    },
  },
  approve_escalation: {
    id: "approve_escalation", label: "Zatwierdź eskalację", to: "escalated", primary: true,
    dialog: {
      title: "Zatwierdzenie eskalacji", description: "Sprawa zostanie przekazana wskazaną ścieżką. Możesz zmienić ścieżkę zaproponowaną przez analityka.",
      reason: "optional", escalationPath: true, confirm: "Zatwierdź eskalację",
    },
  },
  reject_escalation: {
    id: "reject_escalation", label: "Odrzuć eskalację", to: "in_review",
    dialog: {
      title: "Odrzucenie eskalacji", description: "Sprawa wróci do weryfikacji. Napisz analitykowi, czego brakuje.",
      reason: "optional", confirm: "Odrzuć eskalację",
    },
  },
  withdraw_escalation: { id: "withdraw_escalation", label: "Wycofaj wniosek", to: "in_review" },
  close_violation: {
    id: "close_violation", label: "Zamknij: naruszenie potwierdzone", to: "resolved",
    dialog: {
      title: "Zamknięcie: naruszenie potwierdzone", description: "Uzasadnienie trafi do historii decyzji i do pakietu dowodowego.",
      reason: "required", resolutionAction: true, confirm: "Zamknij sprawę",
    },
  },
  record_intervention: {
    id: "record_intervention", label: "Odnotuj interwencję", to: "awaiting_correction",
    dialog: {
      title: "Interwencja i weryfikacja", description: "Opisz, co zrobił urząd (np. pismo do podmiotu). System będzie sprawdzał źródło co 6 godzin i pokaże, czy treść usunięto, poprawiono, czy naruszenie trwa.",
      reason: "required", followUpDays: true, confirm: "Zapisz i obserwuj",
    },
  },
  close_after_follow_up: {
    id: "close_after_follow_up", label: "Zamknij po weryfikacji", to: "resolved", primary: true,
    dialog: {
      title: "Zamknięcie po weryfikacji", description: "Wybierz wynik interwencji. Uzasadnienie trafi do historii decyzji i do raportu z wykrycia.",
      reason: "required", resolutionAction: true, confirm: "Zamknij sprawę",
    },
  },
  reopen_review: { id: "reopen_review", label: "Wróć do weryfikacji", to: "in_review" },
  close_false_positive: {
    id: "close_false_positive", label: "Zamknij: fałszywy alarm", to: "false_positive",
    dialog: {
      title: "Zamknięcie: fałszywy alarm", description: "Sprawa zostanie oznaczona jako fałszywy alarm i trafi do zbioru kalibracyjnego.",
      reason: "required", confirm: "Zamknij sprawę",
    },
  },
};

/** The buttons for this case, this user and this step, primary first. */
export function availableActions(status: Status, role: Role, assignedTo: string | null, me: string): WorkflowAction[] {
  const out: WorkflowAction[] = [];
  if (!CLOSED.includes(status) && assignedTo !== me) out.push({ id: "assign", label: "Przejmij sprawę" });
  if (status === "new") out.push(ACTIONS.start);
  if (status === "in_review") {
    out.push(ACTIONS.request_escalation, ACTIONS.record_intervention, ACTIONS.close_violation, ACTIONS.close_false_positive);
  }
  if (status === "escalation_requested") {
    if (role === "SUPERVISOR") out.push(ACTIONS.approve_escalation, ACTIONS.reject_escalation);
    else out.push(ACTIONS.withdraw_escalation);
  }
  if (status === "escalated") {
    out.push({ ...ACTIONS.record_intervention, primary: true }, ACTIONS.close_violation, ACTIONS.close_false_positive);
  }
  if (status === "awaiting_correction") {
    out.push(ACTIONS.close_after_follow_up, ACTIONS.reopen_review, { ...ACTIONS.request_escalation, primary: false });
  }
  return out.filter((a) => !a.to || TRANSITIONS[status].includes(a.to));
}

/** The stepper: one bar per stage; both closing statuses share the last one. */
export const STEPS: { key: string; label: string; statuses: Status[] }[] = [
  { key: "new", label: "Nowe", statuses: ["new"] },
  { key: "in_review", label: "Weryfikacja", statuses: ["in_review"] },
  { key: "escalation", label: "Eskalacja", statuses: ["escalation_requested", "escalated"] },
  { key: "follow_up", label: "Weryfikacja po interwencji", statuses: ["awaiting_correction"] },
  { key: "closed", label: "Zamknięte", statuses: ["resolved", "false_positive"] },
];
