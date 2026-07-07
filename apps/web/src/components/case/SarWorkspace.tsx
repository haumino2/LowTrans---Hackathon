"use client";

import { useState } from "react";
import { FileWarning } from "lucide-react";
import { api } from "@/lib/api";
import { StructuredCardGrid } from "@/components/agent/StructuredCard";

export function SarWorkspace({
  alertId,
  customerName,
  escalationSummary,
}: {
  alertId: string;
  customerName: string;
  escalationSummary?: string | null;
}) {
  const [draft, setDraft] = useState(escalationSummary || "");
  const [loading, setLoading] = useState(false);
  const [cards, setCards] = useState<{ type: string; title: string; fields: { label: string; value: string }[] }[]>([]);

  const generate = async () => {
    setLoading(true);
    try {
      const res = await api.copilotChat(
        `Generate SAR narrative for ${customerName}`,
        alertId,
        `sar-${alertId}`
      );
      setDraft(res.reply);
      if (res.cards) setCards(res.cards);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-purple-200 bg-purple-50/30 p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <FileWarning className="h-5 w-5 text-purple-700" />
        <h3 className="text-sm font-semibold text-gray-900">SAR Filing Workspace</h3>
      </div>
      <p className="mt-1 text-xs text-gray-500">
        Draft regulatory narrative — human review required before filing.
      </p>
      <button
        type="button"
        onClick={generate}
        disabled={loading}
        className="mt-3 rounded-lg bg-purple-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-purple-800 disabled:opacity-50"
      >
        {loading ? "Generating..." : "Generate SAR Draft"}
      </button>
      <StructuredCardGrid cards={cards} />
      {draft && (
        <pre className="mt-4 max-h-64 overflow-auto rounded-lg border border-purple-100 bg-white p-4 text-xs text-gray-800 whitespace-pre-wrap">
          {draft}
        </pre>
      )}
    </div>
  );
}
