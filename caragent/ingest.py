"""Read explicit Toyota manifests, PDFs and Lemon HTML without guessing metadata."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote, quote, urlunsplit
from urllib.robotparser import RobotFileParser
import json
import posixpath
import threading
import time

from bs4 import BeautifulSoup
import httpx
from pypdf import PdfReader

from .config import ROOT
from .models import Manual, Page, Vehicle, normalize, stable_id

DEFAULT_LEMON_URL = "https://lemon-manuals.la/Toyota/2024/Corolla%20LE/"
USER_AGENT = "CARAGENT/0.1 (Toyota manual research; bounded crawler)"


@dataclass(frozen=True)
class CrawlConfig:
    timeout: float = 45.0
    retries: int = 2
    backoff: float = 1.0
    cache_ttl: float = 86_400.0
    concurrency: int = 1
    refresh_cache: bool = False

    def __post_init__(self):
        if self.timeout <= 0 or not 0 <= self.retries <= 10 or self.backoff < 0:
            raise ValueError("Timeout pozitif, retry 0–10 ve backoff negatif olmayan bir değer olmalı.")
        if self.cache_ttl < 0 or not 1 <= self.concurrency <= 16:
            raise ValueError("Cache süresi negatif olamaz; eşzamanlı istek sayısı 1–16 olmalı.")


class _RequestPacer:
    def __init__(self, delay: float):
        self.delay = delay
        self.next_request = 0.0
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            pause = self.next_request - time.monotonic()
            if pause > 0:
                time.sleep(pause)
            self.next_request = time.monotonic() + self.delay


def cache_is_fresh(path: Path, ttl: float, refresh=False, now=None) -> bool:
    if refresh or ttl == 0 or not path.exists():
        return False
    now = time.time() if now is None else now
    return now - path.stat().st_mtime <= ttl


def request_with_retries(client, url: str, timeout: float, retries: int, backoff: float,
                         pacer=None, allowed_statuses=()):
    """Return (response, attempts); retry transport errors, 429 and 5xx responses."""
    last_error = None
    for attempt in range(retries + 1):
        if pacer:
            pacer.wait()
        try:
            response = client.get(url, timeout=timeout)
            if response.status_code in allowed_statuses or 200 <= response.status_code < 400:
                return response, attempt + 1
            if response.status_code != 429 and response.status_code < 500:
                response.raise_for_status()
            last_error = httpx.HTTPStatusError(
                f"retryable HTTP status {response.status_code}",
                request=response.request, response=response
            )
        except httpx.HTTPError as exc:
            if (isinstance(exc, httpx.HTTPStatusError)
                    and exc.response.status_code != 429
                    and exc.response.status_code < 500):
                exc.caragent_attempts = attempt + 1
                raise
            last_error = exc
        if attempt < retries and backoff:
            time.sleep(backoff * (2 ** attempt))
    assert last_error is not None
    last_error.caragent_attempts = retries + 1
    raise last_error

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


def is_crawlable_directory(url: str, root: str) -> bool:
    """Follow model-local directories while avoiding the duplicate single-page export."""
    path = unquote(urlsplit(url).path)
    return (in_scope(url, root) and path.endswith("/")
            and "/Repair and Diagnosis (Single Page)/" not in path)


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
                output: Path | None = None, *, timeout=45.0, retries=2, backoff=1.0,
                cache_ttl=86_400.0, refresh_cache=False, concurrency=1) -> dict:
    """Bounded, resumable crawl with polite pacing, retries and an expiring cache."""
    started = time.monotonic()
    config = CrawlConfig(timeout, retries, backoff, cache_ttl, concurrency, refresh_cache)
    root = canonical_url(root)
    parsed = urlsplit(root)
    parts = unquote(parsed.path).strip("/").split("/")
    if (parsed.scheme != "https" or parsed.netloc != "lemon-manuals.la"
            or len(parts) < 3 or parts[0] != "Toyota" or not parts[1].isdigit()):
        raise ValueError("Lemon URL bir Toyota/model-yılı/model veya kılavuz dizini olmalı.")
    if not root.endswith("/"):
        root += "/"
    if not 0 <= max_pages <= 100_000 or not 0 <= max_requests <= 500_000 or delay < 0.5:
        raise ValueError("Sayfa 0–100000, istek 0–500000, bekleme en az 0.5 saniye olmalı; 0 sınırsızdır.")
    vehicle = Vehicle(parts[2], int(parts[1]), "Lemon dataset (market unspecified)")
    output = output or ROOT / "data" / "processed" / "toyota-lemon.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    cache = ROOT / "data" / "raw" / "lemon"
    cache.mkdir(parents=True, exist_ok=True)
    queue, seen, manuals, errors = [root], set(), [], []
    fetched = cache_hits = stale_cache_hits = retry_count = 0
    pacer = _RequestPacer(delay)

    def write_manifest(complete=False):
        payload = {
            "schema_version": 1,
            "crawl": {"root": root, "complete": complete, "visited": len(seen),
                      "errors": len(errors)},
            "manuals": manuals,
        }
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=False) as client:
        robots = RobotFileParser()
        response, _ = request_with_retries(client, "https://lemon-manuals.la/robots.txt",
                                           config.timeout, config.retries, config.backoff,
                                           allowed_statuses=(404,))
        if response.status_code == 200:
            robots.parse(response.text.splitlines())
        elif response.status_code == 404:
            robots.parse([])
        else:
            raise ValueError(f"robots.txt kontrol edilemedi ({response.status_code}); tarama yapılmadı.")
        requested_delay = robots.crawl_delay(USER_AGENT) or robots.crawl_delay("*") or 0
        delay = max(delay, requested_delay)
        pacer.delay = delay

        def fetch(url):
            file = cache / (stable_id(url) + ".html")
            if cache_is_fresh(file, config.cache_ttl, config.refresh_cache):
                try:
                    return file.read_text(encoding="utf-8"), 0, "fresh", None
                except OSError as exc:
                    return None, 0, None, exc
            try:
                res, attempts = request_with_retries(client, url, config.timeout, config.retries,
                                                     config.backoff, pacer)
                if "text/html" not in res.headers.get("content-type", "") or len(res.content) > 10_000_000:
                    raise ValueError("HTML dışı veya çok büyük içerik")
                file.write_text(res.text, encoding="utf-8")
                return res.text, attempts, None, None
            except (httpx.HTTPError, ValueError, OSError) as exc:
                attempts = getattr(exc, "caragent_attempts", config.retries + 1)
                permanent_http_error = (isinstance(exc, httpx.HTTPStatusError)
                                        and exc.response.status_code != 429
                                        and exc.response.status_code < 500)
                if permanent_http_error:
                    return None, attempts, None, exc
                if file.exists():
                    try:
                        return file.read_text(encoding="utf-8"), attempts, "stale", exc
                    except OSError:
                        pass
                return None, attempts, None, exc

        def process(url):
            html, attempts, cache_state, warning = fetch(url)
            if html is None:
                return url, None, [], attempts, cache_state, warning
            try:
                page, links = parse_html(html, url)
                return url, page, links, attempts, cache_state, warning
            except (ValueError, OSError) as exc:
                return url, None, [], attempts, cache_state, exc

        while (queue and (max_pages == 0 or len(manuals) < max_pages)
               and (max_requests == 0 or len(seen) < max_requests)):
            batch = []
            batch_limit = config.concurrency
            if max_requests:
                batch_limit = min(batch_limit, max_requests - len(seen))
            if max_pages:
                batch_limit = min(batch_limit, max_pages - len(manuals))
            while queue and len(batch) < batch_limit:
                url = queue.pop()
                if url in seen or not is_crawlable_directory(url, root):
                    continue
                seen.add(url)
                if not robots.can_fetch(USER_AGENT, url):
                    errors.append({"url": url, "error": "robots.txt disallows"})
                    continue
                batch.append(url)
            if not batch:
                continue
            executor = None
            if config.concurrency == 1:
                results = map(process, batch)
            else:
                executor = ThreadPoolExecutor(max_workers=config.concurrency)
                results = executor.map(process, batch)
            try:
                for url, page, links, attempts, cache_state, warning in results:
                    fetched += attempts
                    retry_count += max(0, attempts - 1)
                    cache_hits += int(cache_state == "fresh")
                    stale_cache_hits += int(cache_state == "stale")
                    if warning:
                        errors.append({"url": url, "error": str(warning),
                                       "stale_cache_used": cache_state == "stale"})
                    if page:
                        manuals.append({"key": url, "title": page.title, "vehicle": asdict(vehicle),
                                        "language": "en", "source": url, "pages": [asdict(page)]})
                        total = str(max_pages) if max_pages else "all"
                        print(f"[{len(manuals)}/{total}] {page.title}", flush=True)
                        # Keep the visible JSON in sync with progress. This costs more I/O,
                        # but makes long full-vehicle crawls safely resumable and inspectable.
                        write_manifest()
                    # Lemon overview pages can contain useful text and child directories.
                    # Persist the text above and still traverse every in-scope child.
                    children = [link for link in links
                                if is_crawlable_directory(link, root) and link not in seen]
                    queue.extend(reversed(children))
            finally:
                if executor:
                    executor.shutdown(wait=True)
    complete = not queue and not errors
    if manuals:
        write_manifest(complete)
    report = {"root": root, "complete": complete,
              "articles": len(manuals), "visited": len(seen), "network_requests": fetched,
              "retries": retry_count, "cache_hits": cache_hits, "stale_cache_hits": stale_cache_hits,
              "error_rate": round(len(errors) / len(seen), 4) if seen else 0.0,
              "elapsed_seconds": round(time.monotonic() - started, 3),
              "remaining_links": len(queue), "limited": bool(queue), "errors": errors,
              "settings": {"max_pages": max_pages, "max_requests": max_requests, "delay": delay,
                           "timeout": config.timeout, "retries": config.retries,
                           "backoff": config.backoff, "cache_ttl": config.cache_ttl,
                           "refresh_cache": config.refresh_cache, "concurrency": config.concurrency},
              "manifest": str(output)}
    (ROOT / "data" / "crawl-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not manuals:
        raise ValueError("Metin sayfası alınamadı. data/crawl-report.json dosyasını inceleyin.")
    return report
