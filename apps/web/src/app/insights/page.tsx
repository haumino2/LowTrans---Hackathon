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
} from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
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
      <div className="p-6">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900">Risk Insights</h2>
          <p className="text-sm text-gray-500">Portfolio overview across VASP partners</p>
        </div>

        {loading && <p className="text-sm text-gray-400">Loading insights...</p>}

        {insights && (
          <>
            <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
              {[
                { label: "VASP Partners", value: insights.summary.total_vasps },
                { label: "Needs Attention", value: insights.summary.needs_attention },
                { label: "Portfolio Approval", value: `${insights.summary.portfolio_approval_rate}%` },
                { label: "Pending Alerts", value: insights.summary.pending_alerts },
              ].map((s) => (
                <div key={s.label} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                  <p className="text-2xl font-bold text-gray-900">{s.value}</p>
                  <p className="text-xs uppercase tracking-wide text-gray-500">{s.label}</p>
                </div>
              ))}
            </div>

            <h3 className="mb-3 text-sm font-semibold text-gray-900">VASP Portfolio</h3>
            <div className="mb-8 grid gap-4 md:grid-cols-2">
              {insights.vasps.map((vasp) => (
                <div
                  key={vasp.id}
                  className={`rounded-xl border bg-white p-5 shadow-sm ${
                    vasp.status === "needs_attention" ? "border-amber-200" : "border-gray-200"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold text-gray-900">{vasp.name}</p>
                      {vasp.status === "needs_attention" ? (
                        <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
                          <AlertTriangle className="h-3 w-3" />
                          Needs Attention
                        </span>
                      ) : (
                        <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
                          <CheckCircle2 className="h-3 w-3" />
                          Healthy
                        </span>
                      )}
                    </div>
                    <div className="text-right">
                      <p className="text-xs uppercase tracking-wide text-gray-500">Risk Score</p>
                      <p className={`text-lg font-bold ${
                        vasp.risk_score > 70 ? "text-red-600" : vasp.risk_score > 50 ? "text-amber-600" : "text-emerald-600"
                      }`}>
                        {vasp.risk_score}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-3 gap-3">
                    <div>
                      <div className="flex items-center gap-1 text-gray-400 mb-0.5">
                        <ArrowLeftRight className="h-3 w-3" />
                        <p className="text-xs uppercase tracking-wide">Transactions</p>
                      </div>
                      <p className="text-sm font-medium text-gray-900">{vasp.transactions_30d.toLocaleString()}</p>
                    </div>
                    <div>
                      <div className="flex items-center gap-1 text-gray-400 mb-0.5">
                        <Users className="h-3 w-3" />
                        <p className="text-xs uppercase tracking-wide">Users</p>
                      </div>
                      <p className="text-sm font-medium text-gray-900">{vasp.active_users.toLocaleString()}</p>
                    </div>
                    <div>
                      <div className="flex items-center gap-1 text-gray-400 mb-0.5">
                        <CheckCircle2 className="h-3 w-3" />
                        <p className="text-xs uppercase tracking-wide">Approval</p>
                      </div>
                      <p className="text-sm font-medium text-gray-900">{vasp.approval_rate}%</p>
                    </div>
                  </div>

                  {vasp.pending_alerts > 0 && (
                    <p className="mt-3 text-xs text-amber-700">
                      {vasp.pending_alerts} pending alert{vasp.pending_alerts > 1 ? "s" : ""}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </>
        )}

        <h3 className="mb-3 text-sm font-semibold text-gray-900">Activities</h3>
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm divide-y divide-gray-100">
          {activities.length === 0 ? (
            <p className="p-6 text-center text-sm text-gray-400">No recent activities</p>
          ) : (
            activities.map((act) => (
              <div key={act.id} className="flex items-center gap-4 px-5 py-3.5 hover:bg-gray-50">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">{act.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5 truncate">{act.description}</p>
                  <p className="text-xs text-gray-400 mt-1">{act.agent}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="flex items-center gap-1 text-xs text-gray-400">
                    <Clock className="h-3 w-3" />
                    {new Date(act.timestamp).toLocaleString()}
                  </span>
                  {act.alert_id && (
                    <Link
                      href={`/cases/${act.alert_id}`}
                      className="text-gray-400 hover:text-indigo-600"
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
    </AppShell>
  );
}
