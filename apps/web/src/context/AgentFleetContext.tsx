"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

export type AgentStatus = "idle" | "planning" | "running" | "completed";

export interface AgentState {
  name: string;
  status: AgentStatus;
  lastRun?: string;
}

/** 4-node investigation graph (must match registry.yaml + supervisor) */
export const DEFAULT_AGENTS = [
  "Orchestrator",
  "Entity Identity Agent",
  "Financial Crime Investigator",
  "Arbiter",
] as const;

export type PipelineAgentName = (typeof DEFAULT_AGENTS)[number];

export const PIPELINE_NODES: {
  name: PipelineAgentName;
  short: string;
}[] = [
  { name: "Orchestrator", short: "Orchestrator" },
  { name: "Entity Identity Agent", short: "Entity Identity" },
  { name: "Financial Crime Investigator", short: "Financial Crime" },
  { name: "Arbiter", short: "Arbiter" },
];

export function shortAgentName(agent: string): string {
  return PIPELINE_NODES.find((n) => n.name === agent)?.short ?? agent;
}

interface AgentFleetContextValue {
  agents: AgentState[];
  runningSkillId: string | null;
  completedSkillIds: string[];
  isPlanning: boolean;
  setAgentRunning: (name: string) => void;
  setAgentCompleted: (name: string) => void;
  setAgentsIdle: () => void;
  setPlanning: (planning: boolean) => void;
  syncFromWorkflow: (
    agentNames: string[],
    running?: string,
    runningSkillId?: string | null,
    completedSkillIds?: string[]
  ) => void;
}

const AgentFleetContext = createContext<AgentFleetContextValue | null>(null);

export function AgentFleetProvider({ children }: { children: ReactNode }) {
  const [agents, setAgents] = useState<AgentState[]>(
    DEFAULT_AGENTS.map((name) => ({ name, status: "idle" as AgentStatus }))
  );
  const [runningSkillId, setRunningSkillId] = useState<string | null>(null);
  const [completedSkillIds, setCompletedSkillIds] = useState<string[]>([]);
  const [isPlanning, setIsPlanning] = useState(false);

  const setAgentRunning = useCallback((name: string) => {
    setIsPlanning(false);
    setAgents((prev) =>
      prev.map((a) =>
        a.name === name
          ? { ...a, status: "running" as AgentStatus }
          : a.status === "running" || a.status === "planning"
            ? { ...a, status: "idle" as AgentStatus }
            : a
      )
    );
  }, []);

  const setAgentCompleted = useCallback((name: string) => {
    setAgents((prev) =>
      prev.map((a) =>
        a.name === name
          ? { ...a, status: "completed" as AgentStatus, lastRun: new Date().toISOString() }
          : a
      )
    );
  }, []);

  const setAgentsIdle = useCallback(() => {
    setAgents(DEFAULT_AGENTS.map((name) => ({ name, status: "idle" as AgentStatus })));
    setRunningSkillId(null);
    setCompletedSkillIds([]);
    setIsPlanning(false);
  }, []);

  const setPlanning = useCallback((planning: boolean) => {
    setIsPlanning(planning);
    if (planning) {
      setAgents((prev) =>
        prev.map((a) =>
          a.name === "Orchestrator"
            ? { ...a, status: "planning" as AgentStatus }
            : { ...a, status: "idle" as AgentStatus }
        )
      );
      setRunningSkillId(null);
    }
  }, []);

  const syncFromWorkflow = useCallback(
    (
      agentNames: string[],
      running?: string,
      skillRunning?: string | null,
      skillsDone?: string[]
    ) => {
      setIsPlanning(false);
      setAgents((prev) =>
        prev.map((a) => {
          if (a.name === running) return { ...a, status: "running" as AgentStatus };
          if (agentNames.includes(a.name)) {
            return { ...a, status: "completed" as AgentStatus, lastRun: new Date().toISOString() };
          }
          // Clear stale running/planning on agents that are neither running nor done
          if (a.status === "running" || a.status === "planning") {
            return { ...a, status: "idle" as AgentStatus };
          }
          return a;
        })
      );
      if (skillRunning !== undefined) {
        setRunningSkillId(skillRunning ?? null);
      }
      if (skillsDone !== undefined) {
        setCompletedSkillIds(skillsDone);
      }
    },
    []
  );

  return (
    <AgentFleetContext.Provider
      value={{
        agents,
        runningSkillId,
        completedSkillIds,
        isPlanning,
        setAgentRunning,
        setAgentCompleted,
        setAgentsIdle,
        setPlanning,
        syncFromWorkflow,
      }}
    >
      {children}
    </AgentFleetContext.Provider>
  );
}

export function useAgentFleet() {
  const ctx = useContext(AgentFleetContext);
  if (!ctx) throw new Error("useAgentFleet must be used within AgentFleetProvider");
  return ctx;
}
