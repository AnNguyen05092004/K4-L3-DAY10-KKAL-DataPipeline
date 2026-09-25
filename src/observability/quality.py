from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import great_expectations as gx
from great_expectations import expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Validate a cleaned paper dataframe with the Great Expectations 1.x API."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    required_columns = {
        "paper_id",
        "title",
        "summary",
        "text_for_embedding",
        "published",
        "age_days",
    }
    missing_columns = sorted(required_columns.difference(df.columns))
    if missing_columns:
        payload = {
            "report_name": report_name,
            "success": False,
            "gx_success": False,
            "missing_columns": missing_columns,
            "expectations": [],
            "freshness": None,
        }
        write_json(settings.paths.quality_dir / f"{report_name}_quality_report.json", payload)
        return payload

    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    expectations = [
        gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        gxe.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gxe.ExpectColumnValuesToNotBeNull(column="title"),
        gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        gxe.ExpectColumnValuesToBeUnique(column="paper_id"),
        gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]

    results: list[dict[str, Any]] = []
    for expectation in expectations:
        validation = batch.validate(expectation)
        validation_json = validation.to_json_dict()
        config = validation_json.get("expectation_config", {})
        results.append(
            {
                "expectation_type": config.get("type", expectation.__class__.__name__),
                "success": bool(validation.success),
                "kwargs": config.get("kwargs", {}),
                "result": validation_json.get("result", {}),
                "exception_info": validation_json.get("exception_info", {}),
            }
        )

    freshness_path = settings.paths.quality_dir / f"{report_name}_freshness_report.json"
    freshness = build_freshness_report(df, settings, freshness_path)
    gx_success = all(item["success"] for item in results)
    overall_success = gx_success and freshness["is_fresh"]
    payload = {
        "report_name": report_name,
        "success": overall_success,
        "gx_success": gx_success,
        "expectation_count": len(results),
        "expectations": results,
        "freshness": freshness,
    }
    write_json(settings.paths.quality_dir / f"{report_name}_quality_report.json", payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Report whether at most 25% of papers exceed the freshness SLA."""
    total_rows = int(len(df))
    if "age_days" in df.columns:
        age_days = pd.to_numeric(df["age_days"], errors="coerce")
    elif "published" in df.columns:
        published_for_age = pd.to_datetime(df["published"], errors="coerce", utc=True)
        age_days = (pd.Timestamp(datetime.now(UTC)) - published_for_age).dt.days
    else:
        age_days = pd.Series(index=df.index, dtype="float64")

    stale_mask = age_days > settings.freshness_threshold_days
    stale_rows = int(stale_mask.fillna(False).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 1.0
    published_values = df["published"] if "published" in df.columns else pd.Series(index=df.index, dtype="object")
    published = pd.to_datetime(published_values, errors="coerce", utc=True)
    valid_published = published.dropna()
    latest = valid_published.max().date().isoformat() if not valid_published.empty else None
    oldest = valid_published.min().date().isoformat() if not valid_published.empty else None

    payload = {
        "checked_at": datetime.now(UTC).isoformat(),
        "threshold_days": settings.freshness_threshold_days,
        "maximum_stale_ratio": 0.25,
        "latest_published": latest,
        "oldest_published": oldest,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "is_fresh": total_rows > 0 and stale_ratio <= 0.25,
    }
    write_json(Path(report_path), payload)
    return payload
