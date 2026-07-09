# IBM KG — IBM Knowledge Graph for IBM Sellers

> **v0.5.0** — Enterprise knowledge graph mapping every IBM seller relationship, account install base, product coverage, territory assignment, site-number hierarchy, business partner network, and modernization pipeline. Powered by IBM Granite + Neo4j. Fully operational in demo mode with zero backend dependencies.

---

## What It Does

The IBM Knowledge Graph is a **living, agent-maintained knowledge graph** that turns raw CRM, Passport Advantage, w3, and IFC data into proactive seller intelligence. It answers questions sellers and leaders ask every day:

**Sellers**
- *"What site numbers have the most spend?"* → ranked spend table with visual arc rings and bar fill
- *"What site number is the State of Louisiana on?"* → account-to-site-number mapping (6 Louisiana sites)
- *"What products does site LA-GOV-0041 have?"* → site-product matrix with ✓ deployed / ○ whitespace
- *"Does Louisiana have Cognos on all its sites?"* → per-site coverage report with clickable gap badges
- *"What products does LA-GOV-0117 not have?"* → whitespace opportunity by site
- *"What site numbers does FNB have?"* → lists all 4 First National Bancorp site numbers
- *"Which accounts in my accounts have a renewal coming up — and what should I modernize them to?"*
- *"Draft me a Why-Modernize email to the PO contact for the Cascadia OpenPages renewal."*
- *"What business partners are selling into my accounts, and who is the IBM partner liaison?"*

**Managers & Leadership**
- *"Show me every account that has IBM installs but no open opportunity."* (Whitespace analysis)
- *"Show me the seller hierarchy"* / *"Show ALT and TSL hierarchy"* → full-screen SVG hierarchy flow: SLM → FLM → ALT → TSL → Brand Seller, each card shows role badge and associated site IDs
- *"Give me a weekly digest of my whole book — EOS, renewals, and pipeline."*
- *"Can I trust this data? What is the freshness score by source system?"*

**Any User**
- *"Who manages Marcus Webb?"* → full org chart from SLM → FLM → ALT → TSL → Brand Seller
- *"Is this account record still accurate?"* → confirm or correct any node with human write-back, automatically logged as a provenance-stamped KnowledgeAsset

Every relationship is a **Knowledge Asset** with W3C PROV-DM provenance metadata (source system, confidence score, TTL, `last_verified`). A background **Pruning Agent** validates data freshness — stale records are flagged before they mislead anyone. Human confirmations and corrections close the loop.

---

## What's New in v0.5.0

| Area | Change |
|---|---|
| **Rebrand** | Project renamed from IBM DKG → **IBM KG (IBM Knowledge Graph)** — accurate terminology |
| **Drag-to-reposition** | Every node and hub is draggable — grab any node, edges follow live; hub drag co-moves the entire cluster |
| **Layout reset** | "Layout" toolbar button clears all drag positions and restores the default arrangement |
| **Expanded site data** | 12 site numbers total: Louisiana (6 sites), First National Bancorp (4 sites), Meridian Health (2 sites) |
| **Hierarchy swimlanes** | Hierarchy flow overlay now renders color-coded role swimlanes: SLM / FLM / ALT+TSL / Sellers |
| **Richer site queries** | Direct site-ID lookup (`"What does LA-GOV-0041 have?"`), account-sites list view, broader account recognition |
| **Personal hub rename** | "My Book" → **"My Accounts"** |
| **Broader intent routing** | extractAccountFromQuery covers 7 accounts; extractProductFromQuery covers 8 products |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    IBM KG — IBM Knowledge Graph                              │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │       Zero-dependency Frontend (HTML/SVG) — v0.5.0                   │    │
│  │                                                                      │    │
│  │   ┌─────────────────────┐   ┌─────────────────────────────────────┐  │    │
│  │   │  Enterprise Graph   │   │        Personal Graph               │  │    │
│  │   │  6 hub clusters     │───│  6 personal hubs (My Accounts, NBA, │  │    │
│  │   │  (People, Accounts, │   │   Renewals, Co-sell, Quota, Sites)  │  │    │
│  │   │  Products, Pipeline,│   └─────────────────────────────────────┘  │    │
│  │   │  Partners, Knowledge│                                            │    │
│  │   └─────────────────────┘                                            │    │
│  │                                                                      │    │
│  │  Tabs: Graph │ Insights │ Modernize │ Partners │ Trust               │    │
│  │  Hierarchy flow overlay │ Role/Entitlement pill │ Write-back         │    │
│  │  Conflict detection │ Explainability trail │ Export │ Granite trace  │    │
│  │  Drag engine: child nodes + hub clusters (co-move with dependents)   │    │
│  └─────────────────────────────┬────────────────────────────────────────┘    │
│                                 │ REST / Fetch (graceful fallback to mock)   │
│  ┌──────────────────────────────▼────────────────────────────────────────┐   │
│  │                      FastAPI Backend (v0.2.0)                         │   │
│  │  /graph  /search  /ingest  /pruning  /insights                        │   │
│  │  + watsonx Orchestrate skill (orchestrate/kg_seller_skill.yaml)       │   │
│  └───────────────────┬──────────────────────────┬────────────────────────┘   │
│                      │                          │                            │
│            ┌─────────▼────────┐    ┌────────────▼─────────┐                  │ 
│            │   Neo4j 5.x      │    │   Mock Store         │                  │
│            │  (Live mode)     │    │  (Demo mode — zero   │                  │
│            │  Cypher queries  │    │   credentials needed)│                  │
│            └──────────────────┘    └──────────────────────┘                  │
│                                                                              │
│  ┌──────────────────────────── 3 Agents ────────────────────────────────┐    │
│  │  Ingestion Agent       Pruning Agent         Search Agent            │    │
│  │  Validates + stamps    TTL / stale scan       NL→Cypher + trace      │    │
│  │  W3C PROV-DM           Runs every 6h         IBM Granite synthesis   │    │
│  │  provenance metadata   PruningReport log      Confidence scoring     │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Why "Knowledge Graph"?

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

The app starts in **DEMO MODE** with realistic seed data: 9 sellers (including 2 Partner Liaisons), 4 managers (SLM/FLM/ALT + TSL chain), 8 accounts, 8 products, 10 installs, **12 site numbers** (Louisiana ×6, FNB ×4, Meridian ×2), 3 business partners, and 6 opportunities across 6 territories.

### Option B — Live Mode (Neo4j + watsonx.ai)

```bash
cp .env.example .env
# Fill in: NEO4J_PASSWORD, WATSONX_API_KEY, WATSONX_PROJECT_ID

docker compose up

open frontend/index.html
```

In live mode the search agent runs actual Cypher queries against Neo4j and uses IBM Granite for narrative synthesis. The frontend automatically switches the badge from `DEMO MODE` to `LIVE`.

### Option C — watsonx Orchestrate Integration

Import the KG as a callable skill inside any Orchestrate agent flow:

```bash
export KG_API_URL=http://your-kg-host:8000
orchestrate skills import -f orchestrate/kg_seller_skill.yaml
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

## Frontend Features (v0.5.0)

The frontend is a single self-contained HTML file — no npm, no build step, no external assets.

### SVG Dual-Graph

The graph canvas is a **light-themed SVG dual-graph**:

- **Light theme** — `#f0f4ff` background, white panels, IBM blue accent palette, subtle dotted grid
- **Enterprise Graph (left half)** — 6 hub nodes orbit a central IBM KG node:
  - **People** → Sellers + Managers (blue/purple child nodes)
  - **Accounts** → Account nodes (cyan)
  - **Products** → Product nodes (orange)
  - **Pipeline** → Opportunity nodes (yellow) — hub click switches to Insights tab
  - **Partners** → BusinessPartner nodes (purple) — hub click switches to Partners tab
  - **Knowledge** → SiteNumber, Territory, Install, KnowledgeAsset nodes
- **Personal Graph (right half)** — 6 personal hubs scoped to the current "View As" persona:
  - My Accounts, Next Best Actions, Renewals & EOS, Co-sell Network, Goals/Quota, Site Numbers
- **Hub click filtering** — clicking any enterprise hub filters child nodes to that type and switches the matching sidebar tab; clicking again resets to all types
- **SiteNumber spend rings** — blue arc drawn proportional to site's annual spend vs. max spend across all sites
- **Edge highlighting** — clicking a node dims unrelated edges, highlights connected ones
- **Source rail** — bottom bar shows Salesforce · Passport Advantage · w3 Bluepages · Seismic · IFC logos + KG Protect governance badge

### Drag-to-Reposition (new in v0.5.0)

Every node and hub is draggable:

- **Child nodes** — grab any Seller, Account, Product, Site, etc. and drag freely; hub connector + cross-node edges follow live
- **Hub nodes** — drag People, Accounts, Products (etc.) and the **entire cluster moves with it** — all child nodes co-move, preserving their relative offsets
- Drag positions **persist** through filter toggles and graph rebuilds
- A move of ≤3px still fires as a normal click; >3px commits the drag and suppresses click
- **Layout button** in the toolbar resets all hub and node positions back to the default arrangement

### Hierarchy Flow Overlay

Click **Hierarchy** in the toolbar to open a full-screen, scrollable SVG org chart:

- **4 color-coded swimlane rows**: SLM (purple) / FLM (blue) / ALT+TSL (teal) / Sellers (blue)
- Card-per-person with colored left accent bar, role badge, name, and direct-report count / site IDs
- **SLM → FLMs → ALT → TSL → Brand Sellers** full chain rendered
- **ALT** (Area Leader/Territory) and **TSL** (Territory Sales Leader) roles rendered with distinct teal/blue badges
- Each seller card shows their associated site IDs or account names inline
- Click any card to close the overlay and focus that node in the main graph + right sidebar

### Site Number Intelligence

Three dedicated query modes triggered by natural language search:

**Site Spend Table** (`"What site numbers have the most spend?"`)
- Ranked table with medal icons (①②③), per-account spend summary header, spend bar fill, % of total, active product tags
- 12 site numbers across 3 accounts

**Account-Sites List** (`"What site number is Louisiana on?"`, `"What site numbers does FNB have?"`)
- Lists all sites per account with products and spend; click any row to focus that site node
- Direct site-ID lookup (`"What does LA-GOV-0041 have?"`) shows single-site detail card with sibling sites

**Site-Product Matrix** (`"Show site-product matrix for Louisiana"`)
- Cross-tab: sites as rows, products as columns — ✓ (green) = deployed, ○ (grey) = whitespace

**Product Coverage Report** (`"Does Louisiana have Cognos on all sites?"`)
- Per-account, per-product coverage with progress bar and % badge; clickable deployed/not-deployed site badges

### Toolbar

| Button | Action |
|---|---|
| ⊡ Fit / Reset | Rebuilds the SVG graph at current canvas size |
| ↺ Rebuild | Resets all filters and rebuilds the full graph |
| ↺ Layout | Clears all drag positions, restores default layout |
| Hierarchy | Opens the full-screen SVG org hierarchy flow with swimlanes |
| Export | Opens the export modal (PNG / CSV / JSON) |

### Insights Tab
- **4 summary tiles** — Expired Support, Expiring 90d, Whitespace Gaps, NBA Actions
- **Support alert cards** — severity-badged (CRITICAL / HIGH / MEDIUM), click → focus account
- **Whitespace gap cards** — accounts with IBM installs but zero open pipeline

### Modernize Tab
- **Scoped to your book** — shows only installs for accounts you own (switches automatically with View As role)
- **3 urgency tiers**: EOS/Expired (red), Renewal < 90d (yellow), Upgrade (cyan) — sorted by urgency
- Every card shows: product, account, renewal date, **PO contact name + email from Passport Advantage**, contract value, and exact **modernization path**
- **✉ Draft Email button** → opens pre-filled Why-Modernize email modal (Granite template)
- **✉ Weekly Digest tile** → formatted book-of-business digest — copy-ready for Slack/Teams

### Partners Tab
- Lists Business Partners aligned to your accounts (row-scoped by role)
- Partner tier (★ Gold / ◆ Silver), IBM Partner Liaison, accounts covered, products sold, PO contact
- **Historical IFC data** — sales by year, product, and account with running total
- Partner-linked opportunities shown inline

### Trust Tab
- **Overall trust score** — colour-coded % (green ≥80%, amber ≥50%, red <50%)
- **Per-source freshness bars** — each source system with total nodes, stale count, and freshness %

### Human Validation (Write-Back)
Every selected node shows a **Human Validation** panel in the right sidebar:
- **✓ Confirm** — logs confirmation, simulates confidence +0.05, resets TTL
- **✎ Correct** — opens a correction modal; submissions automatically create a `KnowledgeAsset` node stamped with `source: human_writeback`, author, date, and evidence text
- History log under each node shows all confirmations and corrections with timestamps and confidence delta

### Conflict Detection
- Seeded conflicts between Salesforce CRM, w3 Bluepages, and Passport Advantage
- **⚠ CONFLICT** badge appears on affected nodes in the detail panel
- Conflict panel shows both sources with confidence % and last-verified date, then the resolved value and resolution method

### Explainability Trail
Every node detail panel includes a collapsible **▸ Explainability Trail**:
- Source system, confidence %, last verified date, TTL status, human confirmation count
- Graph edges used to derive the answer, W3C PROV-DM attribution tag

### Role / Entitlement System
- **"View As" pill** in the right sidebar header — switch between 7 personas without reloading
- **Row-level scoping**: Sellers see only their book; Managers see their org; Admin sees everything
- Switching persona reloads Graph, Modernize, Partners, and Insights panels automatically
- Available personas: Marcus Webb (CE), James Kowalski (CE), Monique Tureaud (TSL), David Reyes (FLM), Priya Nambiar (SLM), Derek Callahan (ALT), Admin View

### Granite Query Trace
Every search shows a **Show Trace** toggle revealing:
- Detected intent + confidence bar, keywords extracted, entity types matched
- Exact **Cypher generated** (intent-specific)
- Model ID and synthesis mode

### Export / Share
- **Full Graph PNG** — 2400×1400px with header, timestamp, node counts
- **CSV** — nodes + edges with all metadata fields
- **JSON** — structured graph for programmatic import
- Live preview thumbnail; Copy to Clipboard

---

## Sample Queries

```
"What site numbers have the most spend?"
"What site number is State of Louisiana on?"
"What products does site LA-GOV-0041 have?"
"Does Louisiana have Cognos on all its sites?"
"What products does LA-GOV-0117 not have?"
"Show site-product matrix for Louisiana"
"What site numbers does FNB have?"
"Show me the seller hierarchy"
"Show ALT and TSL hierarchy"
"Who manages Marcus Webb?"
"Who is Monique Tureaud's manager chain?"
"What does First National Bancorp have installed?"
"Which sellers cover watsonx.ai?"
"Find expiring support contracts"
"What opportunities does Louisiana have?"
"Co-sell relationships"
```

---

## Seller Hierarchy Model

```
Priya Nambiar (SLM — Band 11)
├── Sandra Okafor (FLM — Band 10, Northeast)
│   ├── Marcus Webb (CE — NYC Metro)         sites: FNB-CORP-0012, FNB-RET-0031, FNB-TRS-0047, FNB-RIS-0063
│   └── Aisha Thornton (SSR — New England, watsonx)
└── David Reyes (FLM — Band 10, Southeast)
    ├── James Kowalski (CE — Atlanta)
    ├── Lin Mei Zhang (SSR — Miami)
    └── Derek Callahan (ALT — Band 9, Public Sector South)
        └── Monique Tureaud (TSL — Baton Rouge, Cognos/LA Public Sector)
                                               sites: LA-GOV-0041, LA-GOV-0089, LA-GOV-0117,
                                                      LA-GOV-0156, LA-GOV-0203, LA-GOV-0228

Partner Liaisons (independent of FLM chain)
├── Carlos Muniz (PL — Southeast & Mid-Atlantic)
│   ├── Presidio Inc. (Gold BP)
│   └── Perficient Digital (Silver BP)
└── Dana Whitfield (PL — West)
    └── Onix Networking Corp. (Gold BP)
```

- **ALT** = Area Leader/Territory — owns a geographic public sector segment, reports through FLM chain
- **TSL** = Territory Sales Leader — product/segment specialist reporting to ALT

Click any node to see their full org position in the **Org Hierarchy panel** in the right sidebar. Click the **Hierarchy** toolbar button to open the full-screen SVG hierarchy flow with color-coded swimlanes.

---

## Site Number Model

Large accounts like the State of Louisiana have multiple site numbers — one per agency. Each site tracks its own product coverage and spend independently:

```
State of Louisiana (Account) — 6 sites
├── LA-GOV-0041 — DCFS ($1.84M/yr)  → Cognos Analytics ✓ + watsonx.ai ✓
├── LA-GOV-0089 — DOTD ($1.12M/yr)  → Cognos Analytics ✓ (no watsonx)
├── LA-GOV-0117 — DHH  ($670K/yr)   → Turbonomic ✓        ⚠ Cognos whitespace
├── LA-GOV-0156 — OIT  ($980K/yr)   → Turbonomic ✓        ⚠ analytics whitespace
├── LA-GOV-0203 — LDH  ($420K/yr)   → ○ No products yet   ← watsonx.ai pilot opp
└── LA-GOV-0228 — LDWF ($290K/yr)   → ○ No products yet   ← Cognos opportunity

First National Bancorp (Account) — 4 sites
├── FNB-CORP-0012 — HQ       ($3.2M/yr)  → Turbonomic ✓ + CP4Security ✓
├── FNB-RET-0031  — Retail   ($2.6M/yr)  → watsonx.ai expansion in progress
├── FNB-TRS-0047  — Treasury ($1.95M/yr) → Cognos Analytics ✓
└── FNB-RIS-0063  — Risk     ($1.38M/yr) → ○ No products yet ← OpenPages whitespace

Meridian Health Systems (Account) — 2 sites
├── MHS-MAIN-0001 — Main     ($1.1M/yr)  → Turbonomic ✓
└── MHS-EAST-0022 — East Div ($740K/yr)  → watsonx.ai clinical pilot
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

### 1. Site number product gap
Search *"Does Louisiana have Cognos on all its sites?"*
```
LA-GOV-0041 (DCFS): Cognos Analytics ✓  $1.84M/yr
LA-GOV-0089 (DOTD): Cognos Analytics ✓  $1.12M/yr
LA-GOV-0117 (DHH):  Cognos Analytics ○  $670K/yr  ← Whitespace opportunity
LA-GOV-0156 (OIT):  Cognos Analytics ○  $980K/yr  ← Whitespace opportunity
LA-GOV-0203 (LDH):  Cognos Analytics ○  $420K/yr  ← No footprint yet
LA-GOV-0228 (LDWF): Cognos Analytics ○  $290K/yr  ← No footprint yet
```
Coverage: 2/6 sites (33%). Red progress bar. Clickable site badges to focus on graph.

### 2. Top spend sites
Search *"What site numbers have the most spend?"* → ranked table with account summary:
```
① FNB-CORP-0012 (HQ)      $3.20M  Turbonomic · CP4Security
② FNB-RET-0031  (Retail)  $2.60M  watsonx.ai
③ LA-GOV-0041   (DCFS)    $1.84M  Cognos Analytics · watsonx.ai
...  12 sites total · $18.42M combined
```

### 3. Hierarchy flow with swimlanes
Click **Hierarchy** toolbar button → full-screen SVG with 4 swimlane rows:
- **SLM row** (purple): Priya Nambiar
- **FLM row** (blue): Sandra Okafor, David Reyes
- **ALT/TSL row** (teal): Derek Callahan (ALT) → Monique Tureaud (TSL)
- **Sellers row** (blue): all CEs, SSRs, PLs with site IDs and account names

### 4. Drag and reposition
Grab the **People** hub node and drag it — all Seller/Manager child nodes co-move as a cluster. Then grab individual sellers to spread them out. Hit **Layout** in the toolbar to reset.

### 5. Account site lookup
Search *"What site numbers does FNB have?"* → shows all 4 FNB sites with products and spend per site, clickable to focus each node.

### 6. Modernization renewal action
Open the **Modernize** tab. Cards appear sorted by urgency. Click **✉ Draft Email** on the OpenPages @ Cascadia renewal (53 days out, $890K) → pre-filled email to Monica Estrada (grc@cascadia.com) with the `v8.3 → v9 SaaS` upgrade path.

### 7. Human write-back loop
Click any Account node → right sidebar shows the **Human Validation** panel. Click **✓ Confirm** → confirmation logged, confidence updated. Click **✎ Correct**, fill in `field: Primary CE`, `new value: James Kowalski`, `evidence: Customer call 2025-07-10` → a new `KnowledgeAsset` node appears in the graph.

### 8. Business partner discovery
Switch **View As → Monique Tureaud (TSL)** → Partners tab shows Perficient Digital with 3 years of Cognos Analytics IFC data at State of Louisiana, IBM liaison Carlos Muniz, and partner-linked opportunity tags.

### 9. Manager view scoping
Switch **View As → David Reyes (FLM)** → graph filters to his org, Modernize tab shows all installs across James Kowalski, Lin Mei Zhang, and Monique Tureaud's accounts, Weekly Digest totals their combined pipeline.

### 10. Explainability trail
Click any Install node → expand **▸ Explainability Trail** → source: `Passport Advantage`, confidence: `87%`, last verified: `2025-07-01`, TTL: `90 days`, edges used: `HAS_INSTALL→First National Bancorp, RUNS_PRODUCT→IBM Turbonomic`.

---

## Pruning Agent

The pruning agent runs every 6 hours (`PRUNING_INTERVAL_HOURS`) and:

1. **Scans** all ACTIVE nodes — checks `last_verified` against each node's `ttl_days`
2. **Marks** expired nodes `STALE` — unless recently confirmed by human write-back (which resets TTL)
3. **Deletes** nodes STALE for > `stale_delete_threshold_days` (default 90)
4. **Prunes** orphaned relationships where both endpoints are DELETED
5. **Reports** a structured `PruningReport` for audit logging

Trigger manually: `POST /pruning/run` or **▶ Run Cycle** button in the dashboard.

---

## watsonx Orchestrate Integration

```bash
orchestrate skills import -f orchestrate/kg_seller_skill.yaml
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
│   └── kg_seller_skill.yaml     # watsonx Orchestrate skill definition (8 tools)
├── frontend/
│   └── index.html               # Self-contained SVG graph dashboard (~2,400 lines)
│                                # Tabs: Graph / Insights / Modernize / Partners / Trust
│                                # Features: dual-graph SVG, hub clusters, hierarchy flow,
│                                #           drag engine (hubs + children), swimlane hierarchy,
│                                #           site spend/matrix/coverage (12 sites),
│                                #           modernization engine, write-back, conflict detection,
│                                #           explainability trail, role scoping, partner panel,
│                                #           email draft, weekly digest, org hierarchy, export
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
