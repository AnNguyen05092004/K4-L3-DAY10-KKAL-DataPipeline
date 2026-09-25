from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from core.config import Settings

CROSSREF_API_URL = "https://api.crossref.org/works"
_JATS_TAG_RE = re.compile(r"<[^>]+>")
_RETRY_STATUS_CODES = {429, 503}


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_abstract(raw: str | None) -> str:
    if not raw:
        return ""
    return _JATS_TAG_RE.sub("", raw).replace("\n", " ").strip()


def _date_from_parts(item: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        node = item.get(key)
        parts = (node or {}).get("date-parts")
        if parts and parts[0]:
            year, month, day = (list(parts[0]) + [1, 1])[:3]
            return f"{year:04d}-{month:02d}-{day:02d}"
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref `/works` payload thanh list PaperRecord, bo qua record thieu truong bat buoc."""
    items = (payload.get("message") or {}).get("items") or []
    records: list[PaperRecord] = []
    for item in items:
        doi = item.get("DOI")
        titles = item.get("title") or []
        summary = _clean_abstract(item.get("abstract"))
        if not doi or not titles or not summary:
            continue

        authors = [
            " ".join(part for part in (author.get("given"), author.get("family")) if part)
            for author in item.get("author") or []
            if author.get("family")
        ]
        categories = list(item.get("subject") or [])
        primary_category = categories[0] if categories else "Uncategorized"
        published = _date_from_parts(item, ("published", "published-print", "published-online", "issued"))
        updated = (item.get("indexed") or {}).get("date-time", "")[:10] or published
        url = item.get("URL", "")

        records.append(
            PaperRecord(
                paper_id=doi,
                title=titles[0].strip(),
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=url,
                pdf_url=url,
                comment=f"Crossref record {doi}",
            )
        )
    return records


def _call_crossref_api(settings: Settings, max_retries: int = 3) -> dict:
    params = {
        "query.bibliographic": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    delay = 1.0
    for attempt in range(max_retries):
        response = requests.get(CROSSREF_API_URL, params=params, timeout=30)
        if response.status_code in _RETRY_STATUS_CODES and attempt < max_retries - 1:
            time.sleep(delay)
            delay *= 2
            continue
        response.raise_for_status()
        return response.json()
    raise RuntimeError("Crossref API request failed after retries.")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref API, luu raw response + records; fallback ve snapshot local khi loi."""
    paths = settings.paths
    if not settings.refresh_source and paths.raw_records_json.exists():
        return load_raw_records(paths.raw_records_json)

    try:
        payload = _call_crossref_api(settings)
        paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
        paths.raw_api_response.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        records = parse_crossref_payload(payload)
        if not records:
            raise ValueError("Crossref payload yielded no valid records.")
    except Exception:
        if paths.raw_api_response.exists():
            payload = json.loads(paths.raw_api_response.read_text(encoding="utf-8"))
            records = parse_crossref_payload(payload)
        elif paths.raw_records_json.exists():
            return load_raw_records(paths.raw_records_json)
        else:
            raise

    paths.raw_records_json.parent.mkdir(parents=True, exist_ok=True)
    paths.raw_records_json.write_text(
        json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot (list dict) va map thanh `PaperRecord`."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [PaperRecord(**item) for item in data]
