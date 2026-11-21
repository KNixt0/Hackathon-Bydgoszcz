import * as Dialog from "@radix-ui/react-dialog";
import { CircleAlert, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { MODULE_LABEL, MODULES } from "../../domain/labels";
import type { ScanRequest } from "../../types/api";
import type { ModuleId } from "../../types/incident";
import { Button } from "../ui/Button";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Resolves to null on success or an error message to show in the form. */
  onSubmit: (req: ScanRequest) => Promise<string | null>;
}

function validUrl(value: string): boolean {
  try {
    const u = new URL(value);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

export function ScanDialog({ open, onOpenChange, onSubmit }: Props) {
  const [url, setUrl] = useState("");
  const [moduleHint, setModuleHint] = useState<ModuleId | 0>(0);
  const [render, setRender] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!validUrl(trimmed)) {
      setError("Podaj pełny adres zaczynający się od http:// lub https://.");
      return;
    }
    setBusy(true);
    setError(null);
    const failure = await onSubmit({ url: trimmed, ...(moduleHint ? { module_hint: moduleHint } : {}), ...(render ? { render: true } : {}) });
    setBusy(false);
    if (failure) {
      setError(failure);
      return;
    }
    setUrl("");
    onOpenChange(false);
  };

  return (
    <Dialog.Root open={open} onOpenChange={(next) => { if (!next) setError(null); onOpenChange(next); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="dialog">
          <form onSubmit={submit} noValidate>
            <div className="dialog__head">
              <div>
                <Dialog.Title className="dialog__title">Skanuj adres URL</Dialog.Title>
                <Dialog.Description className="dialog__desc">
                  Strona zostanie pobrana, zarchiwizowana i oceniona przez silnik. Wynik trafi do kolejki.
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <Button variant="ghost" iconOnly aria-label="Zamknij"><X aria-hidden="true" /></Button>
              </Dialog.Close>
            </div>
            <div className="dialog__body">
              <label className="field">
                <span className="field__label">Adres materiału</span>
                <input
                  className="input" type="url" inputMode="url" autoFocus required value={url}
                  placeholder="https://przyklad.pl/oferta"
                  aria-invalid={error ? true : undefined} aria-describedby={error ? "scan-error" : undefined}
                  onChange={(e) => { setUrl(e.target.value); if (error) setError(null); }}
                />
              </label>
              <label className="field">
                <span className="field__label">Moduł analityczny</span>
                <select className="select" value={moduleHint} onChange={(e) => setModuleHint(Number(e.target.value) as ModuleId | 0)}>
                  <option value={0}>Wykryj automatycznie</option>
                  {MODULES.map((m) => <option key={m} value={m}>Moduł {m}: {MODULE_LABEL[m]}</option>)}
                </select>
              </label>
              <label className="checkbox">
                <input type="checkbox" checked={render} onChange={(e) => setRender(e.target.checked)} />
                <span>Renderuj stronę w przeglądarce (treści ładowane skryptami, zrzut ekranu)</span>
              </label>
              {error && (
                <p className="form-error" id="scan-error" role="alert"><CircleAlert aria-hidden="true" />{error}</p>
              )}
            </div>
            <div className="dialog__foot">
              <Dialog.Close asChild><Button>Anuluj</Button></Dialog.Close>
              <Button type="submit" variant="primary" disabled={busy}>{busy ? "Zlecanie…" : "Zleć skanowanie"}</Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
