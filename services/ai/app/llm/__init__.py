"""Optional Ollama layer (off by default)."""

from .ollama import OllamaClient
from .tasks import propose_claims, rewrite_rationale

__all__ = ["OllamaClient", "propose_claims", "rewrite_rationale"]
