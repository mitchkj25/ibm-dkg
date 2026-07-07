"""
Graph CRUD router — node and relationship endpoints.
All writes go through the ingestion agent (validation + provenance stamping).
All reads fall back to mock store when Neo4j is unavailable.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from api.agents import ingestion_agent
from api.graph.schemas import RelationshipCreate
from api.mock import mock_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/graph", tags=["Graph"])

_VALID_LABELS = {
    "Seller", "Manager", "Territory", "Product",
    "Account", "Opportunity", "Install", "KnowledgeAsset",
}


def _require_label(label: str) -> str:
    if label not in _VALID_LABELS:
        raise HTTPException(status_code=400, detail=f"Unknown label: {label}. Valid: {sorted(_VALID_LABELS)}")
    return label


# ── Nodes ─────────────────────────────────────────────────────────────────────

@router.get("/nodes", summary="List all nodes (with optional label filter)")
async def list_nodes(
    label: str | None = Query(None, description="Filter by entity label"),
    status: str = Query("ACTIVE", description="ACTIVE | STALE | DELETED"),
    limit: int = Query(200, ge=1, le=1000),
) -> dict[str, Any]:
    if label:
        _require_label(label)
    try:
        from api.graph import neo4j_client as db
        filter_clause = f"WHERE labels(n)[0] = $label AND n.status = $status" if label else "WHERE n.status = $status"
        rows = await db.run_query(
            f"MATCH (n) {filter_clause} RETURN n LIMIT $limit",
            {"label": label, "status": status, "limit": limit},
        )
        return {"nodes": [r["n"] for r in rows], "mode": "live"}
    except Exception:
        nodes = mock_store.get_all_nodes(label=label, status=status)
        return {"nodes": nodes[:limit], "mode": "mock"}


@router.get("/nodes/{label}/{node_id}", summary="Get a single node by label + id")
async def get_node(label: str, node_id: str) -> dict[str, Any]:
    _require_label(label)
    try:
        from api.graph import neo4j_client as db
        node = await db.get_node(label, node_id)
        if not node:
            raise HTTPException(status_code=404, detail=f"{label}:{node_id} not found")
        return {"node": node, "mode": "live"}
    except HTTPException:
        raise
    except Exception:
        node = mock_store.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail=f"{label}:{node_id} not found")
        return {"node": node, "mode": "mock"}


@router.post("/nodes/{label}", summary="Create or update a node")
async def upsert_node(label: str, payload: dict[str, Any]) -> dict[str, Any]:
    _require_label(label)
    try:
        result = await ingestion_agent.ingest_node(label, payload)
        return {"node": result, "mode": "live"}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        node = mock_store.upsert_node(label, payload)
        return {"node": node, "mode": "mock"}


@router.get("/neighbors/{node_id}", summary="Get graph neighborhood for a node")
async def get_neighbors(
    node_id: str,
    depth: int = Query(2, ge=1, le=4),
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    try:
        from api.graph import neo4j_client as db
        result = await db.get_neighbors(node_id, depth=depth, limit=limit)
        return {**result, "mode": "live"}
    except Exception:
        result = mock_store.get_neighbors(node_id, depth=depth, limit=limit)
        return {**result, "mode": "mock"}


# ── Relationships ─────────────────────────────────────────────────────────────

@router.post("/relationships", summary="Create or update a relationship")
async def upsert_relationship(rel: RelationshipCreate) -> dict[str, Any]:
    try:
        success = await ingestion_agent.ingest_relationship(rel)
        return {"success": success, "mode": "live"}
    except Exception:
        edge = mock_store.upsert_edge(rel.from_id, rel.rel_type.value, rel.to_id, rel.props)
        return {"success": True, "edge": edge, "mode": "mock"}


# ── Full graph (for visualisation) ───────────────────────────────────────────

@router.get("/full", summary="Return entire graph for visualisation")
async def full_graph(
    status: str = Query("ACTIVE", description="Filter by node status"),
) -> dict[str, Any]:
    try:
        from api.graph import neo4j_client as db
        nodes = await db.run_query(
            "MATCH (n) WHERE n.status = $status RETURN n", {"status": status}
        )
        edges = await db.run_query(
            "MATCH (a)-[r]->(b) WHERE a.status = $status AND b.status = $status "
            "RETURN a.id AS from, b.id AS to, type(r) AS type, r AS props",
            {"status": status},
        )
        return {
            "nodes": [r["n"] for r in nodes],
            "edges": [{"from": r["from"], "to": r["to"], "type": r["type"]} for r in edges],
            "mode": "live",
        }
    except Exception:
        result = mock_store.get_full_graph(status=status)
        return {**result, "mode": "mock"}


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats", summary="Graph statistics")
async def stats() -> dict[str, Any]:
    try:
        from api.graph import neo4j_client as db
        result = await db.run_query("""
            MATCH (n) RETURN labels(n)[0] AS label, n.status AS status, count(*) AS count
        """)
        by_label: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for row in result:
            by_label[row["label"]] = by_label.get(row["label"], 0) + row["count"]
            by_status[row["status"]] = by_status.get(row["status"], 0) + row["count"]
        edge_count = await db.run_query("MATCH ()-[r]->() RETURN count(r) AS c")
        return {
            "total_nodes": sum(by_label.values()),
            "total_edges": edge_count[0]["c"] if edge_count else 0,
            "by_label": by_label,
            "by_status": by_status,
            "mode": "live",
        }
    except Exception:
        return {**mock_store.get_stats(), "mode": "mock"}
