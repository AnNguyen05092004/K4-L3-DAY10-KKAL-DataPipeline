# Phase 1 — Baseline Pipeline Report

## Source and cleaned data

- Source: Crossref REST API
- Raw records: 24
- Clean records: 24
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Chroma collection: `papers-baseline`
- Evaluation samples: 10

## Baseline metrics

| Metric | Value |
| --- | ---: |
| Retrieval hit rate | 1.0000 |
| Mean token F1 | 1.0000 |
| Judge accuracy | 1.0000 |
| Mean judge score | 5 |
| Judge method | deterministic_token_overlap |

## Data quality

Overall quality status: **PASS**

| Expectation | Status |
| --- | --- |
| `expect_table_row_count_to_be_between` | PASS |
| `expect_column_values_to_not_be_null` | PASS |
| `expect_column_values_to_not_be_null` | PASS |
| `expect_column_values_to_not_be_null` | PASS |
| `expect_column_values_to_be_unique` | PASS |
| `expect_column_value_lengths_to_be_between` | PASS |

## Freshness SLA

- Threshold: `180 days`
- Latest publication: `2026-09-15`
- Oldest publication: `2026-04-01`
- Stale rows: `0/24`
- Stale ratio: `0.0000`
- Status: **FRESH**

## Reproduce

```bash
python script/run_phase1.py
```
