"""Concrete extraction techniques scored by the compliance benchmark.

``DEFAULT_TECHNIQUES`` is the set the headline demos compare: ours, every
publicly available AI agent that can run right now (recorded, or keyed --
see ``ai_agent.available_agents``), and the coverage-optimised baseline.
With no recordings and no keys it is ours against the baseline, and the
demos say so rather than pretending.
"""

from extraction.techniques.ai_agent import AIAgentTechnique, available_agents
from extraction.techniques.compliant import CompliantExtractionTechnique
from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique


def default_techniques():
    return [
        CompliantExtractionTechnique(),
        *available_agents(),
        UnconstrainedExtractionTechnique(),
    ]


DEFAULT_TECHNIQUES = default_techniques()

__all__ = [
    "CompliantExtractionTechnique",
    "AIAgentTechnique",
    "UnconstrainedExtractionTechnique",
    "available_agents",
    "default_techniques",
    "DEFAULT_TECHNIQUES",
]
