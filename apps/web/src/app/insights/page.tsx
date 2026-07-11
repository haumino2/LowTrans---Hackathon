"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ChevronRight,
  AlertTriangle,
  Users,
  ArrowLeftRight,
  CheckCircle2,
  Clock,
  BarChart3,
} from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { StatCard } from "@/components/ui/StatCard";
import { StatGridSkeleton, Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { api, type ActivityItem, type InsightsData } from "@/lib/api";

export default function InsightsPage() {
  const [insights, setInsights] = useState<InsightsData | null>(null);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getInsights(), api.getActivities()])
      .then(([i, a]) => {
        setInsights(i);
        setActivities(a);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell>
      <ErrorBoundary fallbackTitle="Insights failed to render">
        <div className="p-6">
          <SectionHeader
            title="Risk Insights"
            description="Portfolio overview across VASP partners"
          />

          {loading && (
            <>
              <StatGridSkeleton count={4} />
              <div className="mb-8 grid gap-4 md:grid-cols-2">
                {[1, 2].map((i) => (
                  <div key={i} className="rounded-lg border border-chrome-200 bg-white p-5 shadow-sm">
                    <Skeleton className="mb-3 h-5 w-40" />
                    <Skeleton className="h-4 w-24" />
                    <div className="mt-4 grid grid-cols-3 gap-3">
                      <Skeleton className="h-8 w-full" />
                      <Skeleton className="h-8 w-full" />
                      <Skeleton className="h-8 w-full" />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {!loading && !insights && (
            <EmptyState
              icon={<BarChart3 className="h-5 w-5" aria-hidden />}
              title="No portfolio insights yet"
              description="Connect the API and ensure VASP data is seeded to see partner risk scores and approval rates."
            />
          )}

          {insights && (
            <>
              <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
                <StatCard label="VASP Partners" value={insights.summary.total_vasps} />
                <StatCard label="Needs Attention" value={insights.summary.needs_attention} />
                <StatCard
                  label="Portfolio Approval"
                  value={`${insights.summary.portfolio_approval_rate}%`}
                />
                <StatCard label="Pending Alerts" value={insights.summary.pending_alerts} />
              </div>

              <h3 className="mb-3 text-sm font-semibold text-chrome-900">VASP Portfolio</h3>
              <div className="mb-8 grid gap-4 md:grid-cols-2">
                {insights.vasps.map((vasp) => (
                  <div
                    key={vasp.id}
                    className={`rounded-lg border bg-white p-5 shadow-sm ${
                      vasp.status === "needs_attention"
                        ? "border-risk-review/40"
                        : "border-chrome-200"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-semibold text-chrome-900">{vasp.name}</p>
                        {vasp.status === "needs_attention" ? (
                          <span className="mt-1 inline-flex items-center gap-1 rounded-md bg-risk-review-bg px-2 py-0.5 text-xs font-medium text-risk-review">
                            <AlertTriangle className="h-3 w-3" />
                            Needs Attention
                          </span>
                        ) : (
                          <span className="mt-1 inline-flex items-center gap-1 rounded-md bg-risk-clear-bg px-2 py-0.5 text-xs font-medium text-risk-clear">
                            <CheckCircle2 className="h-3 w-3" />
                            Healthy
                          </span>
                        )}
                      </div>
                      <div className="text-right">
                        <p className="text-xs uppercase tracking-wide text-chrome-500">Risk Score</p>
                        <p
                          className={`text-lg font-bold tabular-nums ${
                            vasp.risk_score > 70
                              ? "text-risk-escalate"
                              : vasp.risk_score > 50
                              ? "text-risk-review"
                              : "text-risk-clear"
                          }`}
                        >
                          {vasp.risk_score}
                        </p>
                      </div>
                    </div>

                    <div className="mt-4 grid grid-cols-3 gap-3">
                      <div>
                        <div className="mb-0.5 flex items-center gap-1 text-chrome-400">
                          <ArrowLeftRight className="h-3 w-3" />
                          <p className="text-xs uppercase tracking-wide">Transactions</p>
                        </div>
                        <p className="text-sm font-medium tabular-nums text-chrome-900">
                          {vasp.transactions_30d.toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <div className="mb-0.5 flex items-center gap-1 text-chrome-400">
                          <Users className="h-3 w-3" />
                          <p className="text-xs uppercase tracking-wide">Users</p>
                        </div>
                        <p className="text-sm font-medium tabular-nums text-chrome-900">
                          {vasp.active_users.toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <div className="mb-0.5 flex items-center gap-1 text-chrome-400">
                          <CheckCircle2 className="h-3 w-3" />
                          <p className="text-xs uppercase tracking-wide">Approval</p>
                        </div>
                        <p className="text-sm font-medium tabular-nums text-chrome-900">
                          {vasp.approval_rate}%
                        </p>
                      </div>
                    </div>

                    {vasp.pending_alerts > 0 && (
                      <p className="mt-3 text-xs text-risk-review">
                        {vasp.pending_alerts} pending alert
                        {vasp.pending_alerts > 1 ? "s" : ""}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}

          <h3 className="mb-3 text-sm font-semibold text-chrome-900">Activities</h3>
          <div className="divide-y divide-chrome-100 overflow-hidden rounded-lg border border-chrome-200 bg-white shadow-sm">
            {!loading && activities.length === 0 ? (
              <EmptyState
                title="No recent activities"
                description="Agent triage and case actions will appear here as they happen."
              />
            ) : loading ? (
              <div className="space-y-3 p-5">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : (
              activities.map((act) => (
                <div
                  key={act.id}
                  className="flex items-center gap-4 px-5 py-3.5 hover:bg-chrome-50"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-chrome-900">{act.title}</p>
                    <p className="mt-0.5 truncate text-xs text-chrome-500">{act.description}</p>
                    <p className="mt-1 text-xs text-chrome-400">{act.agent}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <span className="flex items-center gap-1 text-xs text-chrome-400">
                      <Clock className="h-3 w-3" />
                      {new Date(act.timestamp).toLocaleString()}
                    </span>
                    {act.alert_id && (
                      <Link
                        href={`/cases/${act.alert_id}`}
                        className="text-chrome-400 hover:text-accent"
                        aria-label={`Open alert ${act.alert_id}`}
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Link>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </ErrorBoundary>
    </AppShell>
  );
}
