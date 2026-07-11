"""
Enterprise search router — natural language + structured graph queries.
"""
from __future__ import annotations

from fastapi import APIRouter
from api.agents.search_agent import search
from api.graph.schemas import SearchQuery

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", summary="Natural language enterprise search across IBM Scout")
async def enterprise_search(query: SearchQuery):
    """
    Submit a natural language query. The search agent will:
    1. Parse intent (entity types, relationships, named entities)
    2. Run Cypher graph traversal (live) or keyword scoring (mock)
    3. Synthesise a narrative answer with IBM Granite (live) or template (mock)

    Returns: { results, narrative, intent, mode }
    """
    return await search(query)


@router.get("/quick", summary="Quick keyword search (GET convenience endpoint)")
async def quick_search(
    q: str,
    types: str = "",
    limit: int = 10,
):
    """Quick search via GET — useful for frontend typeahead."""
    entity_types = [t.strip() for t in types.split(",") if t.strip()] if types else []
    query = SearchQuery(query=q, entity_types=entity_types, max_results=limit)
    return await search(query)
