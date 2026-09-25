from __future__ import annotations

from datetime import UTC, datetime
import hashlib

import pandas as pd
from pandas.testing import assert_frame_equal

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.phase1 import main as run_phase1
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Corrupt the baseline, repair from raw records, and compare all states."""
    settings = load_settings()
    baseline_inputs = [
        settings.paths.clean_json,
        settings.paths.test_set_json,
        settings.paths.baseline_metrics,
        settings.paths.baseline_quality_report,
        settings.paths.freshness_report,
    ]
    if any(not path.is_file() for path in baseline_inputs):
        print("Baseline artifacts are incomplete; running Phase 1 first.")
        run_phase1()

    clean_df = pd.read_json(settings.paths.clean_json)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_quality = read_json(settings.paths.baseline_quality_report)
    baseline_freshness = read_json(settings.paths.freshness_report)

    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, settings.paths.corrupted_embeddings_json
    )
    corrupted_evaluation = evaluate_pipeline(
        settings,
        corrupted_index,
        settings.paths.test_set_json,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )

    repair_time = datetime.now(UTC)
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, repair_time)
    repeated_repair_df = build_clean_dataframe(raw_records, repair_time)
    assert_frame_equal(repaired_df, repeated_repair_df, check_dtype=True, check_like=False)
    baseline_hash = hashlib.sha256(clean_df.to_json(orient="records", force_ascii=False).encode("utf-8")).hexdigest()
    repaired_hash = hashlib.sha256(repaired_df.to_json(orient="records", force_ascii=False).encode("utf-8")).hexdigest()
    repeated_hash = hashlib.sha256(repeated_repair_df.to_json(orient="records", force_ascii=False).encode("utf-8")).hexdigest()
    repair_verification = {
        "source": str(settings.paths.raw_records_json.relative_to(settings.paths.project_dir)),
        "baseline_sha256": baseline_hash,
        "first_repair_sha256": repaired_hash,
        "second_repair_sha256": repeated_hash,
        "idempotent": repaired_hash == repeated_hash,
        "matches_baseline": repaired_hash == baseline_hash,
        "rows": len(repaired_df),
    }
    write_json(settings.paths.repair_verification, repair_verification)
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    if not repaired_quality["success"]:
        raise RuntimeError("Repair did not restore the quality/freshness gate.")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, settings.paths.repaired_embeddings_json
    )
    repaired_evaluation = evaluate_pipeline(
        settings,
        repaired_index,
        settings.paths.test_set_json,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )

    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_evaluation.summary,
        repaired_evaluation.summary,
        baseline_quality,
        corrupted_quality,
        repaired_quality,
        baseline_freshness,
        corrupted_quality["freshness"],
        repaired_quality["freshness"],
        read_json(settings.paths.corruption_log),
        repair_verification,
    )

    print("Corruption and idempotent repair complete.")
    print("Metric                 Baseline   Corrupted   Repaired")
    for key in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        print(
            f"{key:22} {baseline_metrics[key]:9.4f} "
            f"{corrupted_evaluation.summary[key]:11.4f} {repaired_evaluation.summary[key]:10.4f}"
        )
    print(
        "Quality gate           "
        f"{'PASS' if baseline_quality['success'] else 'FAIL':>9} "
        f"{'PASS' if corrupted_quality['success'] else 'FAIL':>11} "
        f"{'PASS' if repaired_quality['success'] else 'FAIL':>10}"
    )
    print(f"Report: {settings.paths.comparison_report}")
