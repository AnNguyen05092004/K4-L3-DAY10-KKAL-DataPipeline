# Corruption, Repair and Three-State Comparison

All three states use the same fixed benchmark in `data/eval/test_set.json`.
Repair reconstructs the cleaned dataframe from `data/raw/crossref_records.json`.

## Quantitative comparison

| Metric | Baseline | Corrupted | Repaired | Corruption delta | Repair delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| Retrieval hit rate | 1.0000 | 0.4000 | 1.0000 | -0.6000 | 0.6000 |
| Mean token F1 | 1.0000 | 0.3644 | 1.0000 | -0.6356 | 0.6356 |
| Judge accuracy | 1.0000 | 0.3000 | 1.0000 | -0.7000 | 0.7000 |
| Mean judge score | 5 | 2.2000 | 5 | -2.8000 | 2.8000 |

| Signal | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Data Quality Gate | PASS | FAIL | PASS |
| Freshness SLA | FRESH | STALE | FRESH |

## Controlled corruption scenarios

| Scenario | Affected records | Action |
| --- | ---: | --- |
| `drop_latest_records` | 5 | Removed the newest papers before indexing. |
| `blank_summary` | 5 | Replaced selected summaries with empty strings. |
| `inject_text_noise` | 4 | Injected meaningless tokens into text_for_embedding. |
| `truncate_title` | 5 | Truncated selected titles to fewer than ten characters. |
| `stale_date` | 4 | Shifted selected publication dates five years into the past. |
| `duplicate_rows` | 5 | Appended duplicate records while preserving the original row count after the drop scenario. |

## Quality and freshness evidence

- Failed corrupted expectations: `expect_column_values_to_be_unique, expect_column_value_lengths_to_be_between`.
- Corrupted stale rows: `8/24` (`0.3333`).
- Repaired stale rows: `0/24` (`0.0000`).
- Fixed benchmark samples: `10` for all three states.
- Judge method: `deterministic_token_overlap`.

## Idempotent repair evidence

- Trusted source: `data\raw\crossref_records.json`.
- First repair SHA-256: `1c008e237438de27025b9a6cd29f8bb812085a368e7cbc4a277cf9bb4198bdb3`.
- Second repair SHA-256: `1c008e237438de27025b9a6cd29f8bb812085a368e7cbc4a277cf9bb4198bdb3`.
- Idempotent: **True**.
- Matches baseline: **True**.

## Findings

1. Controlled corruption caused a retrieval-hit-rate change of `-0.6000` and a Token F1 change of `-0.6356`.
2. The quality gate detected blank summaries/duplicate identifiers, while the freshness signal detected the increased stale ratio.
3. Rebuilding from the preserved raw records restored the clean schema and freshness status; repaired metrics are reported above without fabricated adjustments.

## Reproduce

```bash
python script/run_corruption_flow.py
```
