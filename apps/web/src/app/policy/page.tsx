"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/shell/AppShell";
import { api, getTenant } from "@/lib/api";

export default function PolicyPage() {
  const [policy, setPolicy] = useState("");
  const [meta, setMeta] = useState<{
    tenant?: string;
    jurisdiction?: string;
    policy_version?: string;
    label?: string;
    display?: string;
  }>({});
  const [suggestion, setSuggestion] = useState<Record<string, unknown> | null>(null);
  const [tenant, setTenantState] = useState(() =>
    typeof window !== "undefined" ? getTenant() : "vn-retail"
  );

  useEffect(() => {
    const onTenant = (e: Event) => {
      const next = (e as CustomEvent<string>).detail;
      if (next) setTenantState(next);
    };
    window.addEventListener("clario-tenant-change", onTenant);
    return () => window.removeEventListener("clario-tenant-change", onTenant);
  }, []);

  useEffect(() => {
    api
      .getPolicy()
      .then((p) => {
        setPolicy(p.content);
        setMeta({
          tenant: p.tenant,
          jurisdiction: p.jurisdiction,
          policy_version: p.policy_version,
          label: p.label,
          display: p.display,
        });
      })
      .catch(() => {});
    api.getPolicySuggestions().then(setSuggestion).catch(() => {});
  }, [tenant]);

  return (
    <AppShell>
      <div className="p-6">
        <h2 className="text-xl font-semibold text-gray-900">Policy & RAG Learning</h2>
        <p className="mt-1 text-sm text-gray-500">
          Compliance policy and AI-suggested refinements from resolved case patterns
          {meta.display ? (
            <span className="ml-2 rounded-md border border-chrome-200 bg-chrome-50 px-2 py-0.5 text-xs font-medium text-chrome-700">
              {meta.display}
            </span>
          ) : null}
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
          <div className="mb-4 flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-gray-900">Active Triage Policy</h3>
            {meta.label && (
              <span className="text-xs text-gray-500">
                {meta.label}
                {meta.policy_version ? ` · ${meta.policy_version}` : ""}
              </span>
            )}
          </div>
          <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed">
            {policy || "Loading policy..."}
          </pre>
        </div>

        <div className="mt-6 rounded-xl border border-chrome-200 bg-white p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-2">How RAG Works in Clario</h3>
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
