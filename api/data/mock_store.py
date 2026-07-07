"""
In-memory mock graph store — loaded from seed_data.json at startup.

When Neo4j is unavailable (no credentials or connection refused), ALL graph
operations route here instead. The mock store is fully functional for demo
purposes: nodes, relationships, search, neighbourhood traversal, pruning
simulation — everything works without any external dependencies.

This is the DEMO MODE engine.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SEED_PATH = Path(__file__).parent / "seed_data.json"

# ── Graph structure ──────────────────────────────────────────────────────────
# MOCK_GRAPH is populated at module load time from the seed file.
MOCK_GRAPH: dict[str, list[dict]] = {"nodes": [], "edges": []}

# Node index: id → node dict
_NODE_INDEX: dict[str, dict] = {}

# Adjacency: node_id → list of edge dicts
_ADJ: dict[str, list[dict]] = {}


def _load_seed() -> None:
    """Load seed data into the in-memory graph. Called once at import time."""
    global MOCK_GRAPH, _NODE_INDEX, _ADJ
    try:
        raw = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("[MockStore] Failed to load seed data: %s", exc)
        return

    now = datetime.now(timezone.utc).isoformat()

    for record in raw.get("nodes", []):
        label = record["label"]
        props = record["props"]
        props.setdefault("lastVerified", now)
        props.setdefault("createdAt", now)
        node = {**props, "label": label}
        MOCK_GRAPH["nodes"].append(node)
        _NODE_INDEX[props["id"]] = node

    for rel in raw.get("relationships", []):
        edge = {
            "id": f"{rel['from_id']}__{rel['rel_type']}__{rel['to_id']}",
            "from": rel["from_id"],
            "to": rel["to_id"],
            "type": rel["rel_type"],
            "props": rel.get("props", {}),
        }
        MOCK_GRAPH["edges"].append(edge)
        _ADJ.setdefault(rel["from_id"], []).append(edge)
        _ADJ.setdefault(rel["to_id"], []).append(edge)  # bidirectional lookup

    logger.info(
        "[MockStore] Loaded %d nodes, %d edges from seed",
        len(MOCK_GRAPH["nodes"]),
        len(MOCK_GRAPH["edges"]),
    )


# ── CRUD operations ──────────────────────────────────────────────────────────

def mock_upsert_node(label: str, props: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    node_id = props.get("id")
    if not node_id:
        raise ValueError("Node must have an 'id' field")

    if node_id in _NODE_INDEX:
        _NODE_INDEX[node_id].update(props)
        _NODE_INDEX[node_id]["lastModified"] = now
    else:
        node = {**props, "label": label, "createdAt": now, "lastModified": now}
        _NODE_INDEX[node_id] = node
        MOCK_GRAPH["nodes"].append(node)

    return _NODE_INDEX[node_id]


def mock_upsert_relationship(
    from_id: str, rel_type: str, to_id: str, props: dict[str, Any]
) -> bool:
    edge_id = f"{from_id}__{rel_type}__{to_id}"
    # Update if exists
    for edge in MOCK_GRAPH["edges"]:
        if edge["id"] == edge_id:
            edge["props"].update(props)
            return True
    # Create new
    edge = {"id": edge_id, "from": from_id, "to": to_id, "type": rel_type, "props": props}
    MOCK_GRAPH["edges"].append(edge)
    _ADJ.setdefault(from_id, []).append(edge)
    _ADJ.setdefault(to_id, []).append(edge)
    return True


def mock_get_node(node_id: str) -> dict[str, Any] | None:
    return _NODE_INDEX.get(node_id)


def mock_get_neighbors(node_id: str, depth: int = 2, limit: int = 100) -> dict[str, Any]:
    """BFS neighbourhood traversal up to `depth` hops."""
    visited_nodes: set[str] = set()
    visited_edges: set[str] = set()
    frontier = {node_id}
    result_nodes: list[dict] = []
    result_edges: list[dict] = []

    if node_id in _NODE_INDEX:
        n = _NODE_INDEX[node_id]
        if n.get("status") != "DELETED":
            result_nodes.append(n)
            visited_nodes.add(node_id)

    for _ in range(depth):
        next_frontier: set[str] = set()
        for nid in frontier:
            for edge in _ADJ.get(nid, []):
                other_id = edge["to"] if edge["from"] == nid else edge["from"]
                other = _NODE_INDEX.get(other_id)
                if not other or other.get("status") == "DELETED":
                    continue
                if other_id not in visited_nodes:
                    visited_nodes.add(other_id)
                    result_nodes.append(other)
                    next_frontier.add(other_id)
                if edge["id"] not in visited_edges:
                    visited_edges.add(edge["id"])
                    result_edges.append(edge)
        frontier = next_frontier
        if len(result_nodes) >= limit:
            break

    return {"nodes": result_nodes[:limit], "edges": result_edges[:limit]}


def mock_mark_stale(node_id: str) -> None:
    if node_id in _NODE_INDEX:
        _NODE_INDEX[node_id]["status"] = "STALE"
        _NODE_INDEX[node_id]["staledAt"] = datetime.now(timezone.utc).isoformat()


def mock_delete_node(node_id: str) -> None:
    if node_id in _NODE_INDEX:
        _NODE_INDEX[node_id]["status"] = "DELETED"
        _NODE_INDEX[node_id]["deletedAt"] = datetime.now(timezone.utc).isoformat()


def mock_run_pruning() -> dict[str, int]:
    """Simulate a pruning run against in-memory data. Returns counts."""
    staled = 0
    deleted = 0
    for node in MOCK_GRAPH["nodes"]:
        if node.get("status") == "STALE" and node.get("id"):
            mock_delete_node(node["id"])
            deleted += 1
    return {"staled": staled, "deleted": deleted}


def get_all_nodes(label: str | None = None, status: str = "ACTIVE") -> list[dict]:
    return [
        n for n in MOCK_GRAPH["nodes"]
        if (label is None or n.get("label") == label)
        and n.get("status") == status
    ]


def get_graph_stats() -> dict[str, Any]:
    stats: dict[str, Any] = {"total_nodes": 0, "total_edges": len(MOCK_GRAPH["edges"]), "by_label": {}}
    for node in MOCK_GRAPH["nodes"]:
        if node.get("status") == "DELETED":
            continue
        lbl = node.get("label", "Unknown")
        stats["by_label"][lbl] = stats["by_label"].get(lbl, 0) + 1
        stats["total_nodes"] += 1
    return stats


# Bootstrap on import
_load_seed()
