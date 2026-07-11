"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronRight,
  ChevronLeft,
  Filter,
} from "lucide-react";
import { RiskBadge, StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { cn } from "@/lib/cn";
import type { Alert } from "@/lib/api";

type SortKey = "kyt_score" | "amount_usd" | "risk_level" | "created_at";
type SortDir = "asc" | "desc";

const RISK_RANK: Record<string, number> = { low: 1, medium: 2, high: 3 };
const PAGE_SIZE = 25;

interface AlertQueueTableProps {
  alerts: Alert[];
  loading?: boolean;
  onResetFilters?: () => void;
  hasActiveFilters?: boolean;
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <ArrowUpDown className="h-3 w-3 text-chrome-400" aria-hidden />;
  return dir === "asc" ? (
    <ArrowUp className="h-3 w-3 text-accent" aria-hidden />
  ) : (
    <ArrowDown className="h-3 w-3 text-accent" aria-hidden />
  );
}

export function AlertQueueTable({
  alerts,
  loading,
  onResetFilters,
  hasActiveFilters,
}: AlertQueueTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("kyt_score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const sorted = useMemo(() => {
    const list = [...alerts];
    list.sort((a, b) => {
      let cmp = 0;
      if (sortKey === "kyt_score") cmp = (a.kyt_score ?? 0) - (b.kyt_score ?? 0);
      else if (sortKey === "amount_usd") cmp = (a.amount_usd ?? 0) - (b.amount_usd ?? 0);
      else if (sortKey === "risk_level")
        cmp = (RISK_RANK[a.risk_level] ?? 0) - (RISK_RANK[b.risk_level] ?? 0);
      else cmp = String(a.created_at || "").localeCompare(String(b.created_at || ""));
      return sortDir === "asc" ? cmp : -cmp;
    });
    return list;
  }, [alerts, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));

  useEffect(() => {
    setPage(1);
  }, [alerts, sortKey, sortDir]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  const pageRows = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return sorted.slice(start, start + PAGE_SIZE);
  }, [sorted, page]);

  const rangeStart = sorted.length === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const rangeEnd = Math.min(page * PAGE_SIZE, sorted.length);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const thSort = (key: SortKey, label: string, align: "left" | "right" = "left") => (
    <th
      className={cn(
        "sticky top-0 z-10 bg-chrome-50 px-3 py-2.5 text-xs font-medium uppercase tracking-wide text-chrome-500",
        align === "right" ? "text-right" : "text-left"
      )}
      scope="col"
    >
      <button
        type="button"
        onClick={() => toggleSort(key)}
        className={cn(
          "inline-flex items-center gap-1 rounded-md hover:text-chrome-800",
          align === "right" && "flex-row-reverse"
        )}
        aria-label={`Sort by ${label}`}
      >
        {label}
        <SortIcon active={sortKey === key} dir={sortDir} />
      </button>
    </th>
  );

  return (
    <div className="overflow-hidden rounded-lg border border-chrome-200 bg-white shadow-sm">
      <div className="max-h-[calc(100vh-22rem)] overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-chrome-200">
              <th className="sticky top-0 z-10 bg-chrome-50 px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">
                Alert ID
              </th>
              <th className="sticky top-0 z-10 bg-chrome-50 px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">
                Customer
              </th>
              <th className="sticky top-0 z-10 bg-chrome-50 px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">
                Wallet
              </th>
              {thSort("amount_usd", "Amount", "right")}
              {thSort("kyt_score", "KYT", "right")}
              {thSort("risk_level", "Risk")}
              <th className="sticky top-0 z-10 bg-chrome-50 px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">
                Status
              </th>
              <th className="sticky top-0 z-10 bg-chrome-50 px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">
                Assigned
              </th>
              {thSort("created_at", "Created")}
              <th className="sticky top-0 z-10 bg-chrome-50 px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">
                Action
              </th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={10} className="p-0">
                  <TableSkeleton rows={8} cols={6} />
                </td>
              </tr>
            ) : sorted.length === 0 ? (
              <tr>
                <td colSpan={10}>
                  <EmptyState
                    icon={<Filter className="h-5 w-5" aria-hidden />}
                    title={hasActiveFilters ? "No alerts match filters" : "No alerts in queue"}
                    description={
                      hasActiveFilters
                        ? "Try clearing status or assignee filters to see more results."
                        : "New KYT alerts will appear here when the API is connected."
                    }
                    action={
                      hasActiveFilters && onResetFilters
                        ? { label: "Reset filters", onClick: onResetFilters }
                        : undefined
                    }
                  />
                </td>
              </tr>
            ) : (
              pageRows.map((a) => {
                const selected = selectedId === a.id;
                return (
                  <tr
                    key={a.id}
                    onClick={() => setSelectedId(a.id)}
                    className={cn(
                      "h-10 border-b border-chrome-100 transition-colors",
                      selected ? "bg-accent-muted" : "hover:bg-chrome-50"
                    )}
                  >
                    <td className="px-3 py-2">
                      <span className="mono text-xs text-chrome-800">{a.id}</span>
                    </td>
                    <td className="px-3 py-2 font-medium text-chrome-900">
                      {a.customer_name}
                    </td>
                    <td className="px-3 py-2">
                      <span className="mono text-xs text-chrome-600" title={a.wallet_address}>
                        {a.wallet_address
                          ? `${a.wallet_address.slice(0, 6)}…${a.wallet_address.slice(-4)}`
                          : "—"}
                      </span>
                    </td>
                    <td className="num px-3 py-2 text-right tabular-nums text-chrome-800">
                      <span className="text-chrome-500">{a.direction}</span>{" "}
                      ${a.amount_usd.toLocaleString()}{" "}
                      <span className="text-chrome-500">{a.asset}</span>
                    </td>
                    <td className="num px-3 py-2 text-right tabular-nums font-medium text-chrome-900">
                      {a.kyt_score}
                    </td>
                    <td className="px-3 py-2">
                      <RiskBadge level={a.risk_level} />
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={a.status} />
                    </td>
                    <td className="px-3 py-2 text-xs text-chrome-600">
                      {a.assigned_to || "—"}
                    </td>
                    <td className="px-3 py-2 text-xs tabular-nums text-chrome-500">
                      {a.created_at
                        ? new Date(a.created_at).toLocaleDateString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "—"}
                    </td>
                    <td className="px-3 py-2">
                      <Link
                        href={`/cases/${a.id}`}
                        className="inline-flex items-center gap-1 font-medium text-accent hover:text-accent-hover"
                        onClick={(e) => e.stopPropagation()}
                      >
                        Investigate
                        <ChevronRight className="h-3.5 w-3.5" aria-hidden />
                      </Link>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {!loading && sorted.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-chrome-200 bg-chrome-50 px-3 py-2.5">
          <p className="text-xs text-chrome-500">
            Showing{" "}
            <span className="font-medium tabular-nums text-chrome-700">
              {rangeStart}–{rangeEnd}
            </span>{" "}
            of{" "}
            <span className="font-medium tabular-nums text-chrome-700">
              {sorted.length}
            </span>
            <span className="text-chrome-400"> · {PAGE_SIZE}/page</span>
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="inline-flex items-center gap-1 rounded-md border border-chrome-200 bg-white px-2.5 py-1.5 text-xs font-medium text-chrome-700 hover:bg-chrome-50 disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="Previous page"
            >
              <ChevronLeft className="h-3.5 w-3.5" aria-hidden />
              Prev
            </button>
            <span className="text-xs tabular-nums text-chrome-600">
              Page {page} / {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="inline-flex items-center gap-1 rounded-md border border-chrome-200 bg-white px-2.5 py-1.5 text-xs font-medium text-chrome-700 hover:bg-chrome-50 disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="Next page"
            >
              Next
              <ChevronRight className="h-3.5 w-3.5" aria-hidden />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
