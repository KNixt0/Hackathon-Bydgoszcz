import type { ReactNode } from "react";

export type SortDirection = "asc" | "desc";
export function SortHeader({ label, active, direction, onSort }: { label: ReactNode; active: boolean; direction: SortDirection; onSort: () => void }) {
  return <th scope="col" aria-sort={active ? (direction === "asc" ? "ascending" : "descending") : "none"}>
    <button type="button" className="sort-heading" onClick={onSort}>
      {label}<span aria-hidden="true">{active ? (direction === "asc" ? "↑" : "↓") : "↕"}</span>
      <span className="sr-only">, sortuj {active && direction === "asc" ? "malejąco" : "rosnąco"}</span>
    </button>
  </th>;
}
