"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Calendar,
  Monitor,
  RefreshCw,
  GitBranch,
  Play,
  RotateCcw,
} from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { RiskGauge } from "@/components/risk/RiskGauge";
import { AgentRecommendation } from "@/components/agent/AgentRecommendation";
import { AgentWorkflowTimeline } from "@/components/agent/AgentWorkflowTimeline";
import { ModuleSidebar } from "@/components/case/ModuleSidebar";
import { ModuleContent } from "@/components/case/ModulePanels";
import { AnalystOverride } from "@/components/case/AnalystOverride";
import { ConnectionsGraph } from "@/components/graph/ConnectionsGraph";
import { SarWorkspace } from "@/components/case/SarWorkspace";
import { useAgentFleet } from "@/context/AgentFleetContext";
import { api, getRole, type Alert, type TriageResult, type WorkflowStep } from "@/lib/api";

const STEP_DELAY_MS = 450;
const TABS = ["Overview", "Connections Graph", "Timeline"] as const;
type Tab = (typeof TABS)[number];

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export default function CasePage() {
  const params = useParams();
  const alertId = params.id as string;
  const { syncFromWorkflow, setAgentsIdle } = useAgentFleet();
  const [alert, setAlert] = useState<Alert | null>(null);
  const [module, setModule] = useState("Customer Details");
  const [activeTab, setActiveTab] = useState<Tab>("Overview");
  const [triaging, setTriaging] = useState(false);
  const [visibleSteps, setVisibleSteps] = useState<WorkflowStep[]>([]);
  const [allSteps, setAllSteps] = useState<WorkflowStep[]>([]);
  const [liveResult, setLiveResult] = useState<TriageResult | null>(null);
  const [showDecision, setShowDecision] = useState(false);
  const [graphHighlight, setGraphHighlight] = useState<string[]>([]);
  const [role, setRole] = useState<string>(() => getRole());
  const [assignee, setAssignee] = useState<string>("");
  const [note, setNote] = useState<string>("");
  const [noteSaving, setNoteSaving] = useState<boolean>(false);

  useEffect(() => {
    const onRoleChange = (e: Event) => {
      const next = (e as CustomEvent<string>).detail;
      if (next) setRole(next);
    };
    window.addEventListener("lowtrans-role-change", onRoleChange);
    return () => window.removeEventListener("lowtrans-role-change", onRoleChange);
  }, []);

  const load = useCallback(async () => {
    const a = await api.getAlert(alertId);
    setAlert(a);
    setAssignee((a.assigned_to as string) || "");
    if (a.triage_result?.workflow_steps) {
      setAllSteps(a.triage_result.workflow_steps);
      setVisibleSteps(a.triage_result.workflow_steps);
      setLiveResult(a.triage_result);
      setShowDecision(true);
      const graphRan = a.triage_result.workflow_steps.some(
        (s) => s.agent === "Graph Analyst Agent" && s.status === "completed"
      );
      if (graphRan) {
        try {
          const graph = await api.getGraph(alertId);
          setGraphHighlight(graph.flagged_node_ids);
        } catch {
          /* no graph for this alert */
        }
      }
    }
  }, [alertId]);

  useEffect(() => {
    load().catch(() => setAlert(null));
  }, [load]);

  const animateWorkflow = async (result: TriageResult) => {
    const steps = result.workflow_steps ?? [];
    setAllSteps(steps);
    setVisibleSteps([]);
    setShowDecision(false);
    setLiveResult(null);
    setGraphHighlight([]);
    setAgentsIdle();

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      if (step.status !== "skipped") {
        syncFromWorkflow(
          steps.slice(0, i).filter((s) => s.status === "completed").map((s) => s.agent),
          step.agent
        );
      }

      if (step.agent === "Graph Analyst Agent" && step.status === "completed") {
        try {
          const graph = await api.getGraph(alertId);
          setGraphHighlight(graph.flagged_node_ids);
        } catch {
          /* graph may not exist for all alerts */
        }
      }

      const running: WorkflowStep = { ...step, status: "running" };
      setVisibleSteps((prev) => {
        const next = [...prev];
        if (next.length > 0 && next[next.length - 1].status === "running") {
          next[next.length - 1] = { ...next[next.length - 1], status: steps[i - 1].status };
        }
        return [...next, running];
      });
      await sleep(STEP_DELAY_MS);
      setVisibleSteps(steps.slice(0, i + 1));
    }

    syncFromWorkflow(
      steps.filter((s) => s.status === "completed").map((s) => s.agent)
    );
    setLiveResult(result);
    setShowDecision(true);
  };

  const handleTriage = async () => {
    setTriaging(true);
    setActiveTab("Timeline");
    setVisibleSteps([]);
    setAllSteps([]);
    setShowDecision(false);
    setLiveResult(null);
    setGraphHighlight([]);
    setAgentsIdle();

    try {
      const completedAgents: string[] = [];
      const result = await api.triageStream(alertId, (data) => {
        if (data.event === "step" && data.step) {
          const step = data.step;
          if (step.status === "completed") {
            completedAgents.push(step.agent);
          }
          if (step.status !== "skipped") {
            syncFromWorkflow([...completedAgents], step.status === "running" ? step.agent : undefined);
          }
          if (step.agent === "Graph Analyst Agent" && step.status === "completed") {
            api.getGraph(alertId).then((g) => setGraphHighlight(g.flagged_node_ids)).catch(() => null);
          }
          setAllSteps((prev) => {
            const idx = prev.findIndex((s) => s.step === step.step);
            if (idx >= 0) {
              const next = [...prev];
              next[idx] = step;
              return next;
            }
            return [...prev, step];
          });
          setVisibleSteps((prev) => {
            const withoutRunning = prev.filter((s) => s.status !== "running");
            return [...withoutRunning, { ...step, status: step.status === "skipped" ? "skipped" : "completed" as const }];
          });
        }
      });
      if (result) {
        setAllSteps(result.workflow_steps ?? []);
        setVisibleSteps(result.workflow_steps ?? []);
        setLiveResult(result);
        setShowDecision(true);
        syncFromWorkflow(
          (result.workflow_steps ?? []).filter((s) => s.status === "completed").map((s) => s.agent)
        );
        await load();
      }
    } catch {
      const result = await api.triage(alertId);
      await animateWorkflow(result);
      await load();
    } finally {
      setTriaging(false);
    }
  };

  const handleReplay = async () => {
    const result = alert?.triage_result ?? liveResult;
    if (!result?.workflow_steps) return;
    setTriaging(true);
    setActiveTab("Timeline");
    try {
      await animateWorkflow(result);
    } finally {
      setTriaging(false);
    }
  };

  const displayResult = liveResult ?? alert?.triage_result;
  const hasWorkflow = (displayResult?.workflow_steps?.length ?? 0) > 0;

  if (!alert) {
    return (
      <AppShell>
        <div className="p-6 text-gray-500">Loading case...</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="border-b border-gray-200 bg-white px-6 py-3">
        <nav className="text-sm text-gray-500">
          <Link href="/" className="hover:text-indigo-600">Alert Queue</Link>
          <span className="mx-2 text-gray-300">/</span>
          <span className="text-gray-700">Customer Intelligence</span>
          <span className="mx-2 text-gray-300">/</span>
          <span className="font-medium text-gray-900">{alert.customer_name}</span>
          <span className="mx-2 text-gray-300">/</span>
          <span className="font-mono text-xs">{alert.session_id}</span>
        </nav>
      </div>

      <div className="border-b border-gray-200 bg-white px-6">
        <div className="flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-indigo-600 text-indigo-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      <div className="flex">
        {activeTab === "Overview" && (
          <ModuleSidebar active={module} onSelect={setModule} />
        )}

        <div className="flex-1 p-6 space-y-6">
          {(activeTab === "Overview" || activeTab === "Timeline") && (
            <div className="flex items-start gap-6">
              <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <RiskGauge level={alert.risk_level} score={alert.kyt_score} />
              </div>

              <div className="flex-1 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 text-lg font-semibold text-gray-700">
                    {alert.customer_name.charAt(0)}
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">{alert.customer_name}</h2>
                    <div className="mt-1 flex flex-wrap gap-4 text-xs text-gray-500">
                      <span className="inline-flex items-center gap-1">
                        <Calendar className="h-3.5 w-3.5" />
                        {alert.account_age_days} days
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <Monitor className="h-3.5 w-3.5" />
                        {alert.device_os}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <RefreshCw className="h-3.5 w-3.5" />
                        {alert.flow_type}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <GitBranch className="h-3.5 w-3.5" />
                        {alert.connections}+ connections
                      </span>
                    </div>
                  </div>
                  <div className="ml-auto flex gap-2">
                    {!hasWorkflow && (
                      <button
                        onClick={handleTriage}
                        disabled={triaging}
                        className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                      >
                        <Play className="h-4 w-4" />
                        {triaging ? "Running Agents..." : "Run Agent Workflow"}
                      </button>
                    )}
                    {hasWorkflow && (
                      <button
                        onClick={handleReplay}
                        disabled={triaging}
                        className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                      >
                        <RotateCcw className="h-4 w-4" />
                        {triaging ? "Replaying..." : "Replay Workflow"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "Overview" && (
            <>
              {showDecision && displayResult && (
                <AgentRecommendation result={displayResult} />
              )}

              {showDecision && (
                <AnalystOverride
                  alertId={alertId}
                  currentDecision={displayResult?.decision}
                  onOverride={load}
                />
              )}

              {showDecision && (
                <div className="rounded-xl border border-gray-200 bg-white p-5">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-gray-900">Assignment & Notes</p>
                      <p className="mt-1 text-xs text-gray-500">Lightweight ops for pilot: assign owner + add internal notes.</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        value={assignee}
                        onChange={(e) => setAssignee(e.target.value)}
                        placeholder="Assignee (e.g. alice@vasp.com)"
                        className="w-64 rounded-lg border border-gray-200 px-3 py-2 text-sm"
                      />
                      <button
                        onClick={async () => {
                          await api.assignAlert(alertId, assignee || "unassigned");
                          await load();
                        }}
                        className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                      >
                        Save
                      </button>
                    </div>
                  </div>

                  <div className="mt-4">
                    <textarea
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      placeholder="Add internal note (not part of SAR)..."
                      rows={3}
                      className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-indigo-300 focus:outline-none focus:ring-1 focus:ring-indigo-300"
                    />
                    <div className="mt-2 flex items-center justify-between">
                      <p className="text-xs text-gray-400">Latest notes: {(alert?.notes?.length ?? 0)}</p>
                      <button
                        disabled={!note.trim() || noteSaving}
                        onClick={async () => {
                          setNoteSaving(true);
                          try {
                            await api.addNote(alertId, note);
                            setNote("");
                            await load();
                          } finally {
                            setNoteSaving(false);
                          }
                        }}
                        className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                      >
                        {noteSaving ? "Saving..." : "Add Note"}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {showDecision &&
                displayResult?.decision === "ESCALATE" &&
                alert.status === "escalate_pending" &&
                role === "supervisor" && (
                  <div className="rounded-xl border border-purple-200 bg-purple-50 p-5">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-purple-900">Supervisor approval required</p>
                        <p className="mt-1 text-xs text-purple-800/80">
                          This case is pending escalation approval. Approving will set status to ESCALATE.
                        </p>
                      </div>
                      <button
                        onClick={async () => {
                          await api.approveEscalation(alertId);
                          await load();
                        }}
                        className="rounded-lg bg-purple-700 px-4 py-2 text-sm font-medium text-white hover:bg-purple-800"
                      >
                        Approve Escalation
                      </button>
                    </div>
                  </div>
                )}

              {showDecision && displayResult?.decision === "ESCALATE" && (
                <SarWorkspace
                  alertId={alertId}
                  customerName={alert.customer_name}
                  escalationSummary={displayResult.escalation_summary}
                />
              )}

              <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <h3 className="mb-4 text-sm font-semibold text-gray-900">{module}</h3>
                <ModuleContent module={module} alert={alert} />
              </div>
            </>
          )}

          {activeTab === "Connections Graph" && (
            <ConnectionsGraph
              alertId={alertId}
              highlightedNodes={graphHighlight}
            />
          )}

          {activeTab === "Timeline" && (
            <>
              <AgentWorkflowTimeline
                steps={visibleSteps}
                allSteps={allSteps}
                summary={displayResult?.workflow_summary}
                decision={showDecision ? displayResult?.decision : undefined}
                confidence={showDecision ? displayResult?.confidence : undefined}
                isAnimating={triaging}
              />

              {showDecision && displayResult && (
                <AgentRecommendation result={displayResult} />
              )}

              {showDecision && graphHighlight.length > 0 && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
                  <p className="text-sm text-red-800">
                    Graph Analyst flagged {graphHighlight.length} node(s). View the{" "}
                    <button
                      onClick={() => setActiveTab("Connections Graph")}
                      className="font-medium underline hover:text-red-900"
                    >
                      Connections Graph
                    </button>{" "}
                    tab for details.
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
