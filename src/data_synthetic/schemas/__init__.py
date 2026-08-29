"""Record schemas, one module per HIS layer (build step 3).

Each layer in `interop.layers.HISLayer` gets its own pydantic schema module.
Keeping them separate preserves the five-layer structure through the pipeline.
"""
