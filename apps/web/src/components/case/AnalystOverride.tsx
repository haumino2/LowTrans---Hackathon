"use client";

import { useState } from "react";
import { CheckCircle, AlertCircle, Shield } from "lucide-react";
import { api, getRole } from "@/lib/api";

interface Props {
  alertId: string;
  currentDecision?: string;
  onOverride: () => void;
}

export function AnalystOverride({ alertId, currentDecision, onOverride }: Props) {
  const [decision, setDecision] = useState("CLEAR");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isAuditor = getRole() === "auditor";

  const handleSubmit = async () => {
    if (!reason.trim() || isAuditor) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.override(alertId, decision, reason);
      setDone(true);
      onOverride();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Override failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (isAuditor) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
        <div className="flex items-center gap-2 text-amber-800">
          <Shield className="h-5 w-5" />
          <p className="text-sm font-medium">Auditor role is read-only — switch to Analyst to override</p>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5">
        <div className="flex items-center gap-2 text-emerald-800">
          <CheckCircle className="h-5 w-5" />
          <p className="text-sm font-medium">Analyst override recorded — {decision}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex items-center gap-2 mb-4">
        <Shield className="h-4 w-4 text-gray-500" />
        <h3 className="text-sm font-semibold text-gray-900">Analyst Override</h3>
        {currentDecision && (
          <span className="ml-auto text-xs text-gray-500">
            Agent decision: <span className="font-medium text-gray-700">{currentDecision}</span>
          </span>
        )}
      </div>

      <div className="flex gap-2 mb-4">
        {(["CLEAR", "REVIEW", "ESCALATE"] as const).map((d) => (
          <button
            key={d}
            onClick={() => setDecision(d)}
            className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
              decision === d
                ? d === "CLEAR"
                  ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                  : d === "ESCALATE"
                  ? "border-red-300 bg-red-50 text-red-700"
                  : "border-amber-300 bg-amber-50 text-amber-700"
                : "border-gray-200 text-gray-600 hover:bg-gray-50"
            }`}
          >
            {d}
          </button>
        ))}
      </div>

      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Reason for override (required)..."
        rows={3}
        className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-indigo-300 focus:outline-none focus:ring-1 focus:ring-indigo-300"
      />

      <div className="mt-3 flex items-center justify-between">
        <p className="flex items-center gap-1 text-xs text-gray-400">
          <AlertCircle className="h-3.5 w-3.5" />
          Overrides are logged to the audit trail
        </p>
        <button
          onClick={handleSubmit}
          disabled={!reason.trim() || submitting}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {submitting ? "Submitting..." : "Submit Override"}
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}
