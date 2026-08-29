"""Record generators, one recipe per catalogue field (build step 3).

Slice 1: ``records.generate_layer_records`` / ``records.build_dataset`` emit
plain-dict records for every field in ``data_synthetic.catalogue``. Per-layer
pydantic schemas come with the full build step 3.
"""

from data_synthetic.generators.records import build_dataset, generate_layer_records

__all__ = ["build_dataset", "generate_layer_records"]
