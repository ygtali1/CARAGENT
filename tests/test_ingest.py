import json
import os
from pathlib import Path

import pytest
from pypdf import PdfWriter

import httpx

from caragent.ingest import (CrawlConfig, cache_is_fresh, canonical_url, in_scope,
                             is_crawlable_directory, parse_html, read_manifest,
                             request_with_retries)
from caragent.models import Manual, Page, Vehicle, components, resolve_chunking, split_text
from caragent.tuning import compare_chunking


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


def test_vehicle_root_covers_all_manual_sections_without_duplicate_export():
    root = "https://lemon-manuals.la/Toyota/2024/Corolla%20LE/"
    assert is_crawlable_directory(root + "Repair%20and%20Diagnosis/", root)
    assert is_crawlable_directory(root + "Labor%20Times/", root)
    assert not is_crawlable_directory(root + "Repair%20and%20Diagnosis%20%28Single%20Page%29/", root)
    assert not is_crawlable_directory("https://lemon-manuals.la/Toyota/2024/Camry/", root)


def test_unlimited_vehicle_crawl_parses_all_sections_and_marks_manifest_complete(monkeypatch, tmp_path):
    root = "https://lemon-manuals.la/Toyota/2024/Corolla%20LE/"
    pages = {
        root: '<div class="main"><h1>Corolla LE</h1><ul>'
              '<li><a href="Repair%20and%20Diagnosis/">Repair</a></li>'
              '<li><a href="Labor%20Times/">Labor</a></li>'
              '<li><a href="Repair%20and%20Diagnosis%20%28Single%20Page%29/">Duplicate</a></li>'
              '</ul></div>',
        root + "Repair%20and%20Diagnosis/": '<div class="main"><h1>Repair</h1><ul>'
              '<li><a href="Engine/">Engine</a></li></ul></div>',
        root + "Labor%20Times/": '<div class="main"><h1>Labor overview</h1>'
              '<div>Labor time overview contains useful text and also links to detailed sections.</div>'
              '<a href="Brakes/">Brakes</a></div>',
        root + "Repair%20and%20Diagnosis/Engine/": '<div class="main"><h1>Engine article</h1>'
              '<div>Engine oil inspection fixture with enough text to become a parsed manual page.</div></div>',
        root + "Labor%20Times/Brakes/": '<div class="main"><h1>Brake labor article</h1>'
              '<div>Brake labor time fixture with enough text to become another parsed manual page.</div></div>',
    }

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, timeout):
            request = httpx.Request("GET", url)
            if url.endswith("/robots.txt"):
                return httpx.Response(200, request=request,
                                      text="User-agent: *\nAllow: /",
                                      headers={"content-type": "text/plain"})
            return httpx.Response(200, request=request, text=pages[url],
                                  headers={"content-type": "text/html"})

    monkeypatch.setattr("caragent.ingest.ROOT", tmp_path)
    monkeypatch.setattr("caragent.ingest.httpx.Client", lambda **kwargs: Client())
    monkeypatch.setattr("caragent.ingest.time.sleep", lambda _: None)
    output_path = tmp_path / "processed" / "complete.json"
    from caragent.ingest import crawl_lemon
    report = crawl_lemon(root, max_pages=0, max_requests=0, delay=0.5, output=output_path)
    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["complete"] is True and report["articles"] == 3
    assert manifest["crawl"]["complete"] is True
    assert {manual["title"] for manual in manifest["manuals"]} == {
        "Engine article", "Labor overview", "Brake labor article"
    }


def test_chunking_covers_text_without_crossing_pages():
    text = " ".join(f"token{i}" for i in range(1000))
    chunks = split_text(text, 300, 50)
    assert all(len(c) <= 300 for c in chunks)
    assert chunks[0].startswith("token0") and chunks[-1].endswith("token999")
    assert all(f"token{i}" in " ".join(chunks) for i in range(1000))
    with pytest.raises(ValueError):
        split_text(text, 300, 300)


def test_character_token_and_paragraph_chunking_have_valid_overlap():
    token_text = " ".join(f"word{i}" for i in range(80))
    token_chunks = split_text(token_text, 20, 5, "token")
    assert len(token_chunks) > 3
    assert token_chunks[0].split()[-5:] == token_chunks[1].split()[:5]
    paragraph_text = "\n".join(f"Paragraph {i}" for i in range(8))
    paragraph_chunks = split_text(paragraph_text, 3, 1, "paragraph")
    assert len(paragraph_chunks) == 4
    assert paragraph_chunks[0].splitlines()[-1] == paragraph_chunks[1].splitlines()[0]
    assert resolve_chunking("token").size == 250
    with pytest.raises(ValueError, match="Chunklama"):
        resolve_chunking("sentence")


def test_cache_ttl_refresh_and_crawl_config_validation(tmp_path):
    cached = tmp_path / "page.html"
    cached.write_text("fixture", encoding="utf-8")
    os.utime(cached, (100, 100))
    assert cache_is_fresh(cached, 20, now=110)
    assert not cache_is_fresh(cached, 5, now=110)
    assert not cache_is_fresh(cached, 20, refresh=True, now=110)
    with pytest.raises(ValueError, match="eşzamanlı"):
        CrawlConfig(concurrency=17)


@pytest.mark.parametrize("retry_status", [429, 503])
def test_retry_uses_exponential_attempt_budget(monkeypatch, retry_status):
    calls = []

    class Client:
        def get(self, url, timeout):
            calls.append((url, timeout))
            request = httpx.Request("GET", url)
            status = retry_status if len(calls) < 3 else 200
            return httpx.Response(status, request=request, text="ok")

    monkeypatch.setattr("caragent.ingest.time.sleep", lambda _: None)
    response, attempts = request_with_retries(Client(), "https://example.test", 3, 2, 0.1)
    assert response.status_code == 200 and attempts == 3 and len(calls) == 3


def test_retry_does_not_repeat_permanent_client_error():
    class Client:
        calls = 0

        def get(self, url, timeout):
            self.calls += 1
            return httpx.Response(404, request=httpx.Request("GET", url))

    client = Client()
    with pytest.raises(httpx.HTTPStatusError) as caught:
        request_with_retries(client, "https://example.test/missing", 3, 2, 0)
    assert client.calls == 1 and caught.value.caragent_attempts == 1


def test_chunk_benchmark_compares_three_profiles_with_retrieval_proxy():
    manuals = read_manifest(Path("data/examples/manifest.json"))
    report = compare_chunking(manuals, [{"query": "engine oil", "expected_phrase": "engine oil"}])
    assert {row["profile"]["strategy"] for row in report["profiles"]} == {
        "character", "token", "paragraph"
    }
    assert all(row["recall_at_5"] == 1.0 for row in report["profiles"])


def test_chunk_benchmark_handles_small_medium_and_large_manuals():
    sentence = "Engine oil level inspection and tire pressure procedure.\nBattery precautions.\n"
    manuals = [Manual(name, name, Vehicle(name, 2024, "Synthetic"), "en", "",
                      (Page(1, sentence * multiplier),))
               for name, multiplier in (("small", 5), ("medium", 50), ("large", 500))]
    cases = [{"query": "engine oil level", "expected_phrase": "engine oil", "manual_key": name}
             for name in ("small", "medium", "large")]
    report = compare_chunking(manuals, cases)
    assert all(row["chunks"] >= 3 for row in report["profiles"])
    assert all(row["recall_at_5"] == 1.0 and row["mrr_at_5"] == 1.0
               for row in report["profiles"])


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
