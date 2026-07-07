# IBM DKG — Federated Provenance Knowledge Graph for IBM Sellers

> **WatsonX Challenge Submission · v0.2.0** — Enterprise knowledge graph mapping every IBM seller relationship, account install base, product coverage, territory assignment, and site-number hierarchy. Powered by IBM Granite + Neo4j. Fully operational in demo mode with zero backend dependencies.

---

## What It Does

The IBM DKG is a **living, agent-maintained knowledge graph** that turns raw CRM data into proactive seller intelligence. It answers questions sellers and leaders ask every day:

**Sellers**
- *"What are my next best actions today?"* → ranked list of expiring contracts, stalled deals, and co-sell gaps
- *"Give me a 360 briefing on First National Bancorp before my call."*
- *"Which IBM specialist should I bring in for a watsonx.ai co-sell in Atlanta?"*
- *"What site numbers does the State of Louisiana have, and what products are on each one?"*

**Managers & Leadership**
- *"Show me every account that has IBM installs but no open opportunity."* (Whitespace analysis)
- *"What is the territory health scorecard across my managers?"*
- *"Which of my accounts are single-threaded — only one seller covering them?"*
- *"Can I trust this data? What is the freshness score by source system?"*

**Any User**
- *"Who manages Marcus Webb?"* → full org chart from SLM → FLM → ALT → TSL → Brand Seller
- *"What site numbers have the most spend?"* → sites ranked by annual spend with visual arc rings
- *"Does Louisiana have Cognos on all its sites?"* → per-site product coverage + whitespace gaps

Every relationship is a **Knowledge Asset** with W3C PROV-DM provenance metadata (source system, confidence score, TTL, `last_verified`). A background **Pruning Agent** validates data freshness every 6 hours — stale records are flagged before they mislead anyone.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    IBM DKG — Federated Provenance Knowledge Graph             │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Zero-dependency Frontend (HTML/Canvas)             │   │
│  │  Graph View │ Insights Tab │ Trust Tab │ Export/Share │ Org Hierarchy │   │
│  └─────────────────────────────┬────────────────────────────────────────┘   │
│                                 │ REST / Fetch                               │
│  ┌──────────────────────────────▼────────────────────────────────────────┐  │
│  │                      FastAPI Backend (v0.2.0)                          │  │
│  │  /graph  /search  /ingest  /pruning  /insights                         │  │
│  │  + watsonx Orchestrate skill (orchestrate/dkg_seller_skill.yaml)       │  │
│  └───────────────────┬──────────────────────────┬─────────────────────────┘  │
│                      │                          │                             │
│            ┌─────────▼────────┐    ┌────────────▼────────┐                  │
│            │   Neo4j 5.x      │    │   Mock Store         │                  │
│            │  (Live mode)     │    │  (Demo mode — zero   │                  │
│            │  Cypher queries  │    │   credentials needed) │                  │
│            └──────────────────┘    └─────────────────────┘                  │
│                                                                               │
│  ┌──────────────────────────── 3 Agents ────────────────────────────────┐   │
│  │  Ingestion Agent       Pruning Agent         Search Agent             │   │
│  │  Validates + stamps    TTL / stale scan       NL→Cypher + trace       │   │
│  │  W3C PROV-DM           Runs every 6h         IBM Granite synthesis    │   │
│  │  provenance metadata   PruningReport log      Confidence scoring      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Why "Federated Provenance"?

Every node in the graph carries provenance metadata from its source system:

```json
{
  "source": "salesforce",
  "confidence": 0.97,
  "ttl_days": 30,
  "last_verified": "2025-07-09T14:22:00Z",
  "status": "ACTIVE"
}
```

Source systems — Salesforce CRM, IBM w3 directory, Passport Advantage install records, manual entries — each contribute independently stamped Knowledge Assets. The **Trust Dashboard** scores each source's freshness and lets leadership ask *"Can I trust this data?"* before the question is asked of them.

---

## Entity Model

| Node | Key Fields | Source System |
|---|---|---|
| **Seller** | name, email, band, geo, sellerType (CE/SSR/TSL) | Salesforce / w3 |
| **Manager** | name, email, band, territory, role (FLM/SLM/ALT) | w3 |
| **Territory** | name, region, quota | CRM |
| **Product** | name, family, version, EOL date | Seismic |
| **Account** | name, industry, segment, revenue | Salesforce |
| **Install** | product, account, version, support_end, contract_value | Passport Advantage |
| **Opportunity** | name, stage, value, close_date | Salesforce |
| **SiteNumber** | siteId, agency, annualSpend, accountId | Billing / PA |
| **KnowledgeAsset** | title, content, tags, type | Seismic / Internal |

### Relationship Model

| Edge | Meaning |
|---|---|
| `REPORTS_TO` | Seller/Manager → Manager (full SLM → FLM → ALT → TSL chain) |
| `OWNS_TERRITORY` | Seller → Territory assignment |
| `COVERS_PRODUCT` | Seller certified on a product |
| `OWNS_ACCOUNT` | Seller is primary CE/TSL for account |
| `HAS_INSTALL` | Account runs a product install |
| `RUNS_PRODUCT` | Install → Product version |
| `HAS_OPPORTUNITY` | Active deal at an account |
| `CO_SELLS` | Seller ↔ Seller co-sell motion |
| `HAS_SITE` | Account → SiteNumber (one account, many sites) |
| `HAS_PRODUCT` | SiteNumber → Product (product coverage per site) |

---

## Quick Start

### Option A — Demo Mode (zero dependencies)

```bash
cd "IBM DKG"

# Install Python deps
pip install -r requirements.txt

# Start the API (runs entirely on embedded seed data — no Neo4j, no watsonx key)
python -m uvicorn api.main:app --reload --port 8000

# Open the frontend (double-click or serve statically)
open frontend/index.html
```

The app starts in **DEMO MODE** with realistic seed data: 7 sellers, 4 managers, 7 accounts, 8 products, 7 installs, 5 site numbers, and 4 opportunities across 5 territories.

### Option B — Live Mode (Neo4j + watsonx.ai)

```bash
cp .env.example .env
# Fill in: NEO4J_PASSWORD, WATSONX_API_KEY, WATSONX_PROJECT_ID

docker compose up

open frontend/index.html
```

In live mode the search agent runs actual Cypher queries against Neo4j and uses IBM Granite for narrative synthesis. The frontend automatically switches the badge from `DEMO MODE` to `LIVE`.

### Option C — watsonx Orchestrate Integration

Import the DKG as a callable skill inside any Orchestrate agent flow:

```bash
# Set your DKG API URL
export DKG_API_URL=http://your-dkg-host:8000

# Import the skill
orchestrate skills import -f orchestrate/dkg_seller_skill.yaml
```

Sellers can then ask questions like *"What are my next best actions?"* from inside their existing Orchestrate assistant — no separate dashboard needed.

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

### Search (NL→Cypher + Granite)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/search` | Natural language search — returns results, narrative, **query_trace** |
| `GET` | `/search/quick?q=...` | Keyword search convenience endpoint |

The `/search` response now includes a `query_trace` block:

```json
{
  "narrative": "First National Bancorp runs Turbonomic v8.10 and CP4Security v1.9...",
  "query_trace": {
    "intent_detected": "account_install",
    "intent_confidence": 0.84,
    "keywords_extracted": ["first", "national", "bancorp", "installed"],
    "cypher_generated": "MATCH (a:Account)-[:HAS_INSTALL]->(i:Install)...",
    "model_used": "ibm/granite-13b-instruct-v2",
    "synthesis_mode": "watsonx_granite",
    "trace_note": "Intent matched with high confidence — targeted Cypher query executed."
  }
}
```

### Insights (Proactive Intelligence)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/insights/nba/{seller_id}` | **Next Best Actions** — ranked list combining expiring installs, stalled opportunities, and co-sell gaps |
| `GET` | `/insights/whitespace` | Accounts with installs but no open opportunity — expansion whitespace |
| `GET` | `/insights/expiring?days=N` | Support contracts expiring within N days, ranked by severity |
| `GET` | `/insights/territory-health` | Quota vs pipeline %, stale data %, health score per manager |
| `GET` | `/insights/account360/{id}` | Call-prep briefing — install base, expiry alerts, open pipeline, co-sellers |
| `GET` | `/insights/cosell-match?product_id=&geo=` | Best-fit co-seller match by product cert + geo + workload |
| `GET` | `/insights/trust` | Data freshness + provenance trust score per source system |
| `GET` | `/insights/summary` | Aggregated insight counts for dashboard header |

### Ingest & Pruning

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ingest/bulk` | Bulk JSON node ingest |
| `POST` | `/ingest/csv/{label}` | CSV file ingest |
| `POST` | `/pruning/run` | Trigger a manual pruning cycle |
| `GET` | `/pruning/last-report` | Last pruning run report |
| `GET` | `/pruning/stale-nodes` | All nodes currently marked STALE |

Interactive docs at: **http://localhost:8000/docs**

---

## Frontend Features

The frontend is a single self-contained HTML file with zero npm dependencies.

### Graph View
- **Force-directed canvas** with glowing nebula aesthetic — nodes pulse, selected edges animate
- **Node types**: Seller (blue), Manager (purple), Account (cyan), Product (orange), Install (green), Opportunity (yellow), Territory (teal), SiteNumber (sky blue), KnowledgeAsset (pink)
- **SiteNumber nodes** render with a spend-proportion arc ring — longer arc = higher annual spend
- **Filter panel** — toggle entity types on/off live
- **Org Hierarchy panel** — click any Manager or Seller to see the full reporting chain (SLM → FLM → ALT → TSL → Brand Seller) as a clickable tree

### Insights Tab *(new in v0.2.0)*
- **4 summary stat tiles** — Expired Support, Expiring 90d, Whitespace Gaps, NBA Actions
- **Support alert cards** — severity-badged (CRITICAL / HIGH / MEDIUM), with account, product, seller, and contract value tags. Click → pan graph to that account
- **Whitespace gap cards** — accounts with IBM installs but zero open pipeline, with recommended expansion products

### Trust Tab *(new in v0.2.0)*
- **Overall trust score** — colour-coded % (green ≥80%, amber ≥50%, red <50%)
- **Per-source freshness bars** — seed / Salesforce / manual / w3 each shown with total nodes, stale count, and freshness %
- **Provenance explanation** — W3C PROV-DM metadata note visible to leadership

### Granite Query Trace *(new in v0.2.0)*
Every search shows a **Show Trace** button that reveals:
- Detected intent + confidence score with colour bar
- Keywords extracted from the NL query
- Entity types matched
- Exact Cypher query generated (or mock explanation)
- Model ID and synthesis mode

### Export / Share *(new in v0.1.1)*
- **Full Graph PNG** — 2400×1400px with header bar, timestamp, node counts, legend
- **Subgraph PNG** — BFS walk from any selected node → top-down hierarchical layout (perfect for sharing a Louisiana → agencies → site numbers map)
- **CSV** — nodes + edges with all metadata fields
- **JSON** — structured graph data for programmatic import
- Live preview thumbnail before download; Copy to Clipboard support

### Sample Queries

```
"What site numbers have the most spend?"
"What site number is State of Louisiana on?"
"Does Louisiana have Cognos on all its sites?"
"Show me the seller hierarchy"
"Who manages Marcus Webb?"
"What does First National Bancorp have installed?"
"Which sellers cover watsonx.ai?"
"Find expiring support contracts"
"What opportunities does Cascadia have?"
"Co-sell relationships"
```

---

## Seller Hierarchy Model

The graph models the full IBM sales hierarchy with ALT and TSL roles:

```
Priya Nambiar (SLM — Band 11)
├── Sandra Okafor (FLM — Band 10, Northeast)
│   ├── Marcus Webb (CE — NYC Metro)
│   └── Aisha Thornton (SSR — New England, watsonx)
└── David Reyes (FLM — Band 10, Southeast)
    ├── James Kowalski (CE — Atlanta)
    ├── Lin Mei Zhang (SSR — Miami)
    └── Derek Callahan (ALT — Band 9, Public Sector South)
        └── Monique Tureaud (TSL — Baton Rouge, Cognos/LA Public Sector)
```

Click any node in the graph to see their position in this tree in the **Org Hierarchy panel**.

---

## Site Number Model

Large public sector accounts like the State of Louisiana have multiple customer/site numbers — one per agency. Each site number tracks its own product coverage and spend independently:

```
State of Louisiana (Account)
├── LA-GOV-0041 — DCFS ($1.84M/yr)  → Cognos Analytics + watsonx.ai
├── LA-GOV-0089 — DOTD ($1.12M/yr)  → Cognos Analytics only
└── LA-GOV-0117 — DHH  ($670K/yr)   → Turbonomic only  ⚠ Cognos whitespace

First National Bancorp (Account)
├── FNB-CORP-0012 — HQ ($3.2M/yr)   → Turbonomic + CP4Security
└── FNB-RET-0031  — Retail ($2.6M/yr) → watsonx.ai expansion in progress
```

Clicking a SiteNumber node shows: Site ID, agency, annual spend, active products, and **Whitespace Opportunity** — products that sibling sites have but this site does not.

---

## Demo Scenarios

### 1. Seller → Manager org chain
*"Who manages Marcus Webb?"*
```
Marcus Webb (CE) → REPORTS_TO → Sandra Okafor (FLM) → REPORTS_TO → Priya Nambiar (SLM)
```
Click Marcus Webb's node → Org Hierarchy panel shows the full tree.

### 2. Account install base + expiry alert
*"What IBM products does First National Bancorp run?"*
```
First National Bancorp
  ├── IBM Turbonomic v8.10    — support ends Apr 2026
  └── IBM CP4Security v1.9   — support ends Jul 2026
```

### 3. Stale install → opportunity
```
Nova Retail Group → HAS_INSTALL → IBM Sterling OMS v9.5
  Status: STALE (support ended Nov 2024)
  → Linked opportunity: Sterling OMS v10 Upgrade ($640K, stage: Identify)
```
The Insights tab surfaces this automatically as a CRITICAL support alert.

### 4. Whitespace analysis
```
Meridian Health Systems — has IBM installs, zero open opportunities
  Owner: James Kowalski
  Recommendation: Create a new opportunity to capture expansion revenue
```

### 5. Site number product gap
*"Does Louisiana have Cognos on all its sites?"*
```
LA-GOV-0041 (DCFS): Cognos Analytics ✓
LA-GOV-0089 (DOTD): Cognos Analytics ✓
LA-GOV-0117 (DHH):  Cognos Analytics ✗ — Whitespace Opportunity
```

### 6. Co-sell matchmaking
*"Find a watsonx.ai specialist for a deal in New England"*
```
Best match: Aisha Thornton (SSR, Boston MA)
  Certified: watsonx.ai, watsonx.governance
  Current accounts: 0  — Available for co-sell
  Match score: 0.89
```

---

## Pruning Agent

The pruning agent runs every 6 hours (configurable via `PRUNING_INTERVAL_HOURS`) and:

1. **Scans** all ACTIVE nodes — checks `last_verified` against each node's `ttl_days`
2. **Marks** expired nodes `STALE` with a `staled_at` timestamp
3. **Deletes** nodes that have been STALE for > `stale_delete_threshold_days` (default: 90)
4. **Prunes** orphaned relationships where both endpoints are DELETED
5. **Reports** a structured `PruningReport` for audit logging

The **Trust Dashboard** renders the output of each pruning cycle as a per-source freshness score — visible to leadership without them having to ask.

Trigger manually: `POST /pruning/run` or the **▶ Run Cycle** button in the dashboard.

---

## watsonx Orchestrate Integration

The DKG exposes itself as a reusable skill for watsonx Orchestrate:

```bash
orchestrate skills import -f orchestrate/dkg_seller_skill.yaml
```

**8 tool functions available to any Orchestrate agent:**

| Tool | Description |
|---|---|
| `search_knowledge_graph` | NL search with Cypher trace |
| `get_next_best_actions` | Ranked NBA list for a seller |
| `get_account_360` | Call-prep briefing |
| `get_whitespace_gaps` | Expansion opportunity analysis |
| `get_expiring_support` | Support contract alerts |
| `find_cosell_match` | Best-fit co-seller recommendation |
| `get_territory_health` | Leadership scorecard |
| `get_trust_dashboard` | Data provenance trust scores |

Sellers query these from inside their existing Orchestrate flows — no separate dashboard needed.

---

## Project Structure

```
IBM DKG/
├── api/
│   ├── main.py                  # FastAPI app, lifespan, routing (v0.2.0)
│   ├── config.py                # Environment-based settings (pydantic-settings)
│   ├── agents/
│   │   ├── ingestion_agent.py   # Validates + W3C PROV-DM stamps on ingest
│   │   ├── pruning_agent.py     # TTL staleness scan + soft-delete + report
│   │   └── search_agent.py      # NL→Cypher, intent confidence, query_trace
│   ├── graph/
│   │   ├── neo4j_client.py      # Async Neo4j driver + Cypher helpers
│   │   └── schemas.py           # Pydantic models (ProvenanceMixin on all nodes)
│   ├── routers/
│   │   ├── graph.py             # CRUD: nodes, relationships, neighbors
│   │   ├── search.py            # NL enterprise search endpoint
│   │   ├── ingest.py            # Bulk + CSV ingest
│   │   ├── pruning.py           # Pruning agent control + reports
│   │   └── insights.py          # NEW: NBA, whitespace, 360, health, trust
│   └── data/
│       ├── mock_store.py        # In-memory BFS graph (zero-dep demo mode)
│       └── seed_data.json       # Full seed: 7 sellers, 7 accounts, 8 products,
│                                #            5 site numbers, ALT/TSL hierarchy
├── orchestrate/
│   └── dkg_seller_skill.yaml    # NEW: watsonx Orchestrate skill definition
├── frontend/
│   └── index.html               # Self-contained canvas graph dashboard
│                                # Tabs: Graph / Insights / Trust
│                                # Features: export, org tree, query trace
├── data/                        # Persistent data / Chroma vector store
├── docker-compose.yml           # Neo4j 5.x + FastAPI
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## Roadmap

| Capability | Dependency | Status |
|---|---|---|
| Salesforce CRM live sync | Salesforce API key | 🔐 Pending |
| Passport Advantage install base import | IBM PA API | 🔐 Pending |
| w3 org chart live sync | IBM w3 API | 🔐 Pending |
| Seismic knowledge asset ingestion | Seismic API | 🔐 Pending |
| watsonx.ai Granite narrative (live) | IBM Cloud credentials | 🔑 Ready to plug in |
| Neo4j Aura (production graph) | Neo4j Aura account | ☁️ Ready to provision |
| watsonx Orchestrate deployment | wxO instance | ✅ Skill YAML ready |
| NL alert subscriptions ("tell me when…") | Scheduler + webhook | 🗓 Planned |
| Embedding-based semantic search (Slate) | watsonx embed creds | 🔑 Ready to plug in |
| Account risk scoring (org-chart single-threading) | Graph data | ✅ Logic in /insights |

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
