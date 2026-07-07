export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY;

const ROLE_KEY = "lowtrans_role";
export const DEFAULT_ROLE = "analyst";

export function getRole(): string {
  if (typeof window === "undefined") return DEFAULT_ROLE;
  return localStorage.getItem(ROLE_KEY) || DEFAULT_ROLE;
}

export function setRole(role: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(ROLE_KEY, role);
    window.dispatchEvent(new CustomEvent("lowtrans-role-change", { detail: role }));
  }
}

export interface Alert {
  id: string;
  customer_id: string;
  customer_name: string;
  email: string;
  partner: string;
  partner_id: string;
  session_id: string;
  status: string;
  assigned_to?: string | null;
  notes?: { timestamp: string; role: string; text: string }[];
  asset: string;
  network: string;
  amount_usd: number;
  direction: string;
  kyt_score: number;
  risk_level: string;
  risk_tags: string[];
  wallet_address: string;
  counterparty: string;
  travel_rule_status: string;
  account_age_days: number;
  device_os: string;
  flow_type: string;
  country: string;
  state: string;
  address: string;
  zip: string;
  phone: string;
  connections: number;
  created_at: string;
  signals: Record<string, unknown>;
  rules_fired: { id: string; name: string; severity: string }[];
  sanctions_screening: { status: string; matches: number; note?: string };
  crypto_details: Record<string, unknown>;
  triage_result?: TriageResult;
  override?: { decision: string; reason: string };
}

export interface CaseSummary {
  case_id: string;
  customer_id: string;
  customer_name: string;
  partner: string;
  country: string;
  risk_level: string;
  max_kyt: number;
  status: string;
  latest_alert_at: string;
  alerts_count: number;
  assigned_to?: string | null;
  state: string;
}

export interface CasePacket extends CaseSummary {
  alerts: Alert[];
  case_notes: { timestamp: string; role: string; text: string }[];
  policy_version?: string | null;
}

export interface WorkflowStep {
  step: number;
  agent: string;
  status: "completed" | "skipped" | "running" | "pending";
  input: string;
  output: string;
  duration_ms: number;
  workspace_link?: string | null;
}

export interface StructuredCard {
  type: string;
  title: string;
  fields: { label: string; value: string }[];
}

export interface WorkflowSummary {
  total_steps: number;
  agents_run: number;
  agents_skipped: number;
  total_duration_ms: number;
}

export interface SimilarCase {
  case_id: string;
  similarity: number;
  resolution: string;
  customer_name: string;
  asset: string;
  kyt_score: number;
  analyst_notes: string;
  risk_tags: string[];
}

export interface TriageResult {
  alert_id: string;
  decision: string;
  confidence: number;
  rationale: string[];
  signals_reviewed: string[];
  similar_cases: SimilarCase[];
  agents_used: string[];
  suggested_disposition: string;
  escalation_summary: string | null;
  rag_enabled: boolean;
  policy_version: string;
  triaged_at: string;
  workflow_steps?: WorkflowStep[];
  workflow_summary?: WorkflowSummary;
}

export interface Stats {
  total_alerts: number;
  pending: number;
  cleared: number;
  escalated: number;
  review: number;
  auto_clear_rate: number;
  rag_cases: number;
  agents: string[];
}

export interface ResolvedCase {
  id: string;
  alert_id: string;
  customer_id: string;
  customer_name: string;
  asset: string;
  network: string;
  amount_usd: number;
  direction: string;
  kyt_score: number;
  risk_tags: string[];
  wallet_address: string;
  counterparty: string;
  travel_rule_status: string;
  resolution: string;
  analyst_notes: string;
  resolved_at: string;
  signals: Record<string, unknown>;
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  subtitle: string;
  risk: string;
  position: { x: number; y: number };
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  amount_usd: number | null;
}

export interface GraphData {
  alert_id: string;
  customer_name: string;
  flagged_node_ids: string[];
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface VaspInsight {
  id: string;
  name: string;
  status: "healthy" | "needs_attention";
  transactions_30d: number;
  active_users: number;
  approval_rate: number;
  pending_alerts: number;
  risk_score: number;
}

export interface InsightsData {
  vasps: VaspInsight[];
  summary: {
    total_vasps: number;
    needs_attention: number;
    portfolio_approval_rate: number;
    pending_alerts: number;
  };
}

export interface ActivityItem {
  id: string;
  type: string;
  title: string;
  description: string;
  alert_id: string | null;
  timestamp: string;
  agent: string;
}

export interface SkillAgent {
  id: string;
  name: string;
  description: string;
  skills: string[];
  version?: string;
  capabilities?: string[];
  workspace?: string;
}

export interface Skill {
  id: string;
  name: string;
  description: string;
  tools: string[];
}

export interface CopilotResponse {
  skill_id: string;
  skill_name: string;
  reply: string;
  type: string;
  sql?: string;
  alert_id?: string | null;
  session_id?: string | null;
  cases?: SimilarCase[];
  cards?: StructuredCard[];
  visualization?: VisualizationData;
  flagged_node_ids?: string[];
}

export interface VisualizationData {
  chart_type: "bar" | "table";
  columns: string[];
  rows: unknown[][];
  label_column?: string | null;
  value_column?: string | null;
  row_count: number;
  summary: string;
  question?: string;
}

export interface AnalystAskResult {
  columns: string[];
  rows: unknown[][];
  row_count: number;
  explanation: string;
  visualization: VisualizationData;
}

export interface AnalystPreview {
  sql: string;
  explanation: string;
  blocked?: boolean;
  error?: string;
}

export interface AnalystResult {
  sql: string;
  columns: string[];
  rows: unknown[][];
  row_count: number;
}

export interface HealthResponse {
  status: string;
  rag_cases_loaded: number;
  rag_backend?: string;
  db_connected?: boolean;
  bedrock?: Record<string, unknown>;
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Role": getRole(),
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  getHealth: () => fetchApi<HealthResponse>("/api/health"),
  getAlerts: () => fetchApi<Alert[]>("/api/alerts"),
  getCases: () => fetchApi<CaseSummary[]>("/api/cases"),
  getCasePacket: (id: string) => fetchApi<CasePacket>(`/api/cases/${id}`),
  setCaseState: (id: string, state: string, reason?: string) =>
    fetchApi<{ ok: boolean }>(`/api/cases/${id}/state`, {
      method: "POST",
      body: JSON.stringify({ state, reason: reason ?? null }),
    }),
  assignCase: (id: string, assignee: string) =>
    fetchApi<{ ok: boolean }>(`/api/cases/${id}/assign`, {
      method: "POST",
      body: JSON.stringify({ assignee }),
    }),
  addCaseNote: (id: string, note: string) =>
    fetchApi<{ ok: boolean }>(`/api/cases/${id}/notes`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  getRules: () => fetchApi<unknown[]>("/api/rules"),
  compileRule: (name: string, description: string, conditions: Record<string, unknown>) =>
    fetchApi<unknown>("/api/rules/compile", {
      method: "POST",
      body: JSON.stringify({ name, description, conditions }),
    }),
  getApprovals: () => fetchApi<Alert[]>("/api/approvals"),
  getAlert: (id: string) => fetchApi<Alert>(`/api/alerts/${id}`),
  triage: (id: string) => fetchApi<TriageResult>(`/api/alerts/${id}/triage`, { method: "POST" }),
  triageStream: (
    id: string,
    onEvent: (data: { event: string; step?: WorkflowStep; result?: TriageResult; message?: string }) => void
  ) =>
    new Promise<TriageResult | null>((resolve, reject) => {
      const es = new EventSource(`${API_BASE}/api/alerts/${id}/triage/stream`);
      es.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          onEvent(data);
          if (data.event === "complete" && data.result) {
            es.close();
            resolve(data.result);
          }
          if (data.event === "error") {
            es.close();
            reject(new Error(data.message || "Stream error"));
          }
        } catch (e) {
          es.close();
          reject(e);
        }
      };
      es.onerror = () => {
        es.close();
        reject(new Error("SSE connection failed"));
      };
    }),
  triageAll: () => fetchApi<{ total: number; cleared: number; auto_clear_rate: number }>("/api/alerts/triage-all", { method: "POST" }),
  getWorkflow: (id: string) =>
    fetchApi<{
      alert_id: string;
      workflow_steps: WorkflowStep[];
      workflow_summary?: WorkflowSummary;
      decision?: string;
      triaged_at?: string;
    }>(`/api/alerts/${id}/workflow`),
  getSimilar: (id: string) => fetchApi<SimilarCase[]>(`/api/alerts/${id}/similar`),
  getStats: () => fetchApi<Stats>("/api/stats"),
  getAudit: () => fetchApi<Record<string, unknown>[]>("/api/audit"),
  getPolicy: () => fetchApi<{ content: string }>("/api/policy"),
  getPolicySuggestions: () => fetchApi<Record<string, unknown>>("/api/policy/suggestions"),
  getResolvedCase: (caseId: string) => fetchApi<ResolvedCase>(`/api/cases/${caseId}`),
  getGraph: (alertId: string) => fetchApi<GraphData>(`/api/alerts/${alertId}/graph`),
  getInsights: () => fetchApi<InsightsData>("/api/insights"),
  getActivities: () => fetchApi<ActivityItem[]>("/api/insights/activities"),
  demoReset: () => fetchApi<{ ok: boolean; alerts_reset: number }>("/api/demo/reset", { method: "POST" }),
  override: (id: string, decision: string, reason: string) =>
    fetchApi<{ ok: boolean }>(`/api/alerts/${id}/override`, {
      method: "POST",
      body: JSON.stringify({ decision, reason }),
    }),
  approveEscalation: (id: string) =>
    fetchApi<{ ok: boolean }>(`/api/alerts/${id}/approve-escalation`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  assignAlert: (id: string, assignee: string) =>
    fetchApi<{ ok: boolean; alert_id: string; assigned_to: string }>(`/api/alerts/${id}/assign`, {
      method: "POST",
      body: JSON.stringify({ assignee }),
    }),
  addNote: (id: string, note: string) =>
    fetchApi<{ ok: boolean; alert_id: string; notes: { timestamp: string; role: string; text: string }[] }>(
      `/api/alerts/${id}/notes`,
      {
        method: "POST",
        body: JSON.stringify({ note }),
      }
    ),
  getSkills: () =>
    fetchApi<{ agents: SkillAgent[]; skills: Skill[] }>("/api/skills"),
  copilotChat: (message: string, alertId?: string, sessionId?: string) =>
    fetchApi<CopilotResponse>("/api/copilot/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        alert_id: alertId ?? null,
        session_id: sessionId ?? null,
      }),
    }),
  copilotChatStream: async (
    message: string,
    alertId: string | undefined,
    sessionId: string,
    onEvent: (ev: { event: string; text?: string; meta?: CopilotResponse; message?: string }) => void
  ) => {
    const res = await fetch(`${API_BASE}/api/copilot/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Role": getRole(),
        ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
      },
      body: JSON.stringify({
        message,
        alert_id: alertId ?? null,
        session_id: sessionId ?? null,
      }),
    });
    if (!res.ok || !res.body) throw new Error(`Stream error: ${res.status}`);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop() || "";
      for (const p of parts) {
        const line = p
          .split("\n")
          .map((l) => l.trim())
          .find((l) => l.startsWith("data:"));
        if (!line) continue;
        const payload = JSON.parse(line.slice(5).trim());
        if (payload.event === "meta") onEvent({ event: "meta", meta: payload.meta });
        else if (payload.event === "token") onEvent({ event: "token", text: payload.text });
        else if (payload.event === "done") onEvent({ event: "done" });
        else if (payload.event === "error") onEvent({ event: "error", message: payload.message });
      }
    }
  },
  getCopilotSession: (sessionId: string) =>
    fetchApi<{ session_id: string; turns: unknown[] }>(`/api/copilot/sessions/${sessionId}`),
  getAuthRoles: () => fetchApi<{ roles: { id: string; label: string }[] }>("/api/auth/roles"),
  exportAudit: () => `${API_BASE}/api/audit/export?format=csv`,
  analystPreview: (question: string) =>
    fetchApi<AnalystPreview>("/api/analyst/preview", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
  analystAsk: (question: string) =>
    fetchApi<AnalystAskResult>("/api/analyst/ask", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
  analystRun: (sql: string) =>
    fetchApi<AnalystResult>("/api/analyst/run", {
      method: "POST",
      body: JSON.stringify({ sql }),
    }),
};
