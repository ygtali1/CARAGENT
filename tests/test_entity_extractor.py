import json

import httpx
import pytest

from caragent.entity_extractor import (ENTITY_TYPES, RELATIONSHIP_TYPES, EntityExtractor,
                                       ExtractorConfig, evaluate_extraction, extract_chunks,
                                       extract_rules, validate_llm_payload)
from caragent.models import Chunk


def chunk(text, identifier="chunk-1", page=3):
    return Chunk(
        id=identifier,
        text=text,
        ordinal=0,
        page_ordinal=0,
        manual_id="manual-1",
        page_id=f"page-{page}",
        page_number=page,
        title="Maintenance",
        source=f"https://example.test/{page}",
        vehicle_id="vehicle-2024",
        vehicle_model="Corolla LE",
        vehicle_year=2024,
    )


def test_rule_extraction_is_grounded_bilingual_and_traceable():
    result = extract_rules(chunk(
        "UYARI: Motor yağı seviyesini kontrol edin. Tire pressure should be checked at 35 psi."
    ))
    entity_types = {entity.type for entity in result.entities}
    relation_types = {relationship.type for relationship in result.relationships}
    assert {"component", "maintenance_action", "warning", "technical_value"} <= entity_types
    assert {"applies_to", "has_value", "warns_about"} <= relation_types
    assert all(entity.type in ENTITY_TYPES for entity in result.entities)
    assert all(relationship.type in RELATIONSHIP_TYPES for relationship in result.relationships)
    assert all(evidence.chunk_id == "chunk-1" and evidence.page_number == 3
               for entity in result.entities for evidence in entity.evidence)
    assert all(evidence.quote.casefold() in result_text.casefold()
               for result_text in ["UYARI: Motor yağı seviyesini kontrol edin. "
                                   "Tire pressure should be checked at 35 psi."]
               for entity in result.entities for evidence in entity.evidence)


def test_ambiguous_cooccurrence_is_not_marked_verified():
    result = extract_rules(chunk("Check the brake and tire at 35 psi."))
    assert result.relationships
    assert all(relationship.status == "needs_review" and relationship.confidence < 0.8
               for relationship in result.relationships)


def test_empty_or_unrecognized_chunk_returns_an_empty_controlled_result():
    result = extract_rules(chunk(""))
    assert result.entities == ()
    assert result.relationships == ()
    assert result.schema_version == "caragent-extraction-v1"


def test_entities_are_deduplicated_across_chunks_but_keep_all_evidence():
    report = extract_chunks([
        chunk("Check engine oil.", "chunk-1", 1),
        chunk("Motor yağı seviyesini kontrol edin.", "chunk-2", 2),
    ])
    oil = [entity for entity in report["entities"]
           if entity["type"] == "component" and entity["normalized_name"] == "engine oil"]
    assert len(oil) == 1
    assert {evidence["chunk_id"] for evidence in oil[0]["evidence"]} == {"chunk-1", "chunk-2"}
    assert report["summary"]["chunks"] == 2


def test_llm_schema_validation_rejects_unknown_and_ungrounded_candidates():
    source = chunk("Check the engine oil at 35 psi.")
    payload = {
        "entities": [
            {"local_id": "e1", "type": "component", "name": "engine oil",
             "quote": "engine oil", "confidence": 0.99},
            {"local_id": "e2", "type": "technical_value", "name": "35 psi",
             "quote": "35 psi", "confidence": 0.99},
            {"local_id": "e3", "type": "fault", "name": "oil leak",
             "quote": "engine oil", "confidence": 0.9},
            {"local_id": "e4", "type": "component", "name": "alternator",
             "quote": "alternator", "confidence": 0.9},
            {"local_id": "e5", "type": "component", "name": "battery",
             "quote": "engine oil", "confidence": 0.9},
        ],
        "relationships": [
            {"type": "has_value", "source": "e1", "target": "e2",
             "quote": "engine oil at 35 psi", "confidence": 0.95, "properties": {}},
            {"type": "causes", "source": "e1", "target": "e2",
             "quote": "engine oil at 35 psi", "confidence": 0.95, "properties": {}},
        ],
    }
    result = validate_llm_payload(source, payload, {"model": "test"})
    assert {entity.name for entity in result.entities} == {"engine oil", "35 psi"}
    assert len(result.relationships) == 1
    assert any("Desteklenmeyen entity" in warning for warning in result.warnings)
    assert any("Kaynakta bulunmayan entity" in warning for warning in result.warnings)
    assert any("kaynak alıntısıyla desteklenmediği" in warning for warning in result.warnings)
    assert any("Desteklenmeyen relationship" in warning for warning in result.warnings)


def test_ollama_integration_parses_structured_json_and_handles_invalid_output():
    valid_payload = {"entities": [{"local_id": "e1", "type": "component",
                                   "name": "battery", "quote": "battery",
                                   "confidence": 0.9}], "relationships": []}

    def valid_handler(request):
        sent = json.loads(request.content)
        assert sent["format"]["additionalProperties"] is False
        return httpx.Response(200, json={"message": {"content": json.dumps(valid_payload)}})

    with httpx.Client(transport=httpx.MockTransport(valid_handler)) as client:
        extractor = EntityExtractor(ExtractorConfig(mode="ollama", model="test-model"), client)
        result = extractor.extract(chunk("Disconnect the battery."))
    assert len(result.entities) == 1 and not result.warnings
    assert result.extractor["model"] == "test-model"

    def invalid_handler(request):
        return httpx.Response(200, json={"message": {"content": "not-json"}})

    with httpx.Client(transport=httpx.MockTransport(invalid_handler)) as client:
        result = EntityExtractor(ExtractorConfig(mode="ollama"), client).extract(
            chunk("Disconnect the battery."))
    assert result.entities == () and "başarısız" in result.warnings[0]


def test_evaluation_reports_precision_recall_and_f1():
    predicted = {
        "entities": [{"type": "component", "normalized_name": "engine oil"},
                     {"type": "component", "normalized_name": "battery"}],
        "relationships": [{"type": "has_value", "source_entity_id": "oil",
                           "target_entity_id": "35psi"}],
    }
    expected = {
        "entities": [{"type": "component", "normalized_name": "engine oil"},
                     {"type": "component", "normalized_name": "brake"}],
        "relationships": [{"type": "has_value", "source_entity_id": "oil",
                           "target_entity_id": "35psi"}],
    }
    report = evaluate_extraction(predicted, expected)
    assert report["entities"]["precision"] == 0.5
    assert report["entities"]["recall"] == 0.5
    assert report["entities"]["f1"] == 0.5
    assert report["relationships"]["f1"] == 1.0
    assert report["macro_f1"] == 0.75


@pytest.mark.parametrize("kwargs", [
    {"mode": "invalid"}, {"temperature": -0.1}, {"timeout": 0}, {"model": " "},
])
def test_invalid_extractor_settings_are_controlled(kwargs):
    with pytest.raises(ValueError):
        ExtractorConfig(**kwargs)
