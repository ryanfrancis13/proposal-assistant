# Meridian Proposal Assistant

This file is the plain-language record of what each part of the project does.
It is updated as the new implementation is built.

## Source data

- `data/raw/` is the source document corpus and is preserved.
- `data/eval/` contains sample RFPs and is preserved.
- The application is being built from these inputs rather than inherited
  application code. The previous implementation and generated artifacts are
  not part of the design.

## Research pipeline

The application is being built in a few stages:

1. Define typed data structures and configuration for RFPs, evidence, proposal
   sections, verification results, and experiment records.
2. Add document ingestion and hybrid retrieval, with stale case-study pricing
   marked as unusable for current quotes.
3. Add structured RFP extraction and deterministic quote construction.
4. Add section drafting, per-section verification, and the three repair
   conditions: none, whole-document resampling, and targeted repair.
5. Add experiment execution, confidence intervals, result export, and DOCX
   proposal export.

## Current status

- Raw documents and sample RFPs retained as source data.
- Shared typed models and YAML settings loader added.
- Document ingestion and ranked lexical evidence retrieval added.
- Case 10 is marked `superseded_pricing` so its prices cannot be treated as
  current quote evidence.
- `pricing.py` computes migration, support, and CSPS prices from the current
  product documents and applies contractual discounts in the documented order.
- `pricing.py` validates R1-R7 and distinguishes hard quote blockers from the
  soft approval flag R6.
- Generation, RFP extraction, verification, repair, experiments, and export
  are not yet implemented.
