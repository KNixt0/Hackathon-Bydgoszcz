"""Multi-agent debate with cross-critique (deterministic; an LLM is optional on top)."""

from .critic import Critic, grounding_error
from .models import AgentReport, DebateClaim
from .orchestrator import DebateOutcome, run_debate

__all__ = ["AgentReport", "Critic", "DebateClaim", "DebateOutcome", "grounding_error", "run_debate"]
