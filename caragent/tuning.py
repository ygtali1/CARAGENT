"""Offline, repeatable chunk-setting comparison for CAR-5."""
from dataclasses import asdict
import re

from .models import CHUNK_DEFAULTS, Manual, split_text


BENCHMARK_PROFILES = tuple(CHUNK_DEFAULTS.values())


def _terms(text: str) -> set[str]:
    return {term.casefold() for term in re.findall(r"[^\W_]+", text) if len(term) > 1}


def _rank(query: str, chunks: list[dict]) -> list[dict]:
    query_terms = _terms(query)
    return sorted(chunks, key=lambda item: (
        len(query_terms & _terms(item["text"])),
        -len(item["text"]),
    ), reverse=True)


def compare_chunking(manuals: list[Manual], cases=None, profiles=BENCHMARK_PROFILES) -> dict:
    """Compare size/duplication and an optional lexical retrieval proxy at rank five.

    Cases contain query, expected_phrase and optionally manual_key. This intentionally
    measures chunk boundaries without requiring Neo4j or live network access.
    """
    cases = cases or []
    results = []
    source_characters = sum(len(page.text) for manual in manuals for page in manual.pages)
    for profile in profiles:
        chunks = []
        for manual in manuals:
            for page in manual.pages:
                for text in split_text(page.text, profile.size, profile.overlap, profile.strategy):
                    chunks.append({"manual_key": manual.key, "page": page.number, "text": text})
        total_chunk_characters = sum(len(item["text"]) for item in chunks)
        reciprocal_ranks = []
        hits = 0
        for case in cases:
            candidates = [item for item in chunks
                          if not case.get("manual_key") or item["manual_key"] == case["manual_key"]]
            ranked = _rank(case["query"], candidates)[:5]
            expected = case["expected_phrase"].casefold()
            rank = next((index for index, item in enumerate(ranked, 1)
                         if expected in item["text"].casefold()), None)
            if rank:
                hits += 1
                reciprocal_ranks.append(1 / rank)
            else:
                reciprocal_ranks.append(0)
        results.append({
            "profile": asdict(profile),
            "chunks": len(chunks),
            "source_characters": source_characters,
            "average_chunk_characters": round(total_chunk_characters / len(chunks), 2)
            if chunks else 0,
            "estimated_overlap_ratio": round(
                max(0, total_chunk_characters - source_characters) / total_chunk_characters, 4
            ) if total_chunk_characters else 0.0,
            "retrieval_cases": len(cases),
            "recall_at_5": round(hits / len(cases), 4) if cases else None,
            "mrr_at_5": round(sum(reciprocal_ranks) / len(cases), 4) if cases else None,
        })
    return {"schema_version": 1, "profiles": results,
            "notes": "Retrieval metrics are a deterministic lexical proxy; validate selected defaults with Neo4j retrieval."}
