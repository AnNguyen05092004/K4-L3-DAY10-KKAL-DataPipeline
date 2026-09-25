from __future__ import annotations

from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed."""
    df = pd.DataFrame(r.__dict__ for r in records)
    if df.empty:
        return df

    df["title"] = df["title"].str.strip()
    df["summary"] = df["summary"].str.strip()
    df = df.drop_duplicates(subset="paper_id").reset_index(drop=True)

    df["published"] = pd.to_datetime(df["published"], errors="coerce", utc=True)
    df = df.dropna(subset=["published", "title", "summary"])
    df["age_days"] = (run_date - df["published"]).dt.days
    df["published"] = df["published"].dt.strftime("%Y-%m-%d")

    df["authors_joined"] = df["authors"].apply(lambda a: ", ".join(a))
    df["categories_joined"] = df["categories"].apply(lambda c: ", ".join(c))
    df["summary_chars"] = df["summary"].str.len()
    df["text_for_embedding"] = (
        df["title"] + ". " + df["summary"] + " Authors: " + df["authors_joined"] +
        ". Categories: " + df["categories_joined"] + "."
    )

    return df.sort_values("published", ascending=False).reset_index(drop=True)
