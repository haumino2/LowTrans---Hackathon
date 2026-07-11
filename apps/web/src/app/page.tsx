"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Play, Bot, Loader2 } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { Button } from "@/components/ui/Button";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { StatCard } from "@/components/ui/StatCard";
import { StatGridSkeleton } from "@/components/ui/Skeleton";
import { AlertQueueTable } from "@/components/ui/AlertQueueTable";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { useToast } from "@/components/ui/Toast";
import { api, type Alert, type Stats } from "@/lib/api";

export default function QueuePage() {
  const router = useRouter();
  const { success, error: toastError } = useToast();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [triaging, setTriaging] = useState(false);
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoStep, setDemoStep] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [assigneeFilter, setAssigneeFilter] = useState<string>("");

  const load = async () => {
    try {
      const [a, s] = await Promise.all([api.getAlerts(), api.getStats()]);
      setAlerts(a);
      setStats(s);
    } catch {
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = alerts
    .filter((a) => (statusFilter === "all" ? true : a.status === statusFilter))
    .filter((a) =>
      assigneeFilter.trim()
        ? String(a.assigned_to || "")
            .toLowerCase()
            .includes(assigneeFilter.trim().toLowerCase())
        : true
    );

  const hasActiveFilters = statusFilter !== "all" || !!assigneeFilter.trim();

  const resetFilters = () => {
    setStatusFilter("all");
    setAssigneeFilter("");
  };

  const handleTriageAll = async () => {
    setTriaging(true);
    try {
      await api.triageAll();
      await load();
      success("Triage complete for pending alerts");
    } catch (e) {
      toastError(e instanceof Error ? e.message : "Triage failed");
    } finally {
      setTriaging(false);
    }
  };

  const handleDemoMode = async () => {
    setDemoRunning(true);
    try {
      setDemoStep("Resetting alerts...");
      await api.demoReset();
      await load();

      setDemoStep("Running agent workflow on ALT-3003 (Elena Vasquez)...");
      await api.triage("ALT-3003");
      await load();

      setDemoStep("Navigating to ALT-3002 (Brooke Ramirez)...");
      await new Promise((r) => setTimeout(r, 800));
      success("Demo mode ready — opening ALT-3002");
      router.push("/cases/ALT-3002");
    } catch {
      setDemoStep("Demo failed — ensure API is running on port 8000");
      toastError("Demo failed — ensure API is running on port 8000");
    } finally {
      setDemoRunning(false);
    }
  };

  return (
    <AppShell>
      <ErrorBoundary fallbackTitle="Alert queue failed to render">
        <div className="p-6">
          <SectionHeader
            title="Alert Queue"
            description="KYT & AML alerts awaiting agent triage"
            actions={
              <>
                <Button
                  variant="secondary"
                  onClick={handleDemoMode}
                  disabled={demoRunning || triaging}
                  aria-label="Run demo mode"
                >
                  {demoRunning ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  ) : (
                    <Play className="h-4 w-4" aria-hidden />
                  )}
                  Demo Mode
                </Button>
                <Button
                  onClick={handleTriageAll}
                  disabled={triaging || demoRunning}
                  aria-label="Run RAG agent on all pending alerts"
                >
                  <Bot className="h-4 w-4" aria-hidden />
                  {triaging ? "Triaging..." : "Run RAG Agent on All Pending"}
                </Button>
              </>
            }
          />

          {demoRunning && demoStep && (
            <div className="mb-4 flex items-center gap-2 rounded-lg border border-chrome-200 bg-accent-muted px-4 py-3">
              <Loader2 className="h-4 w-4 animate-spin text-accent" aria-hidden />
              <p className="text-sm text-chrome-800">{demoStep}</p>
            </div>
          )}

          {loading && !stats ? (
            <StatGridSkeleton />
          ) : stats ? (
            <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-5">
              <StatCard label="Total Alerts" value={stats.total_alerts} />
              <StatCard label="Pending" value={stats.pending} />
              <StatCard label="Auto-Cleared" value={stats.cleared} />
              <StatCard label="Escalated" value={stats.escalated} />
              <StatCard label="Auto-Clear Rate" value={`${stats.auto_clear_rate}%`} />
            </div>
          ) : null}

          <div className="mb-4 flex flex-wrap items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-md border border-chrome-200 bg-white px-3 py-2 text-sm text-chrome-700"
              aria-label="Filter by status"
            >
              <option value="all">All statuses</option>
              <option value="pending">pending</option>
              <option value="clear">clear</option>
              <option value="review">review</option>
              <option value="escalate_pending">escalate_pending</option>
              <option value="escalate">escalate</option>
            </select>
            <input
              value={assigneeFilter}
              onChange={(e) => setAssigneeFilter(e.target.value)}
              placeholder="Filter by assignee..."
              className="w-60 rounded-md border border-chrome-200 px-3 py-2 text-sm"
              aria-label="Filter by assignee"
            />
            <Button variant="secondary" size="sm" onClick={resetFilters}>
              Reset filters
            </Button>
            <span className="ml-auto text-xs text-chrome-500">
              <span className="font-medium tabular-nums text-chrome-700">
                {filtered.length}
              </span>{" "}
              alerts
              {hasActiveFilters ? " matching filters" : ""}
            </span>
          </div>

          <AlertQueueTable
            alerts={filtered}
            loading={loading}
            hasActiveFilters={hasActiveFilters}
            onResetFilters={resetFilters}
          />
        </div>
      </ErrorBoundary>
    </AppShell>
  );
}
