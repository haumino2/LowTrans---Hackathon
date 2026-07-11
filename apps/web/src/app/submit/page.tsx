"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, ShieldCheck } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { api, type Scenario, type TriageResult } from "@/lib/api";

type FormState = {
  scenario_id: string;
  customer_name: string;
  customer_id: string;
  wallet_address: string;
  partner: string;
  amount_usd: string;
  asset: string;
  network: string;
  direction: string;
  counterparty: string;
  travel_rule_status: string;
  country: string;
  account_age_days: string;
  connections: string;
  mixer_exposure: boolean;
  sanctions_hit: boolean;
  pep_hit: boolean;
  device_risk: string;
  risk_tags: string[];
};

const INITIAL: FormState = {
  scenario_id: "",
  customer_name: "Stakeholder Demo User",
  customer_id: "",
  wallet_address: "",
  partner: "Summit Crypto Exchange",
  amount_usd: "12500",
  asset: "USDC",
  network: "Ethereum",
  direction: "withdrawal",
  counterparty: "Unknown VASP wallet",
  travel_rule_status: "complete",
  country: "United States",
  account_age_days: "14",
  connections: "5",
  mixer_exposure: false,
  sanctions_hit: false,
  pep_hit: false,
  device_risk: "low",
  risk_tags: [],
};

const DECISION_BADGE: Record<string, string> = {
  CLEAR: "bg-emerald-100 text-emerald-700",
  REVIEW: "bg-amber-100 text-amber-700",
  ESCALATE: "bg-red-100 text-red-700",
};

export default function SubmitTransactionPage() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(INITIAL);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    alertId: string;
    mlSummary?: string;
    attribution?: { feature: string; contribution: number }[];
    model?: string;
    backend?: string;
    runtime?: string;
    triage?: TriageResult;
  } | null>(null);

  useEffect(() => {
    api.getScenarios().then((r) => setScenarios(r.scenarios)).catch(() => setScenarios([]));
  }, []);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const applyScenario = (s: Scenario | null) => {
    setResult(null);
    setError(null);
    if (!s) {
      setForm({ ...INITIAL, scenario_id: "" });
      return;
    }
    const p = s.payload;
    const str = (v: unknown, d = "") => (v === undefined || v === null ? d : String(v));
    setForm({
      scenario_id: s.id,
      customer_name: str(p.customer_name),
      customer_id: str(p.customer_id),
      wallet_address: str(p.wallet_address),
      partner: str(p.partner, "Summit Crypto Exchange"),
      amount_usd: str(p.amount_usd),
      asset: str(p.asset, "USDC"),
      network: str(p.network, "Ethereum"),
      direction: str(p.direction, "withdrawal"),
      counterparty: str(p.counterparty),
      travel_rule_status: str(p.travel_rule_status, "complete"),
      country: str(p.country),
      account_age_days: str(p.account_age_days, "30"),
      connections: str(p.connections, "3"),
      mixer_exposure: Boolean(p.mixer_exposure),
      sanctions_hit: Boolean(p.sanctions_hit),
      pep_hit: Boolean(p.pep_hit),
      device_risk: str(p.device_risk, "low"),
      risk_tags: Array.isArray(p.risk_tags) ? (p.risk_tags as string[]) : [],
    });
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const tags = new Set(form.risk_tags);
      if (form.mixer_exposure) tags.add("mixer_exposure");
      else tags.delete("mixer_exposure");
      const res = await api.submitTransaction({
        customer_name: form.customer_name,
        customer_id: form.customer_id || undefined,
        wallet_address: form.wallet_address || undefined,
        partner: form.partner || undefined,
        amount_usd: Number(form.amount_usd),
        asset: form.asset,
        network: form.network,
        direction: form.direction,
        counterparty: form.counterparty,
        travel_rule_status: form.travel_rule_status,
        country: form.country,
        account_age_days: Number(form.account_age_days),
        connections: Number(form.connections),
        mixer_exposure: form.mixer_exposure,
        sanctions_hit: form.sanctions_hit,
        pep_hit: form.pep_hit,
        device_risk: form.device_risk,
        risk_tags: Array.from(tags),
        scenario_id: form.scenario_id || undefined,
        run_triage: true,
      });
      setResult({
        alertId: res.alert.id,
        mlSummary: res.ml_score?.summary,
        attribution: res.ml_score?.attribution,
        model: res.ml_score?.model,
        backend: (res.ml_score as { backend?: string } | undefined)?.backend,
        runtime: (res.triage_result as { runtime?: string } | undefined)?.runtime,
        triage: res.triage_result,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submit failed");
    } finally {
      setBusy(false);
    }
  };

  const decision = result?.triage?.decision;
  const inputCls = "mt-1 w-full rounded-lg border border-gray-300 px-3 py-2";

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Submit transaction</h2>
            <p className="mt-1 text-sm text-gray-500">
              Stakeholder trust path — ML validate → 4-node agent investigation → queue.
            </p>
          </div>
          <Link href="/" className="text-sm font-medium text-indigo-600 hover:text-indigo-800">
            Back to queue
          </Link>
        </div>

        {scenarios.length > 0 && (
          <div className="mt-6">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
              Start from a scenario
            </p>
            <p className="mt-1 text-xs text-gray-400">
              Each preset carries a real wallet identity + on-chain graph, so the agents investigate real data.
            </p>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {scenarios.map((s) => {
                const active = form.scenario_id === s.id;
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => applyScenario(s)}
                    className={`rounded-xl border p-4 text-left transition ${
                      active
                        ? "border-indigo-500 bg-indigo-50 shadow-sm"
                        : "border-gray-200 bg-white hover:border-indigo-200"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold text-gray-900">{s.label}</span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          DECISION_BADGE[s.expected_decision] || "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {s.expected_decision}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-gray-500">{s.description}</p>
                  </button>
                );
              })}
              <button
                type="button"
                onClick={() => applyScenario(null)}
                className={`rounded-xl border border-dashed p-4 text-left transition ${
                  form.scenario_id === ""
                    ? "border-indigo-400 bg-indigo-50"
                    : "border-gray-300 bg-white hover:border-indigo-200"
                }`}
              >
                <span className="text-sm font-semibold text-gray-900">Manual entry</span>
                <p className="mt-1 text-xs text-gray-500">Enter a custom transaction and identity by hand.</p>
              </button>
            </div>
          </div>
        )}

        <form onSubmit={onSubmit} className="mt-6 space-y-4 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="text-gray-600">Customer name</span>
              <input
                className={inputCls}
                value={form.customer_name}
                onChange={(e) => set("customer_name", e.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              <span className="text-gray-600">Customer ID</span>
              <input
                className={inputCls}
                value={form.customer_id}
                onChange={(e) => set("customer_id", e.target.value)}
                placeholder="Auto-generated if blank (CUST-…)"
              />
            </label>
            <label className="block text-sm sm:col-span-2">
              <span className="text-gray-600">Wallet address</span>
              <input
                className={`${inputCls} font-mono`}
                value={form.wallet_address}
                onChange={(e) => set("wallet_address", e.target.value)}
                placeholder="0x… / bc1… — required for on-chain graph analysis"
              />
            </label>
            <label className="block text-sm">
              <span className="text-gray-600">Partner (VASP)</span>
              <input
                className={inputCls}
                value={form.partner}
                onChange={(e) => set("partner", e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="text-gray-600">Amount USD</span>
              <input
                type="number"
                min={0}
                step="0.01"
                className={inputCls}
                value={form.amount_usd}
                onChange={(e) => set("amount_usd", e.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              <span className="text-gray-600">Asset</span>
              <select className={inputCls} value={form.asset} onChange={(e) => set("asset", e.target.value)}>
                {["USDC", "USDT", "ETH", "BTC"].map((a) => (
                  <option key={a}>{a}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="text-gray-600">Network</span>
              <select className={inputCls} value={form.network} onChange={(e) => set("network", e.target.value)}>
                {["Ethereum", "Bitcoin", "Solana", "Tron"].map((a) => (
                  <option key={a}>{a}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="text-gray-600">Direction</span>
              <select className={inputCls} value={form.direction} onChange={(e) => set("direction", e.target.value)}>
                <option value="withdrawal">withdrawal</option>
                <option value="deposit">deposit</option>
              </select>
            </label>
            <label className="block text-sm">
              <span className="text-gray-600">Travel Rule</span>
              <select
                className={inputCls}
                value={form.travel_rule_status}
                onChange={(e) => set("travel_rule_status", e.target.value)}
              >
                {["complete", "missing", "incomplete", "mismatch"].map((a) => (
                  <option key={a}>{a}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm sm:col-span-2">
              <span className="text-gray-600">Counterparty</span>
              <input
                className={inputCls}
                value={form.counterparty}
                onChange={(e) => set("counterparty", e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="text-gray-600">Country</span>
              <input className={inputCls} value={form.country} onChange={(e) => set("country", e.target.value)} />
            </label>
            <label className="block text-sm">
              <span className="text-gray-600">Wallet age (days)</span>
              <input
                type="number"
                min={0}
                className={inputCls}
                value={form.account_age_days}
                onChange={(e) => set("account_age_days", e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="text-gray-600">Connections</span>
              <input
                type="number"
                min={0}
                className={inputCls}
                value={form.connections}
                onChange={(e) => set("connections", e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="text-gray-600">Device risk</span>
              <select
                className={inputCls}
                value={form.device_risk}
                onChange={(e) => set("device_risk", e.target.value)}
              >
                {["low", "medium", "high"].map((a) => (
                  <option key={a}>{a}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="flex flex-wrap gap-4 border-t border-gray-100 pt-4 text-sm">
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.mixer_exposure}
                onChange={(e) => set("mixer_exposure", e.target.checked)}
              />
              Mixer exposure
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.sanctions_hit}
                onChange={(e) => set("sanctions_hit", e.target.checked)}
              />
              Sanctions / OFAC hit
            </label>
            <label className="inline-flex items-center gap-2">
              <input type="checkbox" checked={form.pep_hit} onChange={(e) => set("pep_hit", e.target.checked)} />
              PEP hit
            </label>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
            Validate with agents
          </button>
        </form>

        {result && (
          <div className="mt-6 space-y-4">
            <div
              className={`rounded-xl border p-5 ${
                decision === "CLEAR"
                  ? "border-emerald-200 bg-emerald-50"
                  : decision === "ESCALATE"
                  ? "border-red-200 bg-red-50"
                  : "border-amber-200 bg-amber-50"
              }`}
            >
              <p className="text-sm font-medium text-gray-700">Created {result.alertId}</p>
              <p className="mt-1 text-2xl font-semibold text-gray-900">
                {decision ?? "—"}{" "}
                <span className="text-base font-normal text-gray-600">
                  {result.triage?.confidence != null
                    ? `${Math.round(result.triage.confidence * 100)}% confidence`
                    : ""}
                </span>
              </p>
              <p className="mt-2 text-sm text-gray-700">{result.mlSummary}</p>
              {(result.model || result.runtime) && (
                <p className="mt-1 text-xs text-gray-500">
                  {result.backend || result.model}
                  {result.runtime ? ` · runtime ${result.runtime}` : ""}
                </p>
              )}
              <div className="mt-4 flex gap-3">
                <button
                  type="button"
                  onClick={() => router.push(`/cases/${result.alertId}`)}
                  className="rounded-lg bg-gray-900 px-3 py-2 text-sm font-medium text-white"
                >
                  Open case timeline
                </button>
                <Link href="/" className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium">
                  View in queue
                </Link>
              </div>
            </div>

            {!!result.attribution?.length && (
              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <p className="text-sm font-semibold text-gray-900">ML feature attribution</p>
                <ul className="mt-3 space-y-2">
                  {result.attribution.map((a) => (
                    <li key={a.feature} className="flex justify-between text-sm">
                      <span className="text-gray-600">{a.feature}</span>
                      <span className="font-mono text-gray-900">+{a.contribution}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {!!result.triage?.rationale?.length && (
              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <p className="text-sm font-semibold text-gray-900">Arbiter rationale</p>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-gray-700">
                  {result.triage.rationale.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
