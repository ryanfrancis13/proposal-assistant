# Targeted Repair Experiment Protocol

## Research question

With deterministic per-section verification, does repairing only failed
proposal sections achieve a higher strict-compliance rate than no repair or
whole-document resampling, and what is the cost in model calls?

## Conditions

- `none`: draft each section once and keep the result.
- `whole_document`: if any section fails, regenerate every section once.
- `targeted_section`: if a section fails, regenerate only that section once and
  include its specific verifier messages in the repair prompt.

The system does not silently retry beyond the defined condition. A failed
repair remains a failed result.

## Evaluation corpus

The reproducible generator in
[`src/proposal_assistant/synthetic.py`](./src/proposal_assistant/synthetic.py)
creates cases with these seeded traps:

- Unsupported Google Cloud Platform, SAP HANA, or mainframe service.
- Negotiated discount above the 15% cap.
- Discount that breaches the 80% price floor.
- Deadline shorter than the documented migration timeline.
- Certification or mapping not supported by the product documents.
- Requirement with no documentary coverage.
- Stale pricing reference.

For a pilot, run 20 cases with 3 repeats per condition. The final paper should
report the exact generated case count, seed, repeats, and any excluded runs.

## Metrics

### Strict compliance

A proposal is strictly compliant only when every drafted section passes every
deterministic verifier check. This is a binary proposal-level metric.

### Loose compliance

Loose compliance is the proportion of the seven verifier checks that did not
produce an issue, averaged over sections and proposals. The implementation
uses the fixed check set `V1` through `V7`, so a section with multiple issues
does not change the denominator.

### Violations

Report counts by verifier ID and map IDs to the checks in
[`src/proposal_assistant/verification.py`](./src/proposal_assistant/verification.py).
Do not merge distinct violation types before reporting them.

### Cost

Report the mean number of model calls per proposal, with a 95% confidence
interval. Retrieval and deterministic verification are not counted as LLM
calls.

## Statistical reporting

The runner writes raw records and condition summaries to JSON and CSV. Strict
compliance uses a 95% Wilson interval. Loose compliance and model-call counts
use a 95% normal mean interval. Report `n` for every condition and do not call
a result statistically conclusive solely because one point estimate is larger.

## Reproducibility

Example command:

```powershell
python -m proposal_assistant.experiment_cli --count 20 --repeats 3 --seed 7 --output results
```

Record the Python version, configured generator model, embedding model, date,
seed, case count, repeats, and whether any API failures or retries occurred.
Keep raw `records.json` with the summary files.

## Limitations and citation status

The cases are synthetic and intentionally trap-focused; they do not establish
performance on real procurement documents. The 11B model, free-tier rate
limits, prompt format, retrieval settings, and fixed verifier rules may affect
results. Targeted repair also receives more information about the failing
section than a no-repair run, which is intentional but should be discussed.

The proposed related-work references and the claim that no prior study combines
all of these components must be verified against primary sources before being
included as established fact. Until that check is complete, describe the gap as
a hypothesis from a limited search, not as a confirmed literature result.
