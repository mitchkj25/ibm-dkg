"""
IBM Scout — FastAPI application entry point.

Startup sequence:
  1. Load configuration (from .env or environment)
  2. Seed mock store (always — instant startup for demo mode)
  3. Attempt Neo4j connection (non-blocking — falls back to mock on failure)
  4. Start pruning agent scheduler
  5. Mount all routers

Shutdown sequence:
  1. Stop pruning scheduler
  2. Close Neo4j driver
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("IBM Scout API starting up…")

    # 1. Always seed mock store (works with zero credentials)
    from api.data.mock_store import MOCK_GRAPH
    logger.info(
        "Mock store ready — %d nodes, %d edges",
        len(MOCK_GRAPH["nodes"]),
        len(MOCK_GRAPH["edges"]),
    )

    # 2. Attempt Neo4j connection (non-fatal if unavailable)
    try:
        from api.graph.neo4j_client import init_driver
        await init_driver()
        logger.info("Neo4j connected — LIVE mode active")
    except Exception as exc:
        logger.warning("Neo4j not available (%s) — running in DEMO/MOCK mode", exc)

    # 3. Start pruning scheduler
    try:
        from api.agents.pruning_agent import start_scheduler
        start_scheduler()
    except Exception as exc:
        logger.warning("Pruning scheduler failed to start: %s", exc)

    # 4. Seed an initial pruning report so the Trust/Pruning UI never shows "Never"
    try:
        from datetime import datetime, timezone
        from api.data import mock_store as _ms
        _nodes = _ms.get_all_nodes()
        _stale = [n for n in _nodes if n.get("status") == "STALE"]
        from api.routers import pruning as _pruning_router
        _pruning_router._last_report = {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "nodes_scanned": len(_nodes),
            "nodes_marked_stale": len(_stale),
            "nodes_deleted": 0,
            "relationships_pruned": 0,
            "details": [f"STALE: {n['label']}:{n['id']}" for n in _stale],
            "mode": "mock",
            "note": "Initial scan on startup — next scheduled run in 6h",
        }
        logger.info("Pruning bootstrap report seeded — %d nodes scanned, %d stale", len(_nodes), len(_stale))
    except Exception as exc:
        logger.warning("Could not seed initial pruning report: %s", exc)

    logger.info("IBM Scout API ready")
    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("IBM Scout API shutting down…")
    try:
        from api.agents.pruning_agent import stop_scheduler
        stop_scheduler()
    except Exception:
        pass
    try:
        from api.graph.neo4j_client import close_driver
        await close_driver()
    except Exception:
        pass
    logger.info("IBM Scout API stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="IBM Scout: Federated Seller Intelligence",
        description=(
            "IBM Scout (Sales Content Optimization & Utility Tool) — graph-powered seller intelligence for IBM sellers and leadership. "
            "Each node carries W3C PROV-DM provenance metadata (source, confidence, TTL, last_verified), "
            "enabling trust scoring at the edge — the architectural foundation for federated, "
            "distributed knowledge contribution. Source systems (Salesforce, W3 directory, manual) "
            "each contribute signed, provenance-stamped Knowledge Assets that can be independently "
            "verified and pruned. "
            "\n\nCapabilities: proactive NBA alerts, whitespace/coverage gap analysis, "
            "account 360 briefings, co-sell matchmaking, territory health scorecards, "
            "data trust dashboard, NL-to-Cypher with explainability trace, "
            "and watsonx Orchestrate integration."
        ),
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Tighten for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    from api.routers.graph import router as graph_router
    from api.routers.search import router as search_router
    from api.routers.ingest import router as ingest_router
    from api.routers.pruning import router as pruning_router
    from api.routers.insights import router as insights_router
    from api.routers.chat import router as chat_router

    app.include_router(graph_router)
    app.include_router(search_router)
    app.include_router(ingest_router)
    app.include_router(pruning_router)
    app.include_router(insights_router)
    app.include_router(chat_router)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/healthz", tags=["Health"])
    async def health():
        from api.data.mock_store import get_graph_stats
        stats = get_graph_stats()
        neo4j_live = False
        try:
            from api.graph.neo4j_client import run_query
            await run_query("RETURN 1")
            neo4j_live = True
        except Exception:
            pass
        return JSONResponse({
            "status": "ok",
            "neo4j_live": neo4j_live,
            "mode": "live" if neo4j_live else "mock",
            "graph_stats": stats,
        })

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    from api.config import get_settings
    cfg = get_settings()
    uvicorn.run(
        "api.main:app",
        host=cfg.api_host,
        port=cfg.api_port,
        reload=cfg.environment == "development",
        log_level=cfg.log_level,
    )
