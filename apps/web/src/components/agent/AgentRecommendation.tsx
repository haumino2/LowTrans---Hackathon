"use client";

import { useState } from "react";
import type { TriageResult } from "@/lib/api";
import { CaseModal } from "@/components/case/CaseModal";
import { Markdown } from "@/components/ui/Markdown";

const DECISION_STYLES: Record<string, string> = {
  CLEAR: "bg-emerald-50 border-emerald-200 text-emerald-800",
  REVIEW: "bg-amber-50 border-amber-200 text-amber-800",
  ESCALATE: "bg-red-50 border-red-200 text-red-800",
};

export function AgentRecommendation({ result }: { result: TriageResult }) {
  const [selectedCase, setSelectedCase] = useState<string | null>(null);
  const style = DECISION_STYLES[result.decision] || DECISION_STYLES.REVIEW;

  return (
    <>
      <div className={`rounded-xl border p-5 shadow-sm ${style}`}>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide opacity-70">
              Agent disposition · 4-agent investigation
            </p>
            <p className="mt-1 text-2xl font-bold">{result.decision}</p>
            <p className="text-sm opacity-80">
              Confidence {(result.confidence * 100).toFixed(0)}% · {result.suggested_disposition}
            </p>
            {(result.policy_display ||
              (result.jurisdiction && result.policy_version)) && (
              <p className="mt-1 text-xs font-medium opacity-70">
                {result.policy_display ||
                  `policy: ${result.jurisdiction} ${result.policy_version}`}
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-1 justify-end max-w-xs">
            {result.agents_used.map((a) => (
              <span key={a} className="rounded-full bg-white/60 px-2 py-0.5 text-xs font-medium">
                {a}
              </span>
            ))}
          </div>
        </div>

        <div className="mt-4">
          <p className="text-xs font-semibold uppercase opacity-70 mb-2">Rationale</p>
          <ul className="space-y-1">
            {result.rationale.map((r, i) => (
              <li key={i} className="text-sm flex gap-2">
                <span className="text-gray-400">—</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>

        {result.similar_cases.length > 0 && (
          <div className="mt-4 rounded-lg bg-white/50 p-3">
            <p className="text-xs font-semibold uppercase opacity-70 mb-2">
              RAG Memory — Similar Resolved Cases
            </p>
            <div className="space-y-2">
              {result.similar_cases.map((c) => (
                <div key={c.case_id} className="flex items-center justify-between text-sm">
                  <button
                    onClick={() => setSelectedCase(c.case_id)}
                    className="font-mono font-medium text-accent hover:text-chrome-900 hover:underline"
                  >
                    {c.case_id}
                  </button>
                  <span className="text-xs opacity-70">{c.customer_name} · {c.asset}</span>
                  <span className="rounded px-1.5 py-0.5 text-xs font-medium bg-white">
                    {(c.similarity * 100).toFixed(0)}% match
                  </span>
                  <span className={`rounded px-1.5 py-0.5 text-xs font-bold ${
                    c.resolution === "CLEAR" ? "text-emerald-700" : c.resolution === "ESCALATE" ? "text-red-700" : "text-amber-700"
                  }`}>
                    {c.resolution}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {result.escalation_summary && (
          <div className="mt-4 rounded-lg bg-white/70 p-4">
            <p className="text-xs font-semibold uppercase opacity-70 mb-2">SAR Filing Agent — Escalation Summary</p>
            <Markdown content={result.escalation_summary} />
          </div>
        )}
      </div>

      {selectedCase && (
        <CaseModal caseId={selectedCase} onClose={() => setSelectedCase(null)} />
      )}
    </>
  );
}
