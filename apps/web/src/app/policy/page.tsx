"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/shell/AppShell";
import { api } from "@/lib/api";

export default function PolicyPage() {
  const [policy, setPolicy] = useState("");
  const [suggestion, setSuggestion] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.getPolicy().then((p) => setPolicy(p.content)).catch(() => {});
    api.getPolicySuggestions().then(setSuggestion).catch(() => {});
  }, []);

  return (
    <AppShell>
      <div className="p-6">
        <h2 className="text-xl font-semibold text-gray-900">Policy & RAG Learning</h2>
        <p className="mt-1 text-sm text-gray-500">
          Compliance policy and AI-suggested refinements from resolved case patterns
        </p>

        {suggestion && (
          <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-5">
            <p className="text-sm font-semibold text-emerald-900">RAG Policy Suggestion</p>
            <p className="mt-2 text-sm text-emerald-800">{String(suggestion.suggestion)}</p>
            <div className="mt-3 flex gap-4 text-xs text-emerald-700">
              <span>Evidence: {(suggestion.evidence_cases as string[])?.join(", ")}</span>
              <span>Est. FP reduction: {String(suggestion.estimated_fp_reduction)}</span>
              <span>Confidence: {((suggestion.confidence as number) * 100).toFixed(0)}%</span>
            </div>
          </div>
        )}

        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Active Triage Policy</h3>
          <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed">
            {policy || "Loading policy..."}
          </pre>
        </div>

        <div className="mt-6 rounded-xl border border-indigo-200 bg-white p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-2">How RAG Works in LowTrans</h3>
          <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
            <li>Each new KYT alert is embedded as a text document (signals, tags, amounts, Travel Rule status)</li>
            <li>TF-IDF vector search retrieves top-3 similar resolved cases from 15 historical investigations</li>
            <li>Triage agents use RAG matches to justify CLEAR/REVIEW/ESCALATE with cited case IDs</li>
            <li>Audit trail records which RAG cases influenced each decision</li>
            <li>Policy suggestions emerge from patterns in cleared vs escalated case clusters</li>
          </ol>
        </div>
      </div>
    </AppShell>
  );
}
