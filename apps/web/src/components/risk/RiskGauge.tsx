interface RiskGaugeProps {
  level: string;
  score: number;
}

export function RiskGauge({ level, score }: RiskGaugeProps) {
  const colors: Record<string, string> = {
    low: "#22c55e",
    medium: "#eab308",
    high: "#ef4444",
  };
  const color = colors[level] || colors.medium;
  const rotation = level === "low" ? -60 : level === "medium" ? 0 : 60;

  return (
    <div className="flex flex-col items-center">
      <div className="relative h-28 w-48">
        <svg viewBox="0 0 200 110" className="h-full w-full">
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="14"
            strokeLinecap="round"
          />
          <path
            d="M 20 100 A 80 80 0 0 1 100 25"
            fill="none"
            stroke="#22c55e"
            strokeWidth="14"
            strokeLinecap="round"
          />
          <path
            d="M 100 25 A 80 80 0 0 1 140 55"
            fill="none"
            stroke="#eab308"
            strokeWidth="14"
            strokeLinecap="round"
          />
          <path
            d="M 140 55 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#ef4444"
            strokeWidth="14"
            strokeLinecap="round"
          />
          <g transform={`rotate(${rotation}, 100, 100)`}>
            <line x1="100" y1="100" x2="100" y2="35" stroke={color} strokeWidth="3" strokeLinecap="round" />
            <circle cx="100" cy="100" r="6" fill={color} />
          </g>
        </svg>
      </div>
      <p className="text-2xl font-bold capitalize" style={{ color }}>
        {level}
      </p>
      <p className="text-sm text-gray-500">Risk Level · KYT {score}</p>
    </div>
  );
}
