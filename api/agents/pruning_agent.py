"""
Pruning Agent — runs on a configurable schedule (default: every 6 hours).

Lifecycle:
  1. Scan all ACTIVE nodes, check last_verified against TTL.
  2. Nodes past TTL → mark STALE.
  3. Nodes STALE past stale_delete_threshold → soft-delete (DELETED status).
  4. Orphaned relationships (both ends DELETED) → detach and remove.
  5. Emit a PruningReport for observability / audit log.

This agent NEVER silently removes data. All transitions are logged with timestamps.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from api.config import get_settings
from api.graph import neo4j_client as db
from api.graph.schemas import PruningReport

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None

MANAGED_LABELS = [
    "Seller", "Manager", "Territory", "Product",
    "Account", "Opportunity", "Install", "KnowledgeAsset",
]


async def run_pruning_cycle() -> PruningReport:
    """
    Execute one full pruning cycle. Returns a structured report.
    Safe to call manually (e.g., from the admin API endpoint).
    """
    cfg = get_settings()
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=cfg.default_node_ttl_days)
    delete_cutoff = now - timedelta(days=cfg.stale_delete_threshold_days)

    nodes_scanned = 0
    nodes_marked_stale = 0
    nodes_deleted = 0
    relationships_pruned = 0
    details: list[str] = []

    # ── Step 1: Mark overdue ACTIVE nodes as STALE ─────────────────────────
    stale_query = """
    MATCH (n)
    WHERE n.status = 'ACTIVE'
      AND n.last_verified IS NOT NULL
      AND datetime(n.last_verified) < datetime($cutoff)
    RETURN labels(n)[0] AS label, n.id AS id, n.last_verified AS last_verified
    LIMIT 500
    """
    candidates = await db.run_query(
        stale_query, {"cutoff": stale_cutoff.isoformat()}
    )
    nodes_scanned += len(candidates)

    for row in candidates:
        label, node_id = row["label"], row["id"]
        await db.mark_stale(label, node_id)
        nodes_marked_stale += 1
        msg = f"STALE: {label}:{node_id} (last_verified={row['last_verified']})"
        details.append(msg)
        logger.info("[PruningAgent] %s", msg)

    # ── Step 2: Hard-delete STALE nodes past the deletion threshold ─────────
    delete_query = """
    MATCH (n)
    WHERE n.status = 'STALE'
      AND n.staled_at IS NOT NULL
      AND datetime(n.staled_at) < datetime($cutoff)
    RETURN labels(n)[0] AS label, n.id AS id
    LIMIT 200
    """
    for_deletion = await db.run_query(
        delete_query, {"cutoff": delete_cutoff.isoformat()}
    )
    for row in for_deletion:
        label, node_id = row["label"], row["id"]
        await db.delete_node(label, node_id)
        nodes_deleted += 1
        msg = f"DELETED: {label}:{node_id}"
        details.append(msg)
        logger.info("[PruningAgent] %s", msg)

    # ── Step 3: Prune orphaned / inactive relationships ─────────────────────
    rel_prune_query = """
    MATCH (a)-[r]->(b)
    WHERE (a.status = 'DELETED' OR b.status = 'DELETED')
       OR (r.active = false AND r.lastModified < $cutoff)
    WITH r, id(r) AS rid
    DELETE r
    RETURN count(r) AS pruned
    """
    rel_result = await db.run_query(
        rel_prune_query,
        {"cutoff": (now - timedelta(days=cfg.stale_delete_threshold_days)).isoformat()},
    )
    if rel_result:
        relationships_pruned = rel_result[0].get("pruned", 0)
        if relationships_pruned:
            details.append(f"Pruned {relationships_pruned} orphaned/inactive relationships")

    report = PruningReport(
        run_at=now.isoformat(),
        nodes_scanned=nodes_scanned,
        nodes_marked_stale=nodes_marked_stale,
        nodes_deleted=nodes_deleted,
        relationships_pruned=relationships_pruned,
        details=details,
    )

    logger.info(
        "[PruningAgent] Cycle complete — scanned=%d stale=%d deleted=%d rels_pruned=%d",
        nodes_scanned, nodes_marked_stale, nodes_deleted, relationships_pruned,
    )
    return report


async def verify_node(label: str, node_id: str) -> None:
    """
    Called by the ingestion or any agent to stamp a node as freshly verified.
    Resets status to ACTIVE and bumps last_verified.
    """
    now = datetime.now(timezone.utc).isoformat()
    await db.run_query(
        f"MATCH (n:{label} {{id: $id}}) SET n.status = 'ACTIVE', n.last_verified = $now",
        {"id": node_id, "now": now},
    )


def start_scheduler() -> None:
    """Start the background APScheduler (call once at app startup)."""
    global _scheduler
    cfg = get_settings()
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        run_pruning_cycle,
        trigger="interval",
        hours=cfg.pruning_interval_hours,
        id="pruning_agent",
        replace_existing=True,
        misfire_grace_time=300,  # 5 min grace window
    )
    _scheduler.start()
    logger.info(
        "[PruningAgent] Scheduler started — interval=%dh",
        cfg.pruning_interval_hours,
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
