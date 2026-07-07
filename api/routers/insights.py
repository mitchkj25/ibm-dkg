"""
Insights router — proactive business intelligence derived from graph traversal.

All endpoints work in DEMO/MOCK mode with zero credentials.
In LIVE mode they run the equivalent Cypher queries against Neo4j.

Endpoints:
  GET /insights/nba/{seller_id}        — Next Best Actions for a seller
  GET /insights/whitespace             — Accounts with installs but no linked opportunity
  GET /insights/expiring               — Installs with support ending within N days
  GET /insights/territory-health       — Quota vs pipeline vs stale% per manager
  GET /insights/account360/{account_id}— Call-prep briefing (Granite or template)
  GET /insights/cosell-match           — Best-fit co-seller for a product+geo need
  GET /insights/trust                  — Data freshness / provenance trust dashboard
  GET /insights/summary                — Aggregated insight counts for dashboard header
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/insights", tags=["Insights"])


# ── Shared mock helpers ───────────────────────────────────────────────────────

def _mock_graph():
    from api.data.mock_store import MOCK_GRAPH, _NODE_INDEX, _ADJ
    return MOCK_GRAPH, _NODE_INDEX, _ADJ


def _nodes_by_label(label: str) -> list[dict]:
    g, _, _ = _mock_graph()
    return [n for n in g["nodes"] if n.get("label") == label and n.get("status") != "DELETED"]


def _edges_of_type(rel_type: str) -> list[dict]:
    g, _, _ = _mock_graph()
    return [e for e in g["edges"] if e.get("type") == rel_type]


def _node(node_id: str) -> dict | None:
    _, idx, _ = _mock_graph()
    return idx.get(node_id)


def _neighbors(node_id: str, rel_type: str | None = None, direction: str = "both") -> list[dict]:
    """Return neighbour nodes with optional relationship type filter."""
    _, idx, adj = _mock_graph()
    results = []
    for edge in adj.get(node_id, []):
        if rel_type and edge.get("type") != rel_type:
            continue
        if direction == "out" and edge["from"] != node_id:
            continue
        if direction == "in" and edge["to"] != node_id:
            continue
        other_id = edge["to"] if edge["from"] == node_id else edge["from"]
        other = idx.get(other_id)
        if other and other.get("status") != "DELETED":
            results.append({**other, "_edge_type": edge["type"], "_edge_props": edge.get("props", {})})
    return results


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── 1. Next Best Actions ──────────────────────────────────────────────────────

@router.get("/nba/{seller_id}", summary="Next Best Actions for a seller — ranked by urgency and revenue impact")
async def next_best_actions(seller_id: str) -> dict[str, Any]:
    """
    Combines three signals:
      - Expiring installs on owned accounts (time pressure)
      - Open opportunities on owned accounts (revenue signal)
      - Co-sell gaps: products installed but not covered by a specialist

    Returns a ranked list of actions with priority, type, and recommended action text.
    """
    seller = _node(seller_id)
    if not seller:
        return {"seller_id": seller_id, "actions": [], "error": "Seller not found"}

    actions: list[dict] = []
    today = _now()

    # Owned accounts
    owned_accounts = _neighbors(seller_id, rel_type="OWNS_ACCOUNT", direction="out")

    for acc in owned_accounts:
        acc_id = acc["id"]

        # Signal 1: Expiring / stale installs
        installs = _neighbors(acc_id, rel_type="HAS_INSTALL", direction="out")
        for inst in installs:
            support_end = inst.get("supportEnd") or inst.get("support_end")
            is_stale = inst.get("status") == "STALE"
            days_left = None
            if support_end:
                try:
                    end_dt = datetime.fromisoformat(support_end.replace("Z", "+00:00"))
                    days_left = (end_dt - today).days
                except ValueError:
                    pass

            products = _neighbors(inst["id"], rel_type="RUNS_PRODUCT", direction="out")
            prod_name = products[0]["name"] if products else "Unknown product"

            if is_stale or (days_left is not None and days_left < 0):
                actions.append({
                    "priority": 1,
                    "type": "CRITICAL_SUPPORT_EXPIRED",
                    "urgency": "critical",
                    "account": acc["name"],
                    "account_id": acc_id,
                    "install_id": inst["id"],
                    "product": prod_name,
                    "days_left": days_left,
                    "headline": f"⚠ Support expired: {prod_name} at {acc['name']}",
                    "action": f"Schedule upgrade conversation immediately. Revenue at risk if {acc['name']} "
                              f"seeks a vendor switch for {prod_name}.",
                    "estimated_value": inst.get("contractValue") or inst.get("contract_value"),
                })
            elif days_left is not None and days_left <= 90:
                actions.append({
                    "priority": 2,
                    "type": "EXPIRING_SUPPORT",
                    "urgency": "high",
                    "account": acc["name"],
                    "account_id": acc_id,
                    "install_id": inst["id"],
                    "product": prod_name,
                    "days_left": days_left,
                    "headline": f"Support expiring in {days_left}d: {prod_name} at {acc['name']}",
                    "action": f"Initiate renewal discussion for {prod_name} at {acc['name']}. "
                              f"Propose upgrade path to latest version.",
                    "estimated_value": inst.get("contractValue") or inst.get("contract_value"),
                })

        # Signal 2: Open opportunities with stalled stage
        opps = _neighbors(acc_id, rel_type="HAS_OPPORTUNITY", direction="out")
        for opp in opps:
            stage = opp.get("stage", "")
            close_date = opp.get("closeDate") or opp.get("close_date")
            days_to_close = None
            if close_date:
                try:
                    close_dt = datetime.fromisoformat(close_date.replace("Z", "+00:00"))
                    days_to_close = (close_dt - today).days
                except ValueError:
                    pass

            if stage in ("Identify", "Qualify") and days_to_close is not None and days_to_close < 30:
                actions.append({
                    "priority": 2,
                    "type": "STALLED_OPPORTUNITY",
                    "urgency": "high",
                    "account": acc["name"],
                    "account_id": acc_id,
                    "opportunity_id": opp["id"],
                    "stage": stage,
                    "days_to_close": days_to_close,
                    "value": opp.get("value"),
                    "headline": f"Opportunity stalling at {stage}: {opp['name']}",
                    "action": f"Opportunity '{opp['name']}' at {acc['name']} is at {stage} stage "
                              f"with {days_to_close}d to target close. Advance to Propose with "
                              f"a ROI-focused customer briefing.",
                    "estimated_value": opp.get("value"),
                })
            elif stage == "Propose" and (days_to_close is None or days_to_close < 60):
                actions.append({
                    "priority": 3,
                    "type": "OPEN_OPPORTUNITY",
                    "urgency": "medium",
                    "account": acc["name"],
                    "account_id": acc_id,
                    "opportunity_id": opp["id"],
                    "stage": stage,
                    "value": opp.get("value"),
                    "headline": f"Active deal at {stage}: {opp['name']} (${opp.get('value', 0):,.0f})",
                    "action": f"Drive '{opp['name']}' to Validate. Coordinate with technical "
                              f"team for proof point or reference.",
                    "estimated_value": opp.get("value"),
                })

        # Signal 3: Co-sell gap — installed products with no specialist co-seller
        for inst in installs:
            products = _neighbors(inst["id"], rel_type="RUNS_PRODUCT", direction="out")
            for prod in products:
                # Check if any co-seller covers this product on this account
                cosellers = _neighbors(seller_id, rel_type="CO_SELLS", direction="both")
                coseller_ids = {c["id"] for c in cosellers}
                covered = any(
                    prod["id"] in {p["id"] for p in _neighbors(cs_id, rel_type="COVERS_PRODUCT", direction="out")}
                    for cs_id in coseller_ids
                )
                if not covered:
                    actions.append({
                        "priority": 4,
                        "type": "COSELL_GAP",
                        "urgency": "medium",
                        "account": acc["name"],
                        "account_id": acc_id,
                        "product": prod["name"],
                        "product_id": prod["id"],
                        "headline": f"Co-sell gap: no {prod['name']} specialist on {acc['name']}",
                        "action": f"Request a {prod['name']} specialist from your territory team "
                                  f"to co-sell into {acc['name']}. Check 'Co-sell Match' to find "
                                  f"the best certified colleague.",
                        "estimated_value": None,
                    })

    # Deduplicate and rank
    seen = set()
    unique_actions = []
    for a in sorted(actions, key=lambda x: (x["priority"], -(x.get("estimated_value") or 0))):
        key = (a["type"], a.get("account_id"), a.get("product", ""), a.get("opportunity_id", ""))
        if key not in seen:
            seen.add(key)
            unique_actions.append(a)

    return {
        "seller_id": seller_id,
        "seller_name": seller.get("name"),
        "generated_at": _now().isoformat(),
        "action_count": len(unique_actions),
        "critical_count": sum(1 for a in unique_actions if a["urgency"] == "critical"),
        "actions": unique_actions[:20],
        "mode": "mock",
    }


# ── 2. Whitespace & Coverage Gap Analysis ────────────────────────────────────

@router.get("/whitespace", summary="Accounts with installs but no linked opportunity — expansion whitespace")
async def whitespace_analysis(
    min_revenue: float = Query(0, description="Minimum account revenue filter"),
) -> dict[str, Any]:
    """
    Graph traversal: accounts that HAVE installs but do NOT have open opportunities.
    Also surfaces accounts with thin product coverage (installs on <2 products).
    Managers and leadership should see this daily.
    """
    accounts = _nodes_by_label("Account")
    gaps: list[dict] = []

    for acc in accounts:
        acc_id = acc["id"]
        if acc.get("revenue", 0) < min_revenue:
            continue

        installs = _neighbors(acc_id, rel_type="HAS_INSTALL", direction="out")
        opps = _neighbors(acc_id, rel_type="HAS_OPPORTUNITY", direction="out")
        active_opps = [o for o in opps if o.get("status") != "DELETED"]

        if not installs:
            continue  # No install = no whitespace to surface yet

        # Get products from installs
        products_installed = []
        for inst in installs:
            prods = _neighbors(inst["id"], rel_type="RUNS_PRODUCT", direction="out")
            products_installed.extend(prods)
        unique_products = {p["id"]: p for p in products_installed}

        # Get all IBM products to find gaps
        all_products = _nodes_by_label("Product")
        not_installed = [p for p in all_products if p["id"] not in unique_products]

        gap_type = []
        if not active_opps:
            gap_type.append("NO_OPEN_OPPORTUNITY")
        if len(unique_products) < 2:
            gap_type.append("THIN_PRODUCT_COVERAGE")

        if gap_type:
            # Find the owner seller
            seller_node = None
            for edge in _edges_of_type("OWNS_ACCOUNT"):
                if edge["to"] == acc_id:
                    seller_node = _node(edge["from"])
                    break

            gaps.append({
                "account_id": acc_id,
                "account_name": acc["name"],
                "industry": acc.get("industry"),
                "revenue": acc.get("revenue", 0),
                "gap_types": gap_type,
                "installed_products": [p["name"] for p in unique_products.values()],
                "installed_product_count": len(unique_products),
                "open_opportunity_count": len(active_opps),
                "whitespace_products": [p["name"] for p in not_installed[:5]],
                "owner_seller": seller_node.get("name") if seller_node else "Unassigned",
                "owner_seller_id": seller_node.get("id") if seller_node else None,
                "priority_score": (
                    (3 if "NO_OPEN_OPPORTUNITY" in gap_type else 0)
                    + (2 if "THIN_PRODUCT_COVERAGE" in gap_type else 0)
                    + (1 if acc.get("revenue", 0) > 5_000_000_000 else 0)
                ),
                "recommendation": _whitespace_recommendation(acc, gap_type, unique_products, not_installed),
            })

    gaps.sort(key=lambda x: -x["priority_score"])
    return {
        "generated_at": _now().isoformat(),
        "total_gaps": len(gaps),
        "no_opp_count": sum(1 for g in gaps if "NO_OPEN_OPPORTUNITY" in g["gap_types"]),
        "thin_coverage_count": sum(1 for g in gaps if "THIN_PRODUCT_COVERAGE" in g["gap_types"]),
        "gaps": gaps,
        "mode": "mock",
    }


def _whitespace_recommendation(acc, gap_types, installed, not_installed) -> str:
    parts = []
    if "NO_OPEN_OPPORTUNITY" in gap_types:
        parts.append(f"{acc['name']} has active IBM installs but zero open pipeline. "
                     f"Create a new opportunity to capture expansion revenue.")
    if "THIN_PRODUCT_COVERAGE" in gap_types:
        candidates = [p["name"] for p in not_installed[:2]]
        parts.append(f"Only {len(installed)} product family installed. "
                     f"Potential expansion into {', '.join(candidates)}.")
    return " ".join(parts)


# ── 3. Expiring Support ───────────────────────────────────────────────────────

@router.get("/expiring", summary="Installs with support ending within N days — ranked by contract value")
async def expiring_support(
    days: int = Query(180, description="Alert window in days"),
) -> dict[str, Any]:
    installs = _nodes_by_label("Install")
    today = _now()
    alerts: list[dict] = []

    for inst in installs:
        support_end = inst.get("supportEnd") or inst.get("support_end")
        if not support_end:
            continue
        try:
            end_dt = datetime.fromisoformat(support_end.replace("Z", "+00:00"))
        except ValueError:
            continue
        days_left = (end_dt - today).days
        if days_left > days:
            continue

        # Find account and product
        acc_edge = next((e for e in _edges_of_type("HAS_INSTALL") if e["to"] == inst["id"]), None)
        acc = _node(acc_edge["from"]) if acc_edge else None
        prod_neighbors = _neighbors(inst["id"], rel_type="RUNS_PRODUCT", direction="out")
        prod = prod_neighbors[0] if prod_neighbors else None

        # Find responsible seller
        seller = None
        if acc:
            for edge in _edges_of_type("OWNS_ACCOUNT"):
                if edge["to"] == acc["id"]:
                    seller = _node(edge["from"])
                    break

        alerts.append({
            "install_id": inst["id"],
            "install_name": inst.get("name"),
            "product": prod["name"] if prod else "Unknown",
            "product_id": prod["id"] if prod else None,
            "account": acc["name"] if acc else "Unknown",
            "account_id": acc["id"] if acc else None,
            "seller": seller["name"] if seller else "Unassigned",
            "seller_id": seller["id"] if seller else None,
            "support_end_date": support_end,
            "days_remaining": days_left,
            "contract_value": inst.get("contractValue") or inst.get("contract_value"),
            "status": inst.get("status"),
            "severity": "critical" if days_left < 0 else ("high" if days_left < 30 else ("medium" if days_left < 90 else "low")),
            "action": (
                f"EXPIRED — immediate upgrade engagement required"
                if days_left < 0
                else f"Support ends in {days_left} days. Initiate renewal/upgrade conversation."
            ),
        })

    alerts.sort(key=lambda x: x["days_remaining"])
    return {
        "generated_at": _now().isoformat(),
        "alert_window_days": days,
        "total_alerts": len(alerts),
        "critical_count": sum(1 for a in alerts if a["severity"] == "critical"),
        "high_count": sum(1 for a in alerts if a["severity"] == "high"),
        "alerts": alerts,
        "mode": "mock",
    }


# ── 4. Territory Health Scorecard ─────────────────────────────────────────────

@router.get("/territory-health", summary="Territory health scorecard — quota, pipeline, coverage, stale% per manager")
async def territory_health() -> dict[str, Any]:
    managers = _nodes_by_label("Manager")
    cards: list[dict] = []

    for mgr in managers:
        mgr_id = mgr["id"]
        # Find sellers under this manager
        sellers = _neighbors(mgr_id, rel_type="REPORTS_TO", direction="in")
        sellers = [s for s in sellers if s.get("label") == "Seller"]

        total_quota = 0.0
        open_pipeline = 0.0
        accounts_covered: set[str] = set()
        products_covered: set[str] = set()
        stale_nodes = 0
        total_nodes = 0

        for seller in sellers:
            sel_id = seller["id"]
            # Territory quotas
            territories = _neighbors(sel_id, rel_type="OWNS_TERRITORY", direction="out")
            for ter in territories:
                total_quota += ter.get("quota", 0) or 0

            # Accounts and pipeline
            accounts = _neighbors(sel_id, rel_type="OWNS_ACCOUNT", direction="out")
            for acc in accounts:
                accounts_covered.add(acc["id"])
                opps = _neighbors(acc["id"], rel_type="HAS_OPPORTUNITY", direction="out")
                for opp in opps:
                    if opp.get("status") != "DELETED":
                        open_pipeline += opp.get("value", 0) or 0

            # Product coverage
            products = _neighbors(sel_id, rel_type="COVERS_PRODUCT", direction="out")
            for prod in products:
                products_covered.add(prod["id"])

            # Stale data check
            total_nodes += 1
            if seller.get("status") == "STALE":
                stale_nodes += 1

        stale_pct = round((stale_nodes / total_nodes * 100) if total_nodes else 0, 1)
        pipeline_vs_quota = round((open_pipeline / total_quota * 100) if total_quota else 0, 1)
        health_score = _calc_health_score(pipeline_vs_quota, stale_pct, len(accounts_covered), len(products_covered))

        cards.append({
            "manager_id": mgr_id,
            "manager_name": mgr["name"],
            "manager_role": mgr.get("role", "FLM"),
            "band_level": mgr.get("bandLevel"),
            "seller_count": len(sellers),
            "accounts_covered": len(accounts_covered),
            "products_covered": list(products_covered),
            "product_coverage_count": len(products_covered),
            "total_quota": total_quota,
            "open_pipeline": open_pipeline,
            "pipeline_vs_quota_pct": pipeline_vs_quota,
            "stale_data_pct": stale_pct,
            "health_score": health_score,
            "health_label": "Healthy" if health_score >= 70 else ("At Risk" if health_score >= 40 else "Critical"),
            "risks": _territory_risks(pipeline_vs_quota, stale_pct, len(accounts_covered), len(sellers)),
        })

    cards.sort(key=lambda x: x["health_score"])
    return {
        "generated_at": _now().isoformat(),
        "manager_count": len(cards),
        "total_quota": sum(c["total_quota"] for c in cards),
        "total_pipeline": sum(c["open_pipeline"] for c in cards),
        "avg_health_score": round(sum(c["health_score"] for c in cards) / len(cards), 1) if cards else 0,
        "scorecards": cards,
        "mode": "mock",
    }


def _calc_health_score(pipeline_pct, stale_pct, account_count, product_count) -> int:
    score = 50
    score += min(30, pipeline_pct * 0.3)
    score -= stale_pct * 0.5
    score += min(10, account_count * 1.5)
    score += min(10, product_count * 1.2)
    return max(0, min(100, round(score)))


def _territory_risks(pipeline_pct, stale_pct, account_count, seller_count) -> list[str]:
    risks = []
    if pipeline_pct < 50:
        risks.append(f"Pipeline coverage {pipeline_pct:.0f}% of quota — below 50% threshold")
    if stale_pct > 20:
        risks.append(f"Data freshness concern — {stale_pct:.0f}% of nodes are stale")
    if account_count == 0:
        risks.append("No accounts assigned to sellers under this manager")
    if seller_count <= 1 and account_count > 1:
        risks.append(f"Single-threaded risk: {account_count} accounts covered by {seller_count} seller")
    return risks


# ── 5. Account 360 Briefing ───────────────────────────────────────────────────

@router.get("/account360/{account_id}", summary="Account 360 call-prep briefing — Granite-written or template")
async def account_360(account_id: str) -> dict[str, Any]:
    acc = _node(account_id)
    if not acc:
        return {"error": "Account not found", "account_id": account_id}

    installs = _neighbors(account_id, rel_type="HAS_INSTALL", direction="out")
    opps = _neighbors(account_id, rel_type="HAS_OPPORTUNITY", direction="out")
    sites = _neighbors(account_id, rel_type="HAS_SITE", direction="out")

    # Products in install base
    install_details = []
    today = _now()
    for inst in installs:
        prods = _neighbors(inst["id"], rel_type="RUNS_PRODUCT", direction="out")
        prod = prods[0] if prods else None
        support_end = inst.get("supportEnd") or inst.get("support_end")
        days_left = None
        if support_end:
            try:
                end_dt = datetime.fromisoformat(support_end.replace("Z", "+00:00"))
                days_left = (end_dt - today).days
            except ValueError:
                pass
        install_details.append({
            "product": prod["name"] if prod else "Unknown",
            "version": inst.get("version"),
            "support_end": support_end,
            "days_left": days_left,
            "contract_value": inst.get("contractValue") or inst.get("contract_value"),
            "status": inst.get("status"),
        })

    # Sellers covering this account
    sellers_on_account = []
    for edge in _edges_of_type("OWNS_ACCOUNT"):
        if edge["to"] == account_id:
            s = _node(edge["from"])
            if s:
                sellers_on_account.append({"name": s["name"], "role": s.get("sellerType", s.get("role")), "id": s["id"]})

    # Co-sellers
    cosellers = []
    for seller in sellers_on_account:
        for cs in _neighbors(seller["id"], rel_type="CO_SELLS", direction="both"):
            if cs["id"] not in {s["id"] for s in sellers_on_account}:
                cosellers.append({"name": cs["name"], "role": cs.get("sellerType", cs.get("role")), "id": cs["id"]})

    # Site numbers
    site_details = [{"site_id": s.get("siteId"), "agency": s.get("agency"), "spend": s.get("annualSpend")} for s in sites]

    briefing = {
        "account_id": account_id,
        "account_name": acc.get("name"),
        "industry": acc.get("industry"),
        "revenue": acc.get("revenue"),
        "generated_at": _now().isoformat(),
        "install_base": install_details,
        "open_opportunities": [
            {"name": o.get("name"), "stage": o.get("stage"), "value": o.get("value"), "close_date": o.get("closeDate")}
            for o in opps if o.get("status") != "DELETED"
        ],
        "sellers": sellers_on_account,
        "cosellers": cosellers,
        "site_numbers": site_details,
        "narrative": _build_360_narrative(acc, install_details, opps, sellers_on_account, cosellers, today),
        "mode": "mock",
    }
    return briefing


def _build_360_narrative(acc, installs, opps, sellers, cosellers, today) -> str:
    lines = [f"## Account 360 — {acc.get('name')}"]
    if acc.get("industry"):
        lines.append(f"**Industry:** {acc['industry']} | **Revenue:** ${acc.get('revenue', 0):,.0f}")

    lines.append("\n### Install Base")
    if installs:
        for inst in installs:
            alert = ""
            if inst["days_left"] is not None and inst["days_left"] < 0:
                alert = " ⚠ **SUPPORT EXPIRED**"
            elif inst["days_left"] is not None and inst["days_left"] < 90:
                alert = f" ⚠ Expiring in {inst['days_left']}d"
            lines.append(f"- {inst['product']} v{inst.get('version', '?')}{alert}")
    else:
        lines.append("- No active installs on record")

    lines.append("\n### Open Pipeline")
    active_opps = [o for o in opps if o.get("status") != "DELETED"]
    if active_opps:
        for opp in active_opps:
            lines.append(f"- {opp.get('name')} | Stage: {opp.get('stage')} | ${opp.get('value', 0):,.0f}")
    else:
        lines.append("- No open opportunities — **consider creating one**")

    lines.append(f"\n### Team Coverage")
    for s in sellers:
        lines.append(f"- {s['name']} ({s.get('role', 'CE')}) — Primary")
    for cs in cosellers:
        lines.append(f"- {cs['name']} ({cs.get('role', 'SSR')}) — Co-sell")

    return "\n".join(lines)


# ── 6. Co-sell Matchmaker ─────────────────────────────────────────────────────

@router.get("/cosell-match", summary="Find the best-fit co-seller for a product and geography need")
async def cosell_match(
    product_id: str = Query(..., description="Product ID needing specialist coverage"),
    geo: str = Query("", description="Optional geography filter"),
    exclude_seller_id: str = Query("", description="Exclude the requesting seller"),
) -> dict[str, Any]:
    sellers = _nodes_by_label("Seller")
    candidates: list[dict] = []

    for seller in sellers:
        if seller["id"] == exclude_seller_id:
            continue
        products_covered = _neighbors(seller["id"], rel_type="COVERS_PRODUCT", direction="out")
        product_ids = {p["id"] for p in products_covered}
        if product_id not in product_ids:
            continue

        # Geo match score
        seller_geo = (seller.get("geo") or "").lower()
        geo_score = 1.0 if not geo else (1.0 if geo.lower() in seller_geo else 0.5)

        # Workload score (fewer accounts = more available)
        accounts = _neighbors(seller["id"], rel_type="OWNS_ACCOUNT", direction="out")
        workload_score = max(0.2, 1.0 - len(accounts) * 0.1)

        # Existing co-sell relationships (network signal)
        cosell_count = len(_neighbors(seller["id"], rel_type="CO_SELLS", direction="both"))
        network_score = min(1.0, cosell_count * 0.3 + 0.4)

        score = round((geo_score * 0.4 + workload_score * 0.3 + network_score * 0.3), 3)

        prod_obj = _node(product_id)
        candidates.append({
            "seller_id": seller["id"],
            "seller_name": seller["name"],
            "geo": seller.get("geo"),
            "seller_type": seller.get("sellerType", seller.get("role")),
            "band_level": seller.get("bandLevel"),
            "products_covered": [p["name"] for p in products_covered],
            "current_account_count": len(accounts),
            "existing_cosell_count": cosell_count,
            "match_score": score,
            "geo_match": geo_score == 1.0,
            "recommendation": f"{seller['name']} is certified on {prod_obj['name'] if prod_obj else product_id} "
                              f"and covers {seller.get('geo', 'their territory')}.",
        })

    candidates.sort(key=lambda x: -x["match_score"])
    prod_obj = _node(product_id)
    return {
        "product_id": product_id,
        "product_name": prod_obj["name"] if prod_obj else product_id,
        "geo_filter": geo or "Any",
        "candidates": candidates[:5],
        "top_match": candidates[0] if candidates else None,
        "generated_at": _now().isoformat(),
        "mode": "mock",
    }


# ── 7. Data Trust Dashboard ───────────────────────────────────────────────────

@router.get("/trust", summary="Data freshness and provenance trust dashboard")
async def trust_dashboard() -> dict[str, Any]:
    g, _, _ = _mock_graph()
    all_nodes = [n for n in g["nodes"] if n.get("status") != "DELETED"]

    source_stats: dict[str, dict] = {}
    label_stats: dict[str, dict] = {}

    for node in all_nodes:
        source = node.get("source", "unknown")
        label = node.get("label", "Unknown")
        status = node.get("status", "ACTIVE")
        confidence = node.get("confidence", 1.0)

        for key, d in [(source, source_stats), (label, label_stats)]:
            if key not in d:
                d[key] = {"total": 0, "active": 0, "stale": 0, "deleted": 0, "confidence_sum": 0.0}
            d[key]["total"] += 1
            d[key][status.lower()] = d[key].get(status.lower(), 0) + 1
            d[key]["confidence_sum"] += confidence

    def _score(stats):
        if stats["total"] == 0:
            return 0
        fresh_pct = stats["active"] / stats["total"]
        avg_conf = stats["confidence_sum"] / stats["total"]
        return round((fresh_pct * 0.7 + avg_conf * 0.3) * 100, 1)

    sources = []
    for src, stats in source_stats.items():
        sources.append({
            "source": src,
            "total_nodes": stats["total"],
            "active": stats["active"],
            "stale": stats.get("stale", 0),
            "freshness_score": _score(stats),
            "avg_confidence": round(stats["confidence_sum"] / stats["total"], 3),
            "trust_label": "Trusted" if _score(stats) >= 80 else ("Degraded" if _score(stats) >= 50 else "Untrusted"),
            "provenance_note": _provenance_note(src),
        })
    sources.sort(key=lambda x: x["freshness_score"])

    overall_score = round(sum(s["freshness_score"] for s in sources) / len(sources), 1) if sources else 0

    return {
        "generated_at": _now().isoformat(),
        "overall_trust_score": overall_score,
        "overall_trust_label": "Trusted" if overall_score >= 80 else ("Degraded" if overall_score >= 50 else "At Risk"),
        "by_source": sources,
        "by_label": {lbl: {"total": s["total"], "active": s["active"], "stale": s.get("stale", 0),
                           "freshness_score": _score(s)} for lbl, s in label_stats.items()},
        "total_nodes": len(all_nodes),
        "mode": "mock",
    }


def _provenance_note(source: str) -> str:
    notes = {
        "seed": "Seed data loaded at deploy time. Re-verify against source systems.",
        "salesforce": "Synced from Salesforce CRM. Trust is high if sync < 24h old.",
        "manual": "Manually entered. Requires periodic human verification.",
        "w3": "Sourced from internal IBM directory. Generally high confidence.",
    }
    return notes.get(source, f"Source '{source}' — no provenance policy defined.")


# ── 8. Summary (dashboard header) ────────────────────────────────────────────

@router.get("/summary", summary="Aggregated insight counts for dashboard header cards")
async def insights_summary() -> dict[str, Any]:
    expiry_data = await expiring_support(days=90)
    whitespace_data = await whitespace_analysis()
    trust_data = await trust_dashboard()

    return {
        "generated_at": _now().isoformat(),
        "expiring_soon": expiry_data["total_alerts"],
        "critical_support_expired": expiry_data["critical_count"],
        "whitespace_gaps": whitespace_data["total_gaps"],
        "no_opportunity_gaps": whitespace_data["no_opp_count"],
        "overall_trust_score": trust_data["overall_trust_score"],
        "trust_label": trust_data["overall_trust_label"],
        "mode": "mock",
    }
