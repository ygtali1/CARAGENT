from dataclasses import asdict
import re

from neo4j import GraphDatabase

from .models import Manual, components, split_text, stable_id, COMPONENTS

STOP_WORDS = set("a an the is are how what where when to of for and in on do does can i my with please toyota corolla hangi nasıl nasil nedir ne bir ve için icin mı mi mu bu nerede kaç kac var kontrol edilir yapabilirim yapilir yapılır".split())


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
                   "tork": "torque", "uyarı": "warning", "uyari": "warning"}.items():
        if tr in question.casefold():
            words.append(en)
    words = list(dict.fromkeys(words))
    return " OR ".join('"' + word + '"' for word in words)


class GraphStore:
    def __init__(self, settings):
        self.settings = settings
        self.driver = GraphDatabase.driver(settings.neo4j_uri,
                                          auth=(settings.neo4j_user, settings.neo4j_password),
                                          connection_timeout=5, max_transaction_retry_time=15)

    def close(self):
        self.driver.close()

    def verify(self):
        self.driver.verify_connectivity()

    def _query(self, cypher, **params):
        with self.driver.session(database=self.settings.database) as session:
            return session.execute_read(lambda tx: [r.data() for r in tx.run(cypher, parameters=params)])

    def initialize(self):
        with self.driver.session(database=self.settings.database) as session:
            for label in ("Vehicle", "Manual", "Page", "Chunk", "Component"):
                session.run(f"CREATE CONSTRAINT caragent_{label.lower()}_id IF NOT EXISTS "
                            f"FOR (n:Caragent{label}) REQUIRE n.id IS UNIQUE").consume()
            session.run("""CREATE FULLTEXT INDEX caragent_chunks IF NOT EXISTS
                FOR (n:CaragentChunk) ON EACH [n.text, n.title]
                OPTIONS {indexConfig: {`fulltext.analyzer`: 'standard-no-stop-words'}}""").consume()
            session.run("CALL db.awaitIndexes(120)").consume()

    def ingest(self, manual: Manual) -> dict:
        rows, chunk_rows = [], []
        for page in manual.pages:
            page_id = stable_id(manual.id, page.number)
            rows.append({"id": page_id, "number": page.number, "title": page.title or manual.title,
                         "url": page.url or manual.source, "images": list(page.images)})
            previous = None
            for ordinal, text in enumerate(split_text(page.text)):
                chunk_id = stable_id(page_id, ordinal)
                chunk_rows.append({"id": chunk_id, "page_id": page_id, "ordinal": ordinal,
                                   "text": text, "title": page.title or manual.title,
                                   "previous": previous, "components": components(text)})
                previous = chunk_id
        if not chunk_rows:
            raise ValueError("İçe aktarılabilir metin parçası yok.")
        with self.driver.session(database=self.settings.database) as session:
            return session.execute_write(self._write_manual, manual, rows, chunk_rows)

    @staticmethod
    def _write_manual(tx, manual, pages, chunks):
        existing = tx.run("MATCH (m:CaragentManual {id:$id}) RETURN m.content_hash AS hash", id=manual.id).single()
        if existing and existing["hash"] == manual.content_hash:
            return {"title": manual.title, "status": "unchanged", "pages": len(pages), "chunks": len(chunks)}
        # All replacement mutations live in one transaction. Only this document's nodes are touched.
        tx.run("MATCH (c:CaragentChunk {manual_id:$id}) DETACH DELETE c", id=manual.id).consume()
        tx.run("MATCH (p:CaragentPage {manual_id:$id}) DETACH DELETE p", id=manual.id).consume()
        tx.run("""MERGE (v:CaragentVehicle {id:$vehicle_id}) SET v += $vehicle
            MERGE (m:CaragentManual {id:$id}) SET m.title=$title, m.source=$source,
                m.language=$language, m.content_hash=$hash, m.updated_at=datetime()
            MERGE (v)-[:HAS_MANUAL]->(m)""", vehicle_id=manual.vehicle.id,
               vehicle=asdict(manual.vehicle), id=manual.id, title=manual.title,
               source=manual.source, language=manual.language, hash=manual.content_hash).consume()
        tx.run("""MATCH (m:CaragentManual {id:$id}) UNWIND $pages AS row
            CREATE (p:CaragentPage) SET p += row, p.manual_id=$id
            CREATE (m)-[:HAS_PAGE]->(p)""", id=manual.id, pages=pages).consume()
        tx.run("""UNWIND $chunks AS row MATCH (p:CaragentPage {id:row.page_id})
            CREATE (c:CaragentChunk {id:row.id, manual_id:$id, ordinal:row.ordinal,
                text:row.text, title:row.title}) CREATE (p)-[:HAS_CHUNK]->(c)
            FOREACH (name IN row.components |
                MERGE (topic:CaragentComponent {id:name}) SET topic.name=name
                MERGE (c)-[:MENTIONS]->(topic))""", id=manual.id, chunks=chunks).consume()
        tx.run("""UNWIND $chunks AS row WITH row WHERE row.previous IS NOT NULL
            MATCH (a:CaragentChunk {id:row.previous}), (b:CaragentChunk {id:row.id})
            MERGE (a)-[:NEXT]->(b)""", chunks=chunks).consume()
        return {"title": manual.title, "status": "imported", "pages": len(pages), "chunks": len(chunks)}

    def vehicles(self):
        return self._query("""MATCH (v:CaragentVehicle) OPTIONAL MATCH (v)-[:HAS_MANUAL]->(m)
            RETURN v.id AS id, v.make AS make, v.model AS model, v.year AS year,
                v.market AS market, count(m) AS manuals ORDER BY year DESC, model""")

    def stats(self):
        return self._query("""MATCH (n) WHERE any(l IN labels(n) WHERE l STARTS WITH 'Caragent')
            RETURN labels(n)[0] AS label, count(n) AS count ORDER BY label""")

    def search(self, question: str, vehicle_id: str, limit=5):
        query = search_query(question)
        if not query:
            return []
        if not 1 <= limit <= 10:
            raise ValueError("Sonuç sayısı 1–10 olmalı.")
        topics = components(question)
        if "engine_oil" in topics and "engine" in topics:
            topics.remove("engine")
        seeds = self._query("""CALL db.index.fulltext.queryNodes('caragent_chunks', $query)
            YIELD node AS c, score
            MATCH (v:CaragentVehicle {id:$vehicle})-[:HAS_MANUAL]->(m)-[:HAS_PAGE]->(p)-[:HAS_CHUNK]->(c)
            WHERE size($topics)=0 OR EXISTS {
                MATCH (c)-[:MENTIONS]->(t:CaragentComponent) WHERE t.id IN $topics
            }
            RETURN c.id AS id, c.text AS text, c.title AS title, p.number AS page,
                p.url AS url, p.images AS images, m.language AS language,
                v.model AS model, v.year AS year, v.market AS market, score,
                'text_match' AS reason ORDER BY score DESC, id LIMIT $limit""",
                            query=query, vehicle=vehicle_id, limit=limit, topics=topics)
        if not seeds:
            return []
        # Expand actual graph relationships, keeping the selected vehicle and evidence provenance.
        neighbors = self._query("""UNWIND $ids AS seed_id MATCH (seed:CaragentChunk {id:seed_id})
            MATCH (seed)-[:NEXT|MENTIONS*1..2]-(c:CaragentChunk)
            WHERE c.id <> seed.id AND NOT c.id IN $ids
              AND (c.manual_id=seed.manual_id OR size($topics)=0 OR EXISTS {
                  MATCH (c)-[:MENTIONS]->(t:CaragentComponent) WHERE t.id IN $topics
              })
            MATCH (v:CaragentVehicle {id:$vehicle})-[:HAS_MANUAL]->(m)-[:HAS_PAGE]->(p)-[:HAS_CHUNK]->(c)
            WITH DISTINCT c, p, m, v
            WHERE any(term IN $terms WHERE toLower(c.text) CONTAINS term)
            RETURN c.id AS id, c.text AS text, c.title AS title, p.number AS page,
                p.url AS url, p.images AS images, m.language AS language,
                v.model AS model, v.year AS year, v.market AS market, 0.0 AS score,
                'graph_neighbor' AS reason ORDER BY id LIMIT 2""",
                                ids=[s["id"] for s in seeds], vehicle=vehicle_id,
                                topics=topics,
                                terms=re.findall(r'"([^\"]+)"', query))
        return seeds + neighbors

    def graph_preview(self, vehicle_id: str):
        return self._query("""MATCH (v:CaragentVehicle {id:$vehicle})-[:HAS_MANUAL]->(m)
            WITH v,m ORDER BY m.title LIMIT 12
            MATCH (m)-[:HAS_PAGE]->(p)-[:HAS_CHUNK]->(c)
            OPTIONAL MATCH (c)-[:MENTIONS]->(t:CaragentComponent)
            RETURN v.model AS model, v.year AS year, m.title AS manual, p.url AS url,
                count(DISTINCT c) AS chunks, collect(DISTINCT t.name) AS components""", vehicle=vehicle_id)
