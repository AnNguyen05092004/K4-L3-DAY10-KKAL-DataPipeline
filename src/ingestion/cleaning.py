from __future__ import annotations

from datetime import datetime
import html
import re

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(value: object) -> str:
    text = html.unescape(str(value or ""))
    return normalize_whitespace(_TAG_RE.sub(" ", text))


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed."""
    df = pd.DataFrame(r.__dict__ for r in records)
    if df.empty:
        return df

    df["paper_id"] = df["paper_id"].map(_clean_text)
    df["title"] = df["title"].map(_clean_text)
    df["summary"] = df["summary"].map(_clean_text)
    df["authors"] = df["authors"].apply(lambda values: [_clean_text(item) for item in values if _clean_text(item)])
    df["categories"] = df["categories"].apply(lambda values: [_clean_text(item) for item in values if _clean_text(item)])
    df["primary_category"] = df["primary_category"].map(_clean_text)
    df = df.drop_duplicates(subset="paper_id").reset_index(drop=True)

    df["published"] = pd.to_datetime(df["published"], errors="coerce", utc=True)
    df = df.dropna(subset=["published"])
    df = df[(df["paper_id"] != "") & (df["title"] != "") & (df["summary"] != "")]
    df["age_days"] = (run_date - df["published"]).dt.days
    df["published"] = df["published"].dt.strftime("%Y-%m-%d")

    df["authors_joined"] = df["authors"].apply(lambda a: ", ".join(a))
    df["categories_joined"] = df.apply(
        lambda row: ", ".join(row["categories"])
        if row["categories"]
        else (row["primary_category"] or "Uncategorized"),
        axis=1,
    )
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

    return df.sort_values("published", ascending=False).reset_index(drop=True)
