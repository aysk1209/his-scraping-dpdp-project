"""Concrete extraction techniques scored by the compliance benchmark.

``DEFAULT_TECHNIQUES`` is the offline-safe core -- ours and the coverage-optimised
baseline -- and is what tests and ad-hoc scripts may use with any task. The
demos call ``default_techniques(tasks)``, which adds every publicly available AI
agent that can run *those* tasks (a full recording, or a key to record live).
With no recordings and no keys the two are the same list, and the demos say so.
"""

from extraction.techniques.ai_agent import AIAgentTechnique, available_agents
from extraction.techniques.compliant import CompliantExtractionTechnique
from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique

DEFAULT_TECHNIQUES = [
    CompliantExtractionTechnique(),
    UnconstrainedExtractionTechnique(),
]


def default_techniques(tasks, source=None):
    """Ours, every AI agent able to run ``tasks`` (recorded under today's brief,
    or keyed to record live), the baseline."""

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
