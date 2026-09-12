"""Concrete extraction techniques scored by the compliance benchmark.

``DEFAULT_TECHNIQUES`` is the set the headline benchmark demo compares.
"""

from extraction.techniques.compliant import CompliantExtractionTechnique
from extraction.techniques.morality import MoralityTechnique
from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique

DEFAULT_TECHNIQUES = [
    CompliantExtractionTechnique(),
    MoralityTechnique(),
    UnconstrainedExtractionTechnique(),
]

__all__ = [
    "CompliantExtractionTechnique",
    "MoralityTechnique",
    "UnconstrainedExtractionTechnique",
    "DEFAULT_TECHNIQUES",
]
