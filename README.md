# IBM DKG — Federated Provenance Knowledge Graph for IBM Sellers

> **WatsonX Challenge Submission · v0.3.0** — Enterprise knowledge graph mapping every IBM seller relationship, account install base, product coverage, territory assignment, site-number hierarchy, business partner network, and modernization pipeline. Powered by IBM Granite + Neo4j. Fully operational in demo mode with zero backend dependencies.

---

## What It Does

The IBM DKG is a **living, agent-maintained knowledge graph** that turns raw CRM, Passport Advantage, w3, and IFC data into proactive seller intelligence. It answers questions sellers and leaders ask every day:

**Sellers**
- *"What are my next best actions today?"* → ranked list of expiring contracts, stalled deals, and co-sell gaps
- *"Which accounts in my book have a renewal coming up — and what should I modernize them to?"*
- *"Draft me a Why-Modernize email to the PO contact for the Cascadia OpenPages renewal."*
- *"What site numbers does the State of Louisiana have, and what products are on each one?"*
- *"Does Louisiana have Cognos on all its sites?"* → per-site coverage matrix + whitespace gaps
- *"What business partners are selling into my accounts, and who is the IBM partner liaison?"*

**Managers & Leadership**
- *"Show me every account that has IBM installs but no open opportunity."* (Whitespace analysis)
- *"What is the territory health scorecard across my managers?"*
- *"Give me a weekly digest of my whole book — EOS, renewals, and pipeline."*
- *"Can I trust this data? What is the freshness score by source system?"*

**Any User**
- *"Who manages Marcus Webb?"* → full org chart from SLM → FLM → ALT → TSL → Brand Seller
- *"What site numbers have the most spend?"* → ranked spend table with visual arc rings
- *"Is this account record still accurate?"* → confirm or correct any node with human write-back, automatically logged as a provenance-stamped KnowledgeAsset

Every relationship is a **Knowledge Asset** with W3C PROV-DM provenance metadata (source system, confidence score, TTL, `last_verified`). A background **Pruning Agent** validates data freshness — stale records are flagged before they mislead anyone. Human confirmations and corrections close the loop, turning the DKG into a truly decentralized graph where data quality is a shared responsibility.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    IBM DKG — Federated Provenance Knowledge Graph             │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │              Zero-dependency Frontend (HTML/Canvas) — v0.3.0          │   │
│  │  Graph │ Insights │ Modernize │ Partners │ Trust │ Hierarchy │ Export  │   │
│  │  Role/Entitlement pill │ Write-back │ Conflict detection │ Explainability │
│  └─────────────────────────────┬────────────────────────────────────────┘   │
│                                 │ REST / Fetch (graceful fallback to mock)   │
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

Every node carries provenance metadata from its source system:

```json
{
  "source": "salesforce",
  "confidence": 0.97,
  "ttl_days": 30,
  "last_verified": "2025-07-09T14:22:00Z",
  "status": "ACTIVE"
}
```

Source systems — Salesforce CRM, IBM w3 directory, Passport Advantage, IFC partner data, and **human write-back** — each contribute independently stamped Knowledge Assets. When two sources disagree, conflict detection surfaces the discrepancy and resolves it by confidence + recency. The **Trust Dashboard** scores each source's freshness and the **Explainability Trail** on every node shows exactly which edges and sources were used to produce any answer.

---

## Entity Model

| Node | Key Fields | Source System |
|---|---|---|
| **Seller** | name, email, band, geo, sellerType (CE/SSR/TSL/PL) | Salesforce / w3 |
| **Manager** | name, email, band, territory, role (FLM/SLM/ALT) | w3 |
| **Territory** | name, region, quota | CRM |
| **Product** | name, family, version, EOL date | Seismic |
| **Account** | name, industry, segment, revenue | Salesforce |
| **Install** | product, account, version, support_end, contract_value, renewalDate, poContact | Passport Advantage |
| **Opportunity** | name, stage, value, close_date | Salesforce |
| **SiteNumber** | siteId, agency, annualSpend, accountId | Billing / PA |
| **BusinessPartner** | name, partnerTier, poContact, liaisonId | IFC / Partner Portal |
| **KnowledgeAsset** | title, content, tags, type, source (incl. `human_writeback`) | Seismic / Human |

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
| `PARTNER_SELLS` | BusinessPartner → Account (partner-sourced revenue) |
| `LIAISED_BY` | BusinessPartner → Seller (IBM Partner Liaison assignment) |

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

The app starts in **DEMO MODE** with realistic seed data: 9 sellers (including 2 Partner Liaisons), 4 managers, 7 accounts, 8 products, 7 installs, 5 site numbers, 3 business partners, and 4 opportunities across 5 territories.

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
export DKG_API_URL=http://your-dkg-host:8000
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

The `/search` response includes a `query_trace` block with the generated Cypher, intent confidence, and synthesis mode. Intent routing covers: `site_spend`, `site_product_matrix`, `product_coverage`, `account_sites`, `hierarchy`, `org`, `install`, `territory`, `product`, `opportunity`, `cosell`.

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

## Frontend Features (v0.3.0)

The frontend is a single self-contained HTML file — no npm, no build step, no external assets.

### Graph View
- **Force-directed canvas** with glowing nebula aesthetic — nodes pulse, selected edges animate with travelling dots
- **Node types**: Seller (blue), Manager (purple), Account (cyan), Product (orange), Install (green), Opportunity (yellow), Territory (teal), SiteNumber (sky-blue), BusinessPartner (purple), KnowledgeAsset (pink)
- **SiteNumber nodes** render with a spend-proportion arc ring — longer arc = higher annual spend
- **Filter panel** — toggle entity types on/off live
- **👥 Hierarchy button** in graph toolbar — one click shows the full SLM → FLM → ALT → TSL org tree
- **Org Hierarchy panel** — role-colored badges (SLM=purple, FLM=cyan, ALT=teal, TSL/CE=blue, SSR=light-blue), seller site IDs shown inline

### Insights Tab
- **4 summary tiles** — Expired Support, Expiring 90d, Whitespace Gaps, NBA Actions
- **Support alert cards** — severity-badged (CRITICAL / HIGH / MEDIUM), click → pan graph to account
- **Whitespace gap cards** — accounts with IBM installs but zero open pipeline

### Modernize Tab *(new in v0.3.0)*
- **Scoped to your book** — shows only installs for accounts you own (switches automatically with View As role)
- **3 urgency tiers**: EOS/Expired (red), Renewal < 90d (yellow), Upgrade (cyan) — sorted by urgency
- Every card shows: product, account, renewal date, **PO contact name + email from Passport Advantage**, contract value, and exact **modernization path** (e.g. `v8.3 → v9 SaaS — automated controls, AI risk scoring`)
- **✉ Draft Email button** → opens pre-filled Why-Modernize email modal (Granite template)
  - To field pre-filled with PO contact email
  - Subject and body generated with product details, renewal date, upgrade path, and IBM seller signature
  - Edit then **Send via mailto** or **Copy to clipboard**
- **✉ Weekly Digest tile** → formatted book-of-business digest showing EOS, renewals, whitespace gaps, total addressable pipeline ($M), and Next Best Actions — copy-ready for Slack/Teams

### Partners Tab *(new in v0.3.0)*
- Lists **Business Partners** aligned to your accounts (row-scoped by role)
- Each card shows: partner tier (★ Gold / ◆ Silver), **IBM Partner Liaison** name + type, accounts covered, products sold, and PO contact
- **Historical IFC data** — sales by year, product, and account with running total
- **Partner-linked opportunities** — any open deals at your accounts sourced through this partner
- Click any account name to focus it on the graph canvas

### Trust Tab
- **Overall trust score** — colour-coded % (green ≥80%, amber ≥50%, red <50%)
- **Per-source freshness bars** — each source system with total nodes, stale count, and freshness %
- **Provenance explanation** — W3C PROV-DM metadata note visible to leadership

### Human Validation (Write-Back) *(new in v0.3.0)*
Every selected node shows a **Human Validation** panel in the right sidebar:
- **✓ Confirm** — logs confirmation, simulates confidence +0.05, resets TTL. Closes the loop with the pruning agent — a recently confirmed node won't be marked stale
- **✎ Correct** — opens a correction modal with field / current value / corrected value / evidence fields. Submissions are:
  1. Logged to the session write-back ledger
  2. **Automatically create a `KnowledgeAsset` node** stamped with `source: human_writeback`, author, date, and evidence text
  3. The graph rebuilds live to include the new KnowledgeAsset
- History log under each node shows all confirmations and corrections with timestamps and confidence delta
- **Why this matters for decentralization**: data no longer flows only in from source systems — sellers validate and correct facts, raising confidence and resetting TTL, which is exactly what makes a decentralized graph graph trustworthy

### Conflict Detection *(new in v0.3.0)*
- Seeded conflicts between Salesforce CRM, w3 Bluepages, and Passport Advantage on the same node
- **⚠ CONFLICT** badge appears on affected nodes in the detail panel
- Conflict panel shows both sources with confidence % and last-verified date, then the **resolved value** and resolution method (confidence-weighted merge or recency preference)
- Turning provenance metadata from decoration into a working governance feature — scores well on responsible-AI criteria

### Explainability Trail *(new in v0.3.0)*
Every node detail panel includes a collapsible **▸ Explainability Trail**:
- Source system, confidence %, last verified date, TTL status
- Human confirmation count (live-updated by write-back)
- Graph edges used to derive the answer
- W3C PROV-DM attribution tag
- *"Here is the answer and here is exactly why I believe it."*

### Role / Entitlement System *(new in v0.3.0)*
- **"View As" pill** in the right sidebar header — switch between 7 personas without reloading
- **Row-level scoping**: Sellers see only their book; Managers see their org; Admin sees everything
- Switching persona reloads Graph, Modernize, Partners, and Insights panels automatically
- Available personas: Marcus Webb (CE), James Kowalski (CE), Monique Tureaud (TSL), David Reyes (FLM), Priya Nambiar (SLM), Derek Callahan (ALT), Admin View

### Granite Query Trace
Every search shows a **Show Trace** toggle revealing:
- Detected intent + confidence bar, keywords extracted, entity types matched
- Exact **Cypher generated** (intent-specific, not just "mock mode")
- Model ID and synthesis mode

### Export / Share
- **Full Graph PNG** — 2400×1400px with header, timestamp, node counts, legend
- **Subgraph PNG** — BFS walk from selected node → top-down hierarchical layout
- **CSV** — nodes + edges with all metadata fields
- **JSON** — structured graph for programmatic import
- Live preview thumbnail; Copy to Clipboard

---

## Sample Queries

```
"What site numbers have the most spend?"
"What site number is State of Louisiana on?"
"Does Louisiana have Cognos on all its sites?"
"What products does LA-GOV-0117 not have?"
"Louisiana site products"
"Show me the seller hierarchy"
"Show ALT and TSL hierarchy"
"Who manages Marcus Webb?"
"What does First National Bancorp have installed?"
"Which sellers cover watsonx.ai?"
"Find expiring support contracts"
"What opportunities does Cascadia have?"
"Co-sell relationships"
```

---

## Seller Hierarchy Model

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

Partner Liaisons (independent of FLM chain)
├── Carlos Muniz (PL — Southeast & Mid-Atlantic)
│   ├── Presidio Inc. (Gold BP)
│   └── Perficient Digital (Silver BP)
└── Dana Whitfield (PL — West)
    └── Onix Networking Corp. (Gold BP)
```

Click any node to see their full org position in the **Org Hierarchy panel**. Click the **👥 Hierarchy** toolbar button to open the full tree without selecting a node first.

---

## Site Number Model

Large accounts like the State of Louisiana have multiple site numbers — one per agency. Each site tracks its own product coverage and spend independently:

```
State of Louisiana (Account)
├── LA-GOV-0041 — DCFS ($1.84M/yr)  → Cognos Analytics + watsonx.ai
├── LA-GOV-0089 — DOTD ($1.12M/yr)  → Cognos Analytics only
└── LA-GOV-0117 — DHH  ($670K/yr)   → Turbonomic only  ⚠ Cognos whitespace

First National Bancorp (Account)
├── FNB-CORP-0012 — HQ ($3.2M/yr)     → Turbonomic + CP4Security
└── FNB-RET-0031  — Retail ($2.6M/yr) → watsonx.ai expansion in progress
```

Clicking a SiteNumber node shows: Site ID, agency, annual spend, active products, and **Whitespace Opportunity** (products on sibling sites not yet deployed here).

---

## Modernization Data Model

Each install has corresponding `RENEWAL_META` — sourced from Passport Advantage:

| Install | Renewal Date | Type | PO Contact | Modernize To | Contract Value |
|---|---|---|---|---|---|
| Turbonomic @ FNB | 2026-04-15 | Renewal | Janet Holloway | Turbonomic 9.0 | $420K |
| watsonx.ai @ Apex | 2027-01-20 | Upgrade | Derek Tran | watsonx.ai 3.0 | $680K |
| OpenPages @ Cascadia | 2025-09-01 | Renewal | Monica Estrada | OpenPages v9 | $890K |
| Sterling OMS @ Nova Retail | 2024-11-01 | **EOS** | Chris Yamamoto | Sterling OMS v10 | $640K |
| CP4Security @ FNB | 2026-07-10 | Upgrade | Janet Holloway | QRadar SIEM on Cloud | $310K |
| Cognos @ LA DCFS | 2026-02-01 | Renewal | Renee Boudreaux | Cognos Analytics SaaS | $185K |
| Cognos @ LA DOTD | 2025-06-01 | **EOS** | Wayne Arceneaux | Cognos Analytics v12 | $110K |

---

## Business Partner Model

Partners are visible in the **Partners tab**, scoped to your book:

| Partner | Tier | IBM Liaison | Accounts | Total IFC ($) |
|---|---|---|---|---|
| Presidio Inc. | ★ Gold | Carlos Muniz | FNB, Cascadia | $1.09M |
| Perficient Digital | ◆ Silver | Carlos Muniz | State of Louisiana | $515K |
| Onix Networking Corp. | ★ Gold | Dana Whitfield | Apex Technology | $560K |

---

## Demo Scenarios

### 1. Modernization renewal action
Open the **Modernize** tab. Cards appear sorted by urgency. Click **✉ Draft Email** on the OpenPages @ Cascadia renewal (53 days out, $890K) → pre-filled email to Monica Estrada (grc@cascadia.com) with the `v8.3 → v9 SaaS` upgrade path.

### 2. Human write-back loop
Click any Account node → right sidebar shows the **Human Validation** panel. Click **✓ Confirm** → confirmation logged, confidence updated. Click **✎ Correct**, fill in `field: Primary CE`, `new value: James Kowalski`, `evidence: Customer call 2025-07-10` → a new `KnowledgeAsset` node appears in the graph.

### 3. Conflict resolution
Click **First National Bancorp** → the detail panel shows a **⚠ CONFLICT** badge. Expanding it reveals: Salesforce says `Marcus Webb` (91% confidence), w3 says `James Kowalski` (74% confidence) → resolved to `Marcus Webb` by confidence + recency.

### 4. Site number product gap
*"Does Louisiana have Cognos on all its sites?"*
```
LA-GOV-0041 (DCFS): Cognos Analytics ✓  $1.84M/yr
LA-GOV-0089 (DOTD): Cognos Analytics ✓  $1.12M/yr
LA-GOV-0117 (DHH):  Cognos Analytics ○  $670K/yr  ← Whitespace opportunity
```
Coverage: 2/3 sites (67%). Orange progress bar. Clickable site badges to focus on graph.

### 5. Business partner discovery
Switch **View As → Monique Tureaud (TSL)** → Partners tab shows Perficient Digital with 3 years of Cognos Analytics IFC data at State of Louisiana, IBM liaison Carlos Muniz, and partner-linked opportunity tags.

### 6. Manager view scoping
Switch **View As → David Reyes (FLM)** → graph filters to his org, Modernize tab shows all installs across James Kowalski, Lin Mei Zhang, and Monique Tureaud's accounts, Weekly Digest totals their combined pipeline.

### 7. Explainability trail
Click any Install node → expand **▸ Explainability Trail** → source: `Passport Advantage`, confidence: `87%`, last verified: `2025-07-01`, TTL: `90 days`, edges used: `HAS_INSTALL→First National Bancorp, RUNS_PRODUCT→IBM Turbonomic`.

---

## Pruning Agent

The pruning agent runs every 6 hours (`PRUNING_INTERVAL_HOURS`) and:

1. **Scans** all ACTIVE nodes — checks `last_verified` against each node's `ttl_days`
2. **Marks** expired nodes `STALE` — unless recently confirmed by human write-back (which resets TTL)
3. **Deletes** nodes STALE for > `stale_delete_threshold_days` (default 90)
4. **Prunes** orphaned relationships where both endpoints are DELETED
5. **Reports** a structured `PruningReport` for audit logging

Human write-back confirmations directly feed the pruning agent — a seller confirming *"yes, I still own this account"* resets TTL and raises confidence, preventing unnecessary staleness flags. This is the core loop that makes "decentralized" meaningful beyond just graph topology.

Trigger manually: `POST /pruning/run` or **▶ Run Cycle** button in the dashboard.

---

## watsonx Orchestrate Integration

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
│   │   └── insights.py          # NBA, whitespace, 360, health, trust
│   └── data/
│       ├── mock_store.py        # In-memory BFS graph (zero-dep demo mode)
│       └── seed_data.json       # Full seed data
├── orchestrate/
│   └── dkg_seller_skill.yaml    # watsonx Orchestrate skill definition (8 tools)
├── frontend/
│   └── index.html               # Self-contained canvas graph dashboard (~3,200 lines)
│                                # Tabs: Graph / Insights / Modernize / Partners / Trust
│                                # Features: modernization engine, write-back, conflict
│                                #           detection, explainability trail, role scoping,
│                                #           partner panel, email draft, weekly digest,
│                                #           org hierarchy, export, query trace
├── data/
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
| IFC partner sales data live sync | 🔐 Pending IFC API |
| watsonx.ai Granite narrative (live) | 🔑 Ready to plug in |
| Neo4j Aura (production graph) | ☁️ Ready to provision |
| watsonx Orchestrate deployment | ✅ Skill YAML ready |
| Human write-back → backend persistence | 🗓 Session-only today; DB persistence planned |
| Slack / Teams query bot | 🗓 Digest copy-ready today; bot connector planned |
| NL alert subscriptions ("tell me when…") | 🗓 Planned |
| Embedding-based semantic search (Slate) | 🔑 Ready to plug in |
| Account risk scoring (single-threading) | ✅ Logic in /insights |
| Conflict detection persistence + resolution workflow | 🗓 Session-only today |

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
