"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutList,
  Bot,
  ScrollText,
  BookOpen,
  BarChart3,
  Sparkles,
} from "lucide-react";
import { API_BASE, api } from "@/lib/api";

const NAV = [
  { href: "/", label: "Alert Queue", icon: LayoutList },
  { href: "/insights", label: "Risk Insights", icon: BarChart3 },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/rules", label: "Rule Builder", icon: Sparkles },
  { href: "/audit", label: "Audit Trail", icon: ScrollText },
  { href: "/policy", label: "Policy & RAG", icon: BookOpen },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = () => {
      api
        .getHealth()
        .then(() => {
          if (!cancelled) {
            setApiConnected(true);
          }
        })
        .catch(() => {
          if (!cancelled) setApiConnected(false);
        });
    };
    check();
    const interval = setInterval(check, 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="flex min-h-screen bg-[#f4f5f7]">
      <aside className="flex w-14 flex-col items-center border-r border-gray-200 bg-white py-4 gap-1">
        <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white text-xs font-bold">
          LT
        </div>
        {NAV.map((item) => {
          const Icon = item.icon;
          const active =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.label}
              className={`flex h-9 w-9 items-center justify-center rounded-lg transition-colors ${
                active
                  ? "bg-indigo-50 text-indigo-600"
                  : "text-gray-500 hover:bg-gray-100 hover:text-gray-700"
              }`}
            >
              <Icon className="h-[18px] w-[18px]" strokeWidth={1.75} />
            </Link>
          );
        })}
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-6">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold text-gray-900">LowTrans</h1>
            <span className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-0.5 text-xs font-medium text-gray-600">
              AML & KYT for Crypto
            </span>
          </div>
          {apiConnected === false && (
            <div className="text-xs font-medium text-red-600">API Disconnected · {API_BASE}</div>
          )}
        </header>
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
