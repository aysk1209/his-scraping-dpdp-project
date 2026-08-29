"""Concrete extraction techniques scored by the compliance benchmark.

``DEFAULT_TECHNIQUES`` is the set the headline benchmark demo compares.
"""

from extraction.techniques.compliant import CompliantExtractionTechnique
from extraction.techniques.minimising import MinimisingUndocumentedTechnique
from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique

DEFAULT_TECHNIQUES = [
    CompliantExtractionTechnique(),
    MinimisingUndocumentedTechnique(),
    UnconstrainedExtractionTechnique(),
]

__all__ = [
    "CompliantExtractionTechnique",
    "MinimisingUndocumentedTechnique",
    "UnconstrainedExtractionTechnique",
    "DEFAULT_TECHNIQUES",
]
