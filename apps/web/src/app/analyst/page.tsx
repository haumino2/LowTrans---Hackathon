"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Database } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { AnalystVisualization } from "@/components/analyst/AnalystVisualization";
import { api, type AnalystAskResult } from "@/lib/api";

const EXAMPLES = [
  "How many transactions have mixer exposure by partner?",
  "Show top 10 highest KYT score withdrawals",
  "What is the average rule fire rate by risk level?",
  "Travel Rule status breakdown by volume",
  "Trend: daily transaction volume last 30 days",
  "Outliers: top 20 withdrawals by amount and KYT",
];

function AnalystInner() {
  const searchParams = useSearchParams();
  const [alertId, setAlertId] = useState("");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AnalystAskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const aid = searchParams.get("alert_id");
    if (aid) setAlertId(aid);
  }, [searchParams]);

  const ask = async (q?: string) => {
    const text = (q ?? question).trim();
    if (!text) return;
    setQuestion(text);
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const prefix = alertId ? `[case ${alertId}] ` : "";
      const res = await api.analystAsk(prefix + text);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6 flex items-center gap-2">
        <Database className="h-5 w-5 text-indigo-600" />
        <h2 className="text-xl font-semibold text-gray-900">Data Analyst Workspace</h2>
      </div>
      <p className="mb-4 text-sm text-gray-500">
        NL-to-SQL skill — read-only queries over the transaction warehouse.
      </p>

      <input
        value={alertId}
        onChange={(e) => setAlertId(e.target.value)}
        placeholder="Case context alert ID (optional)"
        className="mb-4 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
      />

      <div className="mb-4 flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => ask(ex)}
            className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
          >
            {ex}
          </button>
        ))}
      </div>

      <div className="flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Ask in plain English..."
          className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm"
        />
        <button
          type="button"
          onClick={() => ask()}
          disabled={loading}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? "Running..." : "Run"}
        </button>
      </div>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {result?.visualization && (
        <div className="mt-6">
          <AnalystVisualization data={result.visualization} />
        </div>
      )}
    </div>
  );
}

export default function AnalystPage() {
  return (
    <AppShell>
      <Suspense fallback={<div className="p-6">Loading...</div>}>
        <AnalystInner />
      </Suspense>
    </AppShell>
  );
}
