"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell/AppShell";
import { RiskBadge, StatusBadge } from "@/components/ui/Badge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { api, type CaseSummary } from "@/lib/api";

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
      <ErrorBoundary fallbackTitle="Cases failed to render">
      <div className="p-6">
        <SectionHeader
          title="Cases"
          description="Case-centric queue grouped by customer"
          actions={
            <Button variant="secondary" size="sm" onClick={load}>
              Refresh
            </Button>
          }
        />

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search (case id, customer, partner)..."
            className="w-80 rounded-md border border-chrome-200 px-3 py-2 text-sm"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border border-chrome-200 bg-white px-3 py-2 text-sm text-chrome-700"
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
            className="rounded-md border border-chrome-200 bg-white px-3 py-2 text-sm text-chrome-700"
          >
            <option value="all">All states</option>
            <option value="new">new</option>
            <option value="investigating">investigating</option>
            <option value="waiting_info">waiting_info</option>
            <option value="resolved">resolved</option>
          </select>
          <span className="ml-auto text-xs text-chrome-500">
            Showing <span className="font-medium tabular-nums text-chrome-700">{filtered.length}</span> cases
          </span>
        </div>

        <div className="overflow-hidden rounded-lg border border-chrome-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="border-b border-chrome-200 bg-chrome-50">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">Case</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">Customer</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">Partner</th>
                <th className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-chrome-500">Max KYT</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">Risk</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">Status</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">State</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">Assigned</th>
                <th className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-chrome-500">Alerts</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={9} className="p-0">
                    <TableSkeleton rows={6} cols={6} />
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={9}>
                    <EmptyState
                      title="No cases match"
                      description="Adjust filters or search, or open the alert queue to investigate new alerts."
                    />
                  </td>
                </tr>
              ) : (
                filtered.map((c) => (
                  <tr key={c.case_id} className="h-10 border-b border-chrome-100 hover:bg-chrome-50">
                    <td className="px-4 py-2">
                      <Link href={`/case/${c.case_id}`} className="mono text-xs font-medium text-accent hover:text-accent-hover">
                        {c.case_id}
                      </Link>
                    </td>
                    <td className="px-4 py-2 font-medium text-chrome-900">{c.customer_name}</td>
                    <td className="px-4 py-2 text-chrome-700">{c.partner}</td>
                    <td className="num px-4 py-2 text-right tabular-nums">{c.max_kyt}</td>
                    <td className="px-4 py-2">
                      <RiskBadge level={c.risk_level} />
                    </td>
                    <td className="px-4 py-2">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="px-4 py-2 text-xs text-chrome-700">{c.state}</td>
                    <td className="px-4 py-2 text-xs text-chrome-600">{c.assigned_to || "—"}</td>
                    <td className="num px-4 py-2 text-right text-xs tabular-nums text-chrome-600">{c.alerts_count}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      </ErrorBoundary>
    </AppShell>
  );
}


