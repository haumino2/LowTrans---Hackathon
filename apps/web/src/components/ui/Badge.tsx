import { cn } from "@/lib/cn";

type BadgeTone = "neutral" | "clear" | "review" | "escalate" | "pending";

const TONE: Record<BadgeTone, string> = {
  neutral: "bg-chrome-100 text-chrome-700",
  pending: "bg-chrome-100 text-chrome-700",
  clear: "bg-risk-clear-bg text-risk-clear",
  review: "bg-risk-review-bg text-risk-review",
  escalate: "bg-risk-escalate-bg text-risk-escalate",
};

const STATUS_TONE: Record<string, BadgeTone> = {
  pending: "pending",
  clear: "clear",
  review: "review",
  escalate_pending: "review",
  escalate: "escalate",
  CLEAR: "clear",
  REVIEW: "review",
  ESCALATE: "escalate",
};

const RISK_TONE: Record<string, BadgeTone> = {
  low: "clear",
  medium: "review",
  high: "escalate",
};

interface BadgeProps {
  children: React.ReactNode;
  tone?: BadgeTone;
  status?: string;
  risk?: string;
  className?: string;
}

export function Badge({ children, tone, status, risk, className }: BadgeProps) {
  const resolved: BadgeTone =
    tone ??
    (status ? STATUS_TONE[status] ?? "neutral" : undefined) ??
    (risk ? RISK_TONE[risk.toLowerCase()] ?? "neutral" : undefined) ??
    "neutral";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium capitalize",
        TONE[resolved],
        className
      )}
    >
      {children}
    </span>
  );
}

export function RiskBadge({ level }: { level: string }) {
  return (
    <Badge risk={level} className="font-medium">
      {level}
    </Badge>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge status={status}>{status.replace(/_/g, " ")}</Badge>;
}
