# IBM Scout — Sales Content Optimization & Utility Tool

> **v0.6.0** — Enterprise knowledge graph mapping every IBM seller relationship, account install base, product coverage, territory assignment, site-number hierarchy, deployment adoption health (Gainsight), and open pipeline. Powered by IBM Granite + Neo4j. Fully operational in demo mode with zero backend dependencies.

---

## What It Does

IBM Scout is a **living, graph-powered seller intelligence platform** that turns raw CRM, Passport Advantage, w3, Gainsight, and IFC data into proactive seller intelligence. It answers questions sellers and leaders ask every day:

**Sellers**
- *"Who manages Marcus Webb and what accounts does he own?"* → org hierarchy with role badges, account sub-list
- *"What does First National Bancorp have installed?"* → Account 360 — installs, open pipeline, deployments, site numbers
- *"Show me all stalled deployments"* → Gainsight-sourced deployment health with blockers and expand signals
- *"What open opportunities are closing in the next 30 days?"* → pipeline with urgency flags and stage bar
- *"Which sellers cover the Southeast territory?"* → territory detail with quota bar, sellers, accounts
- *"Which sellers are certified on watsonx.ai?"* → product page with certified seller roster
- *"Find all expiring support contracts in the next 90 days"* → install base with EOS/expiry urgency banners
- *"Who can co-sell watsonx with a CE in the Northeast?"* → co-sell partner matching

**Managers & Leadership**
- *"Show me every account that has IBM installs but no open opportunity."* → Whitespace analysis
- *"Show me the seller hierarchy"* → full-screen SVG hierarchy: SLM → FLM → ATL/TSL → Sellers
- *"Give me a weekly digest of my whole book — EOS, renewals, and pipeline."*

Every relationship is a **Knowledge Asset** with W3C PROV-DM provenance metadata. A background **Pruning Agent** validates data freshness — stale records are flagged before they mislead anyone.

---

## What's New in v0.6.0

| Area | Change |
|---|---|
| **Search hub** | `search.html` — enterprise search landing page with watsonx.hub-style dark UI, hero search, role pills, entity filter pills, and card grid |
| **Rich answer engine** | `buildRichAnswer()` + `pushRichAnswer()` in chat rail — intent-aware HTML panels replacing plain text (8 intents: org, account, install, deployment, opportunity, territory, product, cosell) |
| **Contextual follow-ups** | `getFollowUps()` appends 3 context-aware suggested questions after every chat answer, using actual entity names from the result |
| **Deployment detail page** | `deployment.html` — Gainsight-style page with urgency banner, KPI strip (adoption%, activated/entitled, active users 30d, use cases, status), blockers list, expand signals, use case tracker (Live/Blocked/Planned), CSM + seller team panel, deployment timeline, escalate/expand actions |
| **Account 360 page** | `account.html` — KPI strip (installs/opps/deployments/sites/spend), install base with EOS alerts, pipeline list, deployment health, site numbers with spend bar, account team |
| **Territory detail page** | `territory.html` — quota coverage bar, sellers with role badges, accounts list, pipeline vs quota KPIs |
| **Product detail page** | `product.html` — co-sell motion banner, installed accounts with support status, certified sellers (primary/covered), deployments with Gainsight health |
| **Install record page** | `install.html` — urgency banner (EOS/expiring/stable), contract details, linked deployment panel, support lifecycle timeline, Renew/Upgrade/Account 360 actions |
| **Opportunity detail page** | `opportunity.html` — urgency banner (overdue/closing soon/normal), visual stage pipeline bar, numbered next-steps checklist, related account + install panels |
| **Universal routing** | `openNode()` dispatches on ID prefix — `dep-`/`acc-`/`ter-`/`prd-`/`ins-`/`opp-` each open their own detail page; sellers/managers/site-numbers go to graph view |
| **`/chat` endpoint** | `POST /chat` returns structured `answer` + `follow_ups` + `mode` (live/mock) — consumed by search.html chat rail |
| **Deployment data layer** | 7 Deployment nodes (Turbonomic, watsonx.ai, OpenPages, Sterling OMS, CP4Security, Cognos×2) with `HAS_DEPLOYMENT`, `AT_SITE`, `DRIVES_DEPLOYMENT` relationships in seed data |
| **Gainsight KPIs in seed** | `adoptionPct`, `gainsightScore`, `gainsightHealthLabel`, `activatedUnits`, `entitledUnits`, `activeUsers30d`, `blockers[]`, `expandSignals[]`, `csmName/Email`, `useCasesLive/Identified` |
| **Insights deployment KPIs** | `/insights/summary` now returns `deployment_red_count`, `deployment_stalled_count`, `deployment_expand_ready`, `avg_adoption_pct` |
| **Greeting panel** | 8 intent-labelled suggested-question chips covering all supported query paths |
| **ATL/TSL peer fix** | ATL (Area Tech Leader) and TSL (Technology Sales Leader) are correctly modelled as peers — both report directly to FLM, neither manages the other |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    IBM Scout — Sales Content Optimization & Utility Tool        │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                    Frontend (HTML/CSS/JS — no build step)                │   │
│  │                                                                          │   │
│  │   search.html           deployment.html    account.html                  │   │
│  │   Enterprise search     Gainsight detail   Account 360                   │   │
│  │   hub + chat rail       KPI / blockers /   Installs / opps /             │   │
│  │   Rich answer panels    expand signals     deployments / sites           │   │
│  │                                                                          │   │
│  │   territory.html        product.html       install.html                  │   │
│  │   Quota bar             Co-sell banner     EOS urgency                   │   │
│  │   Sellers / accounts    Certs / installs   Contract + timeline           │   │
│  │                                                                          │   │
│  │   opportunity.html      index.html                                       │   │
│  │   Stage pipeline bar    SVG dual-graph, hierarchy flow, write-back,      │   │
│  │   Next-steps checklist  drag engine, modernize, partners, trust          │   │
│  └──────────────────────────────┬───────────────────────────────────────────┘   │
│                                  │ REST / Fetch (graceful fallback to mock)      │
│  ┌───────────────────────────────▼───────────────────────────────────────────┐   │
│  │                         FastAPI Backend                                   │   │
│  │  /graph   /search   /ingest   /pruning   /insights   /chat                │   │
│  └───────────────────┬──────────────────────────┬─────────────────────────── ┘  │
│                      │                          │                               │
│            ┌─────────▼────────┐    ┌────────────▼─────────┐                    │
│            │   Neo4j 5.x      │    │   Mock Store         │                    │
│            │  (Live mode)     │    │  (Demo mode — zero   │                    │
│            │  Cypher queries  │    │   credentials needed)│                    │
│            └──────────────────┘    └──────────────────────┘                    │
│                                                                                 │
│  ┌──────────────────────────── 3 Agents ─────────────────────────────────────┐  │
│  │  Ingestion Agent       Pruning Agent         Search Agent                 │  │
│  │  Validates + stamps    TTL / stale scan       NL→Cypher + trace           │  │
│  │  W3C PROV-DM           Runs every 6h         IBM Granite synthesis        │  │
│  │  provenance metadata   PruningReport log      12 intent patterns          │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Entity Model

| Node | Key Fields | Source System |
|---|---|---|
| **Seller** | name, email, band, geo, sellerType (CE/BSS/TSL/ATL) | Salesforce / w3 |
| **Manager** | name, email, band, territory, role (FLM/SLM/ATL) | w3 |
| **Territory** | name, region, geo, quota | CRM |
| **Product** | name, family, version | Seismic / PA |
| **Account** | name, industry, segment, revenue | Salesforce |
| **Install** | productId, accountId, version, supportEnd, contractValue | Passport Advantage |
| **Opportunity** | name, stage, value, closeDate, productId | Salesforce |
| **SiteNumber** | siteId, agency, annualSpend, accountId | Billing / PA |
| **Deployment** | deploymentStatus, adoptionPct, gainsightScore, gainsightHealthLabel, activatedUnits, entitledUnits, activeUsers30d, blockers[], expandSignals[], useCasesLive, useCasesIdentified, csmName/Email, goLiveDate | Gainsight |
| **KnowledgeAsset** | title, content, tags, type, source (incl. `human_writeback`) | Seismic / Human |

### Relationship Model

| Edge | Meaning |
|---|---|
| `REPORTS_TO` | Seller/Manager → Manager (SLM → FLM → ATL/TSL chain; ATL and TSL are peers both reporting to FLM) |
| `OWNS_TERRITORY` | Seller → Territory assignment |
| `COVERS_PRODUCT` | Seller certified on a product |
| `OWNS_ACCOUNT` | Seller is primary CE/TSL/BSS for account |
| `HAS_INSTALL` | Account runs a product install |
| `RUNS_PRODUCT` | Install → Product version |
| `HAS_OPPORTUNITY` | Active deal at an account |
| `CO_SELLS` | Seller ↔ Seller co-sell motion |
| `HAS_SITE` | Account → SiteNumber (one account, many sites) |
| `HAS_PRODUCT` | SiteNumber → Product (product coverage per site) |
| `HAS_DEPLOYMENT` | Install → Deployment (Gainsight record) |
| `AT_SITE` | Deployment → SiteNumber (deployment is active at this site) |
| `DRIVES_DEPLOYMENT` | Seller → Deployment (account owner drives this deployment) |

---

## Quick Start

### Option A — Demo Mode (zero dependencies)

```bash
cd "IBM DKG"

# Install Python deps
pip install -r requirements.txt

# Start the API (runs entirely on embedded seed data — no Neo4j, no watsonx key)
python -m uvicorn api.main:app --reload --port 8000

# Open the search hub (recommended entry point)
open frontend/search.html

# Or open the graph view directly
open frontend/index.html
```

The app starts in **DEMO MODE** with realistic seed data:
- **People**: 7 sellers (3 CE, 2 BSS/TSL, 1 ATL, 1 BSS), 4 managers (SLM/2×FLM/ATL)
- **Coverage**: 5 territories, 8 products, 7 accounts, 7 installs, 4 opportunities
- **Sites**: 5 site numbers (3 Louisiana, 2 First National Bancorp)
- **Deployments**: 7 Gainsight deployment records — Turbonomic, watsonx.ai, OpenPages, Sterling OMS, CP4Security, Cognos Analytics ×2

### Option B — Live Mode (Neo4j + watsonx.ai)

```bash
cp .env.example .env
# Fill in: NEO4J_PASSWORD, WATSONX_API_KEY, WATSONX_PROJECT_ID

docker compose up

open frontend/search.html
```

In live mode the search agent runs actual Cypher queries against Neo4j and uses IBM Granite for narrative synthesis. The frontend automatically switches the mode badge from `DEMO MODE` to `LIVE API`.

---

## Frontend Pages

| Page | Entry Point | Purpose |
|---|---|---|
| `search.html` | **Recommended start** | Enterprise search hub — dark theme, hero search, role pills, entity cards, AI chat rail with rich answer panels |
| `index.html` | Graph explorer | Interactive SVG force-directed graph with hub clusters, hierarchy flow, drag engine, write-back, modernize, partners, trust tabs |
| `deployment.html?id=dep-XXX` | Deployment detail | Gainsight-style — urgency banner, KPI strip, blockers, expand signals, use case tracker, team, timeline |
| `account.html?id=acc-XXX` | Account 360 | KPI strip, install base, pipeline, deployments, site numbers, account team |
| `territory.html?id=ter-XXX` | Territory detail | Quota coverage bar, sellers with role badges, accounts list |
| `product.html?id=prd-XXX` | Product catalog | Co-sell banner, installed accounts, certified sellers, deployments |
| `install.html?id=ins-XXX` | Install record | EOS/expiry urgency, contract details, linked deployment, lifecycle timeline |
| `opportunity.html?id=opp-XXX` | Opportunity detail | Stage pipeline bar, next-steps checklist, related account + install |

**Navigation is fully wired** — clicking any card on `search.html` routes to the appropriate detail page by ID prefix. Every detail page links back to Search, Graph View, and related entities.

---

## Search Hub (`search.html`)

The primary entry point for IBM Scout. Features:

- **Hero search bar** — live debounced search (280ms) + Enter key
- **Role pills** — filter by CE/Seller, BSS/Brand Specialist, Manager/FLM, Executive/SLM
- **Entity filter pills** — all label types including Deployment
- **What's New ticker** — live-scrolling deployment signals (RED health, stalled, expand-ready)
- **Insights hero chips** — live from `/insights/summary` — shows expiring support count, RED deployment count, stalled deployments, expand-ready count, avg adoption %, whitespace gaps, trust score
- **Card grid** — Gainsight health badges on deployment cards, support expiry alerts on install cards
- **AI chat rail** — `POST /chat` → rich HTML panel responses (no plain text)
- **8 intent-labelled suggested questions** covering every query type on first load

### Rich Answer Engine (chat rail)

Every search and chat message returns a `buildRichAnswer()` HTML panel — not plain text:

| Intent | What renders |
|---|---|
| `org` | Hierarchy rows (SLM→FLM→seller) with role badges, account sub-rows, site numbers |
| `account` | 4-stat grid (installs/opps/deps/sellers) + install base + pipeline panels |
| `install` | Support status table with days-remaining badges and expired/expiring counts |
| `deployment` | Adoption % per deployment, Gainsight health badges, blocker/expand indicators |
| `opportunity` | Stage-coloured pipeline rows with urgency flag for close < 30d |
| `territory` | Quota bar + seller list with role badges |
| `product` | Product rows + certified seller sub-list |
| `cosell` | Co-sell partner list |
| `general` | Top-7 entity rows |

After every answer, `getFollowUps()` appends 3 context-aware follow-up question chips using actual entity names from the result set.

---

## Deployment & Gainsight Layer

IBM Scout models the post-sale deployment lifecycle through Gainsight-sourced `Deployment` nodes:

```
Install ──HAS_DEPLOYMENT──► Deployment ──AT_SITE──► SiteNumber
                                 ▲
                          DRIVES_DEPLOYMENT
                                 │
                              Seller
```

### Deployment Fields

| Field | Description |
|---|---|
| `deploymentStatus` | `LIVE`, `IN_PROGRESS`, `STALLED`, `NOT_STARTED` |
| `gainsightHealthLabel` | `GREEN`, `YELLOW`, `RED` |
| `gainsightScore` | 0–100 composite health score |
| `adoptionPct` | Activated ÷ Entitled seats × 100 |
| `activatedUnits` / `entitledUnits` | Seat activation ratio |
| `activeUsers30d` | Users active in last 30 days |
| `useCasesLive` / `useCasesIdentified` | Use case completion ratio |
| `blockers[]` | Named blockers preventing deployment progress |
| `expandSignals[]` | Named signals indicating upsell/cross-sell opportunity |
| `csmName` / `csmEmail` | Customer Success Manager assigned |
| `goLiveDate` / `targetGoLiveDate` | Actual and target go-live |
| `lastGainsightSync` | Timestamp of last Gainsight data sync |

### Urgency Scoring (used by `/insights/deployment`)

| Condition | Urgency | Score |
|---|---|---|
| `STALLED` or `CHURNED` | 🔴 Critical | 85+ |
| `IN_PROGRESS` + Gainsight score < 65 | 🟠 High | 70+ |
| `IN_PROGRESS` + score ≥ 65 | 🟡 Medium | 55+ |
| `LIVE` + `YELLOW` health | 🟡 Needs attention | 50 |
| `LIVE` + `GREEN` + expand signals | 🟢 Expand ready | 20 |

### Seed Deployments (7 records)

| Deployment | Status | Gainsight | Adoption |
|---|---|---|---|
| Turbonomic @ First National Bancorp — HQ | LIVE | GREEN 88 | 97% |
| watsonx.ai @ Apex Technology Partners | IN_PROGRESS | YELLOW 61 | 42% |
| OpenPages @ Cascadia Insurance Group | LIVE | YELLOW 72 | 96% |
| Sterling OMS @ Nova Retail Group | STALLED | RED 31 | 38% |
| CP4Security @ First National Bancorp — HQ | IN_PROGRESS | YELLOW 74 | 68% |
| Cognos Analytics @ State of Louisiana — DCFS | LIVE | GREEN 91 | 99% |
| Cognos Analytics @ State of Louisiana — DOTD | STALLED | RED 44 | 51% |

---

## API Reference

### Core Graph

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/healthz` | Health check — mode (live/mock), graph stats |
| `GET` | `/graph/full` | Full graph for visualization |
| `GET` | `/graph/nodes` | List nodes (label, status filters) |
| `GET` | `/graph/nodes/{label}/{id}` | Single node detail |
| `POST` | `/graph/nodes/{label}` | Create/update a node |
| `GET` | `/graph/neighbors/{id}` | BFS neighborhood traversal |
| `POST` | `/graph/relationships` | Create/update a relationship |
| `GET` | `/graph/stats` | Node/edge counts by type |

### Search + Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/search` | Natural language search — results, narrative, `query_trace` |
| `GET` | `/search/quick?q=...` | Keyword search convenience endpoint |
| `POST` | `/chat` | Conversational query — returns `answer`, `follow_ups[]`, `mode`, `entities[]` |

The `/chat` endpoint is consumed by the chat rail in `search.html`. It returns structured follow-up suggestions that render as clickable chips.

### Insights

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/insights/nba/{seller_id}` | **Next Best Actions** — ranked list |
| `GET` | `/insights/whitespace` | Accounts with installs but no open opportunity |
| `GET` | `/insights/expiring?days=N` | Support contracts expiring within N days |
| `GET` | `/insights/territory-health` | Quota vs pipeline %, stale %, health score per manager |
| `GET` | `/insights/account360/{id}` | Call-prep briefing — installs, expiry, pipeline, co-sellers |
| `GET` | `/insights/cosell-match?product_id=&geo=` | Best-fit co-seller by product cert + geo |
| `GET` | `/insights/trust` | Data freshness + provenance trust score per source |
| `GET` | `/insights/deployment` | Deployment urgency scores, blockers, expand signals |
| `GET` | `/insights/summary` | Aggregated counts — expiring, EOS, whitespace, deployment KPIs, trust |

`/insights/summary` returns deployment KPIs used by the hero chip bar:
- `deployment_red_count`, `deployment_stalled_count`, `deployment_expand_ready`, `avg_adoption_pct`

### Ingest & Pruning

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ingest/bulk` | Bulk JSON node ingest |
| `POST` | `/ingest/csv/{label}` | CSV file ingest |
| `POST` | `/pruning/run` | Trigger a manual pruning cycle |
| `GET` | `/pruning/last-report` | Last pruning run report |
| `GET` | `/pruning/stale-nodes` | All nodes currently marked STALE |

Interactive docs: **http://localhost:8000/docs**

---

## Seller Hierarchy Model

```
Priya Nambiar (SLM — Band 11, West US)
├── Sandra Okafor (FLM — Band 10, Northeast)
│   ├── Marcus Webb (CE — NYC Metro)       accounts: First National Bancorp, Cascadia Insurance
│   └── Aisha Thornton (BSS — New England) product: watsonx suite
└── David Reyes (FLM — Band 10, Southeast)
    ├── James Kowalski (CE — Atlanta)       accounts: Meridian Health, Nova Retail Group
    ├── Lin Mei Zhang (TSL — Miami)         accounts: SunCoast Logistics
    ├── Monique Tureaud (BSS/TSL — Baton Rouge)  accounts: State of Louisiana
    │   [TSL peer to ATL — both report directly to FLM David Reyes]
    └── Derek Callahan (ATL — Public Sector South)
        [ATL peer to TSL — both report directly to FLM David Reyes]

Tyler Oduya (CE — San Francisco)           → reports to Priya Nambiar (SLM)
Rachel Patel (BSS/Security — Los Angeles)  → reports to Priya Nambiar (SLM)
```

> **ATL** = Area Tech Leader — technical advocacy and brand activation.
> **TSL** = Technology Sales Leader — brand/product specialist.
> ATL and TSL are **peers** — both report directly to the FLM. Neither manages the other.
> **BSS** = Brand Sales Specialist — same role family as TSL.

---

## Site Number Model

```
State of Louisiana (acc-007) — 3 sites in seed data
├── LA-GOV-0041 — DCFS ($1.84M/yr)  → Cognos v12 ✓  watsonx.ai ✓
├── LA-GOV-0089 — DOTD ($1.12M/yr)  → Cognos v11.2 ✓ (stale, out of support)
└── LA-GOV-0117 — DHH  ($670K/yr)   → Turbonomic ✓   ⚠ no Cognos yet

First National Bancorp (acc-001) — 2 sites in seed data
├── FNB-CORP-0012 — Corporate HQ   ($3.2M/yr)  → Turbonomic ✓ + CP4Security ✓
└── FNB-RET-0031  — Retail Banking ($2.6M/yr)  → watsonx.ai (IN_PROGRESS)
```

---

## Demo Scenarios

### 1. Stalled deployment — seller intervention required
Click `search.html` → search *"stalled deployments"* → Chat rail shows deployment intent panel with RED health badges. Click **Sterling OMS @ Nova Retail** card → `deployment.html` opens with:
- 🔴 Critical urgency banner: 3 blockers (out-of-support, IT freeze, competitive eval)
- 38% adoption, Gainsight score 31
- Action buttons: **⚠ Escalate to Manager**, **🕸 View in Graph**

### 2. Account 360 with install risk
Search *"First National Bancorp"* → `account.html` shows:
- 2 installs (Turbonomic ACTIVE, CP4Security ACTIVE)
- 1 open opportunity ($2.4M watsonx expansion)
- 2 deployments (Turbonomic GREEN 88, CP4Security YELLOW 74)
- 2 site numbers (FNB-CORP-0012, FNB-RET-0031) with spend bar

### 3. Org hierarchy query
Search *"Who manages Marcus Webb?"* → Chat rail renders org intent panel: Sandra Okafor (FLM) → Marcus Webb (CE) with accounts sub-rows. Click any row to open the entity detail page.

### 4. Expiring support with renewal action
Search *"expiring support"* → Chat rail shows install intent panel with EOS badges. Click **OpenPages @ Cascadia** → `install.html` shows:
- 🟠 Warn banner: support ends in <N days
- Linked deployment (LIVE, 96% adoption, YELLOW) with link to `deployment.html`
- Actions: **⚠ Initiate Renewal**, **📦 View Upgrade Path**, **🏢 Account 360**

### 5. Opportunity with stage pipeline bar
Search *"open opportunities"* → click **Cascadia OpenPages Upgrade** → `opportunity.html` shows:
- Visual stage bar: Identify → Qualify → **Propose** → Validate → Close
- 🟠 Warn banner if closing < 30 days
- 4-step numbered next-steps checklist
- Related account link + linked install with adoption %

### 6. Product coverage + co-sell
Search *"watsonx.ai certified sellers"* → `product.html` shows:
- Aisha Thornton (BSS, primary), Tyler Oduya (CE, covered)
- Co-sell motion banner: paired with watsonx.data + watsonx.governance
- 1 active install (Apex, $1.2M) with 42% adoption warning

### 7. Territory quota view
Search *"Bay Area Tech territory"* → `territory.html` shows:
- $9.2M quota, pipeline coverage bar
- Tyler Oduya (CE) with role badge + San Francisco geo
- Linked accounts list

### 8. Human write-back (graph view)
Open `index.html` → click any Account node → Human Validation panel → **✎ Correct** → correction logged as a `KnowledgeAsset` with W3C PROV-DM provenance.

---

## Pruning Agent

Runs every 6 hours (`PRUNING_INTERVAL_HOURS`) and:

1. **Scans** all ACTIVE nodes — checks `last_verified` against `ttl_days`
2. **Marks** expired nodes `STALE` — unless recently confirmed via human write-back
3. **Deletes** nodes STALE for > `stale_delete_threshold_days` (default 90)
4. **Prunes** orphaned relationships where both endpoints are DELETED
5. **Reports** a structured `PruningReport` for audit logging

Trigger manually: `POST /pruning/run`

---

## Project Structure

```
IBM Scout/         (repo folder: IBM DKG)
├── api/
│   ├── main.py                  # FastAPI app, lifespan, 6 routers (incl. /chat)
│   ├── config.py                # Environment-based settings (pydantic-settings)
│   ├── agents/
│   │   ├── ingestion_agent.py   # Validates + W3C PROV-DM stamps on ingest
│   │   ├── pruning_agent.py     # TTL staleness scan + soft-delete + PruningReport
│   │   └── search_agent.py      # NL→Cypher, 12 intent patterns, query_trace
│   ├── graph/
│   │   ├── neo4j_client.py      # Async Neo4j driver + Cypher helpers
│   │   └── schemas.py           # Pydantic models — DeploymentNode (50 fields),
│   │                            #   RelationshipType (incl. HAS_DEPLOYMENT, AT_SITE,
│   │                            #   DRIVES_DEPLOYMENT), ProvenanceMixin
│   ├── routers/
│   │   ├── graph.py             # CRUD: nodes, relationships, neighbors
│   │   ├── search.py            # NL enterprise search
│   │   ├── ingest.py            # Bulk + CSV ingest
│   │   ├── pruning.py           # Pruning agent control + reports
│   │   ├── insights.py          # NBA, whitespace, 360, deployment, health, trust
│   │   └── chat.py              # POST /chat — answer + follow_ups + mode
│   └── data/
│       ├── mock_store.py        # In-memory BFS graph (54 nodes, 85 edges in demo)
│       └── seed_data.json       # Full seed data — 7 Deployment nodes + 19 dep rels
├── frontend/
│   ├── search.html              # Enterprise search hub — hero search, chat rail,
│   │                            #   rich answer engine (8 intents), role/entity pills,
│   │                            #   insights hero chips, What's New ticker
│   ├── index.html               # SVG dual-graph — hub clusters, hierarchy flow,
│   │                            #   drag engine, write-back, modernize, partners, trust
│   ├── deployment.html          # Gainsight deployment detail (7 records)
│   ├── account.html             # Account 360 (7 accounts)
│   ├── territory.html           # Territory detail (5 territories)
│   ├── product.html             # Product catalog (8 products)
│   ├── install.html             # Install record detail (7 installs)
│   ├── opportunity.html         # Opportunity detail (4 opportunities)
│   └── assets/
│       ├── scout-logo.png
│       ├── IBM_Scout_Pitch.pdf
│       └── IBM_Scout_Pitch.pptx
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## Roadmap

| Capability | Status |
|---|---|
| Salesforce CRM live sync | 🔐 Pending API key |
| Passport Advantage install base import | 🔐 Pending IBM PA API |
| w3 org chart live sync | 🔐 Pending IBM w3 API |
| Gainsight live sync (replace seed data) | 🔐 Pending Gainsight API key |
| watsonx.ai Granite narrative (live) | 🔑 Ready to plug in |
| Neo4j Aura (production graph) | ☁️ Ready to provision |
| watsonx Orchestrate skill deployment | 🗓 YAML previously generated; reconnect after skill export |
| Human write-back → backend persistence | 🗓 Session-only today; DB persistence planned |
| Slack / Teams query bot | 🗓 Digest copy-ready today; bot connector planned |
| NL alert subscriptions ("tell me when…") | 🗓 Planned |
| Seller / Manager detail pages | 🗓 Currently → graph view; dedicated pages planned |
| SiteNumber detail page | 🗓 Currently → graph view; dedicated page planned |
| Embedding-based semantic search | 🔑 Ready to plug in |
| Conflict detection persistence | 🗓 Session-only today |

---

## Configuration (`.env`)

```env
# Neo4j (leave blank for demo mode)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=

# watsonx.ai (leave blank for template mode)
WATSONX_API_KEY=
WATSONX_PROJECT_ID=
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-13b-instruct-v2

# Pruning agent
PRUNING_INTERVAL_HOURS=6
DEFAULT_NODE_TTL_DAYS=30
STALE_DELETE_THRESHOLD_DAYS=90
```

Copy `.env.example` to `.env` and fill in only what you have. All fields are optional — the system degrades gracefully to mock mode for any missing credential.
