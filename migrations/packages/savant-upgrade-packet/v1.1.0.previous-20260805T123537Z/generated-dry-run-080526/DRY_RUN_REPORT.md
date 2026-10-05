# Savant Dry-Run Safety Evaluation

- Verdict: **UNSAFE**
- Entries: 3983
- Proposed actions: 213
- Mutation performed: **no**
- Baseline digest: `fca0a4a71479fd3717b339aa52ef7d599c1282d2f5ae8a35909587658618d6f7`
- Staged digest: `f462f5abdce0904905e5782dfcb949fbe9ceb24e8b38fcb03a6310ebc256677d`

## Verdict reasons

- failed gate: proposal-applicability — 2 proposal actions cannot be simulated
- failed gate: python-syntax — 5 Python syntax failures

## Gates

| Gate | Status | Severity | Result |
|---|---:|---:|---|
| `source-integrity` | indeterminate | high | 27 rendered entries could not be byte-reconstructed exactly from the textual dump |
| `content-completeness` | pass | high | all included entries have reconstructable content |
| `proposal-applicability` | fail | critical | 2 proposal actions cannot be simulated |
| `ownership-confidence` | indeterminate | high | 175 actions have confidence below 0.90 |
| `compatibility-contracts` | indeterminate | critical | 62 actions require explicit compatibility paths |
| `python-syntax` | fail | critical | 5 Python syntax failures |
| `json-validity` | pass | critical | all JSON and JSONL files parse |
| `shell-syntax` | pass | critical | all shell files pass bash -n |
| `dependent-presence` | pass | high | all declared dependents are present |

## Interpretation

The proposed changes must not be applied. One or more modeled gates prove breakage or invalid preconditions.
