import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ChevronDown } from "lucide-react";
import { Link } from "react-router-dom";
import { SCAN_STATE_LABEL } from "../../domain/labels";
import type { ScanJob, ScanState } from "../../types/api";
import { Button } from "../ui/Button";
import { EmptyState } from "../ui/States";

const ORDER: ScanState[] = ["queued", "scraping", "analyzing", "done"];

export function JobProgress({ job }: { job: ScanJob }) {
  const reached = job.state === "failed" ? 3 : ORDER.indexOf(job.state);
  return (
    <li className={`job job--${job.state}`}>
      <div className="job__top">
        <span className="job__url truncate" title={job.url}>{job.url}</span>
        <span className="job__state">{SCAN_STATE_LABEL[job.state]}</span>
      </div>
      <div className="job__steps" role="progressbar" aria-valuemin={0} aria-valuemax={3} aria-valuenow={Math.max(0, reached)} aria-valuetext={SCAN_STATE_LABEL[job.state]} aria-label={`Postęp skanowania: ${job.url}`}>
        {ORDER.map((s, i) => (
          <span key={s} className={`job__step${i < reached || job.state === "done" ? " job__step--on" : i === reached ? " job__step--active" : ""}`} />
        ))}
      </div>
      {job.state === "failed" && <p className="job__error">{job.error ?? "Zadanie zakończyło się błędem."}</p>}
      {job.state === "done" && job.incident_id && <Link to={`/sprawy/${job.incident_id}`}>Otwórz sprawę</Link>}
    </li>
  );
}

interface Props {
  jobs: ScanJob[];
  activeCount: number;
  onClearFinished: () => void;
}

/** Link-style trigger "Zadania (2)": the count in brackets only while scans run. */
export function JobsMenu({ jobs, activeCount, onClearFinished }: Props) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button type="button" className="linkbtn hd__menu" aria-label={`Zadania skanowania, aktywne: ${activeCount}`}>
          Zadania{activeCount > 0 && <span className="num"> ({activeCount})</span>}<ChevronDown aria-hidden="true" />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="menu jobs" align="end" sideOffset={8}>
          <div className="jobs__head">
            <span>Zadania skanowania</span>
            {jobs.some((j) => j.state === "done" || j.state === "failed") && (
              <Button variant="ghost" size="sm" onClick={onClearFinished}>Wyczyść zakończone</Button>
            )}
          </div>
          {jobs.length === 0 ? (
            <EmptyState compact title="Brak zadań" text="Przeanalizuj adres URL albo zaimportuj próbki, aby zobaczyć postęp przetwarzania." />
          ) : (
            <ul className="jobs__list">
              {jobs.map((job) => <JobProgress key={job.id} job={job} />)}
            </ul>
          )}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
