"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

export type AgentStatus = "idle" | "running" | "completed";

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
];

interface AgentFleetContextValue {
  agents: AgentState[];
  runningSkillId: string | null;
  completedSkillIds: string[];
  setAgentRunning: (name: string) => void;
  setAgentCompleted: (name: string) => void;
  setAgentsIdle: () => void;
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

  const setAgentRunning = useCallback((name: string) => {
    setAgents((prev) =>
      prev.map((a) =>
        a.name === name ? { ...a, status: "running" as AgentStatus } : a
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
  }, []);

  const syncFromWorkflow = useCallback(
    (
      agentNames: string[],
      running?: string,
      skillRunning?: string | null,
      skillsDone?: string[]
    ) => {
      setAgents((prev) =>
        prev.map((a) => {
          if (a.name === running) return { ...a, status: "running" as AgentStatus };
          if (agentNames.includes(a.name)) {
            return { ...a, status: "completed" as AgentStatus, lastRun: new Date().toISOString() };
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
        setAgentRunning,
        setAgentCompleted,
        setAgentsIdle,
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
