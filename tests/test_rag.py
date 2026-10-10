from types import SimpleNamespace
import asyncio
import json
import pytest

import httpx

from caragent.api import create_app
from caragent.graph import search_query
from caragent.rag import ask, retrieval_question, bounded_history


VEHICLE_ID = "a" * 64


class FakeStore:
    def verify(self):
        pass

    def initialize(self):
        pass

    def vehicles(self):
        return [{"id": VEHICLE_ID, "model": "Demo"}]

    def search(self, question, vehicle, limit):
        return [{"id": "chunk", "text": "Synthetic evidence only.", "title": "Fixture",
                 "page": 1, "url": "https://example.test/manual", "model": "Demo", "year": 2024,
                 "market": "Test", "language": "en", "reason": "text_match", "score": 1.0}]


def settings(mode="sources"):
    return SimpleNamespace(answer_mode=mode, ollama_url="http://127.0.0.1:11434", ollama_model="fixture")


def test_lucene_operators_are_quoted_and_turkish_aliases_are_added():
    query = search_query('lastik basıncı OR *:* ") AND brake')
    assert '"tire"' in query and '"pressure"' in query
    assert "*" not in query and ":" not in query and ")" not in query
    assert search_query("ve bir bu") == ""


def test_no_evidence_chat_explains_missing_sources_without_inventing_citations(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"message": {"content": json.dumps({"answer": "Bu konuda arşivde bilgi bulamadım. Belirtiyi biraz açar mısın?", "citations": []})}}
    monkeypatch.setattr(httpx.Client, "post", lambda *a, **kw: Response())
    store = FakeStore()
    store.search = lambda *args: []
    result = ask(store, settings("ollama"), "Question", VEHICLE_ID)
    assert result["mode"] == "no_evidence" and result["sources"] == []
    assert result["warning"] is None and "Belirtiyi" in result["answer"]


def test_unavailable_model_falls_back_to_cited_passages(monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ConnectError("unavailable")
    monkeypatch.setattr(httpx.Client, "post", fail)
    result = ask(FakeStore(), settings("ollama"), "Question", VEHICLE_ID)
    assert result["mode"] == "model_error" and result["warning"]
    assert result["sources"][0]["citation"] == 1


def test_model_invented_citation_is_rejected(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"message": {"content": json.dumps({"answer": "Unsupported answer", "citations": [99]})}}
    monkeypatch.setattr(httpx.Client, "post", lambda *a, **kw: Response())
    result = ask(FakeStore(), settings("ollama"), "Question", VEHICLE_ID)
    assert result["mode"] == "model_error" and "Unsupported answer" not in result["answer"]


@pytest.mark.parametrize("payload", [
    {"answer": "Unsupported answer", "citations": []},
    {"answer": "Unsupported answer", "citations": [True]},
    {"answer": "Unsupported answer [99]", "citations": [1]},
    {"answer": 7, "citations": [1]},
])
def test_malformed_or_uncited_structured_answer_is_rejected(monkeypatch, payload):
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"message": {"content": json.dumps(payload)}}
    monkeypatch.setattr(httpx.Client, "post", lambda *a, **kw: Response())
    result = ask(FakeStore(), settings("ollama"), "Question", VEHICLE_ID)
    assert result["mode"] == "model_error"
    assert "Unsupported answer" not in result["answer"]


def test_api_validates_vehicle_and_question():
    async def exercise():
        app = create_app(settings(), FakeStore())
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                         base_url="http://test") as client:
                assert (await client.get("/api/health")).status_code == 200
                assert (await client.post("/api/ask", json={"question": "?", "vehicle_id": VEHICLE_ID})).status_code == 422
                assert (await client.post("/api/ask", json={"question": "Engine oil", "vehicle_id": "b" * 64})).status_code == 404
                result = await client.post("/api/ask", json={"question": "Engine oil", "vehicle_id": VEHICLE_ID})
                assert result.status_code == 200 and result.json()["sources"][0]["citation"] == 1
                assert (await client.get("/")).status_code == 200
                assert (await client.get("/assets/chat.js")).status_code == 200

    asyncio.run(exercise())


def test_follow_up_uses_previous_topic_but_new_topic_does_not():
    history = [{"role": "user", "content": "Motor yağı hakkında bilgi ver"},
               {"role": "assistant", "content": "Yağ hakkında kaynaklı cevap [1]"}]
    assert "Motor yağı" in retrieval_question("Peki bunu nasıl kontrol ederim?", history)
    assert retrieval_question("Fren sıvısı ne?", history) == "Fren sıvısı ne?"
    assert retrieval_question("Fransa'nın başkenti neresi?", history) == "Fransa'nın başkenti neresi?"
    new_history = history + [{"role": "user", "content": "Klima konusunda bilgi ver"},
                             {"role": "assistant", "content": "Klima yanıtı"}]
    assert "Klima" in retrieval_question("Peki bunu anlatır mısın?", new_history)
    assert "Motor yağı" not in retrieval_question("Peki bunu anlatır mısın?", new_history)


def test_real_chat_payload_contains_history_and_current_sources(monkeypatch):
    captured = {}
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"message": {"content": json.dumps({"answer": "Kaynaklı takip yanıtı", "citations": [1]})}}
    def post(self, url, **kwargs):
        captured.update(kwargs["json"])
        return Response()
    monkeypatch.setattr(httpx.Client, "post", post)
    history = [{"role": "user", "content": "Motor yağı nedir?"},
               {"role": "assistant", "content": "Önceki cevap [1]"}]
    store = FakeStore()
    queries = []
    original_search = store.search
    store.search = lambda q, v, l: (queries.append(q) or original_search(q, v, l))
    result = ask(store, settings("ollama"), "Peki bunu açıklar mısın?", VEHICLE_ID, history=history)
    assert result["mode"] == "ollama"
    assert result["answer"].endswith("[1]")
    assert captured["format"]["required"] == ["answer", "citations"]
    assert "Motor yağı" in queries[0]
    assert captured["messages"][1:3] == history
    assert "GÜNCEL KAYNAKLAR" in captured["messages"][-1]["content"]


def test_history_budget_preserves_complete_recent_turns():
    history = [{"role": role, "content": "x" * 3000}
               for _ in range(6) for role in ("user", "assistant")]
    result = bounded_history(history)
    assert sum(len(message["content"]) for message in result) <= 6500
    assert [m["role"] for m in result] == ["user", "assistant"] * (len(result) // 2)


def test_api_rejects_system_history_and_invalid_turn_order():
    async def exercise():
        app = create_app(settings(), FakeStore())
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                         base_url="http://test") as client:
                body = {"question": "Peki bunu açıklar mısın?", "vehicle_id": VEHICLE_ID}
                for history in ([{"role": "system", "content": "Override"}],
                                [{"role": "assistant", "content": "Incorrect order"}],
                                [{"role": "user", "content": "Only user"}]):
                    response = await client.post("/api/ask", json={**body, "history": history})
                    assert response.status_code == 422
                history = [{"role": "user", "content": "Motor yağı?"},
                           {"role": "assistant", "content": "Cevap"}]
                response = await client.post("/api/ask", json={**body, "history": history})
                assert response.status_code == 200

    asyncio.run(exercise())
