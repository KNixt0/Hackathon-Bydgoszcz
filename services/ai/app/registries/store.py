"""Register snapshots: bundled JSON, runtime replacements, lookups.

Load order per register: runtime snapshot from `AI_DATA_DIR/registries/` (written by
`PUT /registries/{registry}`) if present, else the bundled file. The demo overlay adds a few
clearly fictional entities (flagged `synthetic`) on top, so that real snapshots stay pure
and a refresh of a real register does not break the demo cases.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from dataclasses import dataclass
from pathlib import Path

from ..config import BUNDLED_DATA_DIR
from .catalog import CONTEXT_ONLY, KNF_SUB_REGISTERS, REGISTRIES
from .matching import Match, best_match, find_brands_in_text

log = logging.getLogger(__name__)
OVERLAY_FILE = "_demo_overlay.json"


@dataclass
class Snapshot:
    registry: str
    snapshot_date: str | None
    entries: list[dict]
    meta: dict


class RegistryStore:
    def __init__(self, data_dir: Path | None = None, demo_overlay: bool = True,
                 bundled_dir: Path = BUNDLED_DATA_DIR / "registries") -> None:
        self.bundled_dir = bundled_dir
        self.runtime_dir = (data_dir / "registries") if data_dir else None
        self.demo_overlay = demo_overlay
        self._lock = threading.Lock()
        self._snapshots: dict[str, Snapshot] = {}
        self.reload()

    # ------------------------------------------------------------ loading
    def _read(self, registry: str) -> tuple[dict | None, bool]:
        for directory, runtime in ((self.runtime_dir, True), (self.bundled_dir, False)):
            if directory is None:
                continue
            path = directory / f"{registry}.json"
            if path.is_file():
                try:
                    return json.loads(path.read_text(encoding="utf-8")), runtime
                except (OSError, json.JSONDecodeError) as exc:
                    log.error("cannot read register snapshot %s: %s", path, exc)
        return None, False

    def reload(self) -> None:
        overlay: dict[str, list[dict]] = {}
        overlay_path = self.bundled_dir / OVERLAY_FILE
        if self.demo_overlay and overlay_path.is_file():
            overlay = json.loads(overlay_path.read_text(encoding="utf-8")).get("registries", {})
        snapshots: dict[str, Snapshot] = {}
        for registry in REGISTRIES:
            if registry in CONTEXT_ONLY:
                snapshots[registry] = Snapshot(registry, None, [], {"context_only": True})
                continue
            raw, runtime = self._read(registry)
            raw = raw or {"snapshot_date": None, "entries": []}
            entries = [dict(e) for e in raw.get("entries", [])]
            entries += [dict(e, synthetic=True) for e in overlay.get(registry, [])]
            meta = {k: v for k, v in raw.items() if k != "entries"}
            meta["runtime"] = runtime
            snapshots[registry] = Snapshot(registry, raw.get("snapshot_date"), entries, meta)
        # The umbrella register is the union of its sub-registers unless it was set explicitly.
        umbrella = snapshots["knf_investment_firms"]
        if not [e for e in umbrella.entries if not e.get("synthetic")]:
            seen: set[str] = set()
            union: list[dict] = []
            for sub in KNF_SUB_REGISTERS:
                for entry in snapshots[sub].entries:
                    if entry["name"] not in seen:
                        seen.add(entry["name"])
                        union.append(dict(entry, source_registry=sub))
            dates = [snapshots[s].snapshot_date for s in KNF_SUB_REGISTERS if snapshots[s].snapshot_date]
            umbrella.entries = union
            umbrella.snapshot_date = min(dates) if dates else None
            umbrella.meta["derived_from"] = KNF_SUB_REGISTERS
        with self._lock:
            self._snapshots = snapshots

    def replace(self, registry: str, snapshot_date: str, entries: list[dict]) -> int:
        """Persist a new snapshot (backend refresh job) and reload."""
        if registry not in REGISTRIES:
            raise KeyError(registry)
        if registry in CONTEXT_ONLY:
            raise ValueError("register is fed only by the analysis context")
        if self.runtime_dir is None:
            raise RuntimeError("no writable data directory configured")
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        label, url = REGISTRIES[registry]
        payload = {
            "registry": registry, "label": label, "url": url, "snapshot_date": snapshot_date,
            "source": "PUT /registries", "entries": entries,
        }
        tmp = self.runtime_dir / f"{registry}.json.tmp"
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.runtime_dir / f"{registry}.json")
        self.reload()
        return len(entries)

    # ------------------------------------------------------------ queries
    def snapshot(self, registry: str) -> Snapshot:
        return self._snapshots[registry]

    def summary(self) -> list[dict]:
        out = []
        for registry, (label, url) in REGISTRIES.items():
            snap = self._snapshots[registry]
            out.append({
                "registry": registry, "label": label, "url": url,
                "entries": len(snap.entries), "snapshot_date": snap.snapshot_date,
            })
        return out

    def lookup(self, registry: str, name: str) -> Match | None:
        return best_match(name, self._snapshots[registry].entries)

    def lookup_number(self, registry: str, number: str) -> dict | None:
        """Find an entry by licence / register number (stored in `number` or an alias)."""
        wanted = _number_key(number)
        if not wanted:
            return None
        for entry in self._snapshots[registry].entries:
            candidates = [str(entry.get("number", "")), *entry.get("aliases", [])]
            if any(_number_key(c) == wanted for c in candidates if c):
                return entry
        return None

    def brands_in_text(self, registry: str, text: str, folded: str) -> list[tuple[int, int, dict]]:
        return find_brands_in_text(text, folded, self._snapshots[registry].entries)


def _number_key(value: str) -> str:
    return re.sub(r"[^0-9a-z]", "", value.lower()).removeprefix("nr").lstrip("0")
