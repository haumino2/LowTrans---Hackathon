"use client";

const MODULES = [
  "Customer Details",
  "Rules",
  "Risk Reason Codes",
  "Sanctions & PEP",
  "Crypto",
  "Device Signals",
  "Travel Rule",
  "Behavior",
];

interface ModuleSidebarProps {
  active: string;
  onSelect: (module: string) => void;
}

export function ModuleSidebar({ active, onSelect }: ModuleSidebarProps) {
  return (
    <nav className="w-52 shrink-0 border-r border-gray-200 bg-white py-4">
      <p className="px-4 pb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
        Intelligence Modules
      </p>
      {MODULES.map((m) => (
        <button
          key={m}
          onClick={() => onSelect(m)}
          className={`block w-full px-4 py-2.5 text-left text-sm transition-colors ${
            active === m
              ? "border-r-2 border-indigo-600 bg-indigo-50 font-medium text-indigo-700"
              : "text-gray-600 hover:bg-gray-50"
          }`}
        >
          {m}
        </button>
      ))}
    </nav>
  );
}
