"use client";

import { useState } from "react";
import { CheckCircle, AlertCircle, Shield } from "lucide-react";
import { api, getRole } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { Button } from "@/components/ui/Button";

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
  const { success, error: toastError } = useToast();

  const handleSubmit = async () => {
    if (!reason.trim() || isAuditor) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.override(alertId, decision, reason);
      setDone(true);
      success(`Override recorded — ${decision}`);
      onOverride();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Override failed";
      setError(msg);
      toastError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (isAuditor) {
    return (
      <div className="rounded-lg border border-risk-review/30 bg-risk-review-bg p-5">
        <div className="flex items-center gap-2 text-risk-review">
          <Shield className="h-5 w-5" />
          <p className="text-sm font-medium">Auditor role is read-only — switch to Analyst to override</p>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="rounded-lg border border-risk-clear/30 bg-risk-clear-bg p-5">
        <div className="flex items-center gap-2 text-risk-clear">
          <CheckCircle className="h-5 w-5" />
          <p className="text-sm font-medium">Analyst override recorded — {decision}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-chrome-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <Shield className="h-4 w-4 text-chrome-500" />
        <h3 className="text-sm font-semibold text-chrome-900">Analyst Override</h3>
        {currentDecision && (
          <span className="ml-auto text-xs text-chrome-500">
            Agent decision: <span className="font-medium text-chrome-700">{currentDecision}</span>
          </span>
        )}
      </div>

      <div className="mb-4 flex gap-2">
        {(["CLEAR", "REVIEW", "ESCALATE"] as const).map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => setDecision(d)}
            className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
              decision === d
                ? d === "CLEAR"
                  ? "border-risk-clear/40 bg-risk-clear-bg text-risk-clear"
                  : d === "ESCALATE"
                  ? "border-risk-escalate/40 bg-risk-escalate-bg text-risk-escalate"
                  : "border-risk-review/40 bg-risk-review-bg text-risk-review"
                : "border-chrome-200 text-chrome-600 hover:bg-chrome-50"
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
        className="w-full rounded-md border border-chrome-200 px-3 py-2 text-sm text-chrome-900 placeholder:text-chrome-400 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
      />

      <div className="mt-3 flex items-center justify-between">
        <p className="flex items-center gap-1 text-xs text-chrome-400">
          <AlertCircle className="h-3.5 w-3.5" />
          Overrides are logged to the audit trail
        </p>
        <Button onClick={handleSubmit} disabled={!reason.trim() || submitting} size="sm">
          {submitting ? "Submitting..." : "Submit Override"}
        </Button>
      </div>
      {error && <p className="mt-2 text-xs text-risk-escalate">{error}</p>}
    </div>
  );
}
