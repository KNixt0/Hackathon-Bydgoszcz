import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ChevronDown, FolderInput, Play } from "lucide-react";
import { Button } from "../ui/Button";

interface Props {
  onTriggerDemo: () => void;
  onImportSamples: () => void;
}

export function DemoMenu({ onTriggerDemo, onImportSamples }: Props) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <Button variant="ghost">
          <span>Demo</span>
          <ChevronDown aria-hidden="true" />
        </Button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="menu" align="end" sideOffset={6}>
          <DropdownMenu.Label className="menu__label">Dane demonstracyjne</DropdownMenu.Label>
          <DropdownMenu.Item className="menu__item" onSelect={onTriggerDemo}>
            <Play aria-hidden="true" />
            <span>
              <span className="menu__item-title" style={{ display: "block" }}>Uruchom próbkę demo</span>
              <span className="menu__item-hint">Przepuszcza nieznaną próbkę przez pełny potok: pobranie, analiza, alert.</span>
            </span>
          </DropdownMenu.Item>
          <DropdownMenu.Item className="menu__item" onSelect={onImportSamples}>
            <FolderInput aria-hidden="true" />
            <span>
              <span className="menu__item-title" style={{ display: "block" }}>Importuj próbki</span>
              <span className="menu__item-hint">Wczytuje pliki z katalogu próbek (nośnik organizatora).</span>
            </span>
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
