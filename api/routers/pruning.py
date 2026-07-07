"""
Pruning agent router — trigger, status, and config endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks
from api.agents.pruning_agent import run_pruning_cycle
from api.mock import mock_store

router = APIRouter(prefix="/pruning", tags=["Pruning Agent"])

_last_report = None


@router.post("/run", summary="Manually trigger a pruning cycle (admin)")
async def trigger_pruning(background_tasks: BackgroundTasks):
    """
    Kick off a pruning cycle. Runs in the background so it doesn't block the request.
    Poll GET /pruning/last-report to see results.
    """
    global _last_report

    async def _run():
        global _last_report
        try:
            _last_report = await run_pruning_cycle()
        except Exception:
            # Mock pruning — simulate scanning seed data
            from datetime import datetime, timezone
            nodes = mock_store.get_all_nodes()
            stale = [n for n in nodes if n.get("status") == "STALE"]
            _last_report = {
                "run_at": datetime.now(timezone.utc).isoformat(),
                "nodes_scanned": len(nodes),
                "nodes_marked_stale": len(stale),
                "nodes_deleted": 0,
                "relationships_pruned": 0,
                "details": [f"STALE: {n['label']}:{n['id']}" for n in stale],
                "mode": "mock",
            }

    background_tasks.add_task(_run)
    return {"status": "Pruning cycle triggered", "check": "/pruning/last-report"}


@router.get("/last-report", summary="Get the most recent pruning report")
async def last_report():
    if _last_report is None:
        return {"message": "No pruning cycle has run yet. POST /pruning/run to trigger one."}
    return _last_report


@router.get("/stale-nodes", summary="List all currently STALE nodes")
async def stale_nodes():
    try:
        from api.graph import neo4j_client as db
        rows = await db.run_query(
            "MATCH (n) WHERE n.status = 'STALE' RETURN labels(n)[0] AS label, n.id AS id, n.name AS name, n.staledAt AS staledAt"
        )
        return {"stale_nodes": rows, "count": len(rows), "mode": "live"}
    except Exception:
        nodes = mock_store.get_all_nodes(status="STALE")
        return {"stale_nodes": nodes, "count": len(nodes), "mode": "mock"}
