import type { Alert } from "@/lib/api";

function Field({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-sm font-medium text-gray-900">{value}</p>
    </div>
  );
}

export function CustomerDetailsPanel({ alert }: { alert: Alert }) {
  return (
    <div className="grid grid-cols-2 gap-8">
      <div className="space-y-4">
        <Field label="Full Name" value={alert.customer_name} />
        <Field label="Partner Name" value={alert.partner} />
        <Field label="Partner ID" value={alert.partner_id} />
        <Field label="Email Address" value={alert.email} />
        <Field label="Phone" value={alert.phone} />
        <Field label="Customer Type" value="Customer" />
        <Field label="Account Age" value={`${alert.account_age_days} days`} />
        <Field label="Connection Graph" value={`${alert.connections}+ Direct Connections`} />
      </div>
      <div className="space-y-4">
        <Field label="Country" value={alert.country} />
        <Field label="State" value={alert.state} />
        <Field label="Address" value={alert.address} />
        <Field label="Zip Code" value={alert.zip} />
        <div className="mt-2 h-32 rounded-lg border border-gray-200 bg-gray-50 flex items-center justify-center text-xs text-gray-400">
          Location Preview
        </div>
      </div>
    </div>
  );
}

export function RulesPanel({ alert }: { alert: Alert }) {
  if (!alert.rules_fired.length) {
    return <p className="text-sm text-gray-500">No rules fired for this alert.</p>;
  }
  return (
    <div className="space-y-3">
      {alert.rules_fired.map((r) => (
        <div key={r.id} className="flex items-center justify-between rounded-lg border border-gray-200 p-4">
          <div>
            <p className="font-medium text-gray-900">{r.name}</p>
            <p className="text-xs text-gray-400">{r.id}</p>
          </div>
          <span className={`rounded-full px-2.5 py-1 text-xs font-semibold uppercase ${
            r.severity === "critical" ? "bg-red-100 text-red-700" :
            r.severity === "high" ? "bg-orange-100 text-orange-700" :
            "bg-yellow-100 text-yellow-700"
          }`}>
            {r.severity}
          </span>
        </div>
      ))}
    </div>
  );
}

export function CryptoPanel({ alert }: { alert: Alert }) {
  return (
    <div className="space-y-4">
      <Field label="Asset" value={`${alert.asset} on ${alert.network}`} />
      <Field label="Direction" value={alert.direction} />
      <Field label="Amount (USD)" value={`$${alert.amount_usd.toLocaleString()}`} />
      <Field label="Wallet Address" value={alert.wallet_address.slice(0, 20) + "..."} />
      <Field label="Counterparty" value={alert.counterparty} />
      <Field label="KYT Score" value={alert.kyt_score} />
      {Object.entries(alert.crypto_details).map(([k, v]) => (
        <Field key={k} label={k.replace(/_/g, " ")} value={String(v)} />
      ))}
    </div>
  );
}

export function SanctionsPanel({ alert }: { alert: Alert }) {
  const s = alert.sanctions_screening;
  return (
    <div className="space-y-4">
      <Field label="Screening Status" value={s.status.toUpperCase()} />
      <Field label="Matches Found" value={s.matches} />
      {s.note && <Field label="Notes" value={s.note} />}
      <Field label="PEP Hit" value={alert.signals.pep_hit ? "Yes" : "No"} />
      <Field label="Sanctions Hit" value={alert.signals.sanctions_hit ? "Yes" : "No"} />
    </div>
  );
}

export function TravelRulePanel({ alert }: { alert: Alert }) {
  return (
    <div className="space-y-4">
      <Field label="Travel Rule Status" value={alert.travel_rule_status} />
      <Field label="IVMS101 Payload" value={alert.travel_rule_status === "complete" ? "Validated" : "Missing / Incomplete"} />
      <Field label="Beneficiary VASP" value={alert.counterparty} />
      <Field label="Threshold" value={alert.amount_usd > 3000 ? "Above $3,000 — required" : "Below threshold"} />
    </div>
  );
}

export function DevicePanel({ alert }: { alert: Alert }) {
  return (
    <div className="space-y-4">
      <Field label="Device OS" value={alert.device_os} />
      <Field label="Device Risk" value={String(alert.signals.device_risk)} />
      <Field label="IP Country" value={String(alert.signals.ip_country)} />
      <Field label="Flow Type" value={alert.flow_type} />
    </div>
  );
}

export function RiskCodesPanel({ alert }: { alert: Alert }) {
  return (
    <div className="space-y-3">
      {alert.risk_tags.length === 0 ? (
        <p className="text-sm text-gray-500">No risk reason codes.</p>
      ) : (
        alert.risk_tags.map((tag) => (
          <span key={tag} className="inline-block rounded-full bg-red-50 px-3 py-1 text-sm font-medium text-red-700 mr-2">
            {tag.replace(/_/g, " ")}
          </span>
        ))
      )}
    </div>
  );
}

export function BehaviorPanel({ alert }: { alert: Alert }) {
  return (
    <div className="space-y-4">
      <Field label="Wallet Age" value={`${alert.signals.wallet_age_days} days`} />
      <Field label="Mixer Exposure" value={alert.signals.mixer_exposure ? "Detected" : "None"} />
      <Field label="Account Age" value={`${alert.account_age_days} days`} />
      <Field label="Connections" value={alert.connections} />
    </div>
  );
}

export function ModuleContent({ module, alert }: { module: string; alert: Alert }) {
  switch (module) {
    case "Customer Details": return <CustomerDetailsPanel alert={alert} />;
    case "Rules": return <RulesPanel alert={alert} />;
    case "Risk Reason Codes": return <RiskCodesPanel alert={alert} />;
    case "Sanctions & PEP": return <SanctionsPanel alert={alert} />;
    case "Crypto": return <CryptoPanel alert={alert} />;
    case "Device Signals": return <DevicePanel alert={alert} />;
    case "Travel Rule": return <TravelRulePanel alert={alert} />;
    case "Behavior": return <BehaviorPanel alert={alert} />;
    default: return <CustomerDetailsPanel alert={alert} />;
  }
}
