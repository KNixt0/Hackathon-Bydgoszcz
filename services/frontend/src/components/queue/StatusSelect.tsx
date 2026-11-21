import { STATUS_LABEL, STATUSES } from "../../domain/labels";
import type { Status } from "../../types/incident";

interface Props {
  value: Status;
  onChange: (next: Status) => void;
  disabled?: boolean;
  label: string;
  size?: "sm" | "md";
}

export function StatusSelect({ value, onChange, disabled = false, label, size = "sm" }: Props) {
  return (
    <select
      className={`select${size === "sm" ? " select--sm" : ""}`}
      aria-label={label}
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value as Status)}
    >
      {STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
    </select>
  );
}
