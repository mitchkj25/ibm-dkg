"""
Search Agent — hybrid enterprise search over the IBM DKG.

Strategy:
  1. Parse natural language query → extract intent, entity types, keywords
  2. Generate a Cypher query for graph traversal
  3. Run fulltext index search for keyword matching
  4. Combine + rank results
  5. Use watsonx.ai (or mock) to synthesize a narrative answer

In MOCK MODE (no watsonx credentials): steps 1-4 run normally against the
in-memory mock graph; step 5 returns a templated response instead of LLM output.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from api.config import get_settings
from api.graph.schemas import SearchQuery, SearchResult

logger = logging.getLogger(__name__)

# ── Optional watsonx import (graceful mock fallback) ─────────────────────────
try:
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai import Credentials
    _WATSONX_AVAILABLE = True
except ImportError:
    _WATSONX_AVAILABLE = False
    logger.warning("[SearchAgent] ibm-watsonx-ai not installed — using mock LLM mode")


# ── Intent patterns ──────────────────────────────────────────────────────────

INTENT_PATTERNS = {
    "seller_manager": re.compile(r"(who.*manage|manager.*for|report.*to|reports to|hierarchy|org chart|alt|tsl)", re.I),
    "seller_territory": re.compile(r"(territory|region|geo|area).*seller|seller.*(territory|region)", re.I),
    "account_install": re.compile(r"(install|running|deployed|product.*on|what.*using)", re.I),
    "seller_account": re.compile(r"(own|cover|responsible|account.*seller|seller.*account)", re.I),
    "seller_product": re.compile(r"(certified|sell|product.*seller|seller.*product)", re.I),
    "co_sell": re.compile(r"(co.sell|partner|team|together|collaborat)", re.I),
    # Site number intents
    "site_spend": re.compile(r"(site.*spend|spend.*site|most.*spend|highest.*spend|site number.*spend|how much.*site)", re.I),
    "site_product": re.compile(r"(site.*product|product.*site|site number.*product|what.*site.*have|cognos.*site|site.*cognos)", re.I),
    "account_sites": re.compile(r"(site.*number|site number|what site|which site|sites.*for|account.*site)", re.I),
}

ENTITY_KEYWORDS = {
    "Seller": ["seller", "rep", "sales rep", "account executive", "ae", "ssr", "alt", "tsl"],
    "Manager": ["manager", "director", "vp", "first line", "second line", "flm", "slm", "alt", "tsl"],
    "Account": ["account", "client", "customer", "company", "enterprise", "state", "louisiana", "government"],
    "Product": ["product", "software", "solution", "platform", "tool", "ibm", "cognos", "watsonx"],
    "Territory": ["territory", "region", "geo", "area", "patch"],
    "Install": ["install", "deployment", "running", "using", "license"],
    "Opportunity": ["opportunity", "opp", "deal", "pipeline", "forecast"],
    "SiteNumber": ["site", "site number", "sitenumber", "customer number", "location"],
}


def _detect_entity_types(query: str) -> list[str]:
    """Detect which entity types are most relevant to this query."""
    q_lower = query.lower()
    detected = []
    for label, keywords in ENTITY_KEYWORDS.items():
        if any(kw in q_lower for kw in keywords):
            detected.append(label)
    return detected if detected else list(ENTITY_KEYWORDS.keys())


def _detect_intent(query: str) -> str:
    for intent, pattern in INTENT_PATTERNS.items():
        if pattern.search(query):
            return intent
    return "general"


def _build_cypher_for_intent(intent: str, keywords: list[str], entity_types: list[str], limit: int) -> tuple[str, dict]:
    """Generate a targeted Cypher query based on detected intent."""

    if intent == "site_spend":
        return (
            """
            MATCH (sn:SiteNumber)
            WHERE sn.status <> 'DELETED'
            RETURN sn {.*, _label: 'SiteNumber'} AS node, sn.annualSpend AS spend
            ORDER BY sn.annualSpend DESC
            LIMIT $limit
            """,
            {"limit": limit},
        )

    if intent == "site_product":
        return (
            """
            MATCH (sn:SiteNumber)-[:HAS_PRODUCT]->(p:Product)
            WHERE toLower(sn.siteId) CONTAINS toLower($kw)
               OR toLower(p.name) CONTAINS toLower($kw)
            WHERE sn.status <> 'DELETED'
            RETURN sn {.*, _label: 'SiteNumber'} AS node,
                   p {.*, _label: 'Product'} AS related,
                   'HAS_PRODUCT' AS relationship
            LIMIT $limit
            """,
            {"kw": keywords[0] if keywords else "", "limit": limit},
        )

    if intent == "account_sites":
        return (
            """
            MATCH (a:Account)-[:HAS_SITE]->(sn:SiteNumber)
            WHERE toLower(a.name) CONTAINS toLower($kw)
               OR toLower(sn.siteId) CONTAINS toLower($kw)
            WHERE a.status <> 'DELETED'
            RETURN a {.*, _label: 'Account'} AS node,
                   sn {.*, _label: 'SiteNumber'} AS related,
                   'HAS_SITE' AS relationship
            LIMIT $limit
            """,
            {"kw": keywords[0] if keywords else "", "limit": limit},
        )

    if intent == "seller_manager":
        return (
            """
            MATCH (s:Seller)-[:REPORTS_TO]->(m:Manager)
            WHERE toLower(s.name) CONTAINS toLower($kw)
               OR toLower(m.name) CONTAINS toLower($kw)
            WHERE s.status <> 'DELETED' AND m.status <> 'DELETED'
            RETURN s {.*, _label: 'Seller'} AS node,
                   m {.*, _label: 'Manager'} AS related,
                   'REPORTS_TO' AS relationship
            LIMIT $limit
            """,
            {"kw": keywords[0] if keywords else "", "limit": limit},
        )

    if intent == "account_install":
        return (
            """
            MATCH (a:Account)-[:HAS_INSTALL]->(i:Install)-[:RUNS_PRODUCT]->(p:Product)
            WHERE toLower(a.name) CONTAINS toLower($kw)
               OR toLower(p.name) CONTAINS toLower($kw)
            WHERE a.status <> 'DELETED'
            RETURN a {.*, _label: 'Account'} AS node,
                   p {.*, _label: 'Product'} AS related,
                   i.version AS installVersion
            LIMIT $limit
            """,
            {"kw": keywords[0] if keywords else "", "limit": limit},
        )

    if intent == "seller_territory":
        return (
            """
            MATCH (s:Seller)-[:OWNS_TERRITORY]->(t:Territory)
            WHERE toLower(s.name) CONTAINS toLower($kw)
               OR toLower(t.name) CONTAINS toLower($kw)
            WHERE s.status <> 'DELETED'
            RETURN s {.*, _label: 'Seller'} AS node,
                   t {.*, _label: 'Territory'} AS related,
                   'OWNS_TERRITORY' AS relationship
            LIMIT $limit
            """,
            {"kw": keywords[0] if keywords else "", "limit": limit},
        )

    # General fallback — fulltext search across all entity types
    label_filter = "|".join(entity_types) if entity_types else "Seller|Manager|Account|Product|Territory"
    return (
        f"""
        CALL db.index.fulltext.queryNodes('entity_fulltext', $kw_query)
        YIELD node, score
        WHERE node.status <> 'DELETED'
        RETURN node {{.*, _label: labels(node)[0]}} AS node, score
        ORDER BY score DESC
        LIMIT $limit
        """,
        {"kw_query": " OR ".join(keywords) if keywords else "*", "limit": limit},
    )


def _extract_keywords(query: str) -> list[str]:
    """Extract meaningful keywords, strip stopwords."""
    stopwords = {
        "who", "what", "where", "which", "how", "is", "are", "the", "a", "an",
        "for", "in", "on", "at", "of", "to", "and", "or", "does", "do", "has",
        "have", "with", "about", "me", "my", "their", "our", "find", "show",
        "tell", "list", "get", "give", "all",
    }
    words = re.findall(r"\b\w+\b", query.lower())
    return [w for w in words if w not in stopwords and len(w) > 2]


# ── Main search function ──────────────────────────────────────────────────────

async def search(query: SearchQuery) -> dict[str, Any]:
    """
    Entry point for enterprise search. Returns structured results + narrative.
    Works in both live (Neo4j) and mock mode.
    """
    from api.graph import neo4j_client as db  # lazy import to avoid circular deps

    cfg = get_settings()
    keywords = _extract_keywords(query.query)
    intent = _detect_intent(query.query)
    entity_types = query.entity_types or _detect_entity_types(query.query)

    logger.info(
        "[SearchAgent] query=%r intent=%s entities=%s keywords=%s",
        query.query, intent, entity_types, keywords,
    )

    # ── Try graph search ──────────────────────────────────────────────────
    graph_results: list[dict] = []
    try:
        cypher, params = _build_cypher_for_intent(intent, keywords, entity_types, query.max_results)
        graph_results = await db.run_query(cypher, params)
    except Exception as exc:
        logger.warning("[SearchAgent] Graph query failed, falling back to mock: %s", exc)
        graph_results = _mock_search(query.query, entity_types, query.max_results)

    # ── Format results ────────────────────────────────────────────────────
    results = _format_results(graph_results, intent)

    # ── Narrative synthesis ───────────────────────────────────────────────
    narrative = await _synthesize_narrative(query.query, results, intent)

    return {
        "query": query.query,
        "intent": intent,
        "result_count": len(results),
        "results": results,
        "narrative": narrative,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "live" if graph_results and not _is_mock_data(graph_results) else "mock",
    }


def _is_mock_data(results: list[dict]) -> bool:
    return any(r.get("_mock") for r in results)


def _format_results(raw: list[dict], intent: str) -> list[dict]:
    formatted = []
    for i, row in enumerate(raw):
        node = row.get("node") or row
        if not node:
            continue
        result = {
            "rank": i + 1,
            "id": node.get("id", node.get("_id", f"node-{i}")),
            "label": node.get("_label", "Entity"),
            "name": node.get("name", "Unknown"),
            "score": round(row.get("score", 1.0 - i * 0.05), 3),
            "status": node.get("status", "ACTIVE"),
            "properties": {k: v for k, v in node.items() if not k.startswith("_")},
            "related": row.get("related"),
            "relationship": row.get("relationship"),
        }
        formatted.append(result)
    return formatted


async def _synthesize_narrative(query: str, results: list[dict], intent: str) -> str:
    """Generate a human-readable narrative. Uses watsonx if available, else templates."""
    if not results:
        return f"No results found for '{query}'. Try broadening your search or checking spelling."

    # Template-based narrative (always works — mock fallback)
    top = results[:3]
    names = [r["name"] for r in top]
    label = top[0]["label"] if top else "entities"

    templates = {
        "seller_manager": f"Found {len(results)} seller-manager relationship(s). Top matches: {', '.join(names)}.",
        "account_install": f"Found {len(results)} account install record(s). Key accounts: {', '.join(names)}.",
        "seller_territory": f"Found {len(results)} territory assignment(s). Sellers: {', '.join(names)}.",
        "seller_product": f"Found {len(results)} product coverage record(s). Top: {', '.join(names)}.",
        "site_spend": f"Found {len(results)} site number(s) ranked by spend. Highest spend sites: {', '.join(names)}.",
        "site_product": f"Found {len(results)} site-product relationship(s). Sites: {', '.join(names)}.",
        "account_sites": f"Found {len(results)} site number(s). Account-to-site mappings: {', '.join(names)}.",
        "general": f"Found {len(results)} {label}(s) matching '{query}'. Top results: {', '.join(names)}.",
    }
    base_narrative = templates.get(intent, templates["general"])

    # Try watsonx enrichment
    if _WATSONX_AVAILABLE:
        try:
            enriched = await _call_watsonx(query, results)
            if enriched:
                return enriched
        except Exception as exc:
            logger.warning("[SearchAgent] watsonx synthesis failed, using template: %s", exc)

    return base_narrative


async def _call_watsonx(query: str, results: list[dict]) -> str | None:
    """Call watsonx.ai to generate a narrative summary of search results."""
    cfg = get_settings()
    context = json.dumps(results[:5], indent=2, default=str)
    prompt = f"""You are an IBM sales intelligence assistant. A seller asked: "{query}"

The knowledge graph returned these results:
{context}

Write a concise, professional 2-3 sentence summary answering the seller's question.
Be specific — use names, territories, and product names from the data.
Do not hallucinate information not present in the results."""

    credentials = Credentials(api_key=cfg.watsonx_api_key, url=cfg.watsonx_url)
    model = ModelInference(
        model_id=cfg.watsonx_model_id,
        credentials=credentials,
        project_id=cfg.watsonx_project_id,
        params={"max_new_tokens": 256, "temperature": 0.2},
    )
    response = model.generate_text(prompt=prompt)
    return response.strip() if response else None


# ── Mock search (no Neo4j needed) ────────────────────────────────────────────

def _mock_search(query: str, entity_types: list[str], limit: int) -> list[dict]:
    """Return mock results from the in-memory seed dataset for demo mode."""
    from api.data.mock_store import MOCK_GRAPH
    q_lower = query.lower()
    results = []
    for node in MOCK_GRAPH["nodes"]:
        label = node.get("label", "")
        if entity_types and label not in entity_types:
            continue
        name = node.get("name", "").lower()
        desc = node.get("description", "").lower()
        score = 0.0
        if q_lower in name:
            score = 0.95
        elif any(kw in name or kw in desc for kw in q_lower.split()):
            score = 0.75
        if score > 0:
            results.append({"node": {**node, "_label": label, "_mock": True}, "score": score})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
