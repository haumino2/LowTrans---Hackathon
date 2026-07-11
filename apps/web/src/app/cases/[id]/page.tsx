"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
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
import type { LivePendingRun } from "@/components/agent/AgentWorkflowTimeline";
import { ModuleSidebar, isCryptoRail, modulesForRail } from "@/components/case/ModuleSidebar";
import { ModuleContent } from "@/components/case/ModulePanels";
import { AnalystOverride } from "@/components/case/AnalystOverride";
import { ConnectionsGraph } from "@/components/graph/ConnectionsGraph";
import { SarWorkspace } from "@/components/case/SarWorkspace";
import { shortAgentName, useAgentFleet } from "@/context/AgentFleetContext";
import { PageSkeleton } from "@/components/ui/Skeleton";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { useToast } from "@/components/ui/Toast";
import { api, getRole, type Alert, type TriageResult, type WorkflowStep } from "@/lib/api";

const STEP_DELAY_MS = 750;
const AGENT_PAUSE_MS = 500;
const ALL_TABS = ["Overview", "Connections Graph", "Timeline"] as const;
type Tab = (typeof ALL_TABS)[number];

function tabsForAlert(alert: Alert | null): readonly Tab[] {
  if (!alert || isCryptoRail(alert.rail)) return ALL_TABS;
  return ["Overview", "Timeline"] as const;
}

function parseTabParam(raw: string | null, allowed: readonly Tab[]): Tab | null {
  if (!raw) return null;
  const normalized = decodeURIComponent(raw).replace(/\+/g, " ").trim();
  return (allowed as readonly string[]).includes(normalized) ? (normalized as Tab) : null;
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export default function CasePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const alertId = params.id as string;
  const { syncFromWorkflow, setAgentsIdle, setPlanning } = useAgentFleet();
  const { success, error: toastError } = useToast();
  const [alert, setAlert] = useState<Alert | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [module, setModule] = useState("Customer Details");
  const [activeTab, setActiveTab] = useState<Tab>("Overview");
  const [focusSar, setFocusSar] = useState(() => searchParams.get("sar") === "1");
  const [triaging, setTriaging] = useState(false);
  const [visibleSteps, setVisibleSteps] = useState<WorkflowStep[]>([]);
  const [allSteps, setAllSteps] = useState<WorkflowStep[]>([]);
  const [liveResult, setLiveResult] = useState<TriageResult | null>(null);
  const [showDecision, setShowDecision] = useState(false);
  const [graphHighlight, setGraphHighlight] = useState<string[]>([]);
  const [liveCue, setLiveCue] = useState<string | null>(null);
  const [pendingRun, setPendingRun] = useState<LivePendingRun | null>(null);
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

  useEffect(() => {
    const allowed = tabsForAlert(alert);
    const tab = parseTabParam(searchParams.get("tab"), allowed);
    if (tab) setActiveTab(tab);
    else if (activeTab === "Connections Graph" && !allowed.includes("Connections Graph")) {
      setActiveTab("Overview");
    }
    setFocusSar(searchParams.get("sar") === "1");
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only re-sync when URL or alert rail changes
  }, [searchParams, alert?.rail]);

  useEffect(() => {
    if (!alert) return;
    const allowed = modulesForRail(alert.rail);
    if (!allowed.includes(module)) {
      setModule("Customer Details");
    }
  }, [alert, module]);

  useEffect(() => {
    if (!focusSar || activeTab !== "Overview") return;
    const t = window.setTimeout(() => {
      document.getElementById("sar-workspace")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 80);
    return () => window.clearTimeout(t);
  }, [focusSar, activeTab, showDecision, liveResult?.decision]);

  const load = useCallback(async () => {
    const a = await api.getAlert(alertId);
    setAlert(a);
    setAssignee((a.assigned_to as string) || "");
    if (a.triage_result?.workflow_steps) {
      setAllSteps(a.triage_result.workflow_steps);
      setVisibleSteps(a.triage_result.workflow_steps);
      setLiveResult(a.triage_result);
      setShowDecision(true);
      const ws = a.triage_result.workflow_steps;
      const finalSkills = ws
        .filter((s) => s.status === "completed" && s.skill_id)
        .map((s) => s.skill_id as string);
      syncFromWorkflow(
        ws.filter((s) => s.status === "completed").map((s) => s.agent),
        undefined,
        null,
        finalSkills
      );
      const graphRan = ws.some(
        (s) =>
          (s.agent === "Graph Analyst Agent" && s.status === "completed") ||
          (s.agent === "Financial Crime Investigator" &&
            !!s.input?.includes("OnChain_Graph") &&
            s.status === "completed")
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
  }, [alertId, syncFromWorkflow]);

  useEffect(() => {
    load()
      .then(() => setLoadFailed(false))
      .catch(() => {
        setAlert(null);
        setLoadFailed(true);
      });
  }, [load]);

  const animateWorkflow = async (result: TriageResult) => {
    const steps = result.workflow_steps ?? [];
    setAllSteps(steps);
    setVisibleSteps([]);
    setShowDecision(false);
    setLiveResult(null);
    setGraphHighlight([]);
    setPendingRun(null);
    setAgentsIdle();

    // D. Planning beat before step 1
    setPlanning(true);
    setLiveCue("Orchestrator is planning the investigation…");
    await sleep(STEP_DELAY_MS);
    setLiveCue(null);
    setPlanning(false);

    let lastAgent: string | null = null;

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];

      // Agent transition micro-pause
      if (lastAgent !== null && step.agent !== lastAgent) {
        setPendingRun(null);
        setLiveCue(`→ ${shortAgentName(step.agent)} investigating…`);
        syncFromWorkflow(
          steps
            .slice(0, i)
            .filter((s) => s.status === "completed")
            .map((s) => s.agent),
          step.agent,
          null,
          steps
            .slice(0, i)
            .filter((s) => s.status === "completed" && s.skill_id)
            .map((s) => s.skill_id as string)
        );
        await sleep(AGENT_PAUSE_MS);
        setLiveCue(null);
      }
      lastAgent = step.agent;

      if (step.status !== "skipped") {
        const doneSkills = steps
          .slice(0, i)
          .filter((s) => s.status === "completed" && s.skill_id)
          .map((s) => s.skill_id as string);
        syncFromWorkflow(
          steps.slice(0, i).filter((s) => s.status === "completed").map((s) => s.agent),
          step.agent,
          step.skill_id ?? null,
          doneSkills
        );
      } else {
        // Still mark agent as active so phase stays highlighted while skipped steps land
        syncFromWorkflow(
          steps.slice(0, i).filter((s) => s.status === "completed").map((s) => s.agent),
          step.agent,
          step.skill_id ?? null,
          steps
            .slice(0, i)
            .filter((s) => s.status === "completed" && s.skill_id)
            .map((s) => s.skill_id as string)
        );
      }

      const isGraphStep =
        step.skill_id === "graph-summary" ||
        (step.agent === "Graph Analyst Agent" && step.status === "completed") ||
        (step.agent === "Financial Crime Investigator" &&
          !!step.input?.includes("OnChain_Graph") &&
          step.status === "completed");
      if (isGraphStep) {
        try {
          const graph = await api.getGraph(alertId);
          setGraphHighlight(graph.flagged_node_ids);
        } catch {
          /* graph may not exist for all alerts */
        }
      }

      const skill = step.input?.trim() || step.skill_id?.replace(/-/g, " ") || "skill";
      setPendingRun(null);
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

      // Peek next step as pending run (live rhythm between steps)
      if (i + 1 < steps.length && steps[i + 1].agent === step.agent) {
        const nxt = steps[i + 1];
        setPendingRun({
          agent: nxt.agent,
          skill: nxt.input?.trim() || nxt.skill_id?.replace(/-/g, " ") || skill,
        });
      } else {
        setPendingRun(null);
      }
    }

    setPendingRun(null);
    setLiveCue(null);
    const finalSkills = steps
      .filter((s) => s.status === "completed" && s.skill_id)
      .map((s) => s.skill_id as string);
    syncFromWorkflow(
      steps.filter((s) => s.status === "completed").map((s) => s.agent),
      undefined,
      null,
      finalSkills
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
    setPendingRun(null);
    setAgentsIdle();

    // Planning cue before first SSE event
    setPlanning(true);
    setLiveCue("Orchestrator is planning the investigation…");
    setPendingRun({ agent: "Orchestrator", skill: "planning" });

    try {
      const completedAgents: string[] = [];
      const completedSkills: string[] = [];
      let lastAgent: string | null = null;
      let agentPause: Promise<void> = Promise.resolve();

      const result = await api.triageStream(alertId, (data) => {
        if (data.event === "step" && data.step) {
          const step = data.step;
          const prevAgent = lastAgent;
          lastAgent = step.agent;

          // Clear planning on first real step
          setLiveCue((cue) => (cue?.includes("planning") ? null : cue));
          setPlanning(false);

          const applyStep = async () => {
            if (step.status === "completed") {
              completedAgents.push(step.agent);
              if (step.skill_id) completedSkills.push(step.skill_id);
            }
            syncFromWorkflow(
              [...completedAgents],
              step.agent,
              step.skill_id ?? null,
              [...completedSkills]
            );
            if (
              step.skill_id === "graph-summary" ||
              (step.agent === "Graph Analyst Agent" && step.status === "completed") ||
              (step.agent === "Financial Crime Investigator" &&
                !!step.input?.includes("OnChain_Graph") &&
                step.status === "completed")
            ) {
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

            // Flash running → final so the live path matches replay rhythm
            setPendingRun(null);
            setVisibleSteps((prev) => {
              const solid = prev.filter((s) => s.status !== "running");
              return [...solid, { ...step, status: "running" }];
            });
            await sleep(Math.min(400, STEP_DELAY_MS));
            setVisibleSteps((prev) => {
              const solid = prev.filter(
                (s) => !(s.step === step.step && s.status === "running")
              );
              return [
                ...solid,
                {
                  ...step,
                  status: step.status === "skipped" ? "skipped" : ("completed" as const),
                },
              ];
            });
            // Ephemeral row while waiting for the next SSE event
            setPendingRun({
              agent: step.agent,
              skill: "working",
            });
          };

          if (prevAgent !== null && step.agent !== prevAgent) {
            setPendingRun(null);
            setLiveCue(`→ ${shortAgentName(step.agent)} investigating…`);
            syncFromWorkflow([...completedAgents], step.agent, null, [...completedSkills]);
            // Chain pauses so rapid SSE events still honor the micro-pause
            agentPause = agentPause.then(async () => {
              await sleep(AGENT_PAUSE_MS);
              setLiveCue(null);
              await applyStep();
            });
          } else {
            agentPause = agentPause.then(() => applyStep());
          }
        }
      });

      await agentPause;
      setPendingRun(null);
      setLiveCue(null);

      if (result) {
        setAllSteps(result.workflow_steps ?? []);
        setVisibleSteps(result.workflow_steps ?? []);
        setLiveResult(result);
        setShowDecision(true);
        const finalSkills = (result.workflow_steps ?? [])
          .filter((s) => s.status === "completed" && s.skill_id)
          .map((s) => s.skill_id as string);
        syncFromWorkflow(
          (result.workflow_steps ?? []).filter((s) => s.status === "completed").map((s) => s.agent),
          undefined,
          null,
          finalSkills
        );
        await load();
        success("Agent workflow complete");
      }
    } catch {
      try {
        const result = await api.triage(alertId);
        await animateWorkflow(result);
        await load();
        success("Agent workflow complete");
      } catch (e) {
        toastError(e instanceof Error ? e.message : "Triage failed");
      }
    } finally {
      setPendingRun(null);
      setLiveCue(null);
      setPlanning(false);
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
  const hasTriage = Boolean(displayResult?.decision);

  if (!alert) {
    return (
      <AppShell>
        {loadFailed ? (
          <div className="flex min-h-[40vh] flex-col items-center justify-center px-6 text-center">
            <p className="text-sm font-semibold text-chrome-900">Case not found</p>
            <p className="mt-1 text-sm text-chrome-500">
              Could not load {alertId}. Check the alert ID or API connection.
            </p>
            <Link href="/" className="mt-4 text-sm font-medium text-accent hover:text-accent-hover">
              Back to alert queue
            </Link>
          </div>
        ) : (
          <PageSkeleton />
        )}
      </AppShell>
    );
  }

  return (
    <AppShell>
      <ErrorBoundary fallbackTitle="Case page failed to render">
      <div className="border-b border-chrome-200 bg-white px-6 py-3">
        <nav className="text-sm text-chrome-500">
          <Link href="/" className="hover:text-accent">Alert Queue</Link>
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
          {tabsForAlert(alert).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-accent text-accent"
                  : "border-transparent text-chrome-500 hover:text-chrome-700"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      <div className="flex">
        {activeTab === "Overview" && (
          <ModuleSidebar active={module} onSelect={setModule} rail={alert.rail} />
        )}

        <div className="flex-1 p-6 space-y-6">
          {(activeTab === "Overview" || activeTab === "Timeline") && (
            <div className="flex items-start gap-6">
              <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <RiskGauge
                  level={alert.risk_level}
                  score={alert.kyt_score}
                  investigated={hasTriage && showDecision}
                  decision={hasTriage && showDecision ? displayResult?.decision : undefined}
                  confidence={hasTriage && showDecision ? displayResult?.confidence : undefined}
                />
              </div>

              <div className="flex-1 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 text-lg font-semibold text-gray-700">
                    {alert.customer_name.charAt(0)}
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">{alert.customer_name}</h2>
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                      {alert.segment && (
                        <span className="rounded-md border border-chrome-200 bg-chrome-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-chrome-700">
                          {alert.segment}
                        </span>
                      )}
                      {alert.product && (
                        <span className="rounded-md border border-accent/30 bg-accent-muted px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-accent">
                          {alert.product}
                        </span>
                      )}
                      {alert.kyc_tier && (
                        <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-emerald-800">
                          KYC {alert.kyc_tier}
                        </span>
                      )}
                    </div>
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
                        className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
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
                          try {
                            await api.assignAlert(alertId, assignee || "unassigned");
                            await load();
                            success("Assignee updated");
                          } catch (e) {
                            toastError(e instanceof Error ? e.message : "Assign failed");
                          }
                        }}
                        className="rounded-md border border-chrome-200 bg-white px-3 py-2 text-sm font-medium text-chrome-700 hover:bg-chrome-50"
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
                      className="w-full rounded-md border border-chrome-200 px-3 py-2 text-sm text-chrome-900 placeholder:text-chrome-400 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                    />
                    <div className="mt-2 flex items-center justify-between">
                      <p className="text-xs text-chrome-400">Latest notes: {(alert?.notes?.length ?? 0)}</p>
                      <button
                        disabled={!note.trim() || noteSaving}
                        onClick={async () => {
                          setNoteSaving(true);
                          try {
                            await api.addNote(alertId, note);
                            setNote("");
                            await load();
                            success("Note added");
                          } catch (e) {
                            toastError(e instanceof Error ? e.message : "Failed to add note");
                          } finally {
                            setNoteSaving(false);
                          }
                        }}
                        className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
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
                  <div className="rounded-lg border border-risk-escalate/30 bg-risk-escalate-bg p-5">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-risk-escalate">Supervisor approval required</p>
                        <p className="mt-1 text-xs text-chrome-600">
                          This case is pending escalation approval. Approving will set status to ESCALATE.
                        </p>
                      </div>
                      <button
                        onClick={async () => {
                          try {
                            await api.approveEscalation(alertId);
                            await load();
                            success("Escalation approved");
                          } catch (e) {
                            toastError(e instanceof Error ? e.message : "Approval failed");
                          }
                        }}
                        className="rounded-md bg-risk-escalate px-4 py-2 text-sm font-medium text-white hover:bg-red-800"
                      >
                        Approve Escalation
                      </button>
                    </div>
                  </div>
                )}

              {showDecision && displayResult?.decision === "ESCALATE" && (
                <div id="sar-workspace">
                  <SarWorkspace
                    alertId={alertId}
                    customerName={alert.customer_name}
                    escalationSummary={displayResult.escalation_summary}
                  />
                </div>
              )}

              {focusSar && activeTab === "Overview" && !(showDecision && displayResult?.decision === "ESCALATE") && (
                <div
                  id="sar-workspace"
                  className="rounded-xl border border-dashed border-chrome-300 bg-chrome-50 p-4 text-sm text-chrome-600"
                >
                  SAR workspace opens here after Arbiter escalates (run triage on this case if empty).
                </div>
              )}

              <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <h3 className="mb-4 text-sm font-semibold text-gray-900">{module}</h3>
                <ModuleContent module={module} alert={alert} />
              </div>
            </>
          )}

          {activeTab === "Connections Graph" && isCryptoRail(alert.rail) && (
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
                liveCue={liveCue}
                pendingRun={pendingRun}
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
      </ErrorBoundary>
    </AppShell>
  );
}
