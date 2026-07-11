"use client";

const SHARED_MODULES = [
  "Customer Details",
  "Rules",
  "Risk Reason Codes",
  "Sanctions & PEP",
  "Device Signals",
  "Behavior",
] as const;

const RETAIL_MODULES = [
  "KYC / Onboarding",
  "Products & Segment",
  "Prior Alerts",
] as const;

const CRYPTO_MODULES = ["Crypto", "Travel Rule"] as const;

export function modulesForRail(rail?: string | null): string[] {
  const isCrypto = (rail || "crypto").toLowerCase() === "crypto";
  if (isCrypto) {
    // Preserve original crypto order: insert Crypto/Travel Rule in place
    return [
      "Customer Details",
      "Rules",
      "Risk Reason Codes",
      "Sanctions & PEP",
      "Crypto",
      "Device Signals",
      "Travel Rule",
      "Behavior",
    ];
  }
  return [
    "Customer Details",
    ...RETAIL_MODULES,
    "Rules",
    "Risk Reason Codes",
    "Sanctions & PEP",
    "Device Signals",
    "Behavior",
  ];
}

export function isCryptoRail(rail?: string | null): boolean {
  return (rail || "crypto").toLowerCase() === "crypto";
}

interface ModuleSidebarProps {
  active: string;
  onSelect: (module: string) => void;
  rail?: string | null;
}

export function ModuleSidebar({ active, onSelect, rail }: ModuleSidebarProps) {
  const modules = modulesForRail(rail);
  return (
    <nav className="w-52 shrink-0 border-r border-gray-200 bg-white py-4">
      <p className="px-4 pb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
        Intelligence Modules
      </p>
      {modules.map((m) => (
        <button
          key={m}
          onClick={() => onSelect(m)}
          className={`block w-full px-4 py-2.5 text-left text-sm transition-colors ${
            active === m
              ? "border-r-2 border-accent bg-accent-muted font-medium text-accent"
              : "text-gray-600 hover:bg-gray-50"
          }`}
        >
          {m}
        </button>
      ))}
    </nav>
  );
}

// Keep exports available for tests / callers that inspect module catalogs
export { SHARED_MODULES, RETAIL_MODULES, CRYPTO_MODULES };
