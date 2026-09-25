from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

_NOISE = " ###GARBAGE### %%%$$$ "


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Apply six deterministic corruption scenarios and write an audit log."""
    required = {
        "paper_id", "title", "summary", "published", "age_days",
        "authors_joined", "categories_joined", "text_for_embedding",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Clean dataframe is missing columns: {', '.join(missing)}")
    if len(df) < 5:
        raise ValueError("At least five rows are required for the corruption suite.")

    df = df.copy(deep=True).sort_values("published", ascending=False).reset_index(drop=True)
    rows_before = len(df)
    log: dict[str, dict] = {}

    # 1. Drop latest records (mat 20% ban ghi moi nhat).
    n_drop = max(1, round(len(df) * 0.2))
    dropped_ids = df.loc[: n_drop - 1, "paper_id"].tolist()
    df = df.drop(index=range(n_drop)).reset_index(drop=True)
    log["drop_latest_records"] = {
        "count": n_drop,
        "fraction": 0.2,
        "paper_ids": dropped_ids,
        "description": "Removed the newest papers before indexing.",
    }

    # 2. Blank summary tren mot so dong.
    n_blank = max(1, round(len(df) * 0.25))
    ranked_idx = df.sort_values("paper_id").index
    blank_idx = ranked_idx[:n_blank]
    blank_ids = df.loc[blank_idx, "paper_id"].tolist()
    df.loc[blank_idx, "summary"] = ""
    log["blank_summary"] = {
        "count": n_blank,
        "paper_ids": blank_ids,
        "description": "Replaced selected summaries with empty strings.",
    }

    # 3. Chon cac dong se bi chen noise truc tiep vao text_for_embedding.
    n_noise = max(1, round(len(df) * 0.2))
    noise_idx = ranked_idx[n_blank : n_blank + n_noise]
    noise_ids = df.loc[noise_idx, "paper_id"].tolist()
    log["inject_text_noise"] = {
        "count": len(noise_idx),
        "paper_ids": noise_ids,
        "noise": _NOISE.strip(),
        "description": "Injected meaningless tokens into text_for_embedding.",
    }

    # 4. Truncate title < 8 ky tu.
    n_trunc = n_blank
    trunc_idx = blank_idx
    trunc_ids = df.loc[trunc_idx, "paper_id"].tolist()
    df.loc[trunc_idx, "title"] = df.loc[trunc_idx, "title"].str.slice(0, 7)
    log["truncate_title"] = {
        "count": n_trunc,
        "max_characters": 7,
        "paper_ids": trunc_ids,
        "description": "Truncated selected titles to fewer than ten characters.",
    }

    # 5. Stale date (lui published ve qua khu).
    n_stale = max(1, round(len(df) * 0.2))
    stale_idx = df.index[:n_stale]
    stale_ids = df.loc[stale_idx, "paper_id"].tolist()
    original_dates = pd.to_datetime(df.loc[stale_idx, "published"])
    stale_dates = original_dates - pd.DateOffset(years=5)
    df.loc[stale_idx, "published"] = stale_dates.dt.strftime("%Y-%m-%d")
    added_days = (original_dates - stale_dates).dt.days.to_numpy()
    df.loc[stale_idx, "age_days"] = pd.to_numeric(df.loc[stale_idx, "age_days"]) + added_days
    log["stale_date"] = {
        "count": n_stale,
        "years_shifted": 5,
        "paper_ids": stale_ids,
        "description": "Shifted selected publication dates five years into the past.",
    }

    # Rebuild embedding text after blanking summaries and truncating titles,
    # then inject noise into the chosen rows.
    df["summary_chars"] = df["summary"].str.len()
    df["text_for_embedding"] = df.apply(
        lambda row: (
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {row['summary']}"
        ),
        axis=1,
    )
    df.loc[noise_idx, "text_for_embedding"] = df.loc[noise_idx, "text_for_embedding"] + _NOISE

    # 6. Duplicate rows.
    n_dup = n_drop
    dup_rows = df.iloc[:n_dup].copy()
    dup_ids = dup_rows["paper_id"].tolist()
    df = pd.concat([df, dup_rows], ignore_index=True)
    log["duplicate_rows"] = {
        "count": n_dup,
        "paper_ids": dup_ids,
        "description": "Appended duplicate records while preserving the original row count after the drop scenario.",
    }

    log["summary"] = {
        "scenario_count": 6,
        "rows_before": rows_before,
        "rows_after": len(df),
        "unique_paper_ids_after": int(df["paper_id"].nunique()),
    }

    log_path = Path(output_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return df.reset_index(drop=True)
