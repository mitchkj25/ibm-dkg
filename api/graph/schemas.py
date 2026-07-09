"""
Pydantic schemas for every IBM KG entity and relationship.
W3C PROV-DM provenance fields are embedded in every node.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid4())


# ── Provenance mixin ─────────────────────────────────────────────────────────

class ProvenanceMixin(BaseModel):
    """Every knowledge asset carries source provenance and a TTL."""
    source: str = Field(default="manual", description="Origin of this data (e.g. salesforce, w3, manual)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    ttl_days: int = Field(default=30, description="Days before this node is considered stale")
    last_verified: str = Field(default_factory=_now)
    created_at: str = Field(default_factory=_now)
    status: str = Field(default="ACTIVE", description="ACTIVE | STALE | DELETED")


# ── Node schemas ─────────────────────────────────────────────────────────────

class SellerNode(ProvenanceMixin):
    id: str = Field(default_factory=_uid)
    name: str
    email: str
    band_level: Optional[str] = None
    geo: Optional[str] = None
    role: str = "Seller"
    hire_date: Optional[str] = None
    last_active: Optional[str] = None
    description: Optional[str] = None


class ManagerNode(ProvenanceMixin):
    id: str = Field(default_factory=_uid)
    name: str
    email: str
    band_level: Optional[str] = None
    territory: Optional[str] = None
    description: Optional[str] = None


class TerritoryNode(ProvenanceMixin):
    id: str = Field(default_factory=_uid)
    name: str
    region: str
    geo: Optional[str] = None
    quota: Optional[float] = None
    description: Optional[str] = None


class ProductNode(ProvenanceMixin):
    id: str = Field(default_factory=_uid)
    name: str
    brand: str = "IBM"
    family: Optional[str] = None
    version: Optional[str] = None
    eol_date: Optional[str] = None
    description: Optional[str] = None


class AccountNode(ProvenanceMixin):
    id: str = Field(default_factory=_uid)
    name: str
    industry: Optional[str] = None
    segment: Optional[str] = None
    revenue: Optional[float] = None
    country: Optional[str] = None
    description: Optional[str] = None


class OpportunityNode(ProvenanceMixin):
    id: str = Field(default_factory=_uid)
    name: str
    stage: str = "Prospecting"
    close_date: Optional[str] = None
    value: Optional[float] = None
    product_id: Optional[str] = None
    description: Optional[str] = None


class InstallNode(ProvenanceMixin):
    id: str = Field(default_factory=_uid)
    product_id: str
    account_id: str
    version: Optional[str] = None
    install_date: Optional[str] = None
    support_end: Optional[str] = None
    contract_value: Optional[float] = None
    description: Optional[str] = None


class KnowledgeAssetNode(ProvenanceMixin):
    id: str = Field(default_factory=_uid)
    asset_type: str  # "process", "policy", "product_brief", "competitive_intel", etc.
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)
    linked_entity_ids: list[str] = Field(default_factory=list)


# ── Relationship schemas ──────────────────────────────────────────────────────

class RelationshipType(str, Enum):
    REPORTS_TO = "REPORTS_TO"
    MANAGES = "MANAGES"
    OWNS_TERRITORY = "OWNS_TERRITORY"
    COVERS_PRODUCT = "COVERS_PRODUCT"
    OWNS_ACCOUNT = "OWNS_ACCOUNT"
    HAS_INSTALL = "HAS_INSTALL"
    RUNS_PRODUCT = "RUNS_PRODUCT"
    HAS_OPPORTUNITY = "HAS_OPPORTUNITY"
    CO_SELLS = "CO_SELLS"
    RELATED_TO = "RELATED_TO"


class RelationshipCreate(BaseModel):
    from_label: str
    from_id: str
    rel_type: RelationshipType
    to_label: str
    to_id: str
    props: dict[str, Any] = Field(default_factory=dict)


# ── API request/response ──────────────────────────────────────────────────────

class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    entity_types: list[str] = Field(default_factory=list, description="Filter to specific node labels")
    max_results: int = Field(default=25, ge=1, le=100)
    include_stale: bool = False


class SearchResult(BaseModel):
    node_id: str
    label: str
    name: str
    score: float
    summary: str
    properties: dict[str, Any]
    related_nodes: list[dict[str, Any]] = Field(default_factory=list)


class GraphVizResponse(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class PruningReport(BaseModel):
    run_at: str
    nodes_scanned: int
    nodes_marked_stale: int
    nodes_deleted: int
    relationships_pruned: int
    details: list[str]
