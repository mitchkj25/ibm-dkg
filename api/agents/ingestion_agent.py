"""
Ingestion Agent — normalises raw data payloads into the IBM DKG graph schema,
writes nodes + relationships with provenance metadata, and triggers pruning
verification on re-ingested entities.

Supports:
  - Single-entity upserts (via API)
  - Bulk JSON ingestion (batch endpoint)
  - CSV import helper (for Salesforce exports, territory files, etc.)
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any

from api.graph import neo4j_client as db
from api.graph.schemas import (
    AccountNode, InstallNode, KnowledgeAssetNode,
    ManagerNode, OpportunityNode, ProductNode,
    RelationshipCreate, SellerNode, TerritoryNode,
)

logger = logging.getLogger(__name__)

_LABEL_SCHEMA_MAP = {
    "Seller": SellerNode,
    "Manager": ManagerNode,
    "Territory": TerritoryNode,
    "Product": ProductNode,
    "Account": AccountNode,
    "Opportunity": OpportunityNode,
    "Install": InstallNode,
    "KnowledgeAsset": KnowledgeAssetNode,
}


def _to_graph_props(model) -> dict[str, Any]:
    """Convert a Pydantic model to a flat dict suitable for Neo4j properties."""
    raw = model.model_dump()
    # Convert snake_case to camelCase for graph property names
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if v is None:
            continue  # skip nulls — don't overwrite existing with null on MERGE
        camel = _snake_to_camel(k)
        out[camel] = v
    return out


def _snake_to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


async def ingest_node(label: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Validate, stamp provenance, upsert node to graph.
    Returns the created/updated graph node properties.
    """
    schema_cls = _LABEL_SCHEMA_MAP.get(label)
    if not schema_cls:
        raise ValueError(f"Unknown entity label: {label}")

    payload.setdefault("last_verified", datetime.now(timezone.utc).isoformat())
    model = schema_cls(**payload)
    props = _to_graph_props(model)

    result = await db.upsert_node(label, props)
    logger.info("[IngestionAgent] Upserted %s:%s", label, props.get("id"))
    return result


async def ingest_relationship(rel: RelationshipCreate) -> bool:
    """Upsert a directed relationship between two nodes."""
    success = await db.upsert_relationship(
        from_label=rel.from_label,
        from_id=rel.from_id,
        rel_type=rel.rel_type.value,
        to_label=rel.to_label,
        to_id=rel.to_id,
        rel_props=rel.props,
    )
    if success:
        logger.info(
            "[IngestionAgent] Relationship %s:%s -[%s]-> %s:%s",
            rel.from_label, rel.from_id, rel.rel_type.value,
            rel.to_label, rel.to_id,
        )
    return success


async def bulk_ingest(records: list[dict[str, Any]]) -> dict[str, int]:
    """
    Process a list of records. Each record must have:
      { "label": "Seller", "props": {...} }
    or for relationships:
      { "type": "relationship", "from_label": ..., "from_id": ...,
        "rel_type": ..., "to_label": ..., "to_id": ..., "props": {...} }

    Returns counts of successes and failures.
    """
    success_count = 0
    error_count = 0

    for record in records:
        try:
            if record.get("type") == "relationship":
                rel = RelationshipCreate(**record)
                await ingest_relationship(rel)
            else:
                label = record["label"]
                await ingest_node(label, record.get("props", {}))
            success_count += 1
        except Exception as exc:
            error_count += 1
            logger.error("[IngestionAgent] Bulk error on record %s: %s", record, exc)

    logger.info(
        "[IngestionAgent] Bulk ingest complete — success=%d errors=%d",
        success_count, error_count,
    )
    return {"success": success_count, "errors": error_count}


async def ingest_csv(label: str, csv_content: str, column_map: dict[str, str]) -> dict[str, int]:
    """
    Parse a CSV string and ingest each row as a node of the given label.
    column_map maps CSV headers → schema field names.
    e.g. {"Employee Name": "name", "Email Address": "email"}
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    records = []
    for row in reader:
        mapped = {column_map.get(k, k): v for k, v in row.items() if column_map.get(k, k)}
        records.append({"label": label, "props": mapped})
    return await bulk_ingest(records)
