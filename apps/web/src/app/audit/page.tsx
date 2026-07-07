"use client";

import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { api } from "@/lib/api";

export default function AuditPage() {
  const [entries, setEntries] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    api.getAudit().then(setEntries).catch(() => setEntries([]));
  }, []);

  return (
    <AppShell>
      <div className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Audit Trail</h2>
            <p className="mt-1 text-sm text-gray-500">
              Triage and analyst override events — export for regulatory review
            </p>
          </div>
          <a
            href={api.exportAudit()}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </a>
        </div>

        <div className="mt-6 overflow-hidden rounded-xl border border-gray-200 bg-white">
          {entries.length === 0 ? (
            <p className="p-8 text-center text-gray-400">
              No audit entries yet. Run agent triage or analyst override.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Timestamp</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Type</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Alert</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Customer</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Decision</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Detail</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e, i) => (
                  <tr key={i} className="border-b border-gray-100">
                    <td className="px-4 py-3 font-mono text-xs">{String(e.timestamp).slice(0, 19)}</td>
                    <td className="px-4 py-3 text-xs uppercase text-gray-500">
                      {String(e.event_type ?? "triage")}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">{String(e.alert_id)}</td>
                    <td className="px-4 py-3">{String(e.customer_name)}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-bold ${
                          e.decision === "CLEAR"
                            ? "bg-emerald-100 text-emerald-700"
                            : e.decision === "ESCALATE"
                            ? "bg-red-100 text-red-700"
                            : "bg-amber-100 text-amber-700"
                        }`}
                      >
                        {String(e.decision)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {e.reason
                        ? String(e.reason)
                        : e.confidence
                        ? `${((e.confidence as number) * 100).toFixed(0)}% · ${(e.agents_used as string[])?.length ?? 0} agents`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AppShell>
  );
}
