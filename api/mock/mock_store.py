"""
Mock data store — in-memory graph for demo mode.

When Neo4j is not available, all graph operations read from and write to
this module's dictionaries. The data is seeded from seed_data.json on startup.

The mock store exposes the same function signatures as neo4j_client so
routers can call either transparently.
"""
from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ── In-memory collections ─────────────────────────────────────────────────────
_nodes: dict[str, dict[str, Any]] = {}       # id → node dict (includes "label")
_edges: list[dict[str, Any]] = []            # list of edge dicts

_SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "seed_data.json")


def load_seed() -> None:
    """Load seed_data.json into the in-memory store. Idempotent."""
    try:
        path = os.path.abspath(_SEED_PATH)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for node in data.get("nodes", []):
            _nodes[node["id"]] = node

        for edge in data.get("edges", []):
            _edges.append(edge)

        logger.info(
            "[MockStore] Loaded %d nodes, %d edges from seed data",
            len(_nodes), len(_edges),
        )
    except Exception as exc:
        logger.warning("[MockStore] Could not load seed data: %s", exc)


def get_all_nodes(label: str | None = None, status: str = "ACTIVE") -> list[dict[str, Any]]:
    result = []
    for node in _nodes.values():
        if label and node.get("label") != label:
            continue
        if status and node.get("status", "ACTIVE") != status:
            continue
        result.append(deepcopy(node))
    return result


def get_node(node_id: str) -> dict[str, Any] | None:
    node = _nodes.get(node_id)
    return deepcopy(node) if node else None


def upsert_node(label: str, props: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    node_id = props.get("id") or props.get("Id")
    if not node_id:
        raise ValueError("Node props must include 'id'")
    existing = _nodes.get(node_id, {})
    merged = {**existing, **props, "label": label, "lastModified": now}
    merged.setdefault("createdAt", now)
    merged.setdefault("status", "ACTIVE")
    _nodes[node_id] = merged
    return deepcopy(merged)


def upsert_edge(from_id: str, rel_type: str, to_id: str, props: dict[str, Any] | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    # Find existing
    for edge in _edges:
        if edge["from"] == from_id and edge["to"] == to_id and edge["type"] == rel_type:
            edge.update(props or {})
            edge["lastModified"] = now
            return deepcopy(edge)
    new_edge = {
        "from": from_id,
        "to": to_id,
        "type": rel_type,
        **(props or {}),
        "createdAt": now,
        "lastModified": now,
        "active": True,
    }
    _edges.append(new_edge)
    return deepcopy(new_edge)


def get_neighbors(node_id: str, depth: int = 2, limit: int = 100) -> dict[str, Any]:
    """BFS up to `depth` hops from node_id. Returns {nodes, edges}."""
    visited_ids: set[str] = set()
    frontier: set[str] = {node_id}
    result_nodes: list[dict[str, Any]] = []
    result_edges: list[dict[str, Any]] = []

    for _ in range(depth):
        next_frontier: set[str] = set()
        for fid in frontier:
            if fid in visited_ids:
                continue
            visited_ids.add(fid)
            node = _nodes.get(fid)
            if node and node.get("status", "ACTIVE") != "DELETED":
                result_nodes.append(deepcopy(node))

            for edge in _edges:
                if not edge.get("active", True):
                    continue
                neighbor_id = None
                if edge["from"] == fid:
                    neighbor_id = edge["to"]
                elif edge["to"] == fid:
                    neighbor_id = edge["from"]

                if neighbor_id and neighbor_id not in visited_ids:
                    next_frontier.add(neighbor_id)
                    if len(result_edges) < limit:
                        result_edges.append(deepcopy(edge))

        frontier = next_frontier
        if not frontier:
            break

    return {"nodes": result_nodes[:limit], "edges": result_edges[:limit]}


def get_full_graph(status: str = "ACTIVE") -> dict[str, Any]:
    """Return ALL nodes and edges — used for the full graph visualisation."""
    nodes = [n for n in _nodes.values() if n.get("status", "ACTIVE") == status]
    active_ids = {n["id"] for n in nodes}
    edges = [
        e for e in _edges
        if e.get("active", True)
        and e["from"] in active_ids
        and e["to"] in active_ids
    ]
    return {"nodes": deepcopy(nodes), "edges": deepcopy(edges)}


def mark_stale(node_id: str) -> None:
    node = _nodes.get(node_id)
    if node:
        node["status"] = "STALE"
        node["staledAt"] = datetime.now(timezone.utc).isoformat()


def delete_node(node_id: str) -> None:
    node = _nodes.get(node_id)
    if node:
        node["status"] = "DELETED"
        node["deletedAt"] = datetime.now(timezone.utc).isoformat()


def get_stats() -> dict[str, Any]:
    label_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for node in _nodes.values():
        lbl = node.get("label", "Unknown")
        st = node.get("status", "ACTIVE")
        label_counts[lbl] = label_counts.get(lbl, 0) + 1
        status_counts[st] = status_counts.get(st, 0) + 1
    return {
        "total_nodes": len(_nodes),
        "total_edges": len(_edges),
        "by_label": label_counts,
        "by_status": status_counts,
    }
