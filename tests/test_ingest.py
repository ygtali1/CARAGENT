import json
from pathlib import Path

import pytest
from pypdf import PdfWriter

from caragent.ingest import canonical_url, in_scope, parse_html, read_manifest
from caragent.models import Vehicle, components, split_text


def test_html_tables_keep_values_and_ignore_navigation():
    html = '''<div class="header">Navigation noise</div><div class="main"><h1>Oil inspection</h1>
    <button>Expand All</button><table><tr><td>Label</td><td>Test value</td></tr>
    <tr><td>Engine oil</td><td>Refer to the correct vehicle manual</td></tr></table>
    <p>This is a synthetic extraction fixture.</p><img src="diagram.png"></div>'''
    page, _ = parse_html(html, "https://lemon-manuals.la/Toyota/2024/Corolla%20LE/test/")
    assert "Label | Test value" in page.text
    assert "Navigation noise" not in page.text and "Expand All" not in page.text
    assert page.images[0].endswith("/test/diagram.png")


def test_directory_is_not_a_manual():
    page, links = parse_html('<div class="main"><h1>Index</h1><ul><li><a href="Oil/">Oil</a></li></ul></div>',
                             "https://lemon-manuals.la/Toyota/2024/Corolla%20LE/")
    assert page is None and links[0].endswith("/Oil/")


def test_crawler_scope_does_not_escape_toyota_variant():
    root = "https://lemon-manuals.la/Toyota/2024/Corolla%20LE/"
    assert in_scope(root + "Oil/#test", root)
    assert not in_scope("https://lemon-manuals.la/Honda/2024/", root)
    assert not in_scope("https://evil.test/Toyota/2024/Corolla%20LE/", root)
    assert not in_scope("http://lemon-manuals.la/Toyota/2024/Corolla%20LE/", root)
    assert not in_scope("https://lemon-manuals.la/Toyota/2024/Corolla%20LEX/", root)
    assert not in_scope(root + "%2e%2e/%2e%2e/%2e%2e/Honda/", root)
    assert canonical_url(root + "Oil/#one") == canonical_url(root + "Oil/#two")


def test_chunking_covers_text_without_crossing_pages():
    text = " ".join(f"token{i}" for i in range(1000))
    chunks = split_text(text, 300, 50)
    assert all(len(c) <= 300 for c in chunks)
    assert chunks[0].startswith("token0") and chunks[-1].endswith("token999")
    assert all(f"token{i}" in " ".join(chunks) for i in range(1000))
    with pytest.raises(ValueError):
        split_text(text, 300, 300)


def test_vehicle_metadata_and_stable_identity():
    with pytest.raises(ValueError):
        Vehicle("Civic", 2024, "US", "Honda")
    assert Vehicle("Corolla LE", 2024, "US").id != Vehicle("Corolla LE", 2023, "US").id
    assert Vehicle("Corolla LE", 2024, "US").id != Vehicle("Corolla LE", 2024, "TR").id
    assert components("oilskin motorbike") == []
    assert "engine_oil" in components("Check engine oil")


def test_manifest_rejects_duplicate_pages_before_graph_write(tmp_path):
    example = json.loads(Path("data/examples/manifest.json").read_text(encoding="utf-8"))
    example["manuals"][0]["pages"][1]["number"] = 1
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(example), encoding="utf-8")
    with pytest.raises(ValueError, match="benzersiz"):
        read_manifest(path)


def test_image_only_pdf_requires_ocr(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(tmp_path / "scan.pdf")
    example = json.loads(Path("data/examples/manifest.json").read_text(encoding="utf-8"))
    item = example["manuals"][0]
    del item["pages"]
    item["file"] = "scan.pdf"
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(example), encoding="utf-8")
    with pytest.raises(ValueError):
        read_manifest(path)
