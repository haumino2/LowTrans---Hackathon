"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Button } from "@/components/ui/Button";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { useToast } from "@/components/ui/Toast";
import { api, type Alert } from "@/lib/api";

export default function ApprovalsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { success, error: toastError } = useToast();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const a = await api.getApprovals();
      setAlerts(a);
    } catch (e) {
      setAlerts([]);
      setError(e instanceof Error ? e.message : "Failed to load approvals");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const sorted = useMemo(() => {
    return [...alerts].sort((a, b) => (b.kyt_score ?? 0) - (a.kyt_score ?? 0));
  }, [alerts]);

  return (
    <AppShell>
      <ErrorBoundary fallbackTitle="Approvals failed to render">
        <div className="p-6">
          <SectionHeader
            title="Supervisor Approvals"
            description="Cases pending ESCALATE approval"
            actions={
              <Button variant="secondary" size="sm" onClick={load}>
                Refresh
              </Button>
            }
          />

          {error && (
            <div className="mb-4 rounded-lg border border-risk-escalate/30 bg-risk-escalate-bg px-4 py-3 text-sm text-risk-escalate">
              {error}
            </div>
          )}

          <div className="overflow-hidden rounded-lg border border-chrome-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="border-b border-chrome-200 bg-chrome-50">
                <tr>
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">
                    Alert
                  </th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">
                    Customer
                  </th>
                  <th className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-chrome-500">
                    KYT
                  </th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">
                    Assigned
                  </th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-chrome-500">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={5} className="p-0">
                      <TableSkeleton rows={5} cols={5} />
                    </td>
                  </tr>
                ) : sorted.length === 0 ? (
                  <tr>
                    <td colSpan={5}>
                      <EmptyState
                        title="No approvals pending"
                        description="Escalations awaiting supervisor review will show up here."
                      />
                    </td>
                  </tr>
                ) : (
                  sorted.map((a) => (
                    <tr key={a.id} className="h-10 border-b border-chrome-100 hover:bg-chrome-50">
                      <td className="px-4 py-2">
                        <span className="mono text-xs">{a.id}</span>
                      </td>
                      <td className="px-4 py-2 font-medium text-chrome-900">{a.customer_name}</td>
                      <td className="num px-4 py-2 text-right tabular-nums">{a.kyt_score}</td>
                      <td className="px-4 py-2 text-xs text-chrome-600">
                        {a.assigned_to || "—"}
                      </td>
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-3">
                          <Link
                            href={`/cases/${a.id}`}
                            className="font-medium text-accent hover:text-accent-hover"
                          >
                            Review
                          </Link>
                          <Button
                            size="sm"
                            variant="danger"
                            onClick={async () => {
                              try {
                                await api.approveEscalation(a.id);
                                await load();
                                success(`Approved ${a.id}`);
                              } catch (e) {
                                toastError(
                                  e instanceof Error ? e.message : "Approval failed"
                                );
                              }
                            }}
                          >
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Approve
                          </Button>
                        </div>
                      </td>
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
