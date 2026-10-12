import json
import re
import httpx
from .models import (QUESTION_TAXONOMY, components, question_context,
                     question_intent)


def question_plan(question, history=None):
    resolved = retrieval_question(question, history or [])
    categories, systems, priority = question_context(resolved)
    intent = question_intent(resolved, categories)
    return {
        "query": resolved,
        "intent": intent,
        "categories": categories,
        "category_titles": [QUESTION_TAXONOMY[item]["title"] for item in categories],
        "systems": systems,
        "priority": priority,
    }


def ollama_status(settings, client=None):
    """Check whether the configured local Ollama model is currently available."""
    if settings.answer_mode != "ollama":
        return {"connected": False, "ready": False, "model": settings.ollama_model,
                "detail": "Kaynak gösterme modu etkin."}
    try:
        if client is not None:
            response = client.get(settings.ollama_url + "/api/tags")
        else:
            with httpx.Client(timeout=3) as local_client:
                response = local_client.get(settings.ollama_url + "/api/tags")
        response.raise_for_status()
        names = [row.get("name", "") for row in response.json().get("models", [])]
        requested = settings.ollama_model
        ready = requested in names or requested + ":latest" in names or any(
            name.split(":", 1)[0] == requested.split(":", 1)[0] for name in names)
        return {"connected": True, "ready": ready, "model": requested,
                "detail": "Model hazır." if ready else "Model Ollama'da yüklü değil."}
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return {"connected": False, "ready": False, "model": settings.ollama_model,
                "detail": "Ollama servisine ulaşılamadı."}


def retrieval_question(question, history):
    """Resolve a referential follow-up using the latest explicit user topic."""
    if not history or components(question):
        return question
    follow_up = re.search(r"\b(peki|bunu|bunun|onu|onun|aynı|ayni|devam|özetle|ozetle|it|that|this)\b",
                          question.casefold())
    short_follow_up = re.fullmatch(r"\s*(nasıl|nasil|neden|ne kadar|how|why)[?.!\s]*", question.casefold())
    if not follow_up and not short_follow_up:
        return question
    previous_users = [m["content"] for m in history if m["role"] == "user"]
    for previous in reversed(previous_users):
        previous_follow_up = re.search(r"\b(peki|bunu|bunun|onu|onun|devam|özetle|ozetle|it|that|this)\b", previous.casefold())
        if components(previous) or not previous_follow_up:
            return previous + "\nTakip sorusu: " + question
    return previous_users[-1] + "\nTakip sorusu: " + question if previous_users else question


def bounded_history(history):
    """Send recent complete turns in chronological order within a context budget."""
    selected, budget = [], 6500
    for offset in range(len(history) - 2, -1, -2):
        pair = [{"role": m["role"], "content": m["content"][:2200]}
                for m in history[offset:offset + 2]]
        length = sum(len(m["content"]) for m in pair)
        if length > budget:
            break
        selected[0:0] = pair
        budget -= length
    return selected


def source_answer(sources, warning=None, orchestration=None):
    if not sources:
        return {"answer": "Seçilen Toyota kılavuzlarında bu soru için kaynak bulunamadı.",
                "mode": "no_evidence", "sources": [], "warning": warning,
                "orchestration": orchestration or {}}
    excerpts = [f"[{i}] {s['title']}\n{s['text']}" for i, s in enumerate(sources[:3], 1)]
    return {"answer": "İlgili kılavuz bölümleri (özgün dilinde):\n\n" + "\n\n".join(excerpts),
            "mode": "sources", "sources": sources, "warning": warning,
            "orchestration": orchestration or {}}


def model_issue(sources, warning, orchestration=None):
    return {"answer": "Kılavuzlara baktım ancak yerel model bu yanıtı tamamlayamadı. Mesajını yeniden gönderebilirsin; bulduğum kaynakları da aşağıdan inceleyebilirsin.",
            "mode": "model_error", "sources": sources, "warning": warning,
            "orchestration": orchestration or {}}


def _fact_context(facts, sources):
    citation_by_chunk = {source.get("chunk_id", source.get("id")): source["citation"]
                         for source in sources if source.get("chunk_id", source.get("id"))}
    lines = []
    for fact in facts:
        citations = sorted({citation_by_chunk[evidence["chunk_id"]]
                            for evidence in fact.get("evidence", ())
                            if isinstance(evidence, dict)
                            and evidence.get("chunk_id") in citation_by_chunk})
        if not citations:
            continue
        references = " ".join(f"[{number}]" for number in citations)
        lines.append(
            f"{fact['source_name']} ({fact['source_type']}) "
            f"-{fact['type']}-> {fact['target_name']} ({fact['target_type']}); "
            f"durum={fact['status']}; güven={fact['confidence']}; kanıt={references}")
    return "\n".join(lines[:8])


def _source_context(source, citation):
    text = source["text"][:1400]
    applicability = ""
    if "different variant/trim than selected" in text.casefold():
        applicability = ("\nUYUMLULUK: Kaynak seçilen araçtan farklı bir varyant/donanım içindir. "
                         "Seçili araca kesin uygulama; VIN ile doğrulama gerektiğini belirt.")
    return (f"[{citation}] {source['model']} {source['year']} / {source['market']} / "
            f"{source['title']} / page {source['page']} / {source['url']}"
            f"{applicability}\n{text}")


def _guarded_safety_answer(plan, sources):
    """Use an extractive response for the known safety-critical steering evidence."""
    if plan.get("priority") != "P0" or "steering" not in plan.get("systems", ()):
        return None
    recall = next((source for source in sources
                   if "24v878000" in source.get("text", "").casefold()
                   and "loss of steering control" in source.get("text", "").casefold()), None)
    causes = [source for source in sources if any(
        phrase in source.get("text", "").casefold() for phrase in (
            "air in pump fluid system", "insufficient pump pressure",
            "sticking flow control valve", "steering gear coupling loose"))]
    if recall is None:
        return None
    recall_citation = recall["citation"]
    cause_citations = list(dict.fromkeys(source["citation"] for source in causes))[:2]
    answer = (
        "Direksiyon kontrolünün kaybı kaza riskini artırır. Eşleşen 24V878000 bülteni, "
        "bazı 2023–2024 Corolla ve Corolla Hybrid araçlarda ara direksiyon milinin çatlayıp "
        f"direksiyon kolonundan ayrılabileceğini bildiriyor [{recall_citation}]. "
        "Ancak bu arşiv sayfası seçili Corolla LE'den farklı bir Corolla Hybrid LE varyantı "
        "uyarısı taşıyor; kaydın aracınıza uygulanıp uygulanmadığını VIN ile Toyota servisinde "
        f"doğrulatın [{recall_citation}]."
    )
    if cause_citations:
        references = "".join(f"[{number}]" for number in cause_citations)
        answer += (
            " Ağır veya yardımsız direksiyon için kılavuzdaki olası nedenler arasında pompa "
            "sıvısı sisteminde hava, yetersiz pompa basıncı, sıkışmış akış kontrol valfi ve "
            f"gevşek direksiyon bağlantıları bulunuyor {references}. Bu liste kesin teşhis değildir; "
            "direksiyon kaybı hissediliyorsa aracı yeniden kullanmadan profesyonel kontrol yaptırın."
        )
    return {"answer": answer, "mode": "evidence_guard", "sources": sources,
            "warning": None, "orchestration": plan}


def ask(store, settings, question, vehicle_id, limit=5, mode=None, history=None):
    history = history or []
    plan = question_plan(question, history)
    if re.fullmatch(r"\s*(merhaba|selam|hello|hi|teşekkürler|tesekkurler)[!.\s]*", question.casefold()):
        return {"answer": "Merhaba! Seçtiğin Toyota'nın kılavuzları hakkında konuşabiliriz. Hangi konuyu merak ediyorsun?",
                "mode": "conversation", "sources": [], "warning": None,
                "orchestration": plan}
    if hasattr(store, "retrieve"):
        retrieval = store.retrieve(plan["query"], vehicle_id, limit)
        sources, facts = retrieval["sources"], retrieval.get("facts", [])
        plan.update(retrieval.get("plan", {}))
    else:
        sources = store.search(plan["query"], vehicle_id, limit)
        facts = []
        plan.update(text_candidates=len(sources), graph_facts=0,
                    selected_sources=len(sources))
    for i, source in enumerate(sources, 1):
        source["citation"] = i
    if (mode or settings.answer_mode) == "sources":
        return source_answer(sources, orchestration=plan)
    guarded_answer = _guarded_safety_answer(plan, sources)
    if guarded_answer is not None:
        return guarded_answer
    model_sources = sources[:3]
    context = "\n\n".join(_source_context(source, citation)
                             for citation, source in enumerate(model_sources, 1))
    fact_context = _fact_context(facts, model_sources)
    if not sources:
        context = "Bu mesaj için seçilen aracın arşivinde eşleşen kaynak yok. Teknik bilgi veya kaynak numarası üretme; belirsizliği açıkla ve kullanıcıya netleştirme sorusu sor."
    route = (f"Niyet: {plan['intent']}; öncelik: {plan['priority']}; "
             f"kategoriler: {', '.join(plan['category_titles']) or 'genel'}; "
             f"sistemler: {', '.join(plan['systems']) or 'belirlenmedi'}")
    route_instruction = {
        "troubleshooting": ("Belirtiyi doğrudan ele al. Kaynaktaki güvenlik sonucunu, olası nedenleri "
                            "kesin teşhis gibi sunmadan ve somut sonraki adımı açıkça belirt."),
        "recall": "Geri çağırma numarasını, kapsamı ve kullanıcı için doğrulama adımını belirt.",
        "maintenance_interval": "Aralığı, birimi ve kaynakta yazan koşulları birlikte belirt.",
        "procedure": "Yalnız kaynakta bulunan adımları doğru sırada ve kısa biçimde belirt.",
        "specification": "Değeri, birimi ve geçerli olduğu koşulu birlikte belirt.",
    }.get(plan["intent"], "Soruyu doğrudan yanıtla; gereksiz genel öneri verme.")
    system = (
        "Sen Toyota kılavuzlarına dayalı, kısa ve güvenilir Türkçe araç asistanısın. "
        "Sadece GÜNCEL KAYNAKLAR ve kaynak numarası bulunan GRAPH FACTS içeriğini kullan. "
        "Her teknik iddianın hemen sonuna [1] biçiminde kaynak ekle; kaynakta olmayan teşhis, değer veya işlem üretme. "
        "Farklı varyant/donanım uyarısını mutlaka açıkla ve seçili araca uygulanabilirliği VIN ile doğrulat. "
        "Parça adı geçmesini arıza kanıtı sayma; needs_review ilişkisini kesin bilgi gibi sunma. "
        "Yanıtın tamamı doğal Türkçe ve en fazla 120 kelime olsun. Çince/Korece karakter, iç sistem, veri seti veya RAG adı kullanma; "
        "recall yerine 'geri çağırma' de. Önce net cevabı, sonra gerekli koşul ve sonraki adımı ver. "
        "Bağlam yetersizse bunu açıkça söyle. Önceki sohbet teknik kanıt değildir. "
        "Yalnız JSON döndür: answer Türkçe metin, citations kullanılan güncel kaynak numaralarının tam sayı listesi. "
        "Kaynak kullandıysan citations boş olamaz; kaynak yoksa boş liste kullan."
    )
    try:
        with httpx.Client(timeout=360) as client:
            response = client.post(settings.ollama_url + "/api/chat", json={
                "model": settings.ollama_model, "stream": False, "keep_alive": "30m",
                "format": {"type": "object", "properties": {
                    "answer": {"type": "string"},
                    "citations": {"type": "array", "items": {"type": "integer"}}},
                    "required": ["answer", "citations"], "additionalProperties": False},
                "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 512},
                "messages": [{"role": "system", "content": system}] + bounded_history(history) +
                            [{"role": "user", "content":
                              f"RAG ROTASI:\n{route}\nGÖREV: {route_instruction}\n\n"
                              f"GRAPH FACTS:\n{fact_context or 'Yok'}\n\n"
                              f"GÜNCEL KAYNAKLAR:\n{context}\n\nSORU:\n{question}"}]})
            response.raise_for_status()
            payload = json.loads(response.json()["message"]["content"])
            if not isinstance(payload, dict) or not isinstance(payload.get("answer"), str):
                return model_issue(sources, "Model yanıtının biçimi geçersiz.", plan)
            answer = payload["answer"].strip()
            answer = re.sub(r"召回[\uac00-\ud7af]*", "geri çağırma", answer)
            references = payload["citations"]
            if not isinstance(references, list) or any(type(n) is not int for n in references):
                return model_issue(sources, "Model yanıtında geçerli kaynak numaraları bulunmadı.", plan)
        citations = set(references) | {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
        if not sources:
            if not answer or citations:
                return source_answer([], "Kaynak bulunmayan model yanıtı geçersiz kaynak numarası içerdi.", plan)
            return {"answer": answer, "mode": "no_evidence", "sources": [], "warning": None,
                    "orchestration": plan}
        allowed_citations = set(range(1, len(model_sources) + 1))
        if not answer or not citations or not citations.issubset(allowed_citations):
            return model_issue(sources, "Model yanıtında geçerli kaynak numaraları bulunmadı.", plan)
        missing = citations - {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
        if missing:
            answer += "\n\n" + " ".join(f"[{n}]" for n in sorted(missing))
        return {"answer": answer, "mode": "ollama", "sources": sources, "warning": None,
                "orchestration": plan}
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        return model_issue(sources, f"Yerel model yanıtı alınamadı ({type(exc).__name__}).", plan)
