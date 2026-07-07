"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Brain, ExternalLink } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { useAgentFleet } from "@/context/AgentFleetContext";
import { api, type Skill, type SkillAgent } from "@/lib/api";

const AGENT_WORKSPACE: Record<string, string> = {
  "aml-copilot": "/agents?focus=aml-copilot",
  "data-analyst": "/agents?focus=data-analyst",
  "transaction-monitoring": "/",
  "sanctions-screening": "/agents?focus=sanctions-screening",
  "graph-analyst": "/",
  "sar-filing": "/",
  "osint-search": "/agents?focus=osint-search",
  "business-due-diligence": "/agents?focus=business-due-diligence",
  "rule-assistant": "/rules",
};

const STATUS_STYLES: Record<string, string> = {
  ready: "bg-gray-100 text-gray-600",
  "in-build": "bg-amber-100 text-amber-700",
  running: "bg-indigo-100 text-indigo-700 animate-pulse",
  completed: "bg-emerald-100 text-emerald-700",
};

export default function AgentsPage() {
  const { agents } = useAgentFleet();
  const [registry, setRegistry] = useState<{ agents: SkillAgent[]; skills: Skill[] } | null>(null);

  useEffect(() => {
    api.getSkills().then(setRegistry).catch(() => null);
  }, []);

  return (
    <AppShell>
      <div className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Agent Fleet</h2>
            <p className="mt-1 text-sm text-gray-500">
              {registry?.agents.length ?? 9} registered agents · 11-step triage pipeline
            </p>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2">
            <Brain className="h-4 w-4 text-indigo-600" />
            <p className="text-sm font-medium text-gray-900">Skill Registry</p>
          </div>
          <p className="mt-1 text-sm text-gray-600">
            Agent → Skills → Tools architecture. {registry?.skills.length ?? 12} skills available.
          </p>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {(registry?.agents ?? []).map((agent) => {
            const fleet = agents.find((a) => a.name === agent.name);
            const href = agent.workspace ?? AGENT_WORKSPACE[agent.id] ?? "/copilot";
            const status =
              fleet?.status === "running"
                ? "running"
                : fleet?.status === "completed"
                ? "completed"
                : (agent.capabilities ?? []).includes("api")
                ? "ready"
                : "in-build";
            return (
              <Link
                key={agent.id}
                href={href}
                className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition hover:border-indigo-200 hover:shadow-md"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
                      v{agent.version ?? "1.0"}
                    </p>
                    <h3 className="mt-1 font-semibold text-gray-900">{agent.name}</h3>
                  </div>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                      STATUS_STYLES[status]
                    }`}
                  >
                    {status}
                  </span>
                </div>
                <p className="mt-2 text-sm text-gray-600 line-clamp-2">{agent.description}</p>
                <p className="mt-2 text-xs text-gray-400">
                  {(agent.capabilities ?? []).join(" · ") || "API"}
                </p>
                <p className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-indigo-600">
                  Open workspace <ExternalLink className="h-3 w-3" />
                </p>
              </Link>
            );
          })}
        </div>
      </div>
    </AppShell>
  );
}
