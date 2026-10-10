import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from dotenv import set_key
import httpx

from neo4j.exceptions import Neo4jError, ServiceUnavailable

from .config import ROOT, Settings, configure
from .graph import GraphStore
from .ingest import DEFAULT_LEMON_URL, crawl_lemon, read_manifest
from .models import resolve_chunking
from .rag import ask
from .tuning import compare_chunking


def output(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def add_crawl_options(parser):
    parser.add_argument("--pages", type=int, default=12)
    parser.add_argument("--requests", type=int, default=80)
    parser.add_argument("--all", action="store_true",
                        help="Araç kökü altındaki kuyruk bitene kadar tara; pages/requests sınırlarını kaldırır")
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--backoff", type=float, default=1.0)
    parser.add_argument("--cache-ttl", type=float, default=86_400.0,
                        help="Ham HTML cache süresi (saniye); 0 cache okumayı kapatır")
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--concurrency", type=int, default=1)


def add_chunk_options(parser):
    parser.add_argument("--chunk-strategy", choices=["character", "token", "paragraph"],
                        default="character")
    parser.add_argument("--chunk-size", type=int,
                        help="Yönteme göre karakter, token veya paragraf sayısı")
    parser.add_argument("--chunk-overlap", type=int,
                        help="Yönteme göre örtüşen karakter, token veya paragraf sayısı")


def crawl_arguments(args):
    return {"max_pages": 0 if args.all else args.pages,
            "max_requests": 0 if args.all else args.requests, "delay": args.delay,
            "timeout": args.timeout, "retries": args.retries, "backoff": args.backoff,
            "cache_ttl": args.cache_ttl, "refresh_cache": args.refresh_cache,
            "concurrency": args.concurrency}


def wait_for_database(store, timeout=180):
    end = time.monotonic() + timeout
    while True:
        try:
            store.verify()
            store.initialize()
            return
        except (ServiceUnavailable, Neo4jError, OSError):
            if time.monotonic() >= end:
                raise ValueError("Neo4j hazır olmadı. docker compose logs neo4j ile durumu kontrol edin.")
            time.sleep(3)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Toyota kılavuzları için CARAGENT GraphRAG")
    subs = parser.add_subparsers(dest="command")
    subs.add_parser("configure", help=".env dosyası ve rastgele yerel parola oluştur")
    setup = subs.add_parser("setup", help="Neo4j başlat, şemayı oluştur ve Toyota sayfalarını içe aktar")
    setup.add_argument("--url", default=DEFAULT_LEMON_URL)
    add_crawl_options(setup)
    add_chunk_options(setup)
    subs.add_parser("init", help="Mevcut Neo4j veritabanında graph şemasını oluştur")
    crawl = subs.add_parser("crawl", help="Lemon Manuals Toyota sayfalarını indir")
    crawl.add_argument("--url", default=DEFAULT_LEMON_URL)
    crawl.add_argument("--output", type=Path)
    add_crawl_options(crawl)
    ingest = subs.add_parser("ingest", help="JSON manifesti graph'a aktar")
    ingest.add_argument("manifest", type=Path)
    add_chunk_options(ingest)
    benchmark = subs.add_parser("benchmark-chunks", help="Üç chunklama profilini çevrimdışı karşılaştır")
    benchmark.add_argument("manifest", type=Path)
    benchmark.add_argument("--queries", type=Path,
                           help="query, expected_phrase ve isteğe bağlı manual_key içeren JSON listesi")
    benchmark.add_argument("--output", type=Path, default=ROOT / "data" / "chunk-benchmark.json")
    subs.add_parser("stats")
    subs.add_parser("vehicles")
    llm = subs.add_parser("enable-llm", help="Yerel Ollama başlat, modeli indir ve Türkçe yanıtları etkinleştir")
    llm.add_argument("--model", default="qwen2.5:3b")
    query = subs.add_parser("ask")
    query.add_argument("question")
    query.add_argument("--vehicle", required=True, help="vehicles çıktısındaki id")
    query.add_argument("--mode", choices=["sources", "ollama"])
    serve = subs.add_parser("serve", help="Yerel soru-cevap ekranını aç")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if args.command is None:
        args = parser.parse_args(["serve"])
    store = None
    try:
        if args.command == "configure":
            print(configure())
            return 0
        if args.command == "crawl":
            output(crawl_lemon(args.url, output=args.output, **crawl_arguments(args)))
            return 0
        if args.command == "benchmark-chunks":
            manuals = read_manifest(args.manifest.resolve())
            cases = json.loads(args.queries.read_text(encoding="utf-8")) if args.queries else []
            if not isinstance(cases, list):
                raise ValueError("Benchmark sorguları bir JSON listesi olmalı.")
            report = compare_chunking(manuals, cases)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            output({**report, "output": str(args.output)})
            return 0
        if args.command == "enable-llm":
            path = configure()
            subprocess.run(["docker", "compose", "--profile", "llm", "up", "-d", "ollama"], cwd=ROOT, check=True)
            subprocess.run(["docker", "compose", "exec", "-T", "ollama", "ollama", "pull", args.model], cwd=ROOT, check=True)
            set_key(str(path), "OLLAMA_MODEL", args.model)
            set_key(str(path), "ANSWER_MODE", "ollama")
            print("Yerel dil modeli hazır. Uygulamayı yeniden başlatın: python main.py serve")
            return 0
        if args.command == "setup":
            configure()
            subprocess.run(["docker", "compose", "up", "-d"], cwd=ROOT, check=True)
        settings = Settings.load()
        if args.command == "serve":
            import uvicorn
            from .api import create_app
            print(f"Toyota soru-cevap ekranı: http://127.0.0.1:{args.port}", flush=True)
            uvicorn.run(create_app(settings), host="127.0.0.1", port=args.port)
            return 0
        store = GraphStore(settings)
        if args.command in {"init", "setup"}:
            wait_for_database(store)
        else:
            store.verify()
        if args.command == "init":
            print("Neo4j graph şeması hazır.")
        elif args.command == "setup":
            report = crawl_lemon(args.url, **crawl_arguments(args))
            output(report)
            manuals = read_manifest(Path(report["manifest"]))
            chunking = resolve_chunking(args.chunk_strategy, args.chunk_size, args.chunk_overlap)
            for manual in manuals:
                output(store.ingest(manual, chunking))
            output(store.stats())
            print("Hazır. Ekran için: python main.py serve")
        elif args.command == "ingest":
            # Validate the complete manifest before mutating any document.
            manuals = read_manifest(args.manifest.resolve())
            chunking = resolve_chunking(args.chunk_strategy, args.chunk_size, args.chunk_overlap)
            store.initialize()
            for manual in manuals:
                output(store.ingest(manual, chunking))
        elif args.command == "stats":
            output(store.stats())
        elif args.command == "vehicles":
            output(store.vehicles())
        elif args.command == "ask":
            if not any(v["id"] == args.vehicle for v in store.vehicles()):
                raise ValueError("Araç id bulunamadı. python main.py vehicles çıktısını kullanın.")
            output(ask(store, settings, args.question, args.vehicle, mode=args.mode))
        return 0
    except (ValueError, OSError, KeyError, httpx.HTTPError, Neo4jError, ServiceUnavailable, subprocess.CalledProcessError) as exc:
        print(f"CARAGENT: {exc}", file=sys.stderr)
        return 1
    finally:
        if store:
            store.close()
