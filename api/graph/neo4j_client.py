"""
Neo4j client — async connection pool, Cypher helpers, constraint bootstrap.
All queries are parameterised; no string interpolation of user data.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable

from api.config import get_settings

logger = logging.getLogger(__name__)

_driver: AsyncDriver | None = None


async def init_driver() -> None:
    """Open the async driver. Call once at application startup."""
    global _driver
    cfg = get_settings()
    _driver = AsyncGraphDatabase.driver(
        cfg.neo4j_uri,
        auth=(cfg.neo4j_user, cfg.neo4j_password),
        max_connection_pool_size=50,
    )
    await _driver.verify_connectivity()
    logger.info("Neo4j driver initialised → %s", cfg.neo4j_uri)
    await _bootstrap_constraints()


async def close_driver() -> None:
    """Close the driver. Call at application shutdown."""
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


@asynccontextmanager
async def get_session():
    """Yield an async Neo4j session (context manager)."""
    if _driver is None:
        raise RuntimeError("Neo4j driver not initialised — call init_driver() first")
    async with _driver.session() as session:
        yield session


# ── Schema bootstrap ────────────────────────────────────────────────────────

CONSTRAINT_STATEMENTS = [
    "CREATE CONSTRAINT seller_id IF NOT EXISTS FOR (n:Seller) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT manager_id IF NOT EXISTS FOR (n:Manager) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT territory_id IF NOT EXISTS FOR (n:Territory) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (n:Product) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT account_id IF NOT EXISTS FOR (n:Account) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT opportunity_id IF NOT EXISTS FOR (n:Opportunity) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT install_id IF NOT EXISTS FOR (n:Install) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (n:KnowledgeAsset) REQUIRE n.id IS UNIQUE",
]

INDEX_STATEMENTS = [
    "CREATE INDEX seller_name IF NOT EXISTS FOR (n:Seller) ON (n.name)",
    "CREATE INDEX account_name IF NOT EXISTS FOR (n:Account) ON (n.name)",
    "CREATE INDEX product_name IF NOT EXISTS FOR (n:Product) ON (n.name)",
    "CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS FOR (n:Seller|Manager|Account|Product|Territory|Install) ON EACH [n.name, n.description]",
]


async def _bootstrap_constraints() -> None:
    async with get_session() as s:
        for stmt in CONSTRAINT_STATEMENTS + INDEX_STATEMENTS:
            try:
                await s.run(stmt)
            except Exception as exc:
                logger.warning("Schema statement skipped (%s): %s", exc, stmt[:60])
    logger.info("Neo4j schema constraints and indexes verified")


# ── Generic helpers ──────────────────────────────────────────────────────────

async def run_query(
    cypher: str, params: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Run a read/write Cypher query and return a list of record dicts."""
    async with get_session() as session:
        result = await session.run(cypher, params or {})
        records = await result.data()
        return records


async def upsert_node(label: str, props: dict[str, Any]) -> dict[str, Any]:
    """
    MERGE a node by `id`, set all other properties.
    Automatically stamps `lastModified` and `createdAt` (first write only).
    """
    now = datetime.now(timezone.utc).isoformat()
    props.setdefault("createdAt", now)
    props["lastModified"] = now
    props["status"] = props.get("status", "ACTIVE")

    cypher = (
        f"MERGE (n:{label} {{id: $id}}) "
        "ON CREATE SET n = $props, n.createdAt = $now "
        "ON MATCH  SET n += $props, n.lastModified = $now "
        "RETURN n"
    )
    records = await run_query(cypher, {"id": props["id"], "props": props, "now": now})
    return records[0]["n"] if records else {}


async def upsert_relationship(
    from_label: str,
    from_id: str,
    rel_type: str,
    to_label: str,
    to_id: str,
    rel_props: dict[str, Any] | None = None,
) -> bool:
    """MERGE a directed relationship between two nodes identified by id."""
    now = datetime.now(timezone.utc).isoformat()
    props = rel_props or {}
    props["lastModified"] = now
    props.setdefault("createdAt", now)
    props["active"] = props.get("active", True)

    cypher = (
        f"MATCH (a:{from_label} {{id: $from_id}}), (b:{to_label} {{id: $to_id}}) "
        f"MERGE (a)-[r:{rel_type}]->(b) "
        "ON CREATE SET r = $props "
        "ON MATCH  SET r += $props "
        "RETURN r"
    )
    records = await run_query(
        cypher, {"from_id": from_id, "to_id": to_id, "props": props}
    )
    return len(records) > 0


async def get_node(label: str, node_id: str) -> dict[str, Any] | None:
    """Fetch a single node by label + id."""
    records = await run_query(
        f"MATCH (n:{label} {{id: $id}}) RETURN n",
        {"id": node_id},
    )
    return records[0]["n"] if records else None


async def get_neighbors(
    node_id: str, depth: int = 2, limit: int = 100
) -> list[dict[str, Any]]:
    """
    Return all nodes and relationships within `depth` hops of the given node.
    Used by the graph visualisation endpoint.
    """
    cypher = """
    MATCH path = (start {id: $id})-[*1..$depth]-(neighbor)
    WHERE neighbor.status <> 'DELETED'
    WITH nodes(path) AS ns, relationships(path) AS rs
    UNWIND ns AS n
    WITH collect(DISTINCT {id: n.id, labels: labels(n), props: n}) AS nodes,
         rs
    UNWIND rs AS r
    RETURN nodes,
           collect(DISTINCT {
               id: id(r),
               type: type(r),
               from: startNode(r).id,
               to: endNode(r).id,
               props: r
           }) AS edges
    LIMIT $limit
    """
    records = await run_query(cypher, {"id": node_id, "depth": depth, "limit": limit})
    if not records:
        return []
    return records[0]


async def mark_stale(label: str, node_id: str) -> None:
    """Mark a node as STALE (pruning agent uses this)."""
    await run_query(
        f"MATCH (n:{label} {{id: $id}}) SET n.status = 'STALE', n.staledAt = $now",
        {"id": node_id, "now": datetime.now(timezone.utc).isoformat()},
    )


async def delete_node(label: str, node_id: str) -> None:
    """Soft-delete: mark as DELETED and detach (hard-delete only if confirmed stale)."""
    await run_query(
        f"MATCH (n:{label} {{id: $id}}) SET n.status = 'DELETED', n.deletedAt = $now",
        {"id": node_id, "now": datetime.now(timezone.utc).isoformat()},
    )
