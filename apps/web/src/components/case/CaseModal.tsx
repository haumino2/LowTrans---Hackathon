"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { api, type ResolvedCase } from "@/lib/api";

interface Props {
  caseId: string;
  onClose: () => void;
}

export function CaseModal({ caseId, onClose }: Props) {
  const [caseData, setCaseData] = useState<ResolvedCase | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getResolvedCase(caseId)
      .then(setCaseData)
      .catch(() => setCaseData(null))
      .finally(() => setLoading(false));
  }, [caseId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-xl border border-gray-200 bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">RAG Memory Case</p>
            <h3 className="text-lg font-semibold text-gray-900">{caseId}</h3>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          {loading && <p className="text-sm text-gray-400">Loading case details...</p>}
          {!loading && !caseData && (
            <p className="text-sm text-gray-500">Case not found in resolved memory index.</p>
          )}
          {caseData && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs uppercase tracking-wide text-gray-500">Customer</p>
                  <p className="text-sm font-medium text-gray-900">{caseData.customer_name}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-gray-500">Resolution</p>
                  <p className={`text-sm font-semibold ${
                    caseData.resolution === "CLEAR" ? "text-emerald-600" :
                    caseData.resolution === "ESCALATE" ? "text-red-600" : "text-amber-600"
                  }`}>
                    {caseData.resolution}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-gray-500">Transaction</p>
                  <p className="text-sm font-medium text-gray-900">
                    {caseData.direction} ${caseData.amount_usd.toLocaleString()} {caseData.asset}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-gray-500">KYT Score</p>
                  <p className="text-sm font-medium text-gray-900">{caseData.kyt_score}</p>
                </div>
              </div>

              {caseData.risk_tags.length > 0 && (
                <div>
                  <p className="text-xs uppercase tracking-wide text-gray-500 mb-1.5">Risk Tags</p>
                  <div className="flex flex-wrap gap-1.5">
                    {caseData.risk_tags.map((tag) => (
                      <span key={tag} className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
                        {tag.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Analyst Notes</p>
                <p className="text-sm text-gray-700 leading-relaxed">{caseData.analyst_notes}</p>
              </div>

              <div className="rounded-lg bg-gray-50 p-3 text-xs text-gray-500">
                Resolved {new Date(caseData.resolved_at).toLocaleDateString()} · Travel Rule: {caseData.travel_rule_status}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
