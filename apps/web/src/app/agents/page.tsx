"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Brain, ExternalLink } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { useAgentFleet } from "@/context/AgentFleetContext";
import { api, type Skill, type SkillAgent } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  ready: "bg-gray-100 text-gray-600",
  "in-build": "bg-amber-100 text-amber-700",
  running: "bg-accent-muted text-accent animate-pulse",
  completed: "bg-emerald-100 text-emerald-700",
};

const SKILL_STYLES: Record<string, string> = {
  idle: "bg-gray-50 text-gray-500 border-gray-200",
  running: "bg-accent-muted text-accent-hover border-accent animate-pulse",
  completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  copilot: "bg-gray-50/80 text-gray-400 border-gray-100",
};

export default function AgentsPage() {
  const { agents, runningSkillId, completedSkillIds } = useAgentFleet();
  const [registry, setRegistry] = useState<{ agents: SkillAgent[]; skills: Skill[] } | null>(null);

  useEffect(() => {
    api.getSkills().then(setRegistry).catch(() => null);
  }, []);

  const skillById = new Map((registry?.skills ?? []).map((s) => [s.id, s]));

  return (
    <AppShell>
      <div className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Agent Fleet</h2>
            <p className="mt-1 text-sm text-gray-500">
              {registry?.agents.length ?? 4} investigation nodes · Orchestrator → Identity → Investigator → Arbiter
            </p>
          </div>
          <Link
            href="/submit"
            className="rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-accent-hover"
          >
            Submit transaction
          </Link>
        </div>

        <div className="mt-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2">
            <Brain className="h-4 w-4 text-accent" />
            <p className="text-sm font-medium text-gray-900">4-node graph + skill tools</p>
          </div>
          <p className="mt-1 text-sm text-gray-600">
            Supervisor routes Identity / Investigator / Arbiter. {registry?.skills.length ?? 0} skills
            available · agent loop with Bedrock tools + deterministic fallback.
            {runningSkillId ? (
              <span className="ml-1 font-medium text-accent">Running: {runningSkillId}</span>
            ) : null}
          </p>
          <p className="mt-2 text-xs text-gray-500">
            triage = chạy mỗi điều tra · copilot = gọi theo yêu cầu
          </p>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {(registry?.agents ?? []).map((agent) => {
            const fleet = agents.find((a) => a.name === agent.name);
            const href = agent.workspace ?? "/cases/ALT-3002";
            const status =
              fleet?.status === "running" || fleet?.status === "planning"
                ? "running"
                : fleet?.status === "completed"
                ? "completed"
                : (agent.capabilities ?? []).includes("api")
                ? "ready"
                : "in-build";
            return (
              <div
                key={agent.id}
                className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
                      v{agent.version ?? "3.0"} · {agent.id}
                    </p>
                    <h3 className="mt-1 font-semibold text-gray-900">{agent.name}</h3>
                  </div>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                      STATUS_STYLES[status]
                    }`}
                  >
                    {fleet?.status === "planning" ? "planning" : status}
                  </span>
                </div>
                <p className="mt-2 text-sm text-gray-600 line-clamp-3">{agent.description}</p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {(agent.skills ?? []).map((sid) => {
                    const meta = skillById.get(sid);
                    const mode = meta?.mode ?? "copilot";
                    const isConditional = !!meta?.conditional;
                    const isLive =
                      runningSkillId === sid || completedSkillIds.includes(sid);
                    const skillStatus =
                      runningSkillId === sid
                        ? "running"
                        : completedSkillIds.includes(sid)
                        ? "completed"
                        : mode === "copilot"
                        ? "copilot"
                        : "idle";
                    const label = isConditional
                      ? `${sid} · conditional`
                      : mode === "copilot"
                      ? `${sid} · via Copilot`
                      : sid;
                    return (
                      <span
                        key={sid}
                        className={`rounded border px-1.5 py-0.5 text-[11px] font-medium ${
                          SKILL_STYLES[skillStatus]
                        } ${
                          mode === "triage" && !isLive
                            ? "border-chrome-300 text-chrome-700"
                            : ""
                        } ${isLive ? "ring-1 ring-accent/40" : ""}`}
                      >
                        {label}
                      </span>
                    );
                  })}
                </div>
                <Link
                  href={href}
                  className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
                >
                  Open workspace <ExternalLink className="h-3 w-3" />
                </Link>
              </div>
            );
          })}
        </div>
      </div>
    </AppShell>
  );
}
