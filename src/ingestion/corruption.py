from __future__ import annotations

import json
from datetime import timedelta

import pandas as pd

_NOISE = " ###GARBAGE### %%%$$$ "


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate 6 dang data corruption tren clean dataframe, ghi log chi tiet."""
    df = df.sort_values("published", ascending=False).reset_index(drop=True)
    rows_before = len(df)
    log: dict[str, dict] = {}

    # 1. Drop latest records (mat 20% ban ghi moi nhat).
    n_drop = max(1, round(len(df) * 0.2))
    dropped_ids = df.loc[: n_drop - 1, "paper_id"].tolist()
    df = df.drop(index=range(n_drop)).reset_index(drop=True)
    log["drop_latest_records"] = {"count": n_drop, "paper_ids": dropped_ids}

    # 2. Blank summary tren mot so dong.
    n_blank = max(1, round(len(df) * 0.2))
    blank_idx = df.index[:n_blank]
    blank_ids = df.loc[blank_idx, "paper_id"].tolist()
    df.loc[blank_idx, "summary"] = ""
    log["blank_summary"] = {"count": n_blank, "paper_ids": blank_ids}

    # 3. Inject noise vao summary.
    n_noise = max(1, round(len(df) * 0.2))
    noise_idx = df.index[n_blank : n_blank + n_noise]
    noise_ids = df.loc[noise_idx, "paper_id"].tolist()
    df.loc[noise_idx, "summary"] = df.loc[noise_idx, "summary"] + _NOISE
    log["inject_noise"] = {"count": len(noise_idx), "paper_ids": noise_ids}

    # 4. Truncate title < 8 ky tu.
    n_trunc = max(1, round(len(df) * 0.2))
    trunc_idx = df.index[-n_trunc:]
    trunc_ids = df.loc[trunc_idx, "paper_id"].tolist()
    df.loc[trunc_idx, "title"] = df.loc[trunc_idx, "title"].str.slice(0, 7)
    log["truncate_title"] = {"count": n_trunc, "paper_ids": trunc_ids}

    # 5. Stale date (lui published ve qua khu).
    n_stale = max(1, round(len(df) * 0.2))
    stale_idx = df.index[:n_stale]
    stale_ids = df.loc[stale_idx, "paper_id"].tolist()
    stale_dates = pd.to_datetime(df.loc[stale_idx, "published"]) - timedelta(days=3650)
    df.loc[stale_idx, "published"] = stale_dates.dt.strftime("%Y-%m-%d")
    df.loc[stale_idx, "age_days"] = df.loc[stale_idx, "age_days"] + 3650
    log["stale_date"] = {"count": n_stale, "paper_ids": stale_ids}

    # 6. Duplicate rows.
    n_dup = max(1, round(len(df) * 0.2))
    dup_rows = df.iloc[:n_dup]
    dup_ids = dup_rows["paper_id"].tolist()
    df = pd.concat([df, dup_rows], ignore_index=True)
    log["duplicate_rows"] = {"count": n_dup, "paper_ids": dup_ids}

    # Rebuild text_for_embedding sau moi thay doi.
    df["text_for_embedding"] = (
        df["title"] + ". " + df["summary"] + " Authors: " + df["authors_joined"] +
        ". Categories: " + df["categories_joined"] + "."
    )

    log["summary"] = {"rows_before": rows_before, "rows_after": len(df)}

    output_log_path.parent.mkdir(parents=True, exist_ok=True)
    output_log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    return df.reset_index(drop=True)
