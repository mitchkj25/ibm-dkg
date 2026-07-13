"""
Chat router — conversational AI endpoint for IBM Scout.

Accepts a natural-language message and returns a structured response with:
  - narrative answer (Granite or template)
  - relevant graph entities
  - suggested follow-up questions
  - provenance/explainability trace

Works in MOCK mode (zero credentials) and live mode (watsonx.ai Granite).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat Agent"])


class ChatMessage(BaseModel):
    message: str
    seller_id: str = ""
    context: list[dict] = []  # prior turns for multi-turn


class ChatResponse(BaseModel):
    answer: str
    entities: list[dict] = []
    follow_ups: list[str] = []
    intent: str = "general"
    mode: str = "mock"
    generated_at: str = ""


@router.post("", response_model=ChatResponse, summary="Conversational agent endpoint")
async def chat(msg: ChatMessage) -> ChatResponse:
    """
    Send a natural language message to the Scout Agent.

    The agent will:
    1. Detect intent and extract entities from the message
    2. Query the knowledge graph (live or mock)
    3. Generate a narrative answer with Granite (live) or template (mock)
    4. Return relevant entities and suggested follow-ups

    This is the backend of the chat rail in search.html.
    """
    from api.agents.search_agent import search
    from api.graph.schemas import SearchQuery

    q = SearchQuery(query=msg.message, max_results=8)
    result = await search(q)

    entities = [
        {
            "id": r["id"],
            "label": r["label"],
            "name": r["name"],
            "status": r.get("status", "ACTIVE"),
        }
        for r in (result.get("results") or [])[:5]
    ]

    follow_ups = _suggest_follow_ups(result.get("intent", "general"), entities, msg.seller_id)

    return ChatResponse(
        answer=result.get("narrative", "I couldn't find relevant results for that query."),
        entities=entities,
        follow_ups=follow_ups,
        intent=result.get("intent", "general"),
        mode=result.get("mode", "mock"),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _suggest_follow_ups(intent: str, entities: list[dict], seller_id: str) -> list[str]:
    """Generate contextual follow-up question suggestions."""
    suggestions = []

    if intent == "seller_manager":
        suggestions = [
            "What accounts does this seller own?",
            "What is their territory quota?",
            "Show me their co-sell partners",
        ]
    elif intent == "account_install":
        suggestions = [
            "Are any of these installs expiring soon?",
            "What opportunities are linked to this account?",
            "Who owns this account?",
        ]
    elif intent == "seller_territory":
        suggestions = [
            "What is the quota for this territory?",
            "Which accounts are in this territory?",
            "Show territory health scorecard",
        ]
    elif intent in ("site_spend", "account_sites"):
        suggestions = [
            "What products are installed at this site?",
            "Who is the seller for this site?",
            "What is the support status?",
        ]
    else:
        # Generic entity-aware suggestions
        if entities:
            top = entities[0]
            label = top.get("label", "")
            name = top.get("name", "")
            if label == "Seller":
                suggestions = [
                    f"What accounts does {name} own?",
                    f"What is {name}'s pipeline?",
                    "Show me all sellers in the Northeast",
                ]
            elif label == "Account":
                suggestions = [
                    f"What is installed at {name}?",
                    f"What opportunities does {name} have?",
                    f"Who owns {name}?",
                ]
            elif label == "Product":
                suggestions = [
                    f"Which accounts have {name} installed?",
                    f"Who is certified on {name}?",
                    f"Are there any {name} support renewals due?",
                ]

    if not suggestions:
        suggestions = [
            "Show me expiring support contracts",
            "What are the whitespace gaps in my territory?",
            "Find co-sell opportunities for watsonx.ai",
        ]

    if seller_id:
        suggestions.insert(0, f"What are my Next Best Actions?")

    return suggestions[:4]
