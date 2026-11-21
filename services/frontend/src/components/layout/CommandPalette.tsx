import * as Dialog from "@radix-ui/react-dialog";
import { Command } from "cmdk";
import { CornerDownLeft, FileSearch, Filter, Inbox, Play, Radar, Search, SlidersHorizontal } from "lucide-react";
import { deriveLevel, type Thresholds } from "../../domain/levels";
import { LEVEL_LABEL, MODULE_LABEL, MODULES } from "../../domain/labels";
import { LEVELS } from "../../domain/levels";
import type { IncidentSummary } from "../../types/incident";
import { useRestoreFocus } from "../../hooks/useRestoreFocus";
import { LevelBadge } from "../ui/LevelBadge";

export type PaletteCommand =
  | { type: "navigate"; to: string }
  | { type: "scan" }
  | { type: "demo" };

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  incidents: IncidentSummary[];
  thresholds: Thresholds;
  onCommand: (command: PaletteCommand) => void;
}

const fold = (s: string) => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/ł/g, "l");

/** Every typed word must occur in the item (case- and diacritics-insensitive): predictable, unlike fuzzy matching. */
export function paletteFilter(value: string, search: string): number {
  const hay = fold(value);
  return fold(search).split(/\s+/).filter(Boolean).every((w) => hay.includes(w)) ? 1 : 0;
}

export function CommandPalette({ open, onOpenChange, incidents, thresholds, onCommand }: Props) {
  const focus = useRestoreFocus();
  const run = (command: PaletteCommand) => {
    onOpenChange(false);
    onCommand(command);
  };
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="dialog palette" aria-describedby={undefined} onOpenAutoFocus={focus.remember} onCloseAutoFocus={focus.restore}>
          <Dialog.Title className="sr-only">Paleta poleceń</Dialog.Title>
          <Command label="Paleta poleceń" loop filter={paletteFilter}>
            <div className="palette__input-row">
              <Search aria-hidden="true" />
              <Command.Input className="palette__input" placeholder="Wpisz tytuł sprawy, podmiot lub polecenie" />
            </div>
            <Command.List className="palette__list">
              <Command.Empty className="palette__empty">Brak wyników. Spróbuj innej frazy.</Command.Empty>

              <Command.Group heading="Polecenia">
                <Command.Item value="kolejka spraw strona główna" onSelect={() => run({ type: "navigate", to: "/" })}>
                  <Inbox aria-hidden="true" /><span className="palette__item-main">Otwórz kolejkę spraw</span>
                </Command.Item>
                <Command.Item value="kalibracja próg suwak precision recall" onSelect={() => run({ type: "navigate", to: "/kalibracja" })}>
                  <SlidersHorizontal aria-hidden="true" /><span className="palette__item-main">Otwórz kalibrację progów</span>
                </Command.Item>
                <Command.Item value="skanuj url adres strona" onSelect={() => run({ type: "scan" })}>
                  <Radar aria-hidden="true" /><span className="palette__item-main">Skanuj adres URL</span>
                </Command.Item>
                <Command.Item value="uruchom próbkę demo" onSelect={() => run({ type: "demo" })}>
                  <Play aria-hidden="true" /><span className="palette__item-main">Uruchom próbkę demo</span>
                </Command.Item>
              </Command.Group>

              <Command.Group heading="Filtruj kolejkę">
                {LEVELS.map((level) => (
                  <Command.Item key={level} value={`poziom ${LEVEL_LABEL[level]}`} onSelect={() => run({ type: "navigate", to: `/?poziom=${level}` })}>
                    <Filter aria-hidden="true" /><span className="palette__item-main">Poziom: {LEVEL_LABEL[level]}</span>
                  </Command.Item>
                ))}
                {MODULES.map((m) => (
                  <Command.Item key={m} value={`moduł ${m} ${MODULE_LABEL[m]}`} onSelect={() => run({ type: "navigate", to: `/?modul=${m}` })}>
                    <Filter aria-hidden="true" /><span className="palette__item-main">Moduł {m}: {MODULE_LABEL[m]}</span>
                  </Command.Item>
                ))}
              </Command.Group>

              {incidents.length > 0 && (
                <Command.Group heading="Sprawy">
                  {incidents.map((it) => (
                    <Command.Item
                      key={it.id}
                      value={`${it.title} ${it.advertiser ?? ""} ${it.firm ?? ""} ${it.id}`}
                      onSelect={() => run({ type: "navigate", to: `/sprawy/${it.id}` })}
                    >
                      <FileSearch aria-hidden="true" />
                      <span className="palette__item-main">
                        <span className="truncate" style={{ display: "block" }}>{it.title}</span>
                        <span className="palette__item-sub truncate" style={{ display: "block" }}>
                          {[it.advertiser, it.firm].filter(Boolean).join(" → ") || "Podmiot nieustalony"}
                        </span>
                      </span>
                      <LevelBadge level={deriveLevel(it.risk_score, thresholds)} />
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
            </Command.List>
          </Command>
          <div className="palette__foot" aria-hidden="true">
            <span><kbd className="kbd">↑</kbd><kbd className="kbd">↓</kbd> wybór</span>
            <span><kbd className="kbd"><CornerDownLeft size={10} /></kbd> otwórz</span>
            <span><kbd className="kbd">Esc</kbd> zamknij</span>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
