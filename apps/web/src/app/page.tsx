"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Play,
  Bot,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { api, type Alert, type Stats } from "@/lib/api";

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  clear: "bg-emerald-100 text-emerald-700",
  review: "bg-amber-100 text-amber-700",
  escalate_pending: "bg-purple-100 text-purple-700",
  escalate: "bg-red-100 text-red-700",
};

const RISK_BADGE: Record<string, string> = {
  low: "text-emerald-600",
  medium: "text-amber-600",
  high: "text-red-600",
};

export default function QueuePage() {
  const router = useRouter();
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

  useEffect(() => { load(); }, []);

  const filtered = alerts
    .filter((a) => (statusFilter === "all" ? true : a.status === statusFilter))
    .filter((a) =>
      assigneeFilter.trim()
        ? String(a.assigned_to || "").toLowerCase().includes(assigneeFilter.trim().toLowerCase())
        : true
    )
    .sort((a, b) => (b.kyt_score ?? 0) - (a.kyt_score ?? 0));

  const handleTriageAll = async () => {
    setTriaging(true);
    try {
      await api.triageAll();
      await load();
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
      router.push("/cases/ALT-3002");
    } catch {
      setDemoStep("Demo failed — ensure API is running on port 8000");
    } finally {
      setDemoRunning(false);
    }
  };

  return (
    <AppShell>
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Alert Queue</h2>
            <p className="text-sm text-gray-500">KYT & AML alerts awaiting agent triage</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDemoMode}
              disabled={demoRunning || triaging}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              {demoRunning ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              Demo Mode
            </button>
            <button
              onClick={handleTriageAll}
              disabled={triaging || demoRunning}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              <Bot className="h-4 w-4" />
              {triaging ? "Triaging..." : "Run RAG Agent on All Pending"}
            </button>
          </div>
        </div>

        {demoRunning && demoStep && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3">
            <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
            <p className="text-sm text-indigo-800">{demoStep}</p>
          </div>
        )}

        {stats && (
          <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-5">
            {[
              { label: "Total Alerts", value: stats.total_alerts },
              { label: "Pending", value: stats.pending },
              { label: "Auto-Cleared", value: stats.cleared },
              { label: "Escalated", value: stats.escalated },
              { label: "Auto-Clear Rate", value: `${stats.auto_clear_rate}%` },
            ].map((s) => (
              <div key={s.label} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                <p className="text-2xl font-bold text-gray-900">{s.value}</p>
                <p className="text-xs uppercase tracking-wide text-gray-500">{s.label}</p>
              </div>
            ))}
          </div>
        )}

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700"
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
            className="w-60 rounded-lg border border-gray-200 px-3 py-2 text-sm"
          />
          <button
            onClick={() => {
              setStatusFilter("all");
              setAssigneeFilter("");
            }}
            className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Reset filters
          </button>
          <span className="ml-auto text-xs text-gray-500">
            Showing <span className="font-medium text-gray-700">{filtered.length}</span> alerts
          </span>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Alert ID</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Customer</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Transaction</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">KYT</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Risk</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Assigned</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
              ) : filtered.map((a) => (
                <tr key={a.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{a.id}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{a.customer_name}</td>
                  <td className="px-4 py-3 text-gray-700">
                    {a.direction} ${a.amount_usd.toLocaleString()} {a.asset}
                  </td>
                  <td className="px-4 py-3">{a.kyt_score}</td>
                  <td className={`px-4 py-3 font-medium capitalize ${RISK_BADGE[a.risk_level]}`}>
                    {a.risk_level}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[a.status] || STATUS_BADGE.pending}`}>
                      {a.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600">{a.assigned_to || "—"}</td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/cases/${a.id}`}
                      className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 font-medium"
                    >
                      Investigate
                      <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}
