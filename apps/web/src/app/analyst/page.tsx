"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Database } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { AnalystVisualization } from "@/components/analyst/AnalystVisualization";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageSkeleton, Skeleton } from "@/components/ui/Skeleton";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
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
  const [asked, setAsked] = useState(false);

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
    setAsked(true);
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
        <Database className="h-5 w-5 text-accent" aria-hidden />
        <h2 className="text-xl font-semibold text-chrome-900">Data Analyst Workspace</h2>
      </div>
      <p className="mb-4 text-sm text-chrome-500">
        NL-to-SQL skill — read-only queries over the transaction warehouse.
      </p>

      <input
        value={alertId}
        onChange={(e) => setAlertId(e.target.value)}
        placeholder="Case context alert ID (optional)"
        className="mb-4 w-full rounded-md border border-chrome-200 px-3 py-2 text-sm mono"
        aria-label="Case context alert ID"
      />

      <div className="mb-4 flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => ask(ex)}
            className="rounded-md border border-chrome-200 bg-white px-3 py-1 text-xs text-chrome-600 hover:bg-chrome-50"
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
          className="flex-1 rounded-md border border-chrome-200 px-3 py-2 text-sm"
          aria-label="Analyst question"
        />
        <Button onClick={() => ask()} disabled={loading}>
          {loading ? "Running..." : "Run"}
        </Button>
      </div>

      {error && <p className="mt-4 text-sm text-risk-escalate">{error}</p>}

      {loading && (
        <div className="mt-6 space-y-3" role="status" aria-label="Running query">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {!loading && asked && !error && !result?.visualization && (
        <EmptyState
          className="mt-6 rounded-lg border border-chrome-200 bg-white"
          title="No rows returned"
          description="Try a broader question, or start with an example like “high-KYT transactions by partner”."
        />
      )}

      {!loading && !asked && (
        <EmptyState
          className="mt-6 rounded-lg border border-chrome-200 bg-white"
          icon={<Database className="h-5 w-5" aria-hidden />}
          title="Ask a portfolio question"
          description="Use an example chip above, or type a question in plain English. Results render as tables and charts."
        />
      )}

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
      <ErrorBoundary fallbackTitle="Analyst workspace failed">
        <Suspense fallback={<PageSkeleton />}>
          <AnalystInner />
        </Suspense>
      </ErrorBoundary>
    </AppShell>
  );
}
