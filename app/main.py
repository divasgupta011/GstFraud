# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import health,vendors,invoices,graph,anomalies,risk,chat,ingest
from .config import get_settings
from .setup_db import init_db

def create_app() -> FastAPI:
    settings = get_settings()
    init_db()
    
    
    app = FastAPI(
        title="GST Fraud Detection Backend",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],   # allows OPTIONS, POST, GET...
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health.router)
    app.include_router(vendors.router)
    app.include_router(invoices.router)
    app.include_router(graph.router)
    app.include_router(anomalies.router)
    app.include_router(risk.router)
    app.include_router(chat.router)
    app.include_router(ingest.router)

    @app.get("/")
    def root():
        return {
            "message": "GST Fraud Detection API",
            "env": settings.app_env,
        }

    return app


app = create_app()
