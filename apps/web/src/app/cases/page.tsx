"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell/AppShell";
import { api, type CaseSummary } from "@/lib/api";

const RISK_BADGE: Record<string, string> = {
  low: "text-emerald-600",
  medium: "text-amber-600",
  high: "text-red-600",
};

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  clear: "bg-emerald-100 text-emerald-700",
  review: "bg-amber-100 text-amber-700",
  escalate_pending: "bg-purple-100 text-purple-700",
  escalate: "bg-red-100 text-red-700",
};

export default function CaseQueuePage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [stateFilter, setStateFilter] = useState("all");
  const [q, setQ] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const c = await api.getCases();
      setCases(c);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const qq = q.trim().toLowerCase();
    return cases
      .filter((c) => (statusFilter === "all" ? true : c.status === statusFilter))
      .filter((c) => (stateFilter === "all" ? true : c.state === stateFilter))
      .filter((c) =>
        qq
          ? `${c.case_id} ${c.customer_name} ${c.customer_id} ${c.partner}`.toLowerCase().includes(qq)
          : true
      )
      .sort((a, b) => (b.max_kyt ?? 0) - (a.max_kyt ?? 0));
  }, [cases, q, statusFilter, stateFilter]);

  return (
    <AppShell>
      <div className="p-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Cases</h2>
            <p className="text-sm text-gray-500">Case-centric queue grouped by customer</p>
          </div>
          <button
            onClick={load}
            className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Refresh
          </button>
        </div>

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search (case id, customer, partner)..."
            className="w-80 rounded-lg border border-gray-200 px-3 py-2 text-sm"
          />
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
          <select
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
            className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700"
          >
            <option value="all">All states</option>
            <option value="new">new</option>
            <option value="investigating">investigating</option>
            <option value="waiting_info">waiting_info</option>
            <option value="resolved">resolved</option>
          </select>
          <span className="ml-auto text-xs text-gray-500">
            Showing <span className="font-medium text-gray-700">{filtered.length}</span> cases
          </span>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Case</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Customer</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Partner</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Max KYT</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Risk</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">State</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Assigned</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Alerts</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-gray-400">
                    Loading...
                  </td>
                </tr>
              ) : (
                filtered.map((c) => (
                  <tr key={c.case_id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs">
                      <Link href={`/case/${c.case_id}`} className="text-indigo-600 hover:text-indigo-800 font-medium">
                        {c.case_id}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-900">{c.customer_name}</td>
                    <td className="px-4 py-3 text-gray-700">{c.partner}</td>
                    <td className="px-4 py-3">{c.max_kyt}</td>
                    <td className={`px-4 py-3 font-medium capitalize ${RISK_BADGE[c.risk_level] || ""}`}>
                      {c.risk_level}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[c.status] || STATUS_BADGE.pending}`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-700">{c.state}</td>
                    <td className="px-4 py-3 text-xs text-gray-600">{c.assigned_to || "—"}</td>
                    <td className="px-4 py-3 text-xs text-gray-600">{c.alerts_count}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}

