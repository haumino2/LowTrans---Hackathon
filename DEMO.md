# LowTrans — Demo Script (4-node AML Agent Platform)

## Setup
1. Terminal 1: `cd apps/api && pip install -r requirements.txt && uvicorn main:app --reload --port 8000`
2. Terminal 2: `cd apps/web && npm install && npm run dev`
3. Open http://localhost:3000
4. Confirm **API Connected** badge in header (green)

## Trust path — Submit a new transaction (stakeholder)
1. Open **Submit Tx** in the nav (or `/submit`)
2. Enter amount / counterparty; optionally toggle mixer or OFAC hit
3. Click **Validate with agents**
4. Show **ML feature attribution** + Arbiter decision (CLEAR / REVIEW / ESCALATE)
5. Open case timeline — 4 nodes: Orchestrator → Entity Identity → Financial Crime Investigator → Arbiter

## Quick Demo (Demo Mode button)
1. On **Alert Queue**, click **Demo Mode**
2. Watch progress: resets alerts → triages ALT-3003 (Elena) → navigates to ALT-3002 (Brooke)
3. On Brooke's case, click **Run Agent Workflow**
4. Switch to **Connections Graph** tab — mixer exposure graph
5. Switch role to **Supervisor** and click **Approve Escalation**

## Demo Flow (3 minutes)

### 1. Alert Queue (30 sec)
- Show pending KYT alerts for crypto on/off-ramps
- Point out **4-node Agent Fleet** under Agents
- Optional: **Submit Tx** live, or **Demo Mode**

### 2. Low-Risk Auto-Clear (45 sec)
- Click **ALT-3003** (Elena Vasquez — low KYT, clean deposit)
- Click **Run Agent Workflow** — timeline shows Orchestrator → Identity → Investigator → Arbiter
- Final: **CLEAR** with RAG citations + ML score

### 3. High-Risk Escalation (60 sec)
- Click **ALT-3002** (Brooke Ramirez — mixer + missing Travel Rule)
- Run workflow — hard policy gates force **ESCALATE**; Arbiter drafts SAR
- Open **Connections Graph** tab
- Supervisor **Approve Escalation**

### 4. Copilot agent loop (30 sec)
- Open Copilot with an alert context
- Ask: “Validate this with ML and check sanctions”
- Show multi-skill tool trace (Bedrock tools when configured; keyword fallback otherwise)

### Stretch trust signals
- Submit Tx shows **Sklearn GB** model name + MAE + feature attribution
- Timeline runtime badge: `langgraph` when package installed (`LOWTRANS_USE_LANGGRAPH=0` to force supervisor)
- UBO / Behavioral / Fiat-Crypto bridge are full mock engines (not one-liners)
- Retrain: `cd apps/api && python scripts/train_ml_model.py`
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
