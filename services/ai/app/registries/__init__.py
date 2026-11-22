"""KNF / KIRP / KIDP register snapshots with fuzzy name matching."""

from .catalog import CONTEXT_ONLY, KNF_FIRM_REGISTERS, KNF_OTHER_LICENSED, KNF_SUB_REGISTERS, REGISTRIES
from .matching import Match, best_match, core_name, normalize_name
from .store import RegistryStore, Snapshot

__all__ = [
    "CONTEXT_ONLY",
    "KNF_FIRM_REGISTERS",
    "KNF_OTHER_LICENSED",
    "KNF_SUB_REGISTERS",
    "REGISTRIES",
    "Match",
    "RegistryStore",
    "Snapshot",
    "best_match",
    "core_name",
    "normalize_name",
]
