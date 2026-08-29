"""Synthetic HIS data generator.

Build step 3. Produces fake patient/admin records shaped to the five-layer HIS
architecture (see `interop.layers`) and structurable into HL7/FHIR-like records.
Everything downstream is developed and tested against this until live HIS access
is usable.

The five layers are kept as distinct schema modules under `schemas/` — do not
flatten them into a single record type (PROJECT_CONTEXT.md).
"""
