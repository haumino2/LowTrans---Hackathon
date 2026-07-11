import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/cn";

interface RiskGaugeProps {
  level: string;
  score: number;
  /** When false, gauge is muted and framed as detection-only (pre-triage). */
  investigated?: boolean;
  decision?: string;
  /** 0–1 confidence from triage_result */
  confidence?: number;
  className?: string;
}

const RISK_COLOR: Record<string, string> = {
  low: "var(--risk-clear)",
  medium: "var(--risk-review)",
  high: "var(--risk-escalate)",
};

const SEGMENT = {
  low: "var(--risk-clear)",
  medium: "var(--risk-review)",
  high: "var(--risk-escalate)",
} as const;

const MUTED = {
  track: "var(--chrome-200)",
  low: "var(--chrome-300)",
  medium: "var(--chrome-400)",
  high: "var(--chrome-500)",
  needle: "var(--chrome-500)",
} as const;

/** Map KYT 0–100 onto needle angle across the semicircle (−90° … +90°). */
function needleAngle(score: number): number {
  const clamped = Math.max(0, Math.min(100, score));
  return -90 + (clamped / 100) * 180;
}

function formatLevel(level: string): string {
  if (!level) return "—";
  return level.charAt(0).toUpperCase() + level.slice(1).toLowerCase();
}

export function RiskGauge({
  level,
  score,
  investigated = false,
  decision,
  confidence,
  className,
}: RiskGaugeProps) {
  const levelKey = (level || "medium").toLowerCase();
  const riskColor = RISK_COLOR[levelKey] || RISK_COLOR.medium;
  const needleColor = investigated ? riskColor : MUTED.needle;
  const rotation = needleAngle(
    Number.isFinite(score) ? score : levelKey === "low" ? 20 : levelKey === "high" ? 80 : 50
  );
  const confidencePct =
    confidence != null && Number.isFinite(confidence)
      ? Math.round(confidence <= 1 ? confidence * 100 : confidence)
      : null;

  // Segment endpoints on r=80 arc centered at (100,100). butt caps — no overlap blobs.
  // low 0–40 · medium 40–65 · high 65–100
  return (
    <div className={cn("flex flex-col items-center text-center", className)}>
      <p className="text-sm font-semibold text-chrome-900">Detection KYT (inbound)</p>
      <p className="mt-0.5 max-w-[16rem] text-xs leading-snug text-chrome-500">
        Score from transaction monitoring that raised this alert — not the investigation verdict.
      </p>

      <div
        className={cn(
          "relative mt-3 h-28 w-48 transition-opacity",
          !investigated && "opacity-60"
        )}
      >
        <svg viewBox="0 0 200 110" className="h-full w-full" aria-hidden>
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke={MUTED.track}
            strokeWidth="14"
            strokeLinecap="round"
          />
          <path
            d="M 20 100 A 80 80 0 0 1 80.89 36.11"
            fill="none"
            stroke={investigated ? SEGMENT.low : MUTED.low}
            strokeWidth="14"
            strokeLinecap="butt"
          />
          <path
            d="M 80.89 36.11 A 80 80 0 0 1 133.78 42.89"
            fill="none"
            stroke={investigated ? SEGMENT.medium : MUTED.medium}
            strokeWidth="14"
            strokeLinecap="butt"
          />
          <path
            d="M 133.78 42.89 A 80 80 0 0 1 180 100"
            fill="none"
            stroke={investigated ? SEGMENT.high : MUTED.high}
            strokeWidth="14"
            strokeLinecap="butt"
          />
          <g transform={`rotate(${rotation}, 100, 100)`}>
            <line
              x1="100"
              y1="100"
              x2="100"
              y2="35"
              stroke={needleColor}
              strokeWidth="3"
              strokeLinecap="round"
            />
            <circle cx="100" cy="100" r="6" fill={needleColor} />
          </g>
        </svg>
      </div>

      {investigated ? (
        <div className="mt-1 space-y-1.5">
          <p className="text-lg font-semibold tabular-nums" style={{ color: riskColor }}>
            Detection KYT {score}{" "}
            <span className="font-medium">({formatLevel(level)})</span>
          </p>
          {decision && (
            <p className="text-sm text-chrome-700">
              <span className="text-chrome-400" aria-hidden>
                →
              </span>{" "}
              <span className="font-medium text-chrome-900">Agent disposition:</span>{" "}
              <span className="font-semibold uppercase tracking-wide text-chrome-900">
                {decision}
              </span>
              {confidencePct != null && (
                <span className="tabular-nums text-chrome-600"> ({confidencePct}%)</span>
              )}
            </p>
          )}
          <p className="max-w-[18rem] text-[11px] leading-snug text-chrome-500">
            Disposition is the investigated outcome from the 4-agent workflow — see rationale below.
          </p>
        </div>
      ) : (
        <div className="mt-1 space-y-2">
          <p className="text-2xl font-bold tabular-nums text-chrome-500">
            {score}
            <span className="ml-1.5 text-base font-medium capitalize text-chrome-400">
              {formatLevel(level)}
            </span>
          </p>
          <Badge tone="neutral">Not investigated yet</Badge>
          <p className="max-w-[16rem] text-xs leading-snug text-chrome-600">
            Run Agent Workflow to produce an investigated disposition
          </p>
        </div>
      )}
    </div>
  );
}
