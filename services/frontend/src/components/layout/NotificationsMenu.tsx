import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Bell } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api/endpoints";
import { formatDateTime } from "../../domain/format";
import { useUi } from "../../hooks/useUi";
import type { CalibrationNotification } from "../../types/api";
import { Button } from "../ui/Button";

const REFRESH_MS = 15000;

/**
 * Calibration changes (ported from #33): when a supervisor saves new global thresholds, every user gets
 * a durable notification with their own read state. A new one also shows once as a toast.
 */
export function NotificationsMenu() {
  const [items, setItems] = useState<CalibrationNotification[]>([]);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const seen = useRef<Set<number> | null>(null); // null until the first load: old items never toast
  const { notify } = useUi();

  const refresh = useCallback(async (signal?: AbortSignal) => {
    try {
      const next = (await api.notifications(signal)).items ?? [];
      if (signal?.aborted) return;
      const fresh = next.filter((item) => !item.read_at && seen.current && !seen.current.has(item.id));
      if (fresh[0]) notify("info", fresh[0].message);
      seen.current = new Set(next.map((item) => item.id));
      setItems(next);
      setError("");
    } catch {
      if (!signal?.aborted) setError("Nie udało się odświeżyć powiadomień.");
    }
  }, [notify]);

  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal);
    const timer = window.setInterval(() => void refresh(controller.signal), REFRESH_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [refresh]);

  const markRead = async (id: number) => {
    setBusyId(id);
    try {
      const result = await api.readNotification(id);
      setItems((current) => current.map((item) => (item.id === id ? { ...item, read_at: result.read_at } : item)));
    } catch {
      setError("Nie udało się oznaczyć powiadomienia jako przeczytanego.");
    } finally {
      setBusyId(null);
    }
  };

  const unread = items.filter((item) => !item.read_at).length;
  return (
    <DropdownMenu.Root onOpenChange={(open) => { if (open) void refresh(); }}>
      <DropdownMenu.Trigger asChild>
        <button type="button" className="linkbtn hd__menu" aria-label={`Powiadomienia, nieprzeczytane: ${unread}`}>
          <Bell aria-hidden="true" />Powiadomienia{unread > 0 && <b className="notification-count" aria-hidden="true">{unread}</b>}
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="menu notifications" align="end" sideOffset={8} aria-label="Powiadomienia o kalibracji">
          <div className="jobs__head">Zmiany kalibracji</div>
          {error && (
            <p role="status" className="notification form-error">
              {error} <button className="linkbtn" type="button" onClick={() => void refresh()}>Spróbuj ponownie</button>
            </p>
          )}
          {!items.length && !error && <p className="notification muted">Brak powiadomień.</p>}
          <ul className="notifications__list">
            {items.map((item) => (
              <li key={item.id} className={`notification${item.read_at ? "" : " notification--unread"}`}>
                <p>{item.message}</p>
                <time dateTime={item.created_at} className="muted">{formatDateTime(item.created_at)}</time>
                {!item.read_at && (
                  <Button size="sm" disabled={busyId === item.id} onClick={() => void markRead(item.id)}>Oznacz jako przeczytane</Button>
                )}
              </li>
            ))}
          </ul>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
