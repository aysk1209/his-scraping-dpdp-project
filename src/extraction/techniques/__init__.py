"""Concrete extraction techniques scored by the compliance benchmark.

``DEFAULT_TECHNIQUES`` is the offline-safe core -- ours and the coverage-optimised
baseline -- and is what tests and ad-hoc scripts may use with any task. The
demos call ``default_techniques(tasks)``, which adds every publicly available AI
agent that can run *those* tasks: a full, fresh recording -- or, only when
``AI_AGENT_MODE`` is ``auto`` or ``live``, a key to record with. The default mode
is ``replay``, so a demo never reaches the network however the shell is set up.
With no recordings the two are the same list, and the demos say so.
"""

from extraction.techniques.ai_agent import AIAgentTechnique, available_agents
from extraction.techniques.compliant import CompliantExtractionTechnique
from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique

DEFAULT_TECHNIQUES = [
    CompliantExtractionTechnique(),
    UnconstrainedExtractionTechnique(),
]


def default_techniques(tasks, source=None):
    """Ours, every AI agent able to run ``tasks`` (recorded under today's brief;
    or keyed to record live when the mode allows), the baseline."""

    return [
        CompliantExtractionTechnique(),
        *available_agents(tasks=list(tasks), source=source),
        UnconstrainedExtractionTechnique(),
    ]


__all__ = [
    "CompliantExtractionTechnique",
    "AIAgentTechnique",
    "UnconstrainedExtractionTechnique",
    "available_agents",
    "default_techniques",
    "DEFAULT_TECHNIQUES",
]
