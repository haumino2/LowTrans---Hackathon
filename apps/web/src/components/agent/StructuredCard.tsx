"use client";

import type { StructuredCard } from "@/lib/api";

const TYPE_STYLES: Record<string, string> = {
  screening: "border-amber-200 bg-amber-50/50",
  graph: "border-red-200 bg-red-50/50",
  sar: "border-purple-200 bg-purple-50/50",
  metrics: "border-indigo-200 bg-indigo-50/50",
  business: "border-gray-200 bg-white",
  kyb: "border-blue-200 bg-blue-50/50",
  rule: "border-emerald-200 bg-emerald-50/50",
  case: "border-gray-200 bg-gray-50",
  policy: "border-gray-200 bg-white",
};

export function StructuredCardView({ card }: { card: StructuredCard }) {
  const style = TYPE_STYLES[card.type] ?? "border-gray-200 bg-white";
  return (
    <div className={`rounded-lg border p-4 ${style}`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{card.type}</p>
      <h4 className="mt-1 text-sm font-semibold text-gray-900">{card.title}</h4>
      <dl className="mt-3 space-y-2">
        {card.fields.map((f) => (
          <div key={f.label} className="flex justify-between gap-4 text-sm">
            <dt className="text-gray-500">{f.label}</dt>
            <dd className="font-medium text-gray-900 text-right">{f.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function StructuredCardGrid({ cards }: { cards: StructuredCard[] }) {
  if (!cards?.length) return null;
  return (
    <div className="mt-3 grid gap-3 sm:grid-cols-2">
      {cards.map((c, i) => (
        <StructuredCardView key={`${c.title}-${i}`} card={c} />
      ))}
    </div>
  );
}
