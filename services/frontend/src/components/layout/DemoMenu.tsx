import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ChevronDown, FolderInput, Play } from "lucide-react";

interface Props {
  onTriggerDemo: () => void;
  onImportSamples: () => void;
}

export function DemoMenu({ onTriggerDemo, onImportSamples }: Props) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button type="button" className="linkbtn hd__menu">
          Dane demo<ChevronDown aria-hidden="true" />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="menu" align="end" sideOffset={8}>
          <DropdownMenu.Label className="menu__label">Dane demonstracyjne</DropdownMenu.Label>
          <DropdownMenu.Item className="menu__item" onSelect={onTriggerDemo}>
            <Play aria-hidden="true" />
            <span>
              <span className="menu__item-title">Uruchom próbkę demonstracyjną</span>
              <span className="menu__item-hint">Przepuszcza nieznaną próbkę przez pełny potok: pobranie, analiza, alert.</span>
            </span>
          </DropdownMenu.Item>
          <DropdownMenu.Item className="menu__item" onSelect={onImportSamples}>
            <FolderInput aria-hidden="true" />
            <span>
              <span className="menu__item-title">Importuj próbki</span>
              <span className="menu__item-hint">Wczytuje pliki z katalogu próbek (nośnik organizatora).</span>
            </span>
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
