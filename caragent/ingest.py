"""Read explicit Toyota manifests, PDFs and Lemon HTML without guessing metadata."""
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote, quote, urlunsplit
from urllib.robotparser import RobotFileParser
import json
import time
import posixpath

from bs4 import BeautifulSoup
import httpx
from pypdf import PdfReader

from .config import ROOT
from .models import Manual, Page, Vehicle, normalize, stable_id

DEFAULT_LEMON_URL = "https://lemon-manuals.la/Toyota/2024/Corolla%20LE/Repair%20and%20Diagnosis/"
USER_AGENT = "CARAGENT/0.1 (Toyota manual research; single-threaded)"


def canonical_url(url: str) -> str:
    p = urlsplit(url)
    decoded = unquote(p.path)
    normalized = posixpath.normpath(decoded)
    if decoded.endswith("/") and not normalized.endswith("/"):
        normalized += "/"
    path = quote(normalized, safe="/")
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, "", ""))


def in_scope(url: str, root: str) -> bool:
    p, r = urlsplit(canonical_url(url)), urlsplit(canonical_url(root))
    return p.scheme == "https" and p.netloc == r.netloc and p.path.startswith(r.path)


def parse_html(html: str, url: str) -> tuple[Page | None, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one(".main") or soup.select_one("main") or soup.select_one("article")
    if body is None:
        raise ValueError("Kılavuz içerik alanı bulunamadı: " + url)
    title_node = body.find("h1")
    title = title_node.get_text(" ", strip=True) if title_node else "Toyota manual"
    links = list(dict.fromkeys(canonical_url(urljoin(url, a["href"]))
                              for a in body.select("a[href]") if a["href"] and not a["href"].startswith("#")))
    images = tuple(dict.fromkeys(urljoin(url, img["src"]) for img in body.select("img[src]")))
    for tag in body.select("script, style, button, nav"):
        tag.decompose()
    # Flatten tables by row; preserve the association between labels and values.
    for table in body.find_all("table"):
        rows = [" | ".join(cell.get_text(" ", strip=True)
                           for cell in row.find_all(["th", "td"], recursive=False))
                for row in table.find_all("tr")]
        table.replace_with("\n" + "\n".join(r for r in rows if r) + "\n")
    # Lemon directory pages contain a list of links, whereas articles have divs/tables.
    directory = body.find("ul", recursive=False) is not None
    if directory:
        return None, links
    if title_node:
        title_node.decompose()
    text = normalize(body.get_text("\n", strip=True))
    if len(text) < 40:
        return None, links
    return Page(1, text, title, url, images), links


def read_manifest(path: Path) -> list[Manual]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("manuals"), list):
        raise ValueError("Manifest schema_version=1 ve manuals listesi içermeli.")
    manuals = []
    for item in data["manuals"]:
        vehicle = Vehicle(**item["vehicle"])
        pages = []
        if "pages" in item:
            for p in item["pages"]:
                pages.append(Page(int(p["number"]), normalize(p["text"]), p.get("title", ""),
                                  p.get("url", ""), tuple(p.get("images", []))))
        else:
            file = (path.parent / item["file"]).resolve()
            if file.suffix.lower() == ".pdf":
                reader = PdfReader(file)
                for number, p in enumerate(reader.pages, 1):
                    text = normalize(p.extract_text() or "")
                    if text:
                        pages.append(Page(number, text, item["title"], item.get("source", "")))
            elif file.suffix.lower() in {".txt", ".md"}:
                for number, text in enumerate(file.read_text(encoding="utf-8").split("\f"), 1):
                    if normalize(text):
                        pages.append(Page(number, normalize(text), item["title"], item.get("source", "")))
            elif file.suffix.lower() in {".html", ".htm"}:
                page, _ = parse_html(file.read_text(encoding="utf-8"), item.get("source", ""))
                if page:
                    pages.append(page)
            else:
                raise ValueError("Desteklenmeyen dosya türü: " + file.suffix)
        if not pages or any(p.number < 1 for p in pages) or len({p.number for p in pages}) != len(pages):
            raise ValueError("Metin içeren, benzersiz pozitif sayfa numaraları gerekli: " + item["key"])
        if not any(p.text.strip() for p in pages):
            raise ValueError("Metin bulunamadı; taranmış PDF için önce OCR uygulayın.")
        manuals.append(Manual(item["key"], item["title"], vehicle, item.get("language", "en"),
                              item.get("source", ""), tuple(sorted(pages, key=lambda p: p.number))))
    if len({m.id for m in manuals}) != len(manuals):
        raise ValueError("Aynı araçta aynı kılavuz key değeri tekrar edemez.")
    return manuals


def crawl_lemon(root=DEFAULT_LEMON_URL, max_pages=12, max_requests=80, delay=1.0,
                output: Path | None = None) -> dict:
    """Bounded, resumable DFS. Store one document per article, never fabricate content."""
    root = canonical_url(root)
    parsed = urlsplit(root)
    parts = unquote(parsed.path).strip("/").split("/")
    if parsed.scheme != "https" or parsed.netloc != "lemon-manuals.la" or len(parts) < 4 or parts[0] != "Toyota":
        raise ValueError("Lemon URL bir Toyota/model-yılı/model/kılavuz dizini olmalı.")
    if not root.endswith("/"):
        root += "/"
    if not 1 <= max_pages <= 1000 or not 1 <= max_requests <= 5000 or delay < 0.5:
        raise ValueError("Sayfa 1–1000, istek 1–5000, bekleme en az 0.5 saniye olmalı.")
    vehicle = Vehicle(parts[2], int(parts[1]), "Lemon dataset (market unspecified)")
    output = output or ROOT / "data" / "processed" / "toyota-lemon.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    cache = ROOT / "data" / "raw" / "lemon"
    cache.mkdir(parents=True, exist_ok=True)
    queue, seen, manuals, errors = [root], set(), [], []
    fetched = 0
    with httpx.Client(timeout=45, headers={"User-Agent": USER_AGENT}, follow_redirects=False) as client:
        robots = RobotFileParser()
        response = client.get("https://lemon-manuals.la/robots.txt")
        if response.status_code == 200:
            robots.parse(response.text.splitlines())
        elif response.status_code == 404:
            robots.parse([])
        else:
            raise ValueError(f"robots.txt kontrol edilemedi ({response.status_code}); tarama yapılmadı.")
        requested_delay = robots.crawl_delay(USER_AGENT) or robots.crawl_delay("*") or 0
        delay = max(delay, requested_delay)
        while queue and len(manuals) < max_pages and len(seen) < max_requests:
            url = queue.pop()
            if url in seen or not in_scope(url, root):
                continue
            seen.add(url)
            if not robots.can_fetch(USER_AGENT, url):
                errors.append({"url": url, "error": "robots.txt disallows"})
                continue
            file = cache / (stable_id(url) + ".html")
            try:
                if file.exists():
                    html = file.read_text(encoding="utf-8")
                else:
                    time.sleep(delay)
                    res = client.get(url)
                    fetched += 1
                    res.raise_for_status()
                    if "text/html" not in res.headers.get("content-type", "") or len(res.content) > 10_000_000:
                        raise ValueError("HTML dışı veya çok büyük içerik")
                    html = res.text
                    file.write_text(html, encoding="utf-8")
                page, links = parse_html(html, url)
                if page:
                    manuals.append({"key": url, "title": page.title, "vehicle": asdict(vehicle),
                                    "language": "en", "source": url, "pages": [asdict(page)]})
                    print(f"[{len(manuals)}/{max_pages}] {page.title}", flush=True)
                    # Persist after every article so interrupted crawls remain useful.
                    output.write_text(json.dumps({"schema_version": 1, "manuals": manuals},
                                                 ensure_ascii=False, indent=2), encoding="utf-8")
                else:
                    children = [link for link in links if in_scope(link, root)
                                and urlsplit(link).path.endswith("/") and link not in seen]
                    queue.extend(reversed(children))
            except (httpx.HTTPError, ValueError, OSError) as exc:
                errors.append({"url": url, "error": str(exc)})
    report = {"root": root, "articles": len(manuals), "visited": len(seen), "network_requests": fetched,
              "remaining_links": len(queue), "limited": bool(queue), "errors": errors, "manifest": str(output)}
    (ROOT / "data" / "crawl-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not manuals:
        raise ValueError("Metin sayfası alınamadı. data/crawl-report.json dosyasını inceleyin.")
    return report
