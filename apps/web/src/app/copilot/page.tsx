"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Send, Bot, Sparkles } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { AnalystVisualization } from "@/components/analyst/AnalystVisualization";
import { StructuredCardGrid } from "@/components/agent/StructuredCard";
import { api, type CopilotResponse } from "@/lib/api";

const STARTERS = [
  "What is the auto-clear threshold for new wallets?",
  "How many high-KYT transactions by partner?",
  "Screening status for this alert",
  "OSINT research on counterparty",
  "Suggest a monitoring rule for mixer exposure",
];

function CopilotInner() {
  const searchParams = useSearchParams();
  const [message, setMessage] = useState("");
  const [alertId, setAlertId] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<
    { role: "user" | "assistant"; content: string; meta?: CopilotResponse }[]
  >([]);

  useEffect(() => {
    const aid = searchParams.get("alert_id");
    const q = searchParams.get("q");
    if (aid) setAlertId(aid);
    if (q) setMessage(q === "screening" ? "Run sanctions screening for this alert" : q);
    api.getSkills().catch(() => null);
  }, [searchParams]);

  const sessionId = alertId ? `copilot-${alertId}` : "copilot-global";

  const send = async (text?: string) => {
    const msg = (text ?? message).trim();
    if (!msg || loading) return;
    setMessage("");
    setHistory((h) => [...h, { role: "user", content: msg }]);
    setLoading(true);
    try {
      const assistantIdx = { idx: -1 };
      setHistory((h) => {
        assistantIdx.idx = h.length + 1;
        return [...h, { role: "assistant", content: "", meta: { reply: "" } as CopilotResponse }];
      });

      let meta: CopilotResponse | undefined;
      let content = "";
      await api.copilotChatStream(msg, alertId || undefined, sessionId, (ev) => {
        if (ev.event === "meta" && ev.meta) meta = ev.meta;
        if (ev.event === "token" && ev.text) content += ev.text;
        if (ev.event === "error") throw new Error(ev.message || "Stream error");
        setHistory((h) =>
          h.map((m, i) =>
            i === assistantIdx.idx
              ? { role: "assistant", content, meta: meta ? ({ ...meta, reply: content } as CopilotResponse) : m.meta }
              : m
          )
        );
      });
      // Fallback if backend returned immediately (should not happen, but safe)
      if (!content && !meta) {
        const res = await api.copilotChat(msg, alertId || undefined, sessionId);
        setHistory((h) => h.filter((_, i) => i !== assistantIdx.idx).concat({ role: "assistant", content: res.reply, meta: res }));
      }
    } catch {
      setHistory((h) => [
        ...h,
        { role: "assistant", content: "Copilot unavailable — check API connection." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-4xl flex-col p-6">
      <div className="mb-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-indigo-600" />
          <h2 className="text-xl font-semibold text-gray-900">AML Copilot</h2>
        </div>
        <p className="mt-1 text-sm text-gray-500">
          Agent → Skills → Tools — policy, RAG, NL-SQL, screening, OSINT, SAR
        </p>
      </div>

      <div className="mb-3 flex gap-2">
        <input
          value={alertId}
          onChange={(e) => setAlertId(e.target.value)}
          placeholder="Alert ID for case context (e.g. ALT-3002)"
          className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm"
        />
      </div>

      <div className="flex flex-1 flex-col overflow-hidden rounded-xl border border-gray-200 bg-white">
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {history.length === 0 && (
            <div className="rounded-lg bg-indigo-50 p-4 text-sm text-indigo-900">
              <Bot className="mb-2 h-5 w-5" />
              Bind an alert ID for case-aware skills (screening, graph, SAR).
            </div>
          )}
          {history.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[90%] rounded-lg px-4 py-3 text-sm ${
                  m.role === "user" ? "bg-indigo-600 text-white" : "bg-gray-50 text-gray-800"
                }`}
              >
                {m.role === "assistant" && m.meta?.skill_name && (
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-indigo-600">
                    {m.meta.skill_name}
                  </p>
                )}
                {m.role === "user" ? (
                  <p className="whitespace-pre-wrap">{m.content}</p>
                ) : m.meta?.type === "visualization" && m.meta.visualization ? (
                  <AnalystVisualization data={m.meta.visualization} />
                ) : (
                  <>
                    <p className="whitespace-pre-wrap">{m.content}</p>
                    {m.meta?.cards && <StructuredCardGrid cards={m.meta.cards} />}
                  </>
                )}
              </div>
            </div>
          ))}
          {loading && <div className="text-sm text-gray-400">Agent running skill...</div>}
        </div>

        <div className="border-t border-gray-100 p-3">
          <div className="mb-2 flex flex-wrap gap-2">
            {STARTERS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => send(s)}
                className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs text-gray-600 hover:bg-gray-100"
              >
                {s}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder="Ask your AML Agent..."
              className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={() => send()}
              disabled={loading}
              className="flex items-center gap-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CopilotPage() {
  return (
    <AppShell>
      <Suspense fallback={<div className="p-6 text-gray-500">Loading copilot...</div>}>
        <CopilotInner />
      </Suspense>
    </AppShell>
  );
}
