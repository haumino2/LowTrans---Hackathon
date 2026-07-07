"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/shell/AppShell";
import { api, type CasePacket } from "@/lib/api";

export default function CasePacketPage() {
  const params = useParams();
  const caseId = params.id as string;
  const [pkt, setPkt] = useState<CasePacket | null>(null);
  const [loading, setLoading] = useState(true);
  const [assignee, setAssignee] = useState("");
  const [state, setState] = useState("new");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const p = await api.getCasePacket(caseId);
      setPkt(p);
      setAssignee(p.assigned_to || "");
      setState(p.state || "new");
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    load();
  }, [load]);

  const alertsSorted = useMemo(() => {
    if (!pkt) return [];
    return [...pkt.alerts].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  }, [pkt]);

  if (loading || !pkt) {
    return (
      <AppShell>
        <div className="p-6 text-gray-500">Loading case packet...</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="p-6 space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Case Packet</h2>
            <p className="mt-1 text-sm text-gray-500">
              Case <span className="font-mono text-xs text-gray-700">{pkt.case_id}</span> · Customer{" "}
              <span className="font-medium text-gray-700">{pkt.customer_name}</span> · Partner {pkt.partner}
            </p>
          </div>
          <button
            onClick={load}
            className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <p className="text-xs uppercase tracking-wide text-gray-500">Status</p>
            <p className="mt-1 text-lg font-semibold text-gray-900">{pkt.status}</p>
            <p className="mt-2 text-xs text-gray-500">Max KYT: {pkt.max_kyt} · Risk: {pkt.risk_level}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <p className="text-xs uppercase tracking-wide text-gray-500">Assignment</p>
            <div className="mt-2 flex gap-2">
              <input
                value={assignee}
                onChange={(e) => setAssignee(e.target.value)}
                placeholder="Assignee..."
                className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
              <button
                onClick={async () => {
                  setSaving(true);
                  try {
                    await api.assignCase(caseId, assignee || "unassigned");
                    await load();
                  } finally {
                    setSaving(false);
                  }
                }}
                className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Save
              </button>
            </div>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <p className="text-xs uppercase tracking-wide text-gray-500">Lifecycle</p>
            <div className="mt-2 flex gap-2">
              <select
                value={state}
                onChange={(e) => setState(e.target.value)}
                className="flex-1 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700"
              >
                <option value="new">new</option>
                <option value="investigating">investigating</option>
                <option value="waiting_info">waiting_info</option>
                <option value="resolved">resolved</option>
              </select>
              <button
                onClick={async () => {
                  setSaving(true);
                  try {
                    await api.setCaseState(caseId, state);
                    await load();
                  } finally {
                    setSaving(false);
                  }
                }}
                className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                disabled={saving}
              >
                Update
              </button>
            </div>
            {pkt.policy_version && <p className="mt-2 text-xs text-gray-500">Policy: {pkt.policy_version}</p>}
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <p className="text-sm font-semibold text-gray-900">Case Notes</p>
          <div className="mt-3 space-y-2">
            {(pkt.case_notes || []).slice().reverse().slice(0, 8).map((n, i) => (
              <div key={i} className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2">
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span className="uppercase">{n.role}</span>
                  <span className="font-mono">{String(n.timestamp).slice(0, 19)}</span>
                </div>
                <p className="mt-1 text-sm text-gray-800 whitespace-pre-wrap">{n.text}</p>
              </div>
            ))}
          </div>
          <div className="mt-3">
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add case note..."
              rows={3}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
            />
            <div className="mt-2 flex justify-end">
              <button
                disabled={!note.trim() || saving}
                onClick={async () => {
                  setSaving(true);
                  try {
                    await api.addCaseNote(caseId, note);
                    setNote("");
                    await load();
                  } finally {
                    setSaving(false);
                  }
                }}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                Add Note
              </button>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <div className="border-b border-gray-200 bg-gray-50 px-5 py-3">
            <p className="text-sm font-semibold text-gray-900">Alerts in this case</p>
          </div>
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 bg-white">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Alert</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Created</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">KYT</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Action</th>
              </tr>
            </thead>
            <tbody>
              {alertsSorted.map((a) => (
                <tr key={a.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{a.id}</td>
                  <td className="px-4 py-3 font-mono text-xs">{String(a.created_at).slice(0, 19)}</td>
                  <td className="px-4 py-3">{a.kyt_score}</td>
                  <td className="px-4 py-3 text-xs">{a.status}</td>
                  <td className="px-4 py-3">
                    <Link href={`/cases/${a.id}`} className="text-indigo-600 hover:text-indigo-800 font-medium">
                      Open alert workspace
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

