import { cn } from "@/lib/cn";

interface StatCardProps {
  label: string;
  value: React.ReactNode;
  className?: string;
}

export function StatCard({ label, value, className }: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-chrome-200 bg-white p-4 shadow-sm",
        className
      )}
    >
      <p className="stat-value text-2xl font-bold tabular-nums text-chrome-900">
        {value}
      </p>
      <p className="mt-0.5 text-xs uppercase tracking-wide text-chrome-500">
        {label}
      </p>
    </div>
  );
}
