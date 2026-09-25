from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, read_json, write_json


@dataclass(frozen=True)
class BenchmarkTestSet:
    samples: list[dict[str, Any]]


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Create ten deterministic questions across five business question types."""
    required = {"paper_id", "title", "summary", "authors_joined", "published", "categories_joined"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Clean dataset is missing columns: {', '.join(sorted(missing))}")
    papers = df.dropna(subset=list(required)).drop_duplicates("paper_id").sort_values("paper_id")
    if len(papers) < 8:
        raise ValueError("At least eight distinct papers are needed for the benchmark.")
    rows = papers.to_dict(orient="records")

    def sample(number: int, kind: str, question: str, answer: str, ids: list[str]) -> dict[str, Any]:
        return {
            "id": f"eval_{number:03d}",
            "type": kind,
            "question_type": "categories" if kind == "category" else kind,
            "question": question, "ground_truth": str(answer),
            "ground_truth_doc_ids": ids,
        }

    def multi_hop_answer(left: dict[str, Any], right: dict[str, Any]) -> str:
        return (
            f"{left['title']}: {first_sentence(left['summary'])} | "
            f"{right['title']}: {first_sentence(right['summary'])}"
        )

    samples = [
        sample(1, "summary", f"What is the main finding of '{rows[0]['title']}'?", first_sentence(rows[0]["summary"]), [rows[0]["paper_id"]]),
        sample(2, "summary", f"What is the main finding of '{rows[1]['title']}'?", first_sentence(rows[1]["summary"]), [rows[1]["paper_id"]]),
        sample(3, "authors", f"Who authored '{rows[2]['title']}'?", rows[2]["authors_joined"], [rows[2]["paper_id"]]),
        sample(4, "authors", f"Who authored '{rows[3]['title']}'?", rows[3]["authors_joined"], [rows[3]["paper_id"]]),
        sample(5, "date", f"When was '{rows[4]['title']}' published?", rows[4]["published"], [rows[4]["paper_id"]]),
        sample(6, "date", f"When was '{rows[5]['title']}' published?", rows[5]["published"], [rows[5]["paper_id"]]),
        sample(7, "category", f"What categories does '{rows[6]['title']}' belong to?", rows[6]["categories_joined"], [rows[6]["paper_id"]]),
        sample(8, "category", f"What categories does '{rows[7]['title']}' belong to?", rows[7]["categories_joined"], [rows[7]["paper_id"]]),
        sample(9, "multi_hop", f"How do '{rows[0]['title']}' and '{rows[1]['title']}' connect their research areas?", multi_hop_answer(rows[0], rows[1]), [rows[0]["paper_id"], rows[1]["paper_id"]]),
        sample(10, "multi_hop", f"How do '{rows[2]['title']}' and '{rows[3]['title']}' connect their research areas?", multi_hop_answer(rows[2], rows[3]), [rows[2]["paper_id"], rows[3]["paper_id"]]),
    ]
    write_json(Path(output_path), samples)
    return samples


def load_or_create_test_set(df: pd.DataFrame, output_path) -> BenchmarkTestSet:
    """Keep the benchmark stable across baseline, corrupted and repaired runs."""
    path = Path(output_path)
    if path.is_file():
        samples = read_json(path)
        valid_ids = set(df["paper_id"].astype(str))
        if isinstance(samples, list) and len(samples) == 10 and all(
            isinstance(item, dict)
            and str(item.get("ground_truth", "")).strip()
            and item.get("ground_truth_doc_ids")
            and set(item["ground_truth_doc_ids"]).issubset(valid_ids)
            for item in samples
        ) and {item.get("type") for item in samples} == {"summary", "authors", "date", "category", "multi_hop"}:
            return BenchmarkTestSet(samples)
    return BenchmarkTestSet(build_test_set(df, path))
