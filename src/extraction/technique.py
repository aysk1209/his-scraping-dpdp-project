"""Extraction technique abstraction.

A *technique* is a strategy for fulfilling an extraction task against a data
source. Crucially, the technique also produces the compliance manifest for its
own run -- so "compliance-aware" is a property of the technique's design, not a
label applied afterwards. The benchmark (``compliance.benchmark``) scores every
technique's output with the same DPDP rule set.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from compliance.models import ExtractedRecord, ExtractionRun, Purpose
from extraction.base import HISDataSource
from interop.layers import HISLayer


class LayerFields(BaseModel):
    """A HIS layer paired with the field names required from it."""

    layer: HISLayer
    fields: list[str]


class ExtractionTask(BaseModel):
    """What a caller wants extracted, and the lawful purpose for it.

    ``needed`` is the *minimum necessary* field set for the purpose. A
    compliance-aware technique pulls exactly this; a coverage-optimised one
    ignores it.
    """

    task_id: str
    purpose: Purpose
    needed: list[LayerFields] = Field(default_factory=list)


class TechniqueOutput(BaseModel):
    """A technique's run manifest plus the records it produced."""

    run: ExtractionRun
    records: list[ExtractedRecord]


class ExtractionTechnique(ABC):
    """A named strategy that turns an ``ExtractionTask`` into a ``TechniqueOutput``."""

    name: str = ""

    @abstractmethod
    def extract(self, source: HISDataSource, task: ExtractionTask) -> TechniqueOutput:
        raise NotImplementedError
