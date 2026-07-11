# LowTrans

**Agent Platform for AML and KYT for Crypto** — with RAG-powered triage as the hero feature.

A hackathon-ready lite version of Sardine-style agentic compliance, built for crypto fiat on/off-ramps, KYT checks, and Travel Rule alerts.

> ⚠️ Hackathon prototype — not production compliance advice.

## Features

- **4-node investigation graph** — Orchestrator → Entity Identity → Financial Crime Investigator → Arbiter
- **Agent loop** — Bedrock tool-calling with deterministic fallback
- **Submit transaction** — Stakeholder intake → explainable ML score → full investigation
- **RAG-Augmented Triage** — Similar resolved cases justify CLEAR / REVIEW / ESCALATE
- **Hard policy gates** — OFAC / Travel Rule never overridden by LLM
- **Connection Graph** — Visual wallet/transaction link tracing (mock data, illustrative only)
- **Sardine-Style UI** — Customer Intelligence view with risk gauge, module sidebar, case tabs
- **Risk Insights** — VASP portfolio dashboard with activities feed
- **Demo Mode** — One-click guided demo: reset → triage low-risk → navigate to high-risk case
- **Analyst Override** — Approve/override agent decisions with audit-logged reasons
- **Supervisor Approval** — ESCALATE requires supervisor approval (mock RBAC via role selector)
- **Escalation Summaries** — Pre-drafted SAR-ready narratives for high-risk cases
- **Audit Trail** — Immutable log of agent decisions with RAG case citations
- **Policy Learning** — AI-suggested policy refinements from resolved case patterns

## Quick Start

### 1. Backend (Python FastAPI)

```bash
cd apps/api
pip install -r requirements.txt
cp .env.example .env   # edit Bedrock key if needed
uvicorn main:app --reload --port 8000
```

**Database (default SQLite, no Docker):** leave `DATABASE_URL` empty. On startup `init_db()` creates `data/lowtrans.db` and seeds transactions when the table is empty (`scripts/seed_db.py`). Set `USE_DB=false` only to force JSON-file fallback. Optional Postgres: set `DATABASE_URL=postgresql://...` (falls back to SQLite if unreachable).

```bash
# Re-seed manually (prints alert / case / transaction counts)
cd apps/api && python scripts/seed_db.py
```

API docs: http://localhost:8000/docs

### 2. Frontend (Next.js)

```bash
cd apps/web
npm install
npm run dev
```

Open: http://localhost:3000

## Project Structure

```
lowtrans/
├── DEMO.md                 # 3-minute demo script
├── data/
│   ├── alerts.json         # 12 pending KYT alerts
│   ├── resolved_cases.json # 15 cases for RAG memory
│   ├── graphs/             # Connection graph mock data per alert
│   ├── policy.md           # AML/KYT triage policy
│   └── audit_log.jsonl     # Generated at runtime
├── apps/
│   ├── api/                # FastAPI + RAG + triage agent
│   └── web/                # Next.js Sardine-style UI
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | API health + RAG index status |
| GET | `/api/alerts` | List all alerts |
| GET | `/api/alerts/{id}` | Get alert detail |
| GET | `/api/alerts/{id}/graph` | Connection graph for alert |
| GET | `/api/cases/{id}` | Resolved case detail (RAG memory) |
| POST | `/api/alerts/{id}/triage` | Run RAG triage on one alert |
| POST | `/api/alerts/{id}/override` | Analyst override with reason |
| POST | `/api/alerts/{id}/approve-escalation` | Supervisor approval for ESCALATE |
| POST | `/api/alerts/triage-all` | Batch triage all pending |
| POST | `/api/demo/reset` | Reset alerts for demo replay |
| GET | `/api/alerts/{id}/similar` | RAG similar cases |
| GET | `/api/insights` | VASP portfolio risk insights |
| GET | `/api/insights/activities` | Agent activity feed |
| GET | `/api/audit` | Audit trail |
| GET | `/api/policy/suggestions` | RAG policy refinement |
| GET | `/api/stats` | Dashboard metrics |

## RAG Architecture

1. **Index** — 15 resolved cases embedded as TF-IDF documents
2. **Retrieve** — Cosine similarity finds top-3 matches for each new alert
3. **Augment** — Triage agent cites similar cases in rationale
4. **Learn** — Policy suggestions derived from clear vs escalate clusters

## Agents

| Agent | Role |
|-------|------|
| Transaction Monitoring Agent | Core KYT alert triage |
| Sanctions Screening Agent | OFAC/PEP screening |
| Graph Analyst Agent | Mixer exposure, wallet graphs |
| SAR Filing Agent | Escalation narratives |
| Doc KYC Agent | Onboarding document review |
| Rule Assistant Agent | Policy → monitoring rules |
| Data Analyst Agent | Transaction summaries |
| OSINT Search Agent | Entity research |
| Business Due Diligence Agent | KYB verification |
| PEP Screening Agent | PEP false positive clearing |

## Demo

See [DEMO.md](./DEMO.md) for the 3-minute hackathon presentation script.
