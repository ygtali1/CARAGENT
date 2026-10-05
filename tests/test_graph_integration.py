from dataclasses import replace
import os
import uuid

import pytest
from neo4j.exceptions import Neo4jError

from caragent.config import Settings
from caragent.graph import GraphStore
from caragent.models import Manual, Page, Vehicle


pytestmark = [pytest.mark.integration,
              pytest.mark.skipif(os.getenv("CARAGENT_INTEGRATION") != "1", reason="Set CARAGENT_INTEGRATION=1")]


def test_real_graph_ingestion_retrieval_isolation_replacement_and_rollback():
    store = GraphStore(Settings.load())
    vehicle = Vehicle("IntegrationFixture-" + uuid.uuid4().hex, 2024, "Synthetic test")
    other = replace(vehicle, year=2023)
    manual = Manual("fixture", "Synthetic engine oil fixture", vehicle, "en", "https://example.test/fixture",
                    (Page(1, "Engine oil inspection synthetic test. " * 100),))
    other_manual = replace(manual, vehicle=other)
    unrelated = replace(manual, key="camera", title="Camera engine controller",
                        pages=(Page(1, "Camera reports an engine controller communication code. " * 10),))
    try:
        store.initialize()
        assert store.ingest(manual)["status"] == "imported"
        assert store.ingest(manual)["status"] == "unchanged"
        store.ingest(other_manual)
        store.ingest(unrelated)
        sources = store.search("engine oil", vehicle.id, limit=2)
        assert sources and all(s["year"] == 2024 for s in sources)
        assert all(s["title"] != unrelated.title for s in sources)
        assert any(s["reason"] == "graph_neighbor" for s in sources)
        updated = replace(manual, title="Battery synthetic fixture", pages=(Page(1, "Battery synthetic fixture evidence. " * 10),))
        store.ingest(updated)
        assert not store.search("engine oil", vehicle.id)
        assert store.search("battery", vehicle.id)
        # Constraint violation after deletion must roll the old document back intact.
        page_row = {"id": "fixture-" + uuid.uuid4().hex, "number": 1, "title": "broken", "url": "", "images": []}
        row = {"id": "duplicate-" + uuid.uuid4().hex, "page_id": page_row["id"], "ordinal": 0,
               "text": "invalid replacement", "title": "broken", "previous": None, "components": []}
        with store.driver.session(database=store.settings.database) as session:
            with pytest.raises(Neo4jError):
                session.execute_write(store._write_manual, replace(updated, title="Broken"), [page_row], [row, row])
        assert store.search("battery", vehicle.id)
    finally:
        with store.driver.session(database=store.settings.database) as session:
            for manual_id in (manual.id, other_manual.id, unrelated.id):
                session.run("MATCH (n) WHERE (n:CaragentChunk OR n:CaragentPage) AND n.manual_id=$id DETACH DELETE n", id=manual_id).consume()
                session.run("MATCH (m:CaragentManual {id:$id}) DETACH DELETE m", id=manual_id).consume()
            session.run("MATCH (v:CaragentVehicle) WHERE v.id IN $ids DETACH DELETE v", ids=[vehicle.id, other.id]).consume()
        store.close()
