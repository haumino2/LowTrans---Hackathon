"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

export type AgentStatus = "idle" | "running" | "completed";

export interface AgentState {
  name: string;
  status: AgentStatus;
  lastRun?: string;
}

const DEFAULT_AGENTS = [
  "Transaction Monitoring Agent",
  "Sanctions Screening Agent",
  "Doc KYC Agent",
  "Graph Analyst Agent",
  "Data Analyst Agent",
  "OSINT Search Agent",
  "Business Due Diligence Agent",
  "Rule Assistant Agent",
  "SAR Filing Agent",
  "PEP Screening Agent",
];

interface AgentFleetContextValue {
  agents: AgentState[];
  setAgentRunning: (name: string) => void;
  setAgentCompleted: (name: string) => void;
  setAgentsIdle: () => void;
  syncFromWorkflow: (agentNames: string[], running?: string) => void;
}

const AgentFleetContext = createContext<AgentFleetContextValue | null>(null);

export function AgentFleetProvider({ children }: { children: ReactNode }) {
  const [agents, setAgents] = useState<AgentState[]>(
    DEFAULT_AGENTS.map((name) => ({ name, status: "idle" as AgentStatus }))
  );

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
  }, []);

  const syncFromWorkflow = useCallback((agentNames: string[], running?: string) => {
    setAgents((prev) =>
      prev.map((a) => {
        if (a.name === running) return { ...a, status: "running" as AgentStatus };
        if (agentNames.includes(a.name)) {
          return { ...a, status: "completed" as AgentStatus, lastRun: new Date().toISOString() };
        }
        return a;
      })
    );
  }, []);

  return (
    <AgentFleetContext.Provider
      value={{ agents, setAgentRunning, setAgentCompleted, setAgentsIdle, syncFromWorkflow }}
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
