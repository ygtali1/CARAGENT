"""Chunking acceptance tests grouped by CAR acceptance criteria."""
import json
import random
import time

import pytest

from caragent.cli import main
from caragent.ingest import parse_html, read_manifest
from caragent.models import (ChunkingConfig, Manual, Page, Vehicle, chunks_for_manual,
                             normalize, split_text)

HEADER = "Description | Part Tightened | N*m | kgf*cm"
WORDS = ("engine", "oil", "brake", "fluid", "motor", "yağı", "fren", "lastik", "basıncı",
         "İnceleme", "ışık", "Çalıştırma", "Ölçüm", "Güvenlik", "torque", "bolt")


def random_document(rng: random.Random) -> str:
    blocks = []
    for _ in range(rng.randint(3, 9)):
        kind = rng.choice(("heading", "prose", "steps", "table"))
        if kind == "heading":
            blocks.append(" ".join(rng.choice(WORDS) for _ in range(3)).upper())
        elif kind == "prose":
            sentences = (" ".join(rng.choice(WORDS) for _ in range(rng.randint(4, 14))).capitalize() + "."
                         for _ in range(rng.randint(1, 8)))
            blocks.append(" ".join(sentences))
        elif kind == "steps":
            blocks.append("\n".join(f"{n}. {' '.join(rng.choice(WORDS) for _ in range(6))}."
                                    for n in range(1, rng.randint(2, 7))))
        else:
            group = rng.choice(WORDS).upper()
            rows = [f"{group} | {rng.choice(WORDS)} x {rng.choice(WORDS)} (Bolt {i}) | "
                    f"{rng.randint(3, 90)}.{rng.randint(0, 9)} N*m | {rng.randint(30, 900)} kgf*cm"
                    for i in range(rng.randint(2, 25))]
            blocks.append(HEADER + "\n" + "\n".join(rows))
    return "\n\n".join(blocks)


def locate(text: str, chunks: list[str]) -> list[tuple[int, int]]:
    """Map each chunk back to its source span; a repeated table header is the only allowed addition."""
    spans, floor = [], 0
    for chunk in chunks:
        body = chunk
        position = text.find(body, floor)
        if position < 0 and chunk.startswith(HEADER + "\n"):
            body = chunk[len(HEADER) + 1:]
            position = text.find(body, floor)
        assert position >= 0, f"chunk is not traceable to the source text: {chunk[:80]!r}"
        spans.append((position, position + len(body)))
        floor = position + 1
    return spans


def fixture_manual(*pages: Page) -> Manual:
    return Manual("torque-manual", "Torque Specifications", Vehicle("Corolla LE", 2024, "US"),
                  "en", "https://example.test/manual", pages)


# İçerik kaybı yok, boyut sınırı, sıra, izlenebilirlik (property-based, seed sabit)
@pytest.mark.parametrize("seed", range(40))
@pytest.mark.parametrize("size,overlap", [(120, 0), (200, 30), (400, 120), (1000, 150), (300, 299)])
def test_random_documents_lose_no_content_and_keep_order(seed, size, overlap):
    text = normalize(random_document(random.Random(seed)))
    chunks = split_text(text, size, overlap)
    assert chunks and all(0 < len(chunk) <= size for chunk in chunks)
    spans = locate(text, chunks)
    assert [start for start, _ in spans] == sorted(start for start, _ in spans)
    covered = [False] * len(text)
    for start, end in spans:
        covered[start:end] = [True] * (end - start)
    assert all(covered[i] for i, character in enumerate(text) if not character.isspace())


@pytest.mark.parametrize("seed", range(20))
def test_table_rows_are_never_cut_in_random_documents(seed):
    text = normalize(random_document(random.Random(seed)))
    rows = {line for line in text.splitlines() if "|" in line}
    for chunk in split_text(text, 300, 80):
        assert all(line in rows for line in chunk.splitlines() if "|" in line)


@pytest.mark.parametrize("strategy,size,overlap", [("token", 20, 5), ("paragraph", 3, 1)])
@pytest.mark.parametrize("seed", range(10))
def test_token_and_paragraph_strategies_lose_no_content(strategy, size, overlap, seed):
    text = normalize(random_document(random.Random(seed)))
    chunks = split_text(text, size, overlap, strategy)
    unit = str.split if strategy == "token" else str.splitlines
    source = [part for part in unit(text) if part.strip()]
    produced = {part for chunk in chunks for part in unit(chunk)}
    assert set(source) <= produced


# Sınır durumları ve geçersiz girdiler
@pytest.mark.parametrize("text", ["", "   ", "\n\n\n", "\t \r\n \t"])
def test_blank_inputs_produce_no_chunks(text):
    assert split_text(text) == []


@pytest.mark.parametrize("value", [None, 42, b"bytes", ["list"]])
def test_non_string_input_is_rejected(value):
    with pytest.raises(TypeError):
        split_text(value)


@pytest.mark.parametrize("kwargs,message", [
    ({"size": True}, "en az"), ({"size": 150.5}, "en az"), ({"size": 99}, "en az 100"),
    ({"overlap": -1}, "boyuttan küçük"), ({"overlap": 1000}, "boyuttan küçük"),
    ({"strategy": "sentence"}, "Chunklama"), ({"strategy": "token", "size": 19, "overlap": 0}, "en az 20"),
])
def test_invalid_chunk_settings_are_rejected_with_clear_errors(kwargs, message):
    with pytest.raises(ValueError, match=message):
        ChunkingConfig(**kwargs)


def test_text_exactly_at_size_is_one_chunk_and_one_more_character_splits():
    text = ("word " * 40)[:200].strip()
    text = text + "x" * (200 - len(text))
    assert split_text(text, 200, 20) == [text]
    assert len(split_text(text + " y", 200, 20)) == 2


def test_unbreakable_token_longer_than_size_is_cut_without_loss():
    token = "A" * 1050
    chunks = split_text(token, 100, 10)
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert "".join(chunk[:-10] if i < len(chunks) - 1 else chunk
                   for i, chunk in enumerate(chunks)) == token


def test_table_row_longer_than_size_terminates_and_keeps_content():
    row = "AIR CONDITIONING UNIT | " + "very long part description " * 20 + "| 25 N*m"
    text = HEADER + "\n" + row + "\n" + row.replace("25", "31")
    chunks = split_text(text, 200, 40)
    assert all(len(chunk) <= 200 for chunk in chunks)
    combined = " ".join(chunks)
    assert "25 N*m" in combined and "31 N*m" in combined


def test_oversized_header_is_not_repeated_but_content_is_kept():
    header = "Description | " + " | ".join(f"Column {letter * 3}" for letter in "ABCDEFGHIJKLMNOP")
    assert 150 < len(header) < 300
    rows = [f"ROW {i} | value {i}" for i in range(40)]
    chunks = split_text(header + "\n" + "\n".join(rows), 300, 0)
    assert all(len(chunk) <= 300 for chunk in chunks)
    assert sum(chunk.count(header) for chunk in chunks) == 1
    assert all(row in "\n".join(chunks) for row in rows)


@pytest.mark.parametrize("raw,expected", [
    ("Line one\r\nLine two", "Line one\nLine two"),
    ("ﬁlter  change\t\tnow", "filter change now"),
    ("Ｅｎｇｉｎｅ ｏｉｌ", "Engine oil"),
])
def test_line_endings_whitespace_and_unicode_forms_are_normalized(raw, expected):
    assert split_text(raw) == [expected]


def test_turkish_characters_and_case_are_preserved_exactly():
    text = "İĞÜŞÖÇ ığüşöç: Motor yağı seviyesini ölçün. Iğdır'da ısınma ışığı yanarsa durun."
    assert split_text(text, 100, 10) == [text]
    long_text = " ".join([text] * 20)
    combined = " ".join(split_text(long_text, 150, 30))
    for character in "İĞÜŞÖÇığüşöç":
        assert character in combined


def test_numbered_steps_are_not_split_inside_a_step():
    steps = [f"{n}. Remove bolt {n} and keep the washer for reassembly later." for n in range(1, 25)]
    for chunk in split_text("\n".join(steps), 250, 60):
        assert all(line in steps for line in chunk.splitlines())


# Kaynak izlenebilirliği
def test_every_chunk_is_grounded_in_its_own_page_with_matching_source():
    rng = random.Random(7)
    pages = tuple(Page(n, random_document(rng), f"Page {n}", f"https://example.test/p{n}")
                  for n in (3, 1, 2))
    manual = fixture_manual(*pages)
    chunks = chunks_for_manual(manual, ChunkingConfig(size=300, overlap=60))
    by_number = {page.number: page for page in manual.pages}
    for chunk in chunks:
        page = by_number[chunk.page_number]
        locate(page.text, [chunk.text])
        assert (chunk.source, chunk.title) == (page.url, page.title)
        assert chunk.manual_id == manual.id and chunk.vehicle_id == manual.vehicle.id
    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))
    assert [chunk.page_number for chunk in chunks] == sorted(chunk.page_number for chunk in chunks)
    assert len({chunk.id for chunk in chunks}) == len(chunks)
    for number in by_number:
        ordinals = [chunk.page_ordinal for chunk in chunks if chunk.page_number == number]
        assert ordinals == list(range(len(ordinals)))


def test_page_without_url_falls_back_to_manual_source_and_title():
    chunk = chunks_for_manual(fixture_manual(Page(1, "Check the brake fluid level.")))[0]
    assert chunk.source == "https://example.test/manual"
    assert chunk.title == "Torque Specifications"


# Deterministik sonuçlar
def test_same_input_from_a_fresh_manifest_round_trip_gives_identical_chunks(tmp_path):
    text = random_document(random.Random(3))
    manifest = {"schema_version": 1, "manuals": [{
        "key": "k", "title": "T", "language": "en", "source": "https://example.test",
        "vehicle": {"model": "Corolla LE", "year": 2024, "market": "US"},
        "pages": [{"number": 1, "text": text, "title": "T", "url": "https://example.test/1"}],
    }]}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    config = ChunkingConfig(size=250, overlap=40)
    first = chunks_for_manual(read_manifest(path)[0], config)
    second = chunks_for_manual(read_manifest(path)[0], config)
    assert first == second
    changed = chunks_for_manual(read_manifest(path)[0], ChunkingConfig(size=250, overlap=41))
    assert {chunk.id for chunk in first}.isdisjoint(chunk.id for chunk in changed)


# Yapılandırılabilirlik (CLI)
def test_cli_chunk_command_applies_configured_size_and_overlap(tmp_path, capsys):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "manuals": [{
        "key": "k", "title": "T", "language": "en", "source": "https://example.test",
        "vehicle": {"model": "Corolla LE", "year": 2024, "market": "US"},
        "pages": [{"number": 1, "text": random_document(random.Random(1)), "url": "https://example.test/1"}],
    }]}), encoding="utf-8")
    output = tmp_path / "chunks.json"
    assert main(["chunk", str(manifest), "--output", str(output),
                 "--chunk-size", "300", "--chunk-overlap", "40"]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["chunking"] == {"strategy": "character", "size": 300, "overlap": 40}
    assert payload["summary"]["chunks"] == len(payload["chunks"]) > 1
    assert all(len(chunk["text"]) <= 300 for chunk in payload["chunks"])


# Mevcut ingest akışı: HTML -> Page -> Manual -> Chunk (uçtan uca, ağ yok)
LEMON_LIKE_HTML = """<div class="main"><h1>Torque Specifications [11/2022 - ]</h1><table>
<thead><tr><th>Description</th><th colspan="4">Part Tightened</th><th>N*m</th><th>kgf*cm</th></tr></thead>
<tr><td rowspan="12">AIR CONDITIONING UNIT</td><td colspan="4">Panel reinforcement x Body (Bolt A)</td><td>25 N*m</td><td>255 kgf*cm</td></tr>
""" + "".join(f'<tr><td colspan="4">Panel brace {i} x Reinforcement assembly</td><td>{i + 5} N*m</td><td>{i + 60} kgf*cm</td></tr>\n'
              for i in range(11)) + """
<tr><td rowspan="2">COMPRESSOR</td><td colspan="4">Compressor x Engine</td><td>25 N*m</td><td>255 kgf*cm</td></tr>
<tr><td colspan="4">Discharge hose x Compressor</td><td>9.8 N*m</td><td>100 kgf*cm</td></tr>
</table></div>"""


def test_lemon_like_table_flows_through_ingest_into_self_contained_chunks():
    page, _ = parse_html(LEMON_LIKE_HTML, "https://lemon-manuals.la/Toyota/2024/Corolla%20LE/torque/")
    manual = fixture_manual(page)
    chunks = chunks_for_manual(manual, ChunkingConfig(size=300, overlap=80))
    assert len(chunks) > 2
    header = "Description | Part Tightened | N*m | kgf*cm"
    for chunk in chunks:
        lines = chunk.text.splitlines()
        assert lines[0] == header
        assert all(line.startswith(("AIR CONDITIONING UNIT | ", "COMPRESSOR | ")) for line in lines[1:])
    compressor = [c for c in chunks if "Discharge hose x Compressor" in c.text]
    assert compressor and "COMPRESSOR | Discharge hose x Compressor | 9.8 N*m" in compressor[0].text


# Performans (karesel yavaşlamaya karşı duman testi)
def test_large_page_is_chunked_quickly():
    text = "\n\n".join(random_document(random.Random(seed)) for seed in range(250))
    started = time.perf_counter()
    chunks = split_text(text, 1000, 150)
    assert time.perf_counter() - started < 5
    assert len(chunks) > 100
