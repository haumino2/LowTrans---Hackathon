"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  LayoutList,
  Bot,
  ScrollText,
  BookOpen,
  BarChart3,
  Sparkles,
  PlusCircle,
  MessageSquare,
  Database,
  CheckCircle2,
  FolderOpen,
  Search,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";
import { API_BASE, api, getRole, setRole, getTenant, setTenant, TENANTS } from "@/lib/api";
import { cn } from "@/lib/cn";

const ROLES = [
  { value: "analyst", label: "Analyst" },
  { value: "supervisor", label: "Supervisor" },
  { value: "auditor", label: "Auditor" },
] as const;

type NavItem = { href: string; label: string; icon: LucideIcon };

const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: "Operations",
    items: [
      { href: "/", label: "Alert Queue", icon: LayoutList },
      { href: "/cases", label: "Cases", icon: FolderOpen },
      { href: "/submit", label: "Submit Tx", icon: PlusCircle },
      { href: "/approvals", label: "Approvals", icon: CheckCircle2 },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { href: "/insights", label: "Risk Insights", icon: BarChart3 },
      { href: "/analyst", label: "Data Analyst", icon: Database },
      { href: "/copilot", label: "AML Copilot", icon: MessageSquare },
    ],
  },
  {
    label: "Platform",
    items: [
      { href: "/agents", label: "Agents", icon: Bot },
      { href: "/rules", label: "Rule Builder", icon: Sparkles },
      { href: "/audit", label: "Audit Trail", icon: ScrollText },
      { href: "/policy", label: "Policy & RAG", icon: BookOpen },
    ],
  },
];

const BREADCRUMB: Record<string, string> = {
  "/": "Alert Queue",
  "/cases": "Cases",
  "/submit": "Submit Transaction",
  "/approvals": "Approvals",
  "/insights": "Risk Insights",
  "/analyst": "Data Analyst",
  "/copilot": "AML Copilot",
  "/agents": "Agents",
  "/rules": "Rule Builder",
  "/audit": "Audit Trail",
  "/policy": "Policy & RAG",
};

function crumbFor(pathname: string): string {
  if (pathname.startsWith("/cases/")) return "Case Detail";
  if (pathname.startsWith("/case/")) return "Customer Case";
  return BREADCRUMB[pathname] ?? "Clario";
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);
  const [bedrockModel, setBedrockModel] = useState<string | null>(null);
  const [role, setRoleState] = useState("analyst");
  const [tenant, setTenantState] = useState("vn-retail");
  const [navOpen, setNavOpen] = useState(true);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQ, setSearchQ] = useState("");

  useEffect(() => {
    setRoleState(getRole());
    setTenantState(getTenant());
    const onRole = (e: Event) => {
      const next = (e as CustomEvent<string>).detail;
      if (next) setRoleState(next);
    };
    const onTenant = (e: Event) => {
      const next = (e as CustomEvent<string>).detail;
      if (next) setTenantState(next);
    };
    window.addEventListener("lowtrans-role-change", onRole);
    window.addEventListener("clario-tenant-change", onTenant);
    return () => {
      window.removeEventListener("lowtrans-role-change", onRole);
      window.removeEventListener("clario-tenant-change", onTenant);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const check = () => {
      api
        .getHealth()
        .then((h) => {
          if (cancelled) return;
          setApiConnected(true);
          const modelId = String(h.bedrock?.model_id || "");
          setBedrockModel(modelId || null);
        })
        .catch(() => {
          if (!cancelled) {
            setApiConnected(false);
            setBedrockModel(null);
          }
        });
    };
    check();
    const interval = setInterval(check, 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const bedrockShort = useMemo(() => {
    if (!bedrockModel) return null;
    // e.g. global.amazon.nova-2-lite-v1:0 → nova-2-lite
    const leaf = bedrockModel.split(".").pop() || bedrockModel;
    return leaf.replace(/-v\d+:\d+$/i, "").replace(/:.*$/, "");
  }, [bedrockModel]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen((v) => !v);
      }
      if (e.key === "Escape") setSearchOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const breadcrumb = useMemo(() => crumbFor(pathname), [pathname]);

  const searchHits = useMemo(() => {
    const q = searchQ.trim().toLowerCase();
    const flat = NAV_GROUPS.flatMap((g) => g.items);
    if (!q) return flat;
    return flat.filter((i) => i.label.toLowerCase().includes(q));
  }, [searchQ]);

  return (
    <div className="flex min-h-screen bg-chrome-50">
      <aside
        className={cn(
          "flex shrink-0 flex-col border-r border-chrome-200 bg-white transition-[width] duration-200",
          navOpen ? "w-56" : "w-14"
        )}
      >
        <div className={cn("flex h-14 items-center border-b border-chrome-200 px-3", navOpen ? "gap-2" : "justify-center")}>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-chrome-900 text-[11px] font-bold text-white">
            CL
          </div>
          {navOpen && (
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-chrome-900">Clario</p>
              <p className="truncate text-[10px] text-chrome-500">AML & KYT</p>
            </div>
          )}
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-3" aria-label="Primary">
          {NAV_GROUPS.map((group) => (
            <div key={group.label} className="mb-4">
              {navOpen && (
                <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-wider text-chrome-400">
                  {group.label}
                </p>
              )}
              <ul className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const active =
                    pathname === item.href ||
                    (item.href !== "/" && pathname.startsWith(item.href));
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        title={item.label}
                        aria-label={item.label}
                        aria-current={active ? "page" : undefined}
                        className={cn(
                          "flex items-center gap-2.5 rounded-md px-2 py-2 text-sm transition-colors",
                          navOpen ? "" : "justify-center",
                          active
                            ? "bg-accent-muted font-medium text-accent"
                            : "text-chrome-600 hover:bg-chrome-100 hover:text-chrome-800"
                        )}
                      >
                        <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} />
                        {navOpen && <span className="truncate">{item.label}</span>}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        <div className="border-t border-chrome-200 p-2">
          <button
            type="button"
            onClick={() => setNavOpen((v) => !v)}
            className={cn(
              "flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm text-chrome-500 hover:bg-chrome-100 hover:text-chrome-700",
              !navOpen && "justify-center"
            )}
            aria-label={navOpen ? "Collapse navigation" : "Expand navigation"}
          >
            {navOpen ? (
              <PanelLeftClose className="h-4 w-4" />
            ) : (
              <PanelLeft className="h-4 w-4" />
            )}
            {navOpen && <span>Collapse</span>}
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between gap-4 border-b border-chrome-200 bg-white px-4">
          <div className="flex min-w-0 items-center gap-3">
            <nav className="flex min-w-0 items-center text-sm text-chrome-500" aria-label="Breadcrumb">
              <Link href="/" className="shrink-0 hover:text-accent">
                Clario
              </Link>
              <span className="mx-2 text-chrome-300" aria-hidden>
                /
              </span>
              <span className="truncate font-medium text-chrome-900">{breadcrumb}</span>
            </nav>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setSearchOpen(true)}
              className="hidden items-center gap-2 rounded-md border border-chrome-200 bg-chrome-50 px-2.5 py-1.5 text-xs text-chrome-500 hover:bg-chrome-100 sm:inline-flex"
              aria-label="Open global search"
            >
              <Search className="h-3.5 w-3.5" aria-hidden />
              <span>Search</span>
              <kbd className="rounded border border-chrome-200 bg-white px-1 font-mono text-[10px] text-chrome-400">
                ⌘K
              </kbd>
            </button>

            <span className="rounded-md border border-chrome-200 bg-chrome-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-chrome-600">
              Demo
            </span>

            {apiConnected === true && (
              <span
                className="hidden max-w-[220px] truncate rounded-md border border-chrome-200 bg-white px-2 py-0.5 text-[10px] font-medium text-chrome-600 lg:inline"
                title={bedrockModel || "Amazon Bedrock"}
              >
                Powered by Amazon Bedrock (Nova)
                {bedrockShort ? ` · ${bedrockShort}` : ""}
              </span>
            )}

            <label className="sr-only" htmlFor="tenant-switcher">
              Jurisdiction / Policy
            </label>
            <select
              id="tenant-switcher"
              value={tenant}
              onChange={(e) => setTenant(e.target.value)}
              className="rounded-md border border-chrome-200 bg-white px-2 py-1.5 text-xs font-medium text-chrome-700"
              aria-label="Switch jurisdiction policy"
              title="Jurisdiction / Policy"
            >
              {TENANTS.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>

            <label className="sr-only" htmlFor="role-switcher">
              Active role
            </label>
            <select
              id="role-switcher"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="rounded-md border border-chrome-200 bg-white px-2 py-1.5 text-xs font-medium text-chrome-700"
              aria-label="Switch role"
            >
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>
        </header>

        {apiConnected === false && (
          <div
            className="border-b border-chrome-200 bg-chrome-100 px-4 py-2 text-center text-xs text-chrome-600"
            role="status"
            title={API_BASE}
          >
            Demo / offline mode — API unreachable; explore the UI with local/demo data where available.
          </div>
        )}

        <main className="flex-1 overflow-auto">{children}</main>
      </div>

      {searchOpen && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-chrome-900/40 pt-[15vh]"
          role="dialog"
          aria-modal="true"
          aria-label="Global search"
          onClick={() => setSearchOpen(false)}
        >
          <div
            className="w-full max-w-lg overflow-hidden rounded-lg border border-chrome-200 bg-white shadow-sm"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 border-b border-chrome-200 px-3">
              <Search className="h-4 w-4 text-chrome-400" aria-hidden />
              <input
                autoFocus
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                placeholder="Jump to page…"
                className="flex-1 border-0 bg-transparent py-3 text-sm text-chrome-900 outline-none placeholder:text-chrome-400"
                aria-label="Search navigation"
              />
              <kbd className="rounded border border-chrome-200 px-1.5 text-[10px] text-chrome-400">
                Esc
              </kbd>
            </div>
            <ul className="max-h-72 overflow-auto py-1">
              {searchHits.map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={() => {
                        setSearchOpen(false);
                        setSearchQ("");
                      }}
                      className="flex items-center gap-2.5 px-3 py-2 text-sm text-chrome-700 hover:bg-chrome-50"
                    >
                      <Icon className="h-4 w-4 text-chrome-400" />
                      {item.label}
                    </Link>
                  </li>
                );
              })}
              {searchHits.length === 0 && (
                <li className="px-3 py-6 text-center text-sm text-chrome-400">No matches</li>
              )}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
