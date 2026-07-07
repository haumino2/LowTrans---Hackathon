"use client";

import Link from "next/link";
import {
  Inbox,
  Brain,
  BarChart3,
  Shield,
  GitBranch,
  TrendingUp,
  FileText,
  Search,
  Zap,
  FileWarning,
  ScrollText,
  Bot,
  Check,
  Minus,
  Circle,
  ExternalLink,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { WorkflowStep, WorkflowSummary } from "@/lib/api";

const STATUS_CONFIG: Record<
  string,
  { Icon: LucideIcon; dot: string; line: string; label: string }
> = {
  completed: {
    Icon: Check,
    dot: "bg-emerald-500 border-emerald-200",
    line: "bg-emerald-200",
    label: "text-emerald-700",
  },
  running: {
    Icon: Circle,
    dot: "bg-indigo-500 border-indigo-200 animate-pulse",
    line: "bg-indigo-200",
    label: "text-indigo-700",
  },
  skipped: {
    Icon: Minus,
    dot: "bg-gray-300 border-gray-200",
    line: "bg-gray-200",
    label: "text-gray-400",
  },
  pending: {
    Icon: Circle,
    dot: "bg-gray-200 border-gray-100",
    line: "bg-gray-100",
    label: "text-gray-300",
  },
};

const AGENT_ICONS: Record<string, LucideIcon> = {
  "Alert Ingestion": Inbox,
  "RAG Memory": Brain,
  "Transaction Monitoring Agent": BarChart3,
  "Sanctions Screening Agent": Shield,
  "Graph Analyst Agent": GitBranch,
  "Data Analyst Agent": TrendingUp,
  "Doc KYC Agent": FileText,
  "OSINT Search Agent": Search,
  "Decision Orchestrator": Zap,
  "SAR Filing Agent": FileWarning,
  "Audit Logger": ScrollText,
};

interface Props {
  steps: WorkflowStep[];
  allSteps?: WorkflowStep[];
  summary?: WorkflowSummary;
  decision?: string;
  confidence?: number;
  isAnimating?: boolean;
}

export function AgentWorkflowTimeline({
  steps,
  allSteps,
  summary,
  decision,
  confidence,
  isAnimating,
}: Props) {
  const total = allSteps?.length ?? steps.length;
  const completed = steps.filter((s) => s.status === "completed").length;

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm">
      <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-900">Agent Workflow</span>
          {isAnimating && (
            <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 animate-pulse">
              LIVE
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          {summary && (
            <>
              <span>{summary.agents_run} agents run</span>
              <span>·</span>
              <span>{summary.total_duration_ms}ms total</span>
            </>
          )}
          <span className="font-medium text-gray-700">
            {completed}/{total} steps
          </span>
        </div>
      </div>

      {isAnimating && total > 0 && (
        <div className="h-1 bg-gray-100">
          <div
            className="h-full bg-indigo-500 transition-all duration-300 ease-out"
            style={{ width: `${(steps.length / total) * 100}%` }}
          />
        </div>
      )}

      <div className="p-5 space-y-0">
        {steps.length === 0 && !isAnimating && (
          <p className="text-sm text-gray-400 text-center py-6">
            Run agent workflow to see the timeline
          </p>
        )}

        {steps.map((step, idx) => {
          const cfg = STATUS_CONFIG[step.status] ?? STATUS_CONFIG.pending;
          const isLast = idx === steps.length - 1;
          const AgentIcon = AGENT_ICONS[step.agent] ?? Bot;
          const StatusIcon = cfg.Icon;

          return (
            <div key={`${step.step}-${step.agent}`} className="flex gap-4">
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-white ${cfg.dot}`}
                >
                  {step.status === "running" ? (
                    <span className="h-2 w-2 rounded-full bg-white animate-ping" />
                  ) : (
                    <StatusIcon className={`h-3.5 w-3.5 ${step.status === "skipped" ? "text-gray-500" : ""}`} strokeWidth={2.5} />
                  )}
                </div>
                {!isLast && <div className={`w-0.5 flex-1 min-h-[2rem] ${cfg.line}`} />}
              </div>

              <div className={`pb-5 flex-1 ${isLast ? "pb-0" : ""}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AgentIcon className="h-4 w-4 text-gray-400" strokeWidth={1.75} />
                    <span className={`text-sm font-semibold ${cfg.label}`}>
                      Step {step.step} — {step.agent}
                    </span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-xs font-medium uppercase ${
                        step.status === "completed"
                          ? "bg-emerald-50 text-emerald-600"
                          : step.status === "skipped"
                          ? "bg-gray-100 text-gray-400"
                          : step.status === "running"
                          ? "bg-indigo-50 text-indigo-600"
                          : "bg-gray-50 text-gray-400"
                      }`}
                    >
                      {step.status}
                    </span>
                  </div>
                  {step.duration_ms > 0 && (
                    <span className="text-xs text-gray-400 font-mono">{step.duration_ms}ms</span>
                  )}
                </div>

                {step.input && (
                  <p className="mt-1 text-xs text-gray-400 truncate" title={step.input}>
                    IN: {step.input}
                  </p>
                )}
                <p
                  className={`mt-1 text-sm ${
                    step.status === "skipped" ? "text-gray-400 italic" : "text-gray-700"
                  }`}
                >
                  {step.output}
                </p>
                {step.workspace_link && step.status === "completed" && (
                  <Link
                    href={step.workspace_link}
                    className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800"
                  >
                    Open agent workspace
                    <ExternalLink className="h-3 w-3" />
                  </Link>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {decision && !isAnimating && steps.length > 0 && (
        <div
          className={`border-t px-5 py-3 flex items-center justify-between ${
            decision === "CLEAR"
              ? "bg-emerald-50 border-emerald-100"
              : decision === "ESCALATE"
              ? "bg-red-50 border-red-100"
              : "bg-amber-50 border-amber-100"
          }`}
        >
          <span className="text-sm font-bold">
            FINAL DECISION: {decision}
          </span>
          {confidence !== undefined && (
            <span className="text-sm opacity-80">{(confidence * 100).toFixed(0)}% confidence</span>
          )}
        </div>
      )}
    </div>
  );
}
