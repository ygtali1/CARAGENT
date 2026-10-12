from dataclasses import asdict
import json
import re

from neo4j import GraphDatabase
from neo4j.exceptions import DriverError

from .entity_extractor import (ENTITY_TYPES, RELATIONSHIP_ENDPOINTS, RELATIONSHIP_TYPES,
                               SCHEMA_VERSION, ExtractionResult, ExtractedEntity,
                               ExtractedRelationship)
from .models import (COMPONENTS, QUESTION_TAXONOMY, ChunkingConfig, Manual,
                     chunks_for_manual, components, question_context,
                     question_intent, stable_id)

STOP_WORDS = set("a an the is are how what where when to of for and in on do does can i my with please toyota corolla hangi nasıl nasil nedir ne bir ve için icin mı mi mu bu nerede kaç kac var kontrol edilir yapabilirim yapilir yapılır".split())
EXTRACTION_STATUSES = frozenset({"verified", "needs_review"})
ENTITY_LABELS = {
    "component": "ComponentEntity", "system": "SystemEntity",
    "maintenance_action": "MaintenanceAction", "warning": "WarningEntity",
    "technical_value": "TechnicalValue", "feature": "FeatureEntity",
    "symptom": "SymptomEntity", "fluid": "FluidEntity", "recall": "RecallEntity",
}
RELATIONSHIP_DB_TYPES = {name: name.upper() for name in RELATIONSHIP_TYPES}


class GraphStoreError(RuntimeError):
    """Controlled graph failure suitable for CLI/API error reporting."""


def _batches(rows, size):
    for start in range(0, len(rows), size):
        yield rows[start:start + size]


def search_query(question: str) -> str:
    """Quote only word tokens: user input cannot become Lucene operators."""
    words = re.findall(r"[^\W_]+", question.casefold(), re.UNICODE)
    words = [w for w in words if w not in STOP_WORDS and len(w) > 1][:24]
    for component in components(question):
        words.extend(re.findall(r"\w+", COMPONENTS[component][0]))
    # Frequent Turkish search phrases used against English manuals.
    for tr, en in {"basınç": "pressure", "basinc": "pressure", "basıncı": "pressure",
                   "değişim": "replacement", "degisim": "replacement", "değiştirme": "replacement",
                   "sıvı": "fluid", "sivi": "fluid", "seviye": "level", "seviyesi": "level",
                   "tork": "torque", "uyarı": "warning", "uyari": "warning",
                   "bakım": "maintenance", "bakim": "maintenance", "aralık": "interval",
                   "aralığ": "interval", "aralik": "interval", "direksiyon": "steering",
                   "ağır": "heavy", "agir": "heavy", "titreşim": "vibration",
                   "titresim": "vibration", "arıza": "malfunction", "ariza": "malfunction",
                   "belirti": "symptom", "geri çağır": "recall", "geri cagir": "recall",
                   "anahtar": "key", "uzaktan": "remote", "ekran": "screen",
                   "telefon": "phone", "şerit": "lane", "serit": "lane",
                   "kamera": "camera"}.items():
        if tr in question.casefold():
            words.append(en)
    words = list(dict.fromkeys(words))
    return " OR ".join('"' + word + '"' for word in words)


class GraphStore:
    def __init__(self, settings):
        self.settings = settings
        self._closed = False
        self.driver = GraphDatabase.driver(settings.neo4j_uri,
                                          auth=(settings.neo4j_user, settings.neo4j_password),
                                          connection_timeout=settings.neo4j_connection_timeout,
                                          max_transaction_retry_time=settings.neo4j_max_retry_time,
                                          max_connection_pool_size=settings.neo4j_pool_size,
                                          connection_acquisition_timeout=settings.neo4j_acquisition_timeout,
                                          max_connection_lifetime=settings.neo4j_connection_lifetime)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        if not self._closed:
            self.driver.close()
            self._closed = True

    def verify(self):
        try:
            self.driver.verify_connectivity()
        except (DriverError, OSError) as exc:
            raise GraphStoreError(f"Neo4j bağlantısı doğrulanamadı ({type(exc).__name__}).") from exc

    def _query(self, cypher, **params):
        try:
            with self.driver.session(database=self.settings.database) as session:
                return session.execute_read(
                    lambda tx: [record.data() for record in tx.run(cypher, parameters=params)])
        except (DriverError, OSError) as exc:
            raise GraphStoreError(f"Neo4j sorgusu tamamlanamadı ({type(exc).__name__}).") from exc

    def initialize(self):
        try:
            with self.driver.session(database=self.settings.database) as session:
                for label in ("Vehicle", "Manual", "Page", "Chunk", "Topic", "Entity",
                              "QuestionCategory", "QuestionSystem"):
                    session.run(f"CREATE CONSTRAINT caragent_{label.lower()}_id IF NOT EXISTS "
                                f"FOR (n:Caragent{label}) REQUIRE n.id IS UNIQUE").consume()
                session.run("""CREATE FULLTEXT INDEX caragent_chunks IF NOT EXISTS
                    FOR (n:CaragentChunk) ON EACH [n.text, n.title]
                    OPTIONS {indexConfig: {`fulltext.analyzer`: 'standard-no-stop-words'}}""").consume()
                session.run("CALL db.awaitIndexes(120)").consume()
        except (DriverError, OSError) as exc:
            raise GraphStoreError(
                f"Neo4j şeması hazırlanamadı ({type(exc).__name__}).") from exc

    def ingest(self, manual: Manual, chunking: ChunkingConfig | None = None) -> dict:
        chunking = chunking or ChunkingConfig()
        rows, chunk_rows = [], []
        for page in manual.pages:
            page_id = stable_id(manual.id, page.number)
            rows.append({"id": page_id, "number": page.number, "title": page.title or manual.title,
                         "url": page.url or manual.source, "images": list(page.images)})
        previous_by_page = {}
        for chunk in chunks_for_manual(manual, chunking):
            previous = previous_by_page.get(chunk.page_id)
            chunk_rows.append({"id": chunk.id, "page_id": chunk.page_id,
                               "ordinal": chunk.page_ordinal, "text": chunk.text,
                               "title": chunk.title, "previous": previous,
                               "components": components(chunk.text),
                               "categories": [{"id": category,
                                               "title": QUESTION_TAXONOMY[category]["title"],
                                               "priority": QUESTION_TAXONOMY[category]["priority"]}
                                              for category in chunk.question_categories],
                               "systems": list(chunk.systems), "priority": chunk.priority})
            previous_by_page[chunk.page_id] = chunk.id
        if not chunk_rows:
            raise ValueError("İçe aktarılabilir metin parçası yok.")
        try:
            with self.driver.session(database=self.settings.database) as session:
                return session.execute_write(self._write_manual, manual, rows, chunk_rows,
                                             manual.content_hash_for(chunking))
        except (DriverError, OSError) as exc:
            raise GraphStoreError(
                f"{manual.title!r} Neo4j transaction'ı tamamlanamadı ({type(exc).__name__})."
            ) from exc

    @staticmethod
    def _write_manual(tx, manual, pages, chunks, content_hash=None):
        content_hash = content_hash or manual.content_hash_for(ChunkingConfig())
        existing = tx.run("MATCH (m:CaragentManual {id:$id}) RETURN m.content_hash AS hash", id=manual.id).single()
        if existing and existing["hash"] == content_hash:
            return {"title": manual.title, "status": "unchanged", "pages": len(pages), "chunks": len(chunks)}
        # All replacement mutations live in one transaction. Only this document's nodes are touched.
        tx.run("MATCH (c:CaragentChunk {manual_id:$id}) DETACH DELETE c", id=manual.id).consume()
        tx.run("MATCH (p:CaragentPage {manual_id:$id}) DETACH DELETE p", id=manual.id).consume()
        tx.run("""MERGE (v:CaragentVehicle {id:$vehicle_id}) SET v += $vehicle
            MERGE (m:CaragentManual {id:$id}) SET m.title=$title, m.source=$source,
                m.language=$language, m.content_hash=$hash, m.updated_at=datetime()
            MERGE (v)-[:HAS_MANUAL]->(m)""", vehicle_id=manual.vehicle.id,
               vehicle=asdict(manual.vehicle), id=manual.id, title=manual.title,
               source=manual.source, language=manual.language, hash=content_hash).consume()
        tx.run("""MATCH (m:CaragentManual {id:$id}) UNWIND $pages AS row
            CREATE (p:CaragentPage) SET p += row, p.manual_id=$id
            CREATE (m)-[:HAS_PAGE]->(p)""", id=manual.id, pages=pages).consume()
        tx.run("""UNWIND $chunks AS row MATCH (p:CaragentPage {id:row.page_id})
            CREATE (c:CaragentChunk {id:row.id, manual_id:$id, ordinal:row.ordinal,
                text:row.text, title:row.title, question_categories:[x IN row.categories | x.id],
                systems:row.systems, priority:row.priority}) CREATE (p)-[:HAS_CHUNK]->(c)
            FOREACH (name IN row.components |
                MERGE (topic:CaragentTopic {id:name}) SET topic.name=name
                MERGE (c)-[:MENTIONS]->(topic))
            FOREACH (category IN row.categories |
                MERGE (q:CaragentQuestionCategory {id:category.id})
                SET q.title=category.title, q.priority=category.priority
                MERGE (c)-[:ANSWERS]->(q))
            FOREACH (system IN row.systems |
                MERGE (s:CaragentQuestionSystem {id:system}) SET s.name=system
                MERGE (c)-[:ABOUT_SYSTEM]->(s))""", id=manual.id, chunks=chunks).consume()
        tx.run("""UNWIND $chunks AS row WITH row WHERE row.previous IS NOT NULL
            MATCH (a:CaragentChunk {id:row.previous}), (b:CaragentChunk {id:row.id})
            MERGE (a)-[:NEXT]->(b)""", chunks=chunks).consume()
        return {"title": manual.title, "status": "imported", "pages": len(pages), "chunks": len(chunks)}

    def reset(self) -> dict:
        """Delete only CARAGENT-owned graph nodes so the pipeline can be rebuilt safely."""
        try:
            with self.driver.session(database=self.settings.database) as session:
                deleted = session.execute_write(self._reset)
            self.initialize()
            return {"status": "reset", "deleted_nodes": deleted}
        except (DriverError, OSError) as exc:
            raise GraphStoreError(
                f"CARAGENT graph sıfırlanamadı ({type(exc).__name__}).") from exc

    @staticmethod
    def _reset(tx):
        record = tx.run("""MATCH (n)
            WHERE any(label IN labels(n) WHERE label STARTS WITH 'Caragent')
            RETURN count(n) AS count""").single()
        count = record["count"] if record else 0
        tx.run("""MATCH (n)
            WHERE any(label IN labels(n) WHERE label STARTS WITH 'Caragent')
            DETACH DELETE n""").consume()
        return count

    @staticmethod
    def _validated_extraction(payload):
        if isinstance(payload, ExtractionResult):
            payload = payload.to_dict()
        if not isinstance(payload, dict):
            raise TypeError("Extraction payload nesne olmalı.")
        if payload.get("schema_version") not in (None, SCHEMA_VERSION):
            raise ValueError(
                f"Extraction şeması {SCHEMA_VERSION} olmalı; eski çıktı yeniden üretilmeli.")
        raw_entities, raw_relationships = payload.get("entities"), payload.get("relationships")
        if not isinstance(raw_entities, (list, tuple)) or not isinstance(raw_relationships, (list, tuple)):
            raise ValueError("Extraction payload entities ve relationships listelerini içermeli.")
        entities = {}
        for item in raw_entities:
            if isinstance(item, ExtractedEntity):
                item = asdict(item)
            if not isinstance(item, dict) or item.get("type") not in ENTITY_TYPES:
                raise ValueError(f"İzin verilmeyen veya hatalı entity türü: {getattr(item, 'type', None) or (item.get('type') if isinstance(item, dict) else None)!r}.")
            if item.get("status") not in EXTRACTION_STATUSES:
                raise ValueError("Entity status verified veya needs_review olmalı.")
            confidence = item.get("confidence")
            required = ("id", "name", "normalized_name", "vehicle_id", "vehicle_model")
            if (any(not isinstance(item.get(key), str) or not item[key].strip() for key in required)
                    or isinstance(item.get("vehicle_year"), bool)
                    or not isinstance(item.get("vehicle_year"), int)
                    or isinstance(confidence, bool) or not isinstance(confidence, (int, float))
                    or not 0 <= confidence <= 1):
                raise ValueError("Entity zorunlu alanları veya confidence değeri geçersiz.")
            evidence = GraphStore._validated_evidence(item.get("evidence"))
            categories = item.get("question_categories", ())
            systems = item.get("systems", ())
            priority = item.get("priority", "P2")
            attributes = item.get("attributes", {})
            if (not isinstance(categories, (list, tuple))
                    or not all(value in QUESTION_TAXONOMY for value in categories)
                    or not isinstance(systems, (list, tuple))
                    or not all(isinstance(value, str) and value for value in systems)
                    or priority not in {"P0", "P1", "P2"}
                    or not isinstance(attributes, dict)):
                raise ValueError("Entity soru kategorisi, sistem, öncelik veya attributes alanı geçersiz.")
            row = {key: item[key] for key in required}
            row.update(type=item["type"], vehicle_year=item["vehicle_year"],
                       confidence=float(confidence), status=item["status"], evidence=evidence,
                       question_categories=list(dict.fromkeys(categories)),
                       systems=list(dict.fromkeys(systems)), priority=priority,
                       attributes_json=json.dumps(attributes, ensure_ascii=False, sort_keys=True))
            if item["id"] in entities and entities[item["id"]] != row:
                raise ValueError(f"Aynı entity kimliği çelişkili içerikle tekrarlandı: {item['id']}.")
            entities[item["id"]] = row
        relationships = {}
        for item in raw_relationships:
            if isinstance(item, ExtractedRelationship):
                item = asdict(item)
            if not isinstance(item, dict) or item.get("type") not in RELATIONSHIP_TYPES:
                raise ValueError(f"İzin verilmeyen veya hatalı relationship türü: {item.get('type') if isinstance(item, dict) else None!r}.")
            if item.get("status") not in EXTRACTION_STATUSES:
                raise ValueError("Relationship status verified veya needs_review olmalı.")
            confidence = item.get("confidence")
            source, target = item.get("source_entity_id"), item.get("target_entity_id")
            if (not isinstance(item.get("id"), str) or not item["id"].strip()
                    or source not in entities or target not in entities
                    or isinstance(confidence, bool) or not isinstance(confidence, (int, float))
                    or not 0 <= confidence <= 1 or not isinstance(item.get("properties"), dict)):
                raise ValueError("Relationship endpoint, properties veya confidence değeri geçersiz.")
            if entities[source]["vehicle_id"] != entities[target]["vehicle_id"]:
                raise ValueError("Relationship farklı araç bağlamlarındaki entity'leri bağlayamaz.")
            allowed_source, allowed_target = RELATIONSHIP_ENDPOINTS[item["type"]]
            if (entities[source]["type"] not in allowed_source
                    or entities[target]["type"] not in allowed_target):
                raise ValueError("Relationship yönü veya endpoint entity türleri geçersiz.")
            evidence = GraphStore._validated_evidence(item.get("evidence"))
            row = {"id": item["id"], "type": item["type"], "source_entity_id": source,
                   "target_entity_id": target, "confidence": float(confidence),
                   "status": item["status"], "properties_json": json.dumps(
                       item["properties"], ensure_ascii=False, sort_keys=True),
                   "evidence": evidence, "evidence_json": json.dumps(
                       evidence, ensure_ascii=False, sort_keys=True),
                   "vehicle_id": entities[source]["vehicle_id"]}
            if item["id"] in relationships and relationships[item["id"]] != row:
                raise ValueError(f"Aynı relationship kimliği çelişkili içerikle tekrarlandı: {item['id']}.")
            relationships[item["id"]] = row
        return list(entities.values()), list(relationships.values())

    @staticmethod
    def _validated_evidence(evidence):
        if not isinstance(evidence, (list, tuple)) or not evidence:
            raise ValueError("Extraction kaydı en az bir kaynak kanıtı içermeli.")
        result = []
        for item in evidence:
            if not isinstance(item, dict):
                try:
                    item = asdict(item)
                except TypeError as exc:
                    raise ValueError("Extraction evidence nesnesi geçersiz.") from exc
            required = ("chunk_id", "page_id", "source", "quote")
            if (any(not isinstance(item.get(key), str) or not item[key].strip() for key in required)
                    or isinstance(item.get("page_number"), bool)
                    or not isinstance(item.get("page_number"), int) or item["page_number"] < 1):
                raise ValueError("Extraction evidence kaynak alanları geçersiz.")
            result.append({key: item[key] for key in (*required, "page_number")})
        return result

    @staticmethod
    def validate_extraction_sources(payload, manuals,
                                    chunking: ChunkingConfig | None = None) -> dict:
        """Preflight extraction provenance against a manifest before a graph reset."""
        entities, relationships = GraphStore._validated_extraction(payload)
        chunking = chunking or ChunkingConfig()
        chunks = {}
        for manual in manuals:
            for chunk in chunks_for_manual(manual, chunking):
                existing = chunks.get(chunk.id)
                if existing is not None and existing != chunk:
                    raise ValueError(f"Manifestte çelişkili chunk kimliği bulundu: {chunk.id}.")
                chunks[chunk.id] = chunk
        for row in (*entities, *relationships):
            for evidence in row["evidence"]:
                chunk = chunks.get(evidence["chunk_id"])
                if (chunk is None or chunk.vehicle_id != row["vehicle_id"]
                        or chunk.page_id != evidence["page_id"]
                        or chunk.page_number != evidence["page_number"]
                        or chunk.source != evidence["source"]):
                    raise ValueError(
                        "Extraction kaynağı manifestteki yeni chunk yapısıyla uyuşmuyor: "
                        f"{evidence['chunk_id']}.")
        return {"chunks": len(chunks), "entities": len(entities),
                "relationships": len(relationships)}

    def ingest_extraction(self, payload, batch_size=500) -> dict:
        """Atomically store validated extraction as typed domain nodes and relationships."""
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or not 1 <= batch_size <= 5000:
            raise ValueError("Extraction batch boyutu 1–5000 arasında olmalı.")
        entities, relationships = self._validated_extraction(payload)
        if not entities and not relationships:
            return {"status": "unchanged", "entities": 0, "relationships": 0}
        try:
            with self.driver.session(database=self.settings.database) as session:
                return session.execute_write(
                    self._write_extraction, entities, relationships, batch_size)
        except ValueError:
            raise
        except (DriverError, OSError) as exc:
            raise GraphStoreError(
                f"Extraction Neo4j transaction'ı tamamlanamadı ({type(exc).__name__})."
            ) from exc

    @staticmethod
    def _write_extraction(tx, entities, relationships, batch_size):
        evidence_rows = [
            {**evidence, "vehicle_id": entity["vehicle_id"]}
            for entity in entities for evidence in entity["evidence"]
        ] + [
            {**evidence, "vehicle_id": relationship["vehicle_id"]}
            for relationship in relationships for evidence in relationship["evidence"]
        ]
        evidence_rows = list({(row["chunk_id"], row["vehicle_id"], row["page_id"],
                               row["page_number"], row["source"]): row
                              for row in evidence_rows}.values())
        for batch in _batches(evidence_rows, batch_size):
            record = tx.run("""UNWIND $rows AS row
                OPTIONAL MATCH (c:CaragentChunk {id:row.chunk_id})
                OPTIONAL MATCH (v:CaragentVehicle {id:row.vehicle_id})-[:HAS_MANUAL]->
                    (m:CaragentManual)-[:HAS_PAGE]->(p:CaragentPage)-[:HAS_CHUNK]->(c)
                WITH row, c, v, m, p
                WHERE c IS NULL OR v IS NULL OR p.id <> row.page_id
                    OR p.number <> row.page_number OR p.url <> row.source
                RETURN collect(row.chunk_id) AS invalid""", rows=batch).single()
            invalid = record["invalid"] if record else []
            if invalid:
                raise ValueError("Extraction kaynak chunk'ı bulunamadı veya araç bağlamı uyuşmadı: "
                                 + ", ".join(sorted(set(invalid))[:5]))
        for batch in _batches(entities, batch_size):
            record = tx.run("""UNWIND $rows AS row
                OPTIONAL MATCH (e:CaragentEntity {id:row.id})
                WITH row, e
                WHERE e IS NOT NULL AND (e.type <> row.type OR e.vehicle_id <> row.vehicle_id)
                RETURN collect(row.id) AS invalid""", rows=batch).single()
            invalid = record["invalid"] if record else []
            if invalid:
                raise ValueError("Entity kimliği başka tür veya araç için kullanılmış: "
                                 + ", ".join(sorted(set(invalid))[:5]))
            tx.run("""UNWIND $rows AS row
                MERGE (e:CaragentEntity {id:row.id})
                SET e.type=row.type, e.name=row.name, e.normalized_name=row.normalized_name,
                    e.vehicle_id=row.vehicle_id, e.vehicle_model=row.vehicle_model,
                    e.vehicle_year=row.vehicle_year, e.confidence=row.confidence,
                    e.status=row.status, e.question_categories=row.question_categories,
                    e.systems=row.systems, e.priority=row.priority,
                    e.attributes_json=row.attributes_json, e.updated_at=datetime()
                WITH e, row
                MATCH (v:CaragentVehicle {id:row.vehicle_id})
                MERGE (e)-[:APPLIES_TO_VEHICLE]->(v)
                WITH e, row UNWIND row.evidence AS evidence
                MATCH (c:CaragentChunk {id:evidence.chunk_id})
                MERGE (c)-[s:SUPPORTS]->(e)
                SET s.page_id=evidence.page_id, s.page_number=evidence.page_number,
                    s.source=evidence.source, s.quote=evidence.quote""", rows=batch).consume()
        for entity_type, label in ENTITY_LABELS.items():
            typed_rows = [row for row in entities if row["type"] == entity_type]
            for batch in _batches(typed_rows, batch_size):
                tx.run(f"""UNWIND $rows AS row
                    MATCH (e:CaragentEntity {{id:row.id}})
                    SET e:Caragent{label}""", rows=batch).consume()
        for relation_type, db_type in RELATIONSHIP_DB_TYPES.items():
            typed_rows = [row for row in relationships if row["type"] == relation_type]
            for batch in _batches(typed_rows, batch_size):
                record = tx.run("""UNWIND $rows AS row
                    OPTIONAL MATCH (actualSource:CaragentEntity)-[r]->(actualTarget:CaragentEntity)
                    WHERE r.id=row.id
                    WITH row, r, actualSource, actualTarget
                    WHERE r IS NOT NULL AND (actualSource.id <> row.source_entity_id
                        OR actualTarget.id <> row.target_entity_id OR type(r) <> $db_type)
                    RETURN collect(row.id) AS invalid""", rows=batch, db_type=db_type).single()
                invalid = record["invalid"] if record else []
                if invalid:
                    raise ValueError("Relationship kimliği farklı tür veya endpoint için kullanılmış: "
                                     + ", ".join(sorted(set(invalid))[:5]))
                tx.run(f"""UNWIND $rows AS row
                    MATCH (source:CaragentEntity {{id:row.source_entity_id}})
                    MATCH (target:CaragentEntity {{id:row.target_entity_id}})
                    MERGE (source)-[r:{db_type} {{id:row.id}}]->(target)
                    SET r.confidence=row.confidence, r.status=row.status,
                        r.properties_json=row.properties_json,
                        r.evidence_json=row.evidence_json, r.updated_at=datetime()""",
                       rows=batch).consume()
        return {"status": "upserted", "entities": len(entities),
                "relationships": len(relationships)}

    def vehicles(self):
        return self._query("""MATCH (v:CaragentVehicle) OPTIONAL MATCH (v)-[:HAS_MANUAL]->(m)
            RETURN v.id AS id, v.make AS make, v.model AS model, v.year AS year,
                v.market AS market, count(m) AS manuals ORDER BY year DESC, model""")

    def stats(self):
        return self._query("""MATCH (n) WHERE any(l IN labels(n) WHERE l STARTS WITH 'Caragent')
            RETURN labels(n)[0] AS label, count(n) AS count ORDER BY label""")

    def rag_overview(self):
        """Return compact counts used by the local operations/UI surface."""
        return {
            "nodes": self.stats(),
            "relationships": self._query("""MATCH (:CaragentEntity)-[r]->(:CaragentEntity)
                RETURN type(r) AS type, count(r) AS count ORDER BY count DESC, type"""),
            "categories": self._query("""MATCH (c:CaragentChunk)-[:ANSWERS]->
                    (q:CaragentQuestionCategory)
                RETURN q.id AS id, q.title AS title, q.priority AS priority,
                    count(c) AS chunks ORDER BY chunks DESC, id"""),
        }

    def domain_facts(self, question: str, vehicle_id: str, limit=10):
        """Find typed graph facts anchored to entity names present in the question."""
        query = search_query(question)
        terms = re.findall(r'"([^\"]+)"', query)
        if not terms:
            return []
        intent = question_intent(question)
        if intent == "maintenance_interval":
            preferred = ["HAS_INTERVAL", "HAS_VALUE", "APPLIES_TO", "REQUIRES"]
        elif intent == "troubleshooting":
            preferred = ["WARNS_ABOUT", "INDICATES", "RESOLVED_BY", "AFFECTS"]
        elif intent == "recall":
            preferred = ["AFFECTS"]
        else:
            preferred = ["APPLIES_TO", "HAS_VALUE", "PART_OF"]
        rows = self._query("""MATCH (v:CaragentVehicle {id:$vehicle})
            <-[:APPLIES_TO_VEHICLE]-(matched:CaragentEntity)
            WHERE matched.type IN ['component', 'system', 'fluid', 'feature', 'symptom', 'recall']
            WITH matched, size([term IN $terms WHERE
                toLower(matched.normalized_name) CONTAINS term OR
                (size(matched.normalized_name) >= 4 AND
                 term CONTAINS toLower(matched.normalized_name))]) AS match_score
            WHERE match_score > 0
            WITH collect({node:matched, score:match_score}) AS candidates
            WITH candidates, reduce(best=0, candidate IN candidates |
                CASE WHEN candidate.score > best THEN candidate.score ELSE best END) AS best
            UNWIND candidates AS candidate
            WITH candidate.node AS matched, candidate.score AS match_score, best
            WHERE match_score=best
            MATCH (source:CaragentEntity)-[r]->(target:CaragentEntity)
            WHERE (source=matched OR target=matched)
              AND source.vehicle_id=$vehicle AND target.vehicle_id=$vehicle
              AND type(r) IN $relationship_types
            WITH source, r, target, max(match_score) AS match_score
            ORDER BY match_score DESC,
                CASE WHEN type(r) IN $preferred THEN 0 ELSE 1 END,
                r.confidence DESC,
                CASE r.status WHEN 'verified' THEN 0 ELSE 1 END,
                source.normalized_name, target.normalized_name
            RETURN r.id AS id, type(r) AS type,
                source.id AS source_id, source.type AS source_type,
                source.name AS source_name, target.id AS target_id,
                target.type AS target_type, target.name AS target_name,
                r.confidence AS confidence, r.status AS status,
                match_score,
                r.properties_json AS properties_json,
                r.evidence_json AS evidence_json LIMIT $limit""",
                           vehicle=vehicle_id, terms=terms,
                           relationship_types=sorted(RELATIONSHIP_DB_TYPES.values()),
                           preferred=preferred, limit=limit)
        for row in rows:
            try:
                row["properties"] = json.loads(row.pop("properties_json") or "{}")
                row["evidence"] = json.loads(row.pop("evidence_json") or "[]")
            except (TypeError, json.JSONDecodeError):
                row["properties"], row["evidence"] = {}, []
        return rows

    def _sources_for_chunk_ids(self, chunk_ids, vehicle_id):
        chunk_ids = list(dict.fromkeys(chunk_ids))
        if not chunk_ids:
            return []
        return self._query("""UNWIND range(0, size($ids)-1) AS rank
            WITH rank, $ids[rank] AS chunk_id
            MATCH (v:CaragentVehicle {id:$vehicle})-[:HAS_MANUAL]->(m:CaragentManual)
                -[:HAS_PAGE]->(p:CaragentPage)-[:HAS_CHUNK]->(c:CaragentChunk {id:chunk_id})
            RETURN c.id AS id, c.id AS chunk_id, c.text AS text, c.title AS title,
                p.id AS page_id, p.number AS page, p.url AS url, p.images AS images,
                m.id AS manual_id, m.title AS manual_title, m.source AS manual_source,
                m.language AS language, v.id AS vehicle_id,
                v.model AS model, v.year AS year, v.market AS market,
                1.0 / (rank + 1) AS score, 'graph_fact' AS reason
            ORDER BY rank""", ids=chunk_ids, vehicle=vehicle_id)

    def retrieve(self, question: str, vehicle_id: str, limit=5):
        """Orchestrate text, semantic taxonomy and typed graph-fact retrieval."""
        categories, systems, priority = question_context(question)
        text_sources = self.search(question, vehicle_id, limit)
        facts = self.domain_facts(question, vehicle_id, limit=max(8, limit * 2))
        intent = question_intent(question, categories)
        if intent == "maintenance_interval":
            useful_types = {"HAS_INTERVAL"}
        elif intent == "troubleshooting":
            useful_types = {"WARNS_ABOUT", "INDICATES", "RESOLVED_BY", "AFFECTS"}
        elif intent == "recall":
            useful_types = {"AFFECTS"}
        elif intent == "procedure":
            useful_types = {"APPLIES_TO", "REQUIRES", "RESOLVED_BY"}
        else:
            useful_types = {"HAS_VALUE", "PART_OF", "APPLIES_TO"}
        facts = [fact for fact in facts if fact["type"] in useful_types]
        evidence_ids = [evidence["chunk_id"] for fact in facts
                        for evidence in fact.get("evidence", ())
                        if isinstance(evidence, dict) and evidence.get("chunk_id")]
        fact_sources = self._sources_for_chunk_ids(evidence_ids, vehicle_id)

        selected, seen = [], set()
        reserve = min(2, len(fact_sources))
        for source in text_sources[:max(1, limit - reserve)]:
            selected.append(source)
            seen.add(source["chunk_id"])
        for source in fact_sources:
            if source["chunk_id"] not in seen:
                selected.append(source)
                seen.add(source["chunk_id"])
            if len(selected) >= limit:
                break
        for source in text_sources:
            if len(selected) >= limit:
                break
            if source["chunk_id"] not in seen:
                selected.append(source)
                seen.add(source["chunk_id"])
        return {
            "sources": selected,
            "facts": facts,
            "plan": {"categories": categories, "systems": systems, "priority": priority,
                     "text_candidates": len(text_sources),
                     "graph_facts": len(facts), "selected_sources": len(selected)},
        }

    def search(self, question: str, vehicle_id: str | None = None, limit=5, *,
               model: str | None = None, year: int | None = None,
               manual_id: str | None = None, page_number: int | None = None):
        query = search_query(question)
        if not query:
            return []
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10:
            raise ValueError("Sonuç sayısı 1–10 olmalı.")
        if not any(value is not None for value in (vehicle_id, model, year, manual_id)):
            raise ValueError("Arama vehicle_id, model/yıl veya manual_id ile sınırlandırılmalı.")
        if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
            raise ValueError("Araç yılı tam sayı olmalı.")
        if page_number is not None and (isinstance(page_number, bool)
                                        or not isinstance(page_number, int)
                                        or page_number < 1):
            raise ValueError("Sayfa numarası pozitif tam sayı olmalı.")
        for label, value in (("vehicle_id", vehicle_id), ("model", model),
                             ("manual_id", manual_id)):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{label} boş olmayan metin olmalı.")
        topics = components(question)
        question_categories, question_systems, _ = question_context(question)
        if "engine_oil" in topics and "engine" in topics:
            topics.remove("engine")
        seeds = self._query("""CALL db.index.fulltext.queryNodes('caragent_chunks', $query)
            YIELD node AS c, score
            MATCH (v:CaragentVehicle)-[:HAS_MANUAL]->(m)-[:HAS_PAGE]->(p)-[:HAS_CHUNK]->(c)
            WHERE ($vehicle IS NULL OR v.id=$vehicle)
              AND ($model IS NULL OR toLower(v.model)=toLower($model))
              AND ($year IS NULL OR v.year=$year)
              AND ($manual IS NULL OR m.id=$manual)
              AND ($page IS NULL OR p.number=$page)
              AND (size($topics)=0 OR EXISTS {
                  MATCH (c)-[:MENTIONS]->(t:CaragentTopic) WHERE t.id IN $topics
              })
            WITH c, p, m, v, score,
                size([category IN c.question_categories WHERE category IN $question_categories]) AS category_hits,
                size([system IN c.systems WHERE system IN $question_systems]) AS system_hits
            RETURN c.id AS id, c.id AS chunk_id, c.text AS text, c.title AS title,
                p.id AS page_id, p.number AS page, p.url AS url, p.images AS images,
                m.id AS manual_id, m.title AS manual_title, m.source AS manual_source,
                m.language AS language, v.id AS vehicle_id,
                v.model AS model, v.year AS year, v.market AS market,
                score + category_hits * 0.25 + system_hits * 0.25 AS score,
                'text_match' AS reason ORDER BY score DESC, id LIMIT $limit""",
                            query=query, vehicle=vehicle_id, model=model, year=year,
                            manual=manual_id, page=page_number, limit=limit, topics=topics,
                            question_categories=question_categories,
                            question_systems=question_systems)
        if not seeds:
            return []
        # Expand actual graph relationships, keeping the selected vehicle and evidence provenance.
        neighbors = self._query("""UNWIND $ids AS seed_id MATCH (seed:CaragentChunk {id:seed_id})
            MATCH (seed)-[:NEXT|MENTIONS|ANSWERS|ABOUT_SYSTEM*1..2]-(c:CaragentChunk)
            WHERE c.id <> seed.id AND NOT c.id IN $ids
              AND (c.manual_id=seed.manual_id OR size($topics)=0 OR EXISTS {
                  MATCH (c)-[:MENTIONS]->(t:CaragentTopic) WHERE t.id IN $topics
              })
            MATCH (v:CaragentVehicle)-[:HAS_MANUAL]->(m)-[:HAS_PAGE]->(p)-[:HAS_CHUNK]->(c)
            WITH DISTINCT c, p, m, v
            WHERE ($vehicle IS NULL OR v.id=$vehicle)
              AND ($model IS NULL OR toLower(v.model)=toLower($model))
              AND ($year IS NULL OR v.year=$year)
              AND ($manual IS NULL OR m.id=$manual)
              AND ($page IS NULL OR p.number=$page)
              AND any(term IN $terms WHERE toLower(c.text) CONTAINS term)
            RETURN c.id AS id, c.id AS chunk_id, c.text AS text, c.title AS title,
                p.id AS page_id, p.number AS page, p.url AS url, p.images AS images,
                m.id AS manual_id, m.title AS manual_title, m.source AS manual_source,
                m.language AS language, v.id AS vehicle_id,
                v.model AS model, v.year AS year, v.market AS market, 0.0 AS score,
                'graph_neighbor' AS reason ORDER BY id LIMIT $neighbor_limit""",
                                ids=[s["id"] for s in seeds], vehicle=vehicle_id,
                                model=model, year=year, manual=manual_id, page=page_number,
                                topics=topics, neighbor_limit=min(2, limit),
                                terms=re.findall(r'"([^\"]+)"', query))
        return seeds + neighbors

    def graph_preview(self, vehicle_id: str):
        return self._query("""MATCH (v:CaragentVehicle {id:$vehicle})-[:HAS_MANUAL]->(m)
            WITH v,m ORDER BY m.title LIMIT 12
            MATCH (m)-[:HAS_PAGE]->(p)-[:HAS_CHUNK]->(c)
            OPTIONAL MATCH (c)-[:MENTIONS]->(t:CaragentTopic)
            RETURN v.model AS model, v.year AS year, m.title AS manual, p.url AS url,
                count(DISTINCT c) AS chunks, collect(DISTINCT t.name) AS components""", vehicle=vehicle_id)
