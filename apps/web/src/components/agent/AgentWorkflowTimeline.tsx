"use client";

import Link from "next/link";
import {
  Zap,
  Shield,
  GitBranch,
  FileWarning,
  Check,
  Minus,
  Loader2,
  ExternalLink,
  Bot,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { WorkflowStep, WorkflowSummary } from "@/lib/api";
import {
  DEFAULT_AGENTS,
  PIPELINE_NODES,
  shortAgentName,
  useAgentFleet,
  type AgentStatus,
} from "@/context/AgentFleetContext";
import { cn } from "@/lib/cn";

const AGENT_ICONS: Record<string, LucideIcon> = {
  Orchestrator: Zap,
  "Entity Identity Agent": Shield,
  "Financial Crime Investigator": GitBranch,
  Arbiter: FileWarning,
};

/** Skills that use mock vendor data — show honest label in the timeline. */
const SIMULATED_SKILL_IDS = new Set([
  "osint-research",
  "kyb-verify",
  "ubo-unroll",
  "fiat-crypto-bridge",
]);

function isSimulatedStep(step: WorkflowStep): boolean {
  if (step.skill_id && SIMULATED_SKILL_IDS.has(step.skill_id)) return true;
  return /\[simulated\]/i.test(step.output || "") || /\[simulated\]/i.test(step.input || "");
}

function skillLabel(step: Pick<WorkflowStep, "input" | "skill_id">): string {
  if (step.input?.trim()) return step.input.trim();
  if (step.skill_id) return step.skill_id.replace(/-/g, " ");
  return "skill";
}

type PhaseStatus = "pending" | "planning" | "running" | "completed";

function derivePhaseStatus(
  agentName: string,
  phaseSteps: WorkflowStep[],
  fleetStatus: AgentStatus | undefined,
  isPlanning: boolean,
  isAnimating: boolean,
  activeAgent: string | null
): PhaseStatus {
  if (isAnimating && isPlanning && agentName === "Orchestrator") return "planning";
  if (fleetStatus === "planning" && agentName === "Orchestrator") return "planning";
  if (fleetStatus === "running" || (isAnimating && activeAgent === agentName)) return "running";
  if (fleetStatus === "completed") return "completed";
  if (phaseSteps.length > 0) {
    const allDone = phaseSteps.every((s) => s.status === "completed" || s.status === "skipped");
    if (allDone && !isAnimating) return "completed";
    if (phaseSteps.some((s) => s.status === "running")) return "running";
    if (allDone) return "completed";
  }
  return "pending";
}

export interface LivePendingRun {
  agent: string;
  skill: string;
}

interface Props {
  steps: WorkflowStep[];
  allSteps?: WorkflowStep[];
  summary?: WorkflowSummary;
  decision?: string;
  confidence?: number;
  isAnimating?: boolean;
  /** Planning / agent-switch cue shown above steps */
  liveCue?: string | null;
  /** Ephemeral running row while waiting for the next SSE / replay step */
  pendingRun?: LivePendingRun | null;
}

export function AgentWorkflowTimeline({
  steps,
  allSteps,
  summary,
  decision,
  confidence,
  isAnimating = false,
  liveCue = null,
  pendingRun = null,
}: Props) {
  const { agents, isPlanning } = useAgentFleet();

  const catalog = allSteps && allSteps.length > 0 ? allSteps : steps;
  const total = catalog.length;
  const doneCount = steps.filter(
    (s) => s.status === "completed" || s.status === "skipped"
  ).length;

  const activeAgent =
    pendingRun?.agent ??
    steps.find((s) => s.status === "running")?.agent ??
    agents.find((a) => a.status === "running" || a.status === "planning")?.name ??
    null;

  const phases = DEFAULT_AGENTS.map((agentName) => {
    const phaseSteps = steps.filter((s) => s.agent === agentName);
    const catalogSteps = catalog.filter((s) => s.agent === agentName);
    const fleet = agents.find((a) => a.name === agentName);
    const status = derivePhaseStatus(
      agentName,
      phaseSteps,
      fleet?.status,
      isPlanning,
      isAnimating,
      activeAgent
    );
    return {
      agentName,
      short: shortAgentName(agentName),
      steps: phaseSteps,
      total: Math.max(catalogSteps.length, phaseSteps.length),
      status,
      Icon: AGENT_ICONS[agentName] ?? Bot,
    };
  });

  // Orphan steps from legacy agent names
  const known = new Set<string>(DEFAULT_AGENTS);
  const orphans = steps.filter((s) => !known.has(s.agent));

  return (
    <div className="overflow-hidden rounded-xl border border-chrome-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-chrome-200 bg-chrome-50 px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-chrome-900">Agent Workflow</span>
          {isAnimating && (
            <span className="animate-pulse rounded-full bg-accent-muted px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-accent">
              LIVE
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-chrome-500">
          {summary && (
            <>
              <span className="tabular-nums">{summary.agents_run} agents run</span>
              <span>·</span>
              <span className="font-mono tabular-nums">{summary.total_duration_ms}ms</span>
            </>
          )}
          <span className="font-medium tabular-nums text-chrome-700">
            {doneCount}/{total || "—"} steps
          </span>
        </div>
      </div>

      {/* Progress bar */}
      {isAnimating && total > 0 && (
        <div className="h-1 bg-chrome-100">
          <div
            className="h-full bg-accent transition-all duration-300 ease-out"
            style={{ width: `${Math.min(100, (doneCount / total) * 100)}%` }}
          />
        </div>
      )}

      {/* A. Pipeline stepper */}
      <div className="border-b border-chrome-100 px-5 py-4">
        <PipelineStepper
          phases={phases.map((p) => ({
            name: p.short,
            status: p.status,
            Icon: p.Icon,
          }))}
          isAnimating={isAnimating}
        />
      </div>

      <div className="space-y-3 p-5">
        {steps.length === 0 && !isAnimating && !liveCue && (
          <p className="py-6 text-center text-sm text-chrome-400">
            Run agent workflow to see the timeline
          </p>
        )}

        {/* D. Planning / transition cue */}
        {liveCue && (
          <div className="flex items-center gap-2 rounded-lg border border-accent/20 bg-accent-muted px-3 py-2 text-sm text-accent">
            <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" strokeWidth={2.5} />
            <span className="font-medium">{liveCue}</span>
          </div>
        )}

        {/* B. Phases grouped by agent */}
        {phases.map((phase) => {
          const isActive =
            phase.status === "running" || phase.status === "planning";
          const isPending = phase.status === "pending";
          const showBody =
            !isPending &&
            (phase.steps.length > 0 ||
              (pendingRun && pendingRun.agent === phase.agentName) ||
              (isActive && isAnimating));

          if (isPending && isAnimating && phase.total === 0 && phase.steps.length === 0) {
            return (
              <div
                key={phase.agentName}
                className="rounded-lg border border-chrome-100 bg-chrome-50/40 px-3 py-2.5 opacity-40"
              >
                <PhaseHeader
                  short={phase.short}
                  Icon={phase.Icon}
                  status="pending"
                  done={0}
                  total={0}
                  dimmed
                />
              </div>
            );
          }

          if (isPending && !isAnimating && phase.steps.length === 0 && phase.total === 0) {
            return null;
          }

          const doneInPhase = phase.steps.filter(
            (s) => s.status === "completed" || s.status === "skipped"
          ).length;

          return (
            <div
              key={phase.agentName}
              className={cn(
                "rounded-lg border transition-all duration-300",
                isActive &&
                  "border-accent/30 bg-accent-muted/40 shadow-sm ring-1 ring-accent/10",
                phase.status === "completed" && "border-chrome-200 bg-white",
                isPending && "border-chrome-100 bg-chrome-50/50 opacity-45"
              )}
            >
              <div className={cn("px-3 py-2.5", showBody && "border-b border-chrome-100")}>
                <PhaseHeader
                  short={phase.short}
                  Icon={phase.Icon}
                  status={phase.status}
                  done={doneInPhase}
                  total={phase.total || phase.steps.length}
                  dimmed={isPending}
                />
              </div>

              {showBody && (
                <div className="space-y-0 px-3 py-2">
                  {phase.steps.map((step, idx) => (
                    <StepRow
                      key={`${step.step}-${step.agent}-${step.skill_id ?? idx}`}
                      step={step}
                      isLast={
                        idx === phase.steps.length - 1 &&
                        !(pendingRun && pendingRun.agent === phase.agentName)
                      }
                    />
                  ))}
                  {pendingRun && pendingRun.agent === phase.agentName && (
                    <PendingRow agent={pendingRun.agent} skill={pendingRun.skill} />
                  )}
                </div>
              )}
            </div>
          );
        })}

        {/* Legacy / unmapped agents */}
        {orphans.length > 0 && (
          <div className="rounded-lg border border-chrome-200 bg-white px-3 py-2">
            {orphans.map((step, idx) => (
              <StepRow
                key={`orphan-${step.step}-${idx}`}
                step={step}
                isLast={idx === orphans.length - 1}
              />
            ))}
          </div>
        )}

        {/* Pending run when agent not yet in a visible phase body */}
        {pendingRun &&
          !phases.some(
            (p) =>
              p.agentName === pendingRun.agent &&
              (p.steps.length > 0 ||
                p.status === "running" ||
                p.status === "planning")
          ) && (
            <div className="rounded-lg border border-accent/30 bg-accent-muted/40 px-3 py-2">
              <PendingRow agent={pendingRun.agent} skill={pendingRun.skill} />
            </div>
          )}
      </div>

      {/* Final decision banner */}
      {decision && !isAnimating && steps.length > 0 && (
        <div
          className={cn(
            "flex items-center justify-between border-t px-5 py-3",
            decision === "CLEAR" && "border-emerald-100 bg-risk-clear-bg",
            decision === "ESCALATE" && "border-red-100 bg-risk-escalate-bg",
            decision !== "CLEAR" &&
              decision !== "ESCALATE" &&
              "border-amber-100 bg-risk-review-bg"
          )}
        >
          <span
            className={cn(
              "text-sm font-bold",
              decision === "CLEAR" && "text-risk-clear",
              decision === "ESCALATE" && "text-risk-escalate",
              decision !== "CLEAR" &&
                decision !== "ESCALATE" &&
                "text-risk-review"
            )}
          >
            FINAL DECISION: {decision}
          </span>
          {confidence !== undefined && (
            <span className="text-sm tabular-nums opacity-80">
              {(confidence * 100).toFixed(0)}% confidence
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Pipeline stepper ─────────────────────────────────────────── */

function PipelineStepper({
  phases,
  isAnimating,
}: {
  phases: { name: string; status: PhaseStatus; Icon: LucideIcon }[];
  isAnimating: boolean;
}) {
  return (
    <div className="flex items-center gap-0">
      {phases.map((node, i) => {
        const isLast = i === phases.length - 1;
        const active =
          node.status === "running" || node.status === "planning";
        const done = node.status === "completed";
        const pending = node.status === "pending";
        const next = phases[i + 1];
        const connectorFilled =
          done || (active && next && next.status !== "pending");

        return (
          <div key={node.name} className="flex min-w-0 flex-1 items-center">
            <div
              className={cn(
                "flex min-w-0 flex-col items-center gap-1.5 px-1",
                pending && "opacity-40"
              )}
            >
              <div
                className={cn(
                  "relative flex h-9 w-9 items-center justify-center rounded-full border-2 transition-all duration-300",
                  done && "border-emerald-200 bg-emerald-500 text-white",
                  active &&
                    "border-accent bg-accent text-accent-foreground shadow-sm shadow-accent/25",
                  pending && "border-chrome-200 bg-chrome-50 text-chrome-400",
                  active && isAnimating && "animate-pulse"
                )}
              >
                {done ? (
                  <Check className="h-4 w-4" strokeWidth={2.5} />
                ) : active ? (
                  <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2.5} />
                ) : (
                  <node.Icon className="h-3.5 w-3.5" strokeWidth={2} />
                )}
              </div>
              <span
                className={cn(
                  "max-w-[5.5rem] truncate text-center text-[10px] font-semibold leading-tight",
                  done && "text-emerald-700",
                  active && "text-accent",
                  pending && "text-chrome-400"
                )}
                title={PIPELINE_NODES[i]?.name}
              >
                {node.name}
              </span>
              <span
                className={cn(
                  "text-[9px] font-bold uppercase tracking-wider",
                  done && "text-emerald-600",
                  active && "text-accent",
                  pending && "text-chrome-300"
                )}
              >
                {node.status === "planning"
                  ? "planning"
                  : node.status === "running"
                    ? "running"
                    : node.status === "completed"
                      ? "done"
                      : "queued"}
              </span>
            </div>

            {!isLast && (
              <div className="mb-6 h-0.5 min-w-[8px] flex-1 overflow-hidden rounded-full bg-chrome-100">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-500 ease-out",
                    done && "w-full bg-emerald-400",
                    active && "w-1/2 bg-accent",
                    active && isAnimating && "animate-pulse",
                    pending && "w-0",
                    connectorFilled && !done && !active && "w-full bg-emerald-300"
                  )}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ─── Phase header ─────────────────────────────────────────────── */

function PhaseHeader({
  short,
  Icon,
  status,
  done,
  total,
  dimmed,
}: {
  short: string;
  Icon: LucideIcon;
  status: PhaseStatus;
  done: number;
  total: number;
  dimmed?: boolean;
}) {
  return (
    <div className={cn("flex items-center justify-between gap-2", dimmed && "opacity-70")}>
      <div className="flex min-w-0 items-center gap-2">
        <Icon
          className={cn(
            "h-4 w-4 shrink-0",
            status === "running" || status === "planning"
              ? "text-accent"
              : status === "completed"
                ? "text-emerald-600"
                : "text-chrome-400"
          )}
          strokeWidth={1.75}
        />
        <span
          className={cn(
            "truncate text-sm font-semibold",
            status === "running" || status === "planning"
              ? "text-accent"
              : status === "completed"
                ? "text-chrome-900"
                : "text-chrome-400"
          )}
        >
          {short}
        </span>
        <StatusChip status={status} />
      </div>
      <span className="shrink-0 font-mono text-[11px] tabular-nums text-chrome-400">
        {done}/{total || "—"} steps
      </span>
    </div>
  );
}

function StatusChip({ status }: { status: PhaseStatus | WorkflowStep["status"] }) {
  const styles: Record<string, string> = {
    completed: "bg-emerald-50 text-emerald-700",
    running: "bg-accent-muted text-accent",
    planning: "bg-accent-muted text-accent",
    skipped: "bg-chrome-100 text-chrome-500",
    pending: "bg-chrome-50 text-chrome-400",
    idle: "bg-chrome-50 text-chrome-400",
  };
  const label =
    status === "planning"
      ? "planning"
      : status === "running"
        ? "running"
        : status === "completed"
          ? "done"
          : status === "skipped"
            ? "skipped"
            : "queued";
  return (
    <span
      className={cn(
        "rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide",
        styles[status] ?? styles.pending,
        (status === "running" || status === "planning") && "animate-pulse"
      )}
    >
      {label}
    </span>
  );
}

/* ─── Step rows ────────────────────────────────────────────────── */

function StepRow({ step, isLast }: { step: WorkflowStep; isLast: boolean }) {
  const status = step.status;
  const running = status === "running";
  const completed = status === "completed";
  const skipped = status === "skipped";
  const pending = status === "pending";

  return (
    <div
      className={cn(
        "group flex gap-3 py-2 transition-opacity",
        pending && "opacity-35",
        skipped && "opacity-70"
      )}
    >
      <div className="flex flex-col items-center">
        <div
          className={cn(
            "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2",
            completed && "border-emerald-200 bg-emerald-500 text-white",
            running && "border-accent bg-accent text-accent-foreground",
            skipped && "border-chrome-200 bg-chrome-200 text-chrome-500",
            pending && "border-chrome-100 bg-chrome-50 text-chrome-300"
          )}
        >
          {running ? (
            <Loader2 className="h-3 w-3 animate-spin" strokeWidth={2.5} />
          ) : completed ? (
            <Check className="h-3 w-3" strokeWidth={2.5} />
          ) : skipped ? (
            <Minus className="h-3 w-3" strokeWidth={2.5} />
          ) : (
            <span className="h-1.5 w-1.5 rounded-full bg-chrome-300" />
          )}
        </div>
        {!isLast && (
          <div
            className={cn(
              "w-0.5 flex-1 min-h-[1.25rem]",
              completed && "bg-emerald-200",
              running && "bg-accent/30",
              (skipped || pending) && "bg-chrome-100"
            )}
          />
        )}
      </div>

      <div className="min-w-0 flex-1 pb-1">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 flex-wrap items-center gap-1.5">
            <span
              className={cn(
                "text-[13px] font-semibold",
                completed && "text-chrome-800",
                running && "text-accent",
                skipped && "text-chrome-400",
                pending && "text-chrome-300"
              )}
            >
              <span className="font-mono text-[11px] tabular-nums text-chrome-400">
                #{step.step}
              </span>{" "}
              {skillLabel(step)}
            </span>
            <StatusChip status={status} />
            {isSimulatedStep(step) && (
              <span
                className="rounded border border-chrome-200 bg-chrome-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-chrome-500"
                title="Uses simulated / mock vendor data"
              >
                simulated
              </span>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            {step.duration_ms > 0 && (completed || skipped) && (
              <span className="font-mono text-[11px] tabular-nums text-chrome-400">
                {step.duration_ms}ms
              </span>
            )}
            {step.workspace_link && completed && (
              <Link
                href={step.workspace_link}
                title="Open agent workspace"
                className="rounded p-0.5 text-chrome-300 opacity-0 transition-opacity hover:bg-accent-muted hover:text-accent group-hover:opacity-100"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </Link>
            )}
          </div>
        </div>

        {!pending && step.output && (
          <p
            className={cn(
              "mt-0.5 text-[12.5px] leading-snug",
              skipped ? "italic text-chrome-400" : "text-chrome-600",
              running && "text-chrome-700"
            )}
          >
            {step.output}
          </p>
        )}
      </div>
    </div>
  );
}

function PendingRow({ agent, skill }: { agent: string; skill: string }) {
  return (
    <div className="flex gap-3 py-2">
      <div className="flex flex-col items-center">
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-accent bg-accent text-accent-foreground">
          <Loader2 className="h-3 w-3 animate-spin" strokeWidth={2.5} />
        </div>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[13px] font-semibold text-accent">
            {shortAgentName(agent)} · {skill}
          </span>
          <StatusChip status="running" />
        </div>
        <p className="mt-0.5 text-[12.5px] text-chrome-500">running…</p>
      </div>
    </div>
  );
}
