"""Source-grounded entity and relationship extraction for manual chunks.

This module deliberately stops at a graph-neutral JSON contract.  It does not
write domain nodes or relationships to Neo4j; graph schema decisions can evolve
without coupling them to extraction.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import re
from typing import Any, Iterable

import httpx

from .models import Chunk, normalize, stable_id


SCHEMA_VERSION = "caragent-extraction-v1"
EXTRACTOR_VERSION = "1.0.0"
ENTITY_TYPES = frozenset({"component", "system", "maintenance_action", "warning",
                          "technical_value"})
RELATIONSHIP_TYPES = frozenset({"applies_to", "has_value", "warns_about", "part_of",
                                "requires"})

COMPONENT_ALIASES = {
    "engine oil": ("engine oil", "motor yağı", "motor yagi"),
    "engine": ("engine", "motor"),
    "brake": ("brake", "fren"),
    "battery": ("battery", "akü", "aku"),
    "tire": ("tire", "tyre", "lastik"),
    "coolant": ("coolant", "antifreeze", "soğutma sıvısı", "sogutma sivisi"),
    "transmission": ("transmission", "şanzıman", "sanziman"),
    "airbag": ("airbag", "hava yastığı", "hava yastigi", "srs"),
}
SYSTEM_ALIASES = {
    "brake system": ("brake system", "braking system", "fren sistemi"),
    "cooling system": ("cooling system", "soğutma sistemi", "sogutma sistemi"),
    "charging system": ("charging system", "şarj sistemi", "sarj sistemi"),
    "lubrication system": ("lubrication system", "yağlama sistemi", "yaglama sistemi"),
}
ACTION_ALIASES = {
    "inspect": ("inspect", "inspection", "check", "kontrol edin", "kontrol", "inceleyin"),
    "replace": ("replace", "replacement", "değiştirin", "degistirin", "değişim", "degisim"),
    "tighten": ("tighten", "torque", "sıkın", "sikin", "sıkma", "sikma"),
    "fill": ("fill", "refill", "add", "doldurun", "ekleyin"),
    "clean": ("clean", "temizleyin", "temizleme"),
}
WARNING_WORDS = ("warning", "caution", "notice", "uyarı", "uyari", "dikkat")
VALUE_PATTERN = re.compile(
    r"(?<!\w)\d+(?:[.,]\d+)?\s?(?:N[·.]?m|psi|kPa|MPa|bar|L|mL|qt|mm|cm|V|A|°C|°F)(?!\w)",
    re.IGNORECASE,
)


def normalize_entity_name(value: str) -> str:
    """Normalize spelling without guessing whether two ambiguous entities are equal."""
    value = normalize(value).casefold().replace("ı", "i")
    value = re.sub(r"[^\w°·.]+", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


@dataclass(frozen=True)
class Evidence:
    chunk_id: str
    page_id: str
    page_number: int
    source: str
    quote: str


@dataclass(frozen=True)
class ExtractedEntity:
    id: str
    type: str
    name: str
    normalized_name: str
    vehicle_id: str
    vehicle_model: str
    vehicle_year: int
    confidence: float
    status: str
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class ExtractedRelationship:
    id: str
    type: str
    source_entity_id: str
    target_entity_id: str
    confidence: float
    status: str
    properties: dict[str, Any]
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class ExtractionResult:
    schema_version: str
    chunk_id: str
    manual_id: str
    page_id: str
    page_number: int
    source: str
    vehicle_id: str
    vehicle_model: str
    vehicle_year: int
    extractor: dict[str, Any]
    entities: tuple[ExtractedEntity, ...] = ()
    relationships: tuple[ExtractedRelationship, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def graph_payload(self) -> dict[str, list[dict[str, Any]]]:
        """Return graph-neutral rows which graph.py can consume in a later task."""
        return {
            "entities": [asdict(entity) for entity in self.entities],
            "relationships": [asdict(relationship) for relationship in self.relationships],
        }


@dataclass(frozen=True)
class ExtractorConfig:
    mode: str = "rules"
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "qwen2.5:3b"
    temperature: float = 0.0
    timeout: float = 180.0

    def __post_init__(self):
        if self.mode not in {"rules", "ollama"}:
            raise ValueError("Extraction mode rules veya ollama olmalı.")
        if not self.model.strip():
            raise ValueError("Extraction model adı boş olamaz.")
        if not 0 <= self.temperature <= 1:
            raise ValueError("Extraction temperature 0–1 arasında olmalı.")
        if self.timeout <= 0:
            raise ValueError("Extraction timeout pozitif olmalı.")


def _evidence(chunk: Chunk, quote: str) -> Evidence:
    return Evidence(chunk.id, chunk.page_id, chunk.page_number, chunk.source, quote)


def _mentioned(text: str, quote: str) -> bool:
    return normalize(quote).casefold() in normalize(text).casefold()


def _entity_name_supported(entity_type: str, name: str, quote: str) -> bool:
    normalized_name = normalize_entity_name(name)
    normalized_quote = normalize_entity_name(quote)
    if normalized_name in normalized_quote:
        return True
    aliases_by_type = {"component": COMPONENT_ALIASES, "system": SYSTEM_ALIASES,
                       "maintenance_action": ACTION_ALIASES}
    aliases = aliases_by_type.get(entity_type, {}).get(name.casefold().strip(), ())
    return any(normalize_entity_name(alias) in normalized_quote for alias in aliases)


def _entity(chunk: Chunk, entity_type: str, name: str, quote: str,
            confidence: float = 1.0) -> ExtractedEntity:
    normalized_name = normalize_entity_name(name)
    status = "verified" if confidence >= 0.8 else "needs_review"
    return ExtractedEntity(
        id=stable_id(chunk.vehicle_id, entity_type, normalized_name),
        type=entity_type,
        name=name,
        normalized_name=normalized_name,
        vehicle_id=chunk.vehicle_id,
        vehicle_model=chunk.vehicle_model,
        vehicle_year=chunk.vehicle_year,
        confidence=round(confidence, 3),
        status=status,
        evidence=(_evidence(chunk, quote),),
    )


def _find_aliases(chunk: Chunk, entity_type: str,
                  aliases_by_name: dict[str, tuple[str, ...]]) -> list[ExtractedEntity]:
    candidates = []
    for canonical, aliases in aliases_by_name.items():
        for alias in aliases:
            # Turkish technical nouns frequently carry case suffixes (akü -> aküyü,
            # sistem -> sistemi). Keep the full surface form as evidence.
            suffix = r"(?:y?[ıiuü]|n[ıiuü]|s[ıiuü]|[dt][ae]n|[dt][ae])?"
            for match in re.finditer(r"(?<!\w)" + re.escape(alias) + suffix + r"(?!\w)",
                                     chunk.text, re.IGNORECASE):
                candidates.append((match.start(), match.end(), canonical, match.group(0)))
    found = []
    for start, end, canonical, quote in candidates:
        if any(other_start <= start and end <= other_end and other_end - other_start > end - start
               for other_start, other_end, _, _ in candidates):
            continue
        found.append(_entity(chunk, entity_type, canonical, quote))
    return list(_merge_entities(found))


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def _merge_entities(entities: Iterable[ExtractedEntity]) -> tuple[ExtractedEntity, ...]:
    merged: dict[str, ExtractedEntity] = {}
    for entity in entities:
        current = merged.get(entity.id)
        if current is None:
            merged[entity.id] = entity
            continue
        evidence = tuple(dict.fromkeys(current.evidence + entity.evidence))
        merged[entity.id] = ExtractedEntity(
            **{**asdict(current), "evidence": evidence,
               "confidence": max(current.confidence, entity.confidence),
               "status": "verified" if max(current.confidence, entity.confidence) >= 0.8
               else "needs_review"}
        )
    return tuple(sorted(merged.values(), key=lambda item: (item.type, item.normalized_name)))


def _relationship(chunk: Chunk, relation_type: str, source: ExtractedEntity,
                  target: ExtractedEntity, quote: str, confidence: float,
                  properties: dict[str, Any] | None = None) -> ExtractedRelationship:
    status = "verified" if confidence >= 0.8 else "needs_review"
    return ExtractedRelationship(
        id=stable_id(chunk.vehicle_id, relation_type, source.id, target.id, chunk.id),
        type=relation_type,
        source_entity_id=source.id,
        target_entity_id=target.id,
        confidence=round(confidence, 3),
        status=status,
        properties=properties or {},
        evidence=(_evidence(chunk, quote),),
    )


def extract_rules(chunk: Chunk) -> ExtractionResult:
    entities: list[ExtractedEntity] = []
    entities.extend(_find_aliases(chunk, "component", COMPONENT_ALIASES))
    entities.extend(_find_aliases(chunk, "system", SYSTEM_ALIASES))
    entities.extend(_find_aliases(chunk, "maintenance_action", ACTION_ALIASES))
    for match in VALUE_PATTERN.finditer(chunk.text):
        entities.append(_entity(chunk, "technical_value", match.group(0), match.group(0)))
    for sentence in _sentences(chunk.text):
        if any(re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", sentence,
                         re.IGNORECASE) for word in WARNING_WORDS):
            entities.append(_entity(chunk, "warning", sentence[:240], sentence))
    consolidated = _merge_entities(entities)
    relationships = []
    for sentence in _sentences(chunk.text):
        present = [entity for entity in consolidated
                   if any(_mentioned(sentence, evidence.quote) for evidence in entity.evidence)]
        components = [entity for entity in present if entity.type == "component"]
        components = [entity for entity in components if not any(
            entity.normalized_name != other.normalized_name
            and entity.normalized_name in other.normalized_name
            for other in components)]
        actions = [entity for entity in present if entity.type == "maintenance_action"]
        values = [entity for entity in present if entity.type == "technical_value"]
        warnings = [entity for entity in present if entity.type == "warning"]
        systems = [entity for entity in present if entity.type == "system"]
        confidence = 1.0 if len(components) == 1 else 0.6
        for action in actions:
            for component in components:
                relationships.append(_relationship(chunk, "applies_to", action, component,
                                                   sentence, confidence))
        for component in components:
            for value in values:
                relationships.append(_relationship(chunk, "has_value", component, value,
                                                   sentence, confidence,
                                                   {"raw_value": value.name}))
        for warning in warnings:
            for component in components:
                relationships.append(_relationship(chunk, "warns_about", warning, component,
                                                   sentence, confidence))
        # Co-occurrence alone does not prove PART_OF, so keep it explicitly unverified.
        for component in components:
            for system in systems:
                relationships.append(_relationship(chunk, "part_of", component, system,
                                                   sentence, 0.6))
    metadata = {"name": "caragent-rules", "version": EXTRACTOR_VERSION,
                "mode": "rules", "parameters": {"language": "tr+en"}}
    return _result(chunk, metadata, consolidated, tuple(relationships))


LLM_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {"type": "array", "items": {"type": "object", "properties": {
            "local_id": {"type": "string"}, "type": {"type": "string"},
            "name": {"type": "string"}, "quote": {"type": "string"},
            "confidence": {"type": "number"}},
            "required": ["local_id", "type", "name", "quote", "confidence"],
            "additionalProperties": False}},
        "relationships": {"type": "array", "items": {"type": "object", "properties": {
            "type": {"type": "string"}, "source": {"type": "string"},
            "target": {"type": "string"}, "quote": {"type": "string"},
            "confidence": {"type": "number"}, "properties": {"type": "object"}},
            "required": ["type", "source", "target", "quote", "confidence", "properties"],
            "additionalProperties": False}},
    },
    "required": ["entities", "relationships"],
    "additionalProperties": False,
}


def extraction_prompt(chunk: Chunk) -> str:
    return (
        "You extract only explicitly supported facts from a Toyota manual chunk. "
        f"Allowed entity types: {', '.join(sorted(ENTITY_TYPES))}. "
        f"Allowed relationship types: {', '.join(sorted(RELATIONSHIP_TYPES))}. "
        "Every entity and relationship must contain an exact quote copied from SOURCE. "
        "Use local_id values to connect relationships. Do not infer faults, compatibility, "
        "causality, or unstated requirements. Mark ambiguity with confidence below 0.8. "
        "Return only JSON matching the supplied schema.\n\n"
        f"VEHICLE: {chunk.vehicle_model} {chunk.vehicle_year}\n"
        f"PAGE: {chunk.page_number}\nSOURCE:\n{chunk.text}"
    )


def _valid_confidence(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        return None
    return float(value)


def validate_llm_payload(chunk: Chunk, payload: Any, metadata: dict[str, Any]) -> ExtractionResult:
    warnings: list[str] = []
    if not isinstance(payload, dict) or not isinstance(payload.get("entities"), list) \
            or not isinstance(payload.get("relationships"), list):
        return _result(chunk, metadata, warnings=("LLM çıktısı geçerli extraction JSON'u değil.",))
    entities, local_ids = [], {}
    for index, candidate in enumerate(payload["entities"]):
        if not isinstance(candidate, dict):
            warnings.append(f"Entity {index} nesne olmadığı için reddedildi.")
            continue
        entity_type, name, quote = (candidate.get("type"), candidate.get("name"),
                                    candidate.get("quote"))
        confidence = _valid_confidence(candidate.get("confidence"))
        if entity_type not in ENTITY_TYPES:
            warnings.append(f"Desteklenmeyen entity türü reddedildi: {entity_type!r}.")
            continue
        if not all(isinstance(value, str) and value.strip() for value in
                   (candidate.get("local_id"), name, quote)) or confidence is None:
            warnings.append(f"Entity {index} eksik veya hatalı olduğu için reddedildi.")
            continue
        if not _mentioned(chunk.text, quote):
            warnings.append(f"Kaynakta bulunmayan entity reddedildi: {name!r}.")
            continue
        if not _entity_name_supported(entity_type, name, quote):
            warnings.append(f"Entity adı kaynak alıntısıyla desteklenmediği için reddedildi: {name!r}.")
            continue
        entity = _entity(chunk, entity_type, name.strip(), quote.strip(), confidence)
        entities.append(entity)
        local_ids[candidate["local_id"]] = entity
    consolidated = _merge_entities(entities)
    relationships = []
    for index, candidate in enumerate(payload["relationships"]):
        if not isinstance(candidate, dict):
            warnings.append(f"Relationship {index} nesne olmadığı için reddedildi.")
            continue
        relation_type, quote = candidate.get("type"), candidate.get("quote")
        confidence = _valid_confidence(candidate.get("confidence"))
        source, target = local_ids.get(candidate.get("source")), local_ids.get(candidate.get("target"))
        if relation_type not in RELATIONSHIP_TYPES:
            warnings.append(f"Desteklenmeyen relationship türü reddedildi: {relation_type!r}.")
            continue
        if (source is None or target is None or not isinstance(quote, str) or not quote.strip()
                or confidence is None or not isinstance(candidate.get("properties"), dict)):
            warnings.append(f"Relationship {index} eksik veya hatalı olduğu için reddedildi.")
            continue
        if not _mentioned(chunk.text, quote):
            warnings.append(f"Kaynakta bulunmayan relationship reddedildi: {relation_type!r}.")
            continue
        if not (_mentioned(quote, source.evidence[0].quote)
                and _mentioned(quote, target.evidence[0].quote)):
            warnings.append(
                f"Relationship endpoint'leri aynı kaynak alıntısıyla desteklenmediği için reddedildi: "
                f"{relation_type!r}."
            )
            continue
        relationships.append(_relationship(chunk, relation_type, source, target, quote.strip(),
                                           confidence, candidate["properties"]))
    return _result(chunk, metadata, consolidated, tuple(relationships), tuple(warnings))


def _result(chunk: Chunk, metadata: dict[str, Any],
            entities: tuple[ExtractedEntity, ...] = (),
            relationships: tuple[ExtractedRelationship, ...] = (),
            warnings: tuple[str, ...] = ()) -> ExtractionResult:
    return ExtractionResult(
        SCHEMA_VERSION, chunk.id, chunk.manual_id, chunk.page_id, chunk.page_number,
        chunk.source, chunk.vehicle_id, chunk.vehicle_model, chunk.vehicle_year,
        metadata, entities, relationships, warnings,
    )


class EntityExtractor:
    def __init__(self, config: ExtractorConfig | None = None,
                 client: httpx.Client | None = None):
        self.config = config or ExtractorConfig()
        self.client = client

    def extract(self, chunk: Chunk) -> ExtractionResult:
        if not isinstance(chunk, Chunk):
            raise TypeError("Extraction girdisi Chunk olmalı.")
        if self.config.mode == "rules":
            return extract_rules(chunk)
        metadata = {"name": "ollama", "version": EXTRACTOR_VERSION, "mode": "ollama",
                    "model": self.config.model,
                    "parameters": {"temperature": self.config.temperature}}
        request = {
            "model": self.config.model,
            "stream": False,
            "format": LLM_OUTPUT_SCHEMA,
            "options": {"temperature": self.config.temperature, "num_ctx": 8192,
                        "num_predict": 2048},
            "messages": [{"role": "system", "content": extraction_prompt(chunk)},
                         {"role": "user", "content": "Extract the grounded JSON now."}],
        }
        try:
            if self.client is not None:
                response = self.client.post(self.config.ollama_url.rstrip("/") + "/api/chat",
                                            json=request)
            else:
                with httpx.Client(timeout=self.config.timeout) as client:
                    response = client.post(self.config.ollama_url.rstrip("/") + "/api/chat",
                                           json=request)
            response.raise_for_status()
            content = response.json()["message"]["content"]
            payload = json.loads(content) if isinstance(content, str) else content
            return validate_llm_payload(chunk, payload, metadata)
        except (httpx.HTTPError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            return _result(chunk, metadata,
                           warnings=(f"LLM extraction kontrollü biçimde başarısız oldu ({type(exc).__name__}).",))


def extract_chunks(chunks: Iterable[Chunk], extractor: EntityExtractor | None = None) -> dict[str, Any]:
    extractor = extractor or EntityExtractor()
    results = [extractor.extract(chunk) for chunk in chunks]
    entities = _merge_entities(entity for result in results for entity in result.entities)
    relationships = {relationship.id: relationship for result in results
                     for relationship in result.relationships}
    return {
        "schema_version": SCHEMA_VERSION,
        "extractor": asdict(extractor.config),
        "chunks": [result.to_dict() for result in results],
        "entities": [asdict(entity) for entity in entities],
        "relationships": [asdict(value) for value in sorted(
            relationships.values(), key=lambda item: (item.type, item.id))],
        "summary": {"chunks": len(results), "entities": len(entities),
                    "relationships": len(relationships),
                    "warnings": sum(len(result.warnings) for result in results)},
    }


def _metric_counts(predicted: set[tuple], expected: set[tuple]) -> dict[str, float | int]:
    true_positive = len(predicted & expected)
    precision = true_positive / len(predicted) if predicted else (1.0 if not expected else 0.0)
    recall = true_positive / len(expected) if expected else (1.0 if not predicted else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"true_positive": true_positive, "predicted": len(predicted), "expected": len(expected),
            "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def evaluate_extraction(predicted: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    """Measure exact normalized entity and relationship labels."""
    predicted_entities = {(item["type"], normalize_entity_name(item["normalized_name"]))
                          for item in predicted.get("entities", [])}
    expected_entities = {(item["type"], normalize_entity_name(item["normalized_name"]))
                         for item in expected.get("entities", [])}
    predicted_relations = {(item["type"], item["source_entity_id"], item["target_entity_id"])
                           for item in predicted.get("relationships", [])}
    expected_relations = {(item["type"], item["source_entity_id"], item["target_entity_id"])
                          for item in expected.get("relationships", [])}
    entity_metrics = _metric_counts(predicted_entities, expected_entities)
    relationship_metrics = _metric_counts(predicted_relations, expected_relations)
    return {"schema_version": SCHEMA_VERSION, "entities": entity_metrics,
            "relationships": relationship_metrics,
            "macro_f1": round((entity_metrics["f1"] + relationship_metrics["f1"]) / 2, 4)}
