"use client";

import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/shell/AppShell";
import { api } from "@/lib/api";

type RulePreview = {
  matches?: number;
  avg_kyt?: number;
  avg_amount?: number;
  error?: string;
};

type RuleConditions = {
  mixer_exposure: boolean;
  sanctions_hit: boolean;
  kyt_min: number;
  amount_min: number;
  direction: "withdrawal" | "deposit";
  travel_rule_status: "missing" | "complete" | "incomplete" | "mismatch";
};

type RuleCompileResponse = {
  id: string;
  name: string;
  description: string;
  conditions: RuleConditions;
  sql: string;
  preview: RulePreview;
  created_at: string;
};

export default function RulesPage() {
  const [name, setName] = useState("Mixer + Travel Rule Missing");
  const [desc, setDesc] = useState("Flag withdrawals with mixer exposure and missing travel rule.");
  const [conditions, setConditions] = useState<RuleConditions>({
    mixer_exposure: true,
    sanctions_hit: false,
    kyt_min: 65,
    amount_min: 3000,
    direction: "withdrawal",
    travel_rule_status: "missing",
  });
  const [saving, setSaving] = useState(false);
  const [compiled, setCompiled] = useState<RuleCompileResponse | null>(null);
  const [recent, setRecent] = useState<RuleCompileResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadRecent = async () => {
    try {
      const rules = await api.getRules();
      setRecent(rules as RuleCompileResponse[]);
    } catch {
      setRecent([]);
    }
  };

  useEffect(() => {
    loadRecent();
  }, []);

  const previewText = useMemo(() => {
    if (!compiled) return "";
    const p = compiled.preview || {};
    if (p.error) return String(p.error);
    return `matches: ${p.matches ?? "?"} · avg_kyt: ${p.avg_kyt ?? "—"} · avg_amount: ${p.avg_amount ?? "—"}`;
  }, [compiled]);

  const compile = async () => {
    setSaving(true);
    setError(null);
    try {
      const res = await api.compileRule(name, desc, conditions);
      setCompiled(res as RuleCompileResponse);
      await loadRecent();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Compile failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl p-6 space-y-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Rule Builder</h2>
          <p className="mt-1 text-sm text-gray-500">
            Build a monitoring rule and preview estimated matches (pilot-grade, not full DSL).
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
        )}

        <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Name</p>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Description</p>
              <input
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={conditions.mixer_exposure}
                onChange={(e) => setConditions((c) => ({ ...c, mixer_exposure: e.target.checked }))}
              />
              mixer_exposure
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={conditions.sanctions_hit}
                onChange={(e) => setConditions((c) => ({ ...c, sanctions_hit: e.target.checked }))}
              />
              sanctions_hit
            </label>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-700">direction</span>
              <select
                value={conditions.direction}
                onChange={(e) =>
                  setConditions((c) => ({ ...c, direction: e.target.value as RuleConditions["direction"] }))
                }
                className="rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-sm"
              >
                <option value="withdrawal">withdrawal</option>
                <option value="deposit">deposit</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-700">kyt_min</span>
              <input
                type="number"
                value={conditions.kyt_min}
                onChange={(e) => setConditions((c) => ({ ...c, kyt_min: Number(e.target.value) }))}
                className="w-28 rounded-lg border border-gray-200 px-2 py-1.5 text-sm"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-700">amount_min</span>
              <input
                type="number"
                value={conditions.amount_min}
                onChange={(e) => setConditions((c) => ({ ...c, amount_min: Number(e.target.value) }))}
                className="w-28 rounded-lg border border-gray-200 px-2 py-1.5 text-sm"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-700">travel_rule_status</span>
              <select
                value={conditions.travel_rule_status}
                onChange={(e) =>
                  setConditions((c) => ({
                    ...c,
                    travel_rule_status: e.target.value as RuleConditions["travel_rule_status"],
                  }))
                }
                className="rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-sm"
              >
                <option value="missing">missing</option>
                <option value="complete">complete</option>
                <option value="incomplete">incomplete</option>
                <option value="mismatch">mismatch</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              disabled={saving}
              onClick={compile}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {saving ? "Compiling..." : "Compile & Preview"}
            </button>
          </div>
        </div>

        {compiled && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
            <p className="text-sm font-semibold text-gray-900">Preview</p>
            <p className="text-sm text-gray-700">{previewText}</p>
            <p className="text-xs uppercase tracking-wide text-gray-500">SQL</p>
            <pre className="overflow-auto rounded-lg bg-gray-50 p-3 text-xs text-gray-700">{compiled.sql}</pre>
          </div>
        )}

        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <p className="text-sm font-semibold text-gray-900">Recent compiled rules</p>
          <div className="mt-3 space-y-2">
            {recent.length === 0 ? (
              <p className="text-sm text-gray-400">No rules yet.</p>
            ) : (
              recent.slice(0, 8).map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => setCompiled(r)}
                  className="w-full rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-left hover:bg-gray-100"
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-gray-900">{r.name}</p>
                    <p className="font-mono text-xs text-gray-500">{String(r.created_at).slice(0, 19)}</p>
                  </div>
                  <p className="mt-1 text-xs text-gray-600 line-clamp-1">{r.description}</p>
                </button>
              ))
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}

