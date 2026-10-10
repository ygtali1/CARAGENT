from dataclasses import replace

import pytest

from caragent.models import (ChunkingConfig, Manual, Page, Vehicle,
                             chunks_for_manual, normalize, split_text)
from caragent.graph import GraphStore


def fixture_manual(pages=None):
    vehicle = Vehicle("  Corolla   LE ", 2024, " US / Canada ")
    return Manual(
        " corolla-owner ",
        " Toyota   Owner Manual ",
        vehicle,
        "EN",
        "https://example.test/manual",
        pages or (Page(1, "Engine oil inspection instructions.", " Engine oil ",
                       "https://example.test/manual/1"),),
    )


def test_models_normalize_fields_and_validate_required_data():
    manual = fixture_manual()
    assert manual.key == "corolla-owner"
    assert manual.title == "Toyota Owner Manual"
    assert manual.language == "en"
    assert manual.vehicle.model == "Corolla LE"
    assert manual.vehicle.market == "US / Canada"
    with pytest.raises(ValueError, match="Sayfa metni"):
        Page(1, "  \n  ")
    with pytest.raises(ValueError, match="sayfa numaraları"):
        fixture_manual((Page(1, "one"), Page(1, "two")))
    with pytest.raises(TypeError, match="Model yılı"):
        Vehicle("Corolla", "2024", "US")


def test_empty_short_and_repeated_text_are_handled_predictably():
    assert split_text("") == []
    assert split_text("Short English text.") == ["Short English text."]
    assert normalize("Başlık\nBaşlık\n\nİçerik") == "Başlık\n\nİçerik"


def test_long_text_is_bounded_and_has_no_content_loss():
    text = " ".join(f"unique{i}" for i in range(500))
    chunks = split_text(text, size=180, overlap=30)
    combined = " ".join(chunks)
    assert len(chunks) > 10
    assert all(len(chunk) <= 180 for chunk in chunks)
    assert all(f"unique{i}" in combined for i in range(500))


def test_paragraph_heading_and_procedure_boundaries_are_preferred():
    text = (
        "ENGINE OIL INSPECTION\n\n"
        + "Overview information " * 6
        + "\n\nPROCEDURE\n\n"
        + "1. Park the vehicle safely. " * 6
        + "\n\n2. Check the indicated level. " * 6
    )
    chunks = split_text(text, size=180, overlap=25)
    assert chunks[0].startswith("ENGINE OIL INSPECTION")
    assert any("PROCEDURE" in chunk for chunk in chunks)
    assert any(chunk.rstrip().endswith("safely.") for chunk in chunks)
    assert all(len(chunk) <= 180 for chunk in chunks)
    without_overlap = split_text(text, size=180, overlap=0)
    assert any(chunk.startswith("PROCEDURE") for chunk in without_overlap)


def test_overlap_is_bounded_and_preserves_shared_context():
    chunks = split_text(" ".join(f"word{i}" for i in range(160)), size=140, overlap=35)
    for left, right in zip(chunks, chunks[1:]):
        shared = max((length for length in range(1, min(35, len(left), len(right)) + 1)
                      if left[-length:] == right[:length]), default=0)
        assert 0 < shared <= 35


@pytest.mark.parametrize("text", [
    "Motor yağı seviyesini kontrol edin. Aracı düz zemine park edin.",
    "Check the engine oil level. Park the vehicle on level ground.",
])
def test_turkish_and_english_text_are_deterministic(text):
    assert split_text(text, 100, 15) == split_text(text, 100, 15)


def test_chunks_keep_manual_page_vehicle_source_and_order_metadata():
    pages = (
        Page(2, "Second page content. " * 12, "Second", "https://example.test/p2"),
        Page(1, "First page content. " * 12, "First", "https://example.test/p1"),
    )
    manual = fixture_manual(pages)
    config = ChunkingConfig(size=120, overlap=20)
    chunks = chunks_for_manual(manual, config)
    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))
    assert chunks[0].page_number == 1 and chunks[0].page_ordinal == 0
    first_page_two = next(chunk for chunk in chunks if chunk.page_number == 2)
    assert first_page_two.page_ordinal == 0
    assert chunks[0].manual_id == manual.id
    assert chunks[0].page_id and chunks[0].vehicle_id == manual.vehicle.id
    assert chunks[0].vehicle_model == "Corolla LE" and chunks[0].vehicle_year == 2024
    assert chunks[0].source == "https://example.test/p1" and chunks[0].title == "First"
    assert chunks == chunks_for_manual(manual, config)
    assert chunks[0].id != chunks_for_manual(manual, replace(config, size=140))[0].id
    assert manual.content_hash_for(config) != manual.content_hash_for(replace(config, size=140))


def test_invalid_chunk_settings_are_rejected():
    with pytest.raises(ValueError, match="en az 100"):
        ChunkingConfig(size=99, overlap=10)
    with pytest.raises(ValueError, match="boyuttan küçük"):
        ChunkingConfig(size=100, overlap=100)


def test_graph_ingest_consumes_configured_chunks_without_changing_schema():
    captured = {}

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute_write(self, function, manual, pages, chunks, content_hash):
            captured.update(manual=manual, pages=pages, chunks=chunks,
                            content_hash=content_hash, function=function)
            return {"status": "captured", "chunks": len(chunks)}

    class Driver:
        def session(self, **kwargs):
            return Session()

    store = object.__new__(GraphStore)
    store.driver = Driver()
    store.settings = type("Settings", (), {"database": "neo4j"})()
    manual = fixture_manual((Page(1, "First page evidence. " * 20),
                             Page(2, "Second page evidence. " * 20)))
    config = ChunkingConfig(size=120, overlap=20)
    result = store.ingest(manual, config)
    assert result["status"] == "captured" and result["chunks"] > 2
    assert captured["content_hash"] == manual.content_hash_for(config)
    assert captured["chunks"][0]["previous"] is None
    page_two = next(row for row in captured["chunks"]
                    if row["page_id"] == captured["pages"][1]["id"])
    assert page_two["previous"] is None
