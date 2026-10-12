from types import SimpleNamespace

import pytest
from neo4j.exceptions import ServiceUnavailable

from caragent.graph import GraphStore, GraphStoreError


def settings(**overrides):
    values = {
        "neo4j_uri": "bolt://example.test:7687",
        "neo4j_user": "neo4j",
        "neo4j_password": "secret",
        "database": "neo4j",
        "neo4j_connection_timeout": 4.0,
        "neo4j_max_retry_time": 9.0,
        "neo4j_pool_size": 17,
        "neo4j_acquisition_timeout": 8.0,
        "neo4j_connection_lifetime": 90.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def extraction_payload():
    evidence = [{"chunk_id": "chunk-1", "page_id": "page-1", "page_number": 7,
                 "source": "https://example.test/manual#7", "quote": "Check engine oil."}]
    entities = [
        {"id": "entity-oil", "type": "component", "name": "engine oil",
         "normalized_name": "engine oil", "vehicle_id": "vehicle-1",
         "vehicle_model": "Corolla LE", "vehicle_year": 2024,
         "confidence": 1.0, "status": "verified", "evidence": evidence},
        {"id": "entity-check", "type": "maintenance_action", "name": "check",
         "normalized_name": "check", "vehicle_id": "vehicle-1",
         "vehicle_model": "Corolla LE", "vehicle_year": 2024,
         "confidence": 0.9, "status": "verified", "evidence": evidence},
    ]
    relationships = [
        {"id": "relationship-1", "type": "applies_to",
         "source_entity_id": "entity-check", "target_entity_id": "entity-oil",
         "confidence": 0.9, "status": "verified", "properties": {},
         "evidence": evidence},
    ]
    return {"entities": entities, "relationships": relationships}


def test_driver_uses_configured_pool_timeouts_and_close_is_idempotent(monkeypatch):
    captured = {}

    class Driver:
        closes = 0

        def close(self):
            self.closes += 1

    driver = Driver()

    def create(uri, **kwargs):
        captured.update(uri=uri, **kwargs)
        return driver

    monkeypatch.setattr("caragent.graph.GraphDatabase.driver", create)
    store = GraphStore(settings())
    store.close()
    store.close()

    assert driver.closes == 1
    assert captured["max_connection_pool_size"] == 17
    assert captured["connection_timeout"] == 4.0
    assert captured["connection_acquisition_timeout"] == 8.0


def test_search_parameterizes_filters_and_preserves_source_metadata():
    store = object.__new__(GraphStore)
    calls = []
    source = {"id": "chunk-1", "chunk_id": "chunk-1", "text": "Oil evidence",
              "title": "Lubrication", "page_id": "page-7", "page": 7,
              "url": "https://example.test/page/7", "images": [],
              "manual_id": "manual-1", "manual_title": "Repair Manual",
              "manual_source": "https://example.test/manual", "language": "en",
              "vehicle_id": "vehicle-1", "model": "Corolla LE", "year": 2024,
              "market": "US", "score": 2.1, "reason": "text_match"}

    def query(cypher, **params):
        calls.append((cypher, params))
        return [source] if len(calls) == 1 else []

    store._query = query
    result = store.search("engine oil", model="Corolla LE", year=2024,
                          manual_id="manual-1", page_number=7, limit=3)

    assert result == [source]
    cypher, params = calls[0]
    assert "Corolla LE" not in cypher and "manual-1" not in cypher
    assert params["model"] == "Corolla LE" and params["year"] == 2024
    assert params["manual"] == "manual-1" and params["page"] == 7
    assert "manual_source" in cypher and "chunk_id" in cypher and "page_id" in cypher


@pytest.mark.parametrize("field,value,message", [
    ("type", "invented", "entity türü"),
    ("status", "draft", "status"),
])
def test_extraction_rejects_unknown_entity_values(field, value, message):
    payload = extraction_payload()
    payload["entities"][0][field] = value
    with pytest.raises(ValueError, match=message):
        GraphStore._validated_extraction(payload)


def test_extraction_rejects_missing_and_cross_vehicle_endpoints():
    payload = extraction_payload()
    payload["relationships"][0]["target_entity_id"] = "missing"
    with pytest.raises(ValueError, match="endpoint"):
        GraphStore._validated_extraction(payload)

    payload = extraction_payload()
    payload["entities"][1]["vehicle_id"] = "vehicle-2"
    with pytest.raises(ValueError, match="farklı araç"):
        GraphStore._validated_extraction(payload)


def test_extraction_write_validates_provenance_and_uses_merge():
    statements = []

    class Result:
        def single(self):
            return {"invalid": []}

        def consume(self):
            return None

    class Tx:
        def run(self, cypher, **params):
            statements.append((cypher, params))
            return Result()

    entities, relationships = GraphStore._validated_extraction(extraction_payload())
    result = GraphStore._write_extraction(Tx(), entities, relationships, batch_size=1)

    assert result == {"status": "upserted", "entities": 2, "relationships": 1}
    joined = "\n".join(statement for statement, _ in statements)
    assert "HAS_MANUAL" in joined and "MERGE (e:CaragentEntity" in joined
    assert "MERGE (source)-[r:CaragentExtractedRelation" in joined
    relation_rows = next(params["rows"] for statement, params in statements
                         if "CaragentExtractedRelation {id:row.id}" in statement
                         and "SET r.kind" in statement)
    assert '"chunk_id": "chunk-1"' in relation_rows[0]["evidence_json"]


def test_ingest_extraction_reports_transaction_failure_without_partial_success():
    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def execute_write(self, *_args):
            raise ServiceUnavailable("offline")

    class Driver:
        def session(self, **_kwargs):
            return Session()

    store = object.__new__(GraphStore)
    store.driver = Driver()
    store.settings = settings()
    with pytest.raises(GraphStoreError, match="transaction"):
        store.ingest_extraction(extraction_payload())


def test_verify_exposes_controlled_connection_error():
    class Driver:
        def verify_connectivity(self):
            raise ServiceUnavailable("offline")

    store = object.__new__(GraphStore)
    store.driver = Driver()
    with pytest.raises(GraphStoreError, match="bağlantısı doğrulanamadı"):
        store.verify()


def test_search_rejects_unscoped_and_invalid_filters():
    store = object.__new__(GraphStore)
    with pytest.raises(ValueError, match="sınırlandırılmalı"):
        store.search("engine oil")
    with pytest.raises(ValueError, match="Sayfa"):
        store.search("engine oil", "vehicle-1", page_number=0)
