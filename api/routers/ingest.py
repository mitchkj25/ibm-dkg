"""
Ingest router — bulk and CSV ingestion endpoints.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from api.agents import ingestion_agent
from api.mock import mock_store

router = APIRouter(prefix="/ingest", tags=["Ingest"])


@router.post("/bulk", summary="Bulk ingest nodes and relationships from JSON array")
async def bulk_ingest(records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Each record must be either:
      { "label": "Seller", "props": { "id": "...", "name": "...", ... } }
    or a relationship:
      { "type": "relationship", "from_label": "Seller", "from_id": "...",
        "rel_type": "REPORTS_TO", "to_label": "Manager", "to_id": "..." }
    """
    if not records:
        raise HTTPException(status_code=422, detail="Empty records list")
    if len(records) > 5000:
        raise HTTPException(status_code=413, detail="Batch size exceeds 5000 records")

    try:
        result = await ingestion_agent.bulk_ingest(records)
        return {**result, "mode": "live"}
    except Exception:
        # Mock fallback
        success = 0
        errors = 0
        for rec in records:
            try:
                label = rec.get("label", "")
                props = rec.get("props", {})
                if label and props:
                    mock_store.upsert_node(label, props)
                    success += 1
                elif rec.get("type") == "relationship":
                    mock_store.upsert_edge(rec["from_id"], rec["rel_type"], rec["to_id"])
                    success += 1
            except Exception:
                errors += 1
        return {"success": success, "errors": errors, "mode": "mock"}


@router.post("/csv/{label}", summary="Ingest CSV file as nodes of the given label")
async def ingest_csv(
    label: str,
    file: UploadFile = File(...),
    column_map: str = Form(default="{}", description="JSON string mapping CSV headers to schema fields"),
) -> dict[str, Any]:
    """
    Upload a CSV file (e.g. Salesforce export) and ingest each row as a node.
    column_map example: '{"Employee Name": "name", "Email": "email"}'
    """
    import json as _json
    try:
        col_map = _json.loads(column_map)
    except Exception:
        raise HTTPException(status_code=422, detail="column_map must be valid JSON")

    content = await file.read()
    csv_str = content.decode("utf-8", errors="replace")

    try:
        result = await ingestion_agent.ingest_csv(label, csv_str, col_map)
        return {**result, "mode": "live"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
