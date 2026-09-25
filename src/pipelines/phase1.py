from __future__ import annotations

from datetime import UTC, datetime

from core.config import load_settings
from core.utils import write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set, load_or_create_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def main() -> None:
    """Run the clean-data baseline pipeline and generate all Phase 1 artifacts."""
    settings = load_settings()
    records = fetch_source_records(settings)
    clean_df = build_clean_dataframe(records, datetime.now(UTC))
    if clean_df.empty:
        raise RuntimeError("Cleaning produced no valid paper records.")

    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = quality["freshness"]
    write_json(settings.paths.baseline_quality_report, quality)
    write_json(settings.paths.freshness_report, freshness)
    if not quality["success"]:
        raise RuntimeError("Baseline data failed the quality or freshness gate. See data/quality/.")

    if settings.refresh_test_set:
        samples = build_test_set(clean_df, settings.paths.test_set_json)
    else:
        samples = load_or_create_test_set(clean_df, settings.paths.test_set_json).samples

    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    evaluation = evaluate_pipeline(
        settings,
        index,
        settings.paths.test_set_json,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )

    demos = []
    for sample in samples[:2]:
        answer = answer_question(sample["question"], settings, index)
        demos.append({"question": sample["question"], "answer": answer.answer})
    write_json(settings.paths.demo_answers, demos)

    source_summary = {
        "source": settings.source_api,
        "raw_records": len(records),
        "clean_records": len(clean_df),
        "embedding_model": settings.embedding_model,
        "collection_name": index.collection_name,
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary,
        evaluation.summary,
        quality,
        freshness,
    )

    print(f"Phase 1 complete: {len(clean_df)} clean papers, {len(samples)} benchmark questions.")
    print(f"Retrieval hit rate: {evaluation.summary['retrieval_hit_rate']:.4f}")
    print(f"Mean token F1: {evaluation.summary['mean_token_f1']:.4f}")
    print(f"Report: {settings.paths.baseline_report}")
