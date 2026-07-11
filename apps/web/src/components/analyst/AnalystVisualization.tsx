"use client";

export interface VisualizationData {
  chart_type: "bar" | "table";
  columns: string[];
  rows: unknown[][];
  label_column?: string | null;
  value_column?: string | null;
  row_count: number;
  summary: string;
  question?: string;
}

function toNumber(val: unknown): number {
  if (typeof val === "number") return val;
  return Number(String(val).replace(/,/g, "")) || 0;
}

export function AnalystVisualization({ data }: { data: VisualizationData }) {
  const { chart_type, columns, rows, label_column, value_column, summary, row_count } = data;

  if (chart_type === "bar" && label_column && value_column) {
    const labelIdx = columns.indexOf(label_column);
    const valueIdx = columns.indexOf(value_column);
    const items = rows.map((row) => ({
      label: String(row[labelIdx] ?? ""),
      value: toNumber(row[valueIdx]),
    }));
    const max = Math.max(...items.map((i) => i.value), 1);

    return (
      <div className="mt-3 space-y-3">
        <p className="text-sm font-medium text-gray-800">{summary}</p>
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <div className="mb-3 flex items-center justify-between text-xs text-gray-500">
            <span>{value_column}</span>
            <span>{row_count} results</span>
          </div>
          <div className="space-y-2">
            {items.map((item) => (
              <div key={item.label}>
                <div className="mb-1 flex justify-between text-xs text-gray-600">
                  <span className="truncate pr-2">{item.label}</span>
                  <span className="font-medium text-gray-900">
                    {item.value.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                  <div
                    className="h-full rounded-full bg-accent-muted0 transition-all"
                    style={{ width: `${Math.max((item.value / max) * 100, 4)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-3 space-y-3">
      <p className="text-sm font-medium text-gray-800">{summary}</p>
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        <div className="border-b border-gray-100 px-4 py-2 text-xs text-gray-500">
          {row_count} row(s)
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                {columns.map((c) => (
                  <th key={c} className="px-4 py-2 text-left font-medium text-gray-600">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className="border-t border-gray-100">
                  {row.map((cell, j) => (
                    <td key={j} className="px-4 py-2 text-gray-800">
                      {String(cell ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
