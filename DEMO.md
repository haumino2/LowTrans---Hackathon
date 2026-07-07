# LowTrans — 3-Minute Hackathon Demo Script

## Setup
1. Terminal 1: `cd apps/api && pip install -r requirements.txt && uvicorn main:app --reload --port 8000`
2. Terminal 2: `cd apps/web && npm install && npm run dev`
3. Open http://localhost:3000
4. Confirm **API Connected** badge in header (green) — not "Disconnected"

## Quick Demo (Demo Mode button)
1. On **Alert Queue**, click **Demo Mode**
2. Watch progress: resets alerts → triages ALT-3003 (Elena) → navigates to ALT-3002 (Brooke)
3. On Brooke's case, click **Run Agent Workflow**
4. Switch to **Connections Graph** tab — see mixer exposure graph with disclaimer banner
5. Click a **CASE-xxx** chip in RAG results to open resolved case modal
6. Switch role to **Supervisor** and click **Approve Escalation** (ESCALATE requires approval)

## Demo Flow (3 minutes)

### 1. Alert Queue (30 sec)
- Show **12 pending KYT alerts** for crypto on/off-ramps
- Point out stats and **API Connected** health banner
- Optional: click **Demo Mode** for guided flow
- Or click **Run RAG Agent on All Pending** — watch auto-clear rate hit **~75-90%**

### 2. Low-Risk Auto-Clear (45 sec)
- Click **ALT-3003** (Elena Vasquez — low KYT, clean deposit)
- Click **Run Agent Workflow** — watch timeline animate step-by-step:
  - RAG Memory → Transaction Monitoring → Doc KYC → Decision → Audit
- Show **11 workflow steps** with skipped agents (Sanctions, Graph, SAR)
- Final: **CLEAR** with RAG citations — click CASE chip to view resolved case

### 3. High-Risk Escalation (60 sec)
- Click **ALT-3002** (Brooke Ramirez — mixer + missing Travel Rule)
- Run **Agent Workflow** — watch:
  - RAG Memory retrieves CASE-1205
  - Graph Analyst flags mixer exposure (nodes highlighted on graph tab)
  - SAR Filing Agent drafts escalation summary
- Open **Connections Graph** tab — illustrative wallet tracing
- Use **Analyst Override** to set **REVIEW** with reason
- Switch role to **Supervisor** and **Approve Escalation** (sets final status to ESCALATE)
- Click **Replay Workflow** to re-demo the animation

### 4. Risk Insights (30 sec)
- Navigate to **Risk Insights** in sidebar
- Show VASP portfolio cards (Summit Crypto, Nordic Digital, etc.)
- Review **Activities** feed with agent-generated insights

### 5. RAG & Policy Learning (30 sec)
- Navigate to **Policy & RAG** tab
- Show active triage policy
- Show **RAG Policy Suggestion** derived from resolved case patterns

### 6. Audit Trail (15 sec)
- Navigate to **Audit Trail**
- Show immutable log: timestamp, decision, agents, RAG case IDs

## Connection Graphs Available
- **ALT-3002** — Brooke Ramirez (mixer + mule network)
- **ALT-3005** — Ahmed Al-Rashid (sanctions/PEP links)
- **ALT-3010** — Nina Kowalski (privacy pools + structuring)

## Key Talking Points
- "LowTrans auto-clears 90% of false-positive KYT alerts using RAG memory from past cases"
- "Every decision is explainable — signals, policy, and similar case citations"
- "Connection graphs trace wallet links — illustrative mock data, not certified on-chain"
- "High-risk cases get pre-drafted escalation summaries for SAR workflow"
- "Continuous improvement: RAG suggests policy refinements from resolved patterns"

## Reset Demo
```bash
python scripts/reset_demo.py
# or POST http://localhost:8000/api/demo/reset
```
