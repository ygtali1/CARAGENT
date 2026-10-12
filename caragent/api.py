from contextlib import asynccontextmanager
from pathlib import Path
import logging
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from pydantic import BaseModel, Field, model_validator

from .config import Settings
from .graph import GraphStore, GraphStoreError
from .rag import ask


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=6000)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    vehicle_id: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    limit: int = Field(default=5, ge=1, le=10)
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def valid_history(self):
        if self.history:
            roles = [message.role for message in self.history]
            if len(roles) % 2 or roles != ["user", "assistant"] * (len(roles) // 2):
                raise ValueError("Sohbet geçmişi user/assistant çiftlerinden oluşmalı.")
        return self


def create_app(settings=None, store=None):
    settings = settings or Settings.load()
    owns_store = store is None
    store = store or GraphStore(settings)

    @asynccontextmanager
    async def lifespan(app):
        try:
            store.verify()
            store.initialize()
            yield
        finally:
            if owns_store:
                store.close()

    app = FastAPI(title="CARAGENT — Toyota GraphRAG", version="0.1.0", lifespan=lifespan)
    app.mount("/assets", StaticFiles(directory=Path(__file__).parent / "web"), name="assets")

    @app.exception_handler(Neo4jError)
    @app.exception_handler(ServiceUnavailable)
    @app.exception_handler(GraphStoreError)
    async def database_error(request, exc):
        logging.getLogger(__name__).error("Neo4j request failed: %s", type(exc).__name__)
        return JSONResponse(status_code=503, content={"detail": "Veritabanına erişilemiyor. Docker ve .env ayarlarını kontrol edin."})

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(Path(__file__).parent / "web" / "index.html")

    @app.get("/api/health")
    def health():
        store.verify()
        return {"status": "ok", "answer_mode": settings.answer_mode}

    @app.get("/api/stats")
    def stats():
        return {"counts": store.stats(), "answer_mode": settings.answer_mode}

    @app.get("/api/vehicles")
    def vehicles():
        return {"vehicles": store.vehicles()}

    def validate_vehicle(vehicle_id):
        if not any(v["id"] == vehicle_id for v in store.vehicles()):
            raise HTTPException(404, "Seçilen araç için içe aktarılmış kılavuz yok.")

    @app.get("/api/graph/{vehicle_id}")
    def graph(vehicle_id: str):
        validate_vehicle(vehicle_id)
        return {"documents": store.graph_preview(vehicle_id)}

    @app.post("/api/ask")
    def answer(body: AskRequest):
        validate_vehicle(body.vehicle_id)
        return ask(store, settings, body.question, body.vehicle_id, body.limit,
                   history=[message.model_dump() for message in body.history])

    return app
