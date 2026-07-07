# IBM DKG — Decentralized Knowledge Graph for IBM Sellers

> **WatsonX Challenge Submission** — Enterprise knowledge graph mapping every IBM seller relationship, account install base, product coverage, and territory assignment. Powered by IBM Granite + Neo4j. Fully functional in demo mode with no backend dependencies.

---

## What It Does

The IBM DKG is a **living, agent-maintained knowledge graph** that answers questions like:

- *"Who manages Marcus Webb, and what accounts does his team own?"*
- *"What IBM products does First National Bancorp have installed?"*
- *"Which sellers in the Northeast are certified on watsonx.ai?"*
- *"Show me all opportunities linked to accounts with expiring support contracts."*

Every relationship is modelled as a **Knowledge Asset** with provenance metadata (source, confidence, TTL). A background **Pruning Agent** continuously validates data freshness — stale records are flagged before they mislead sellers.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          IBM DKG Platform                               │
│                                                                         │
│  ┌───────────────┐    ┌─────────────────────────────────────────────┐  │
│  │  React/D3     │    │              FastAPI Backend                 │  │
│  │  Frontend     │◄──►│  /graph  /search  /ingest  /pruning         │  │
│  │  Dashboard    │    └─────────────────────────────────────────────┘  │
│  └───────────────┘              │              │                        │
│                                 ▼              ▼                        │
│                    ┌─────────────────┐  ┌────────────┐                 │
│                    │    Neo4j 5.x    │  │  Mock Store │                 │
│                    │  (Live mode)    │  │  (Demo mode)│                 │
│                    └─────────────────┘  └────────────┘                 │
│                                 │                                       │
│    ┌────────────────────────────┼──────────────────────────────────┐   │
│    │                     3 Agents                                  │   │
│    │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐   │   │
│    │  │ Ingestion Agent │  │  Pruning Agent  │  │ Search Agent│   │   │
│    │  │ Validates+stamps│  │ Scans TTL/stale │  │ NL→Cypher   │   │   │
│    │  │ provenance      │  │ Runs every 6h   │  │ +IBM Granite│   │   │
│    │  └─────────────────┘  └─────────────────┘  └─────────────┘   │   │
│    └───────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Entity Model

| Node | Key Fields | Source |
|---|---|---|
| **Seller** | name, email, band, geo, role | Salesforce / w3 |
| **Manager** | name, email, band, territory | w3 |
| **Territory** | name, region, quota | CRM |
| **Product** | name, family, version, EOL date | Seismic |
| **Account** | name, industry, segment, revenue | Salesforce |
| **Install** | product, account, version, support_end | Passport Advantage |
| **Opportunity** | name, stage, value, close_date | Salesforce |
| **KnowledgeAsset** | title, content, tags, type | Seismic / Internal |

### Relationship Model

| Edge | Meaning |
|---|---|
| `REPORTS_TO` | Seller → Manager org hierarchy |
| `MANAGES` | Manager → Seller |
| `OWNS_TERRITORY` | Seller → Territory assignment |
| `COVERS_PRODUCT` | Seller certified on a product |
| `OWNS_ACCOUNT` | Seller is primary CE for account |
| `HAS_INSTALL` | Account runs a product (install base) |
| `RUNS_PRODUCT` | Install → Product version |
| `HAS_OPPORTUNITY` | Active deal at an account |
| `CO_SELLS` | Seller ↔ Seller co-sell motion |

---

## Quick Start

### Option A — Demo Mode (zero dependencies)

```bash
cd "IBM DKG"

# Install Python deps
pip install -r requirements.txt

# Start API (runs with embedded seed data, no Neo4j needed)
python -m uvicorn api.main:app --reload --port 8000

# Open the frontend
open frontend/index.html
```

The app will start in **DEMO MODE** using realistic mock data for 6 sellers, 3 managers, 6 accounts, 7 products, 5 installs, and 4 opportunities across 5 territories.

### Option B — Live Mode with Neo4j + watsonx.ai

```bash
# Copy env template
cp .env.example .env
# Fill in NEO4J_PASSWORD, WATSONX_API_KEY, WATSONX_PROJECT_ID

# Start with Docker Compose (Neo4j + API)
docker compose up

# Open frontend
open frontend/index.html
```

### Option C — Docker only (neo4j community, no watsonx)

```bash
cp .env.example .env
# Set NEO4J_PASSWORD=yourpassword (leave WATSONX fields blank)
docker compose up
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/healthz` | Health check + mode indicator |
| `GET` | `/graph/full` | Full graph for visualization |
| `GET` | `/graph/nodes` | List nodes (filter by label, status) |
| `GET` | `/graph/nodes/{label}/{id}` | Single node detail |
| `POST` | `/graph/nodes/{label}` | Create/update a node |
| `GET` | `/graph/neighbors/{id}` | Neighborhood traversal |
| `POST` | `/graph/relationships` | Create/update relationship |
| `GET` | `/graph/stats` | Node/edge counts by type |
| `POST` | `/search` | Natural language enterprise search |
| `GET` | `/search/quick?q=...` | Quick keyword search |
| `POST` | `/ingest/bulk` | Bulk JSON ingest |
| `POST` | `/ingest/csv/{label}` | CSV file ingest |
| `POST` | `/pruning/run` | Trigger manual pruning cycle |
| `GET` | `/pruning/last-report` | Last pruning report |
| `GET` | `/pruning/stale-nodes` | List all stale nodes |

Interactive docs at: http://localhost:8000/docs

---

## Demo Scenarios

### 1. Seller → Manager chain
*"Who manages Marcus Webb?"*
```
Marcus Webb (Seller) → REPORTS_TO → Sandra Okafor (Manager) → REPORTS_TO → Priya Nambiar (Sr. Manager)
```

### 2. Account install base
*"What IBM products does First National Bancorp run?"*
```
First National Bancorp → HAS_INSTALL → IBM Turbonomic 8.10 (support until 2026)
First National Bancorp → HAS_INSTALL → IBM Cloud Pak for Security 1.9
```

### 3. Expiring support detection (pruning surface)
```
Nova Retail Group → HAS_INSTALL → IBM Sterling OMS 9.5 [STALE — support ended Nov 2024]
→ Opportunity: Sterling OMS v10 Upgrade (stage: Identify, $640k)
```

### 4. Co-sell relationship
```
Marcus Webb (CE, NYC) ─── CO_SELLS ──► Aisha Thornton (watsonx Specialist)
  └── Account: First National Bancorp
  └── Opportunity: FNB watsonx Expansion ($2.4M, stage: Validate)
```

---

## Pruning Agent

The pruning agent runs every 6 hours (configurable) and:

1. **Scans** all ACTIVE nodes for TTL expiry (`last_verified` > `ttl_days` ago)
2. **Marks** expired nodes as `STALE` with a timestamp
3. **Deletes** nodes that have been STALE for > `stale_delete_threshold_days` (default 90)
4. **Prunes** orphaned relationships
5. **Reports** a structured `PruningReport` for audit logging

TTL defaults:
- Sellers / Accounts / Opportunities: **30 days** (high-change data)
- Products / Installs: **180 / 365 days** (more stable)
- Managers / Territories: **90 days**

Trigger manually via `POST /pruning/run` or the dashboard button.

---

## Roadmap (pending IBM approval + API access)

| Capability | Dependency | Status |
|---|---|---|
| Salesforce CRM sync (live sellers, opps) | Salesforce API key | 🔐 Pending |
| Passport Advantage install base import | IBM PA API | 🔐 Pending |
| w3 org chart sync (manager chains) | IBM w3 API | 🔐 Pending |
| Seismic knowledge asset ingestion | Seismic API | 🔐 Pending |
| watsonx.ai narrative answers | IBM Cloud credentials | 🔑 Ready to plug in |
| Neo4j Aura (production graph) | Neo4j Aura account | ☁️ Ready to provision |
| watsonx Orchestrate agent integration | wxO instance | 🔐 Pending |

---

## Project Structure

```
IBM DKG/
├── api/
│   ├── main.py                 # FastAPI app, lifespan, routing
│   ├── config.py               # Environment-based settings
│   ├── agents/
│   │   ├── ingestion_agent.py  # Validates + writes entities to graph
│   │   ├── pruning_agent.py    # TTL-based staleness detection + cleanup
│   │   └── search_agent.py     # NL→Cypher + watsonx synthesis
│   ├── graph/
│   │   ├── neo4j_client.py     # Async Neo4j connection + Cypher helpers
│   │   └── schemas.py          # Pydantic models for all entities
│   ├── routers/
│   │   ├── graph.py            # CRUD endpoints
│   │   ├── search.py           # Enterprise search endpoint
│   │   ├── ingest.py           # Bulk + CSV ingest
│   │   └── pruning.py          # Pruning agent control
│   └── data/
│       ├── mock_store.py       # In-memory graph for demo mode
│       └── seed_data.json      # Realistic IBM demo data
├── frontend/
│   └── index.html              # Force-directed graph dashboard (D3.js)
├── data/                       # Persistent data directory
├── docker-compose.yml          # Neo4j + API
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```
