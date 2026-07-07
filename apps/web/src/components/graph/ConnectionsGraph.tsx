"use client";

import { useCallback, useEffect, useMemo, useState, type MouseEvent } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  MarkerType,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { AlertTriangle, User, Wallet, Shuffle, Building2 } from "lucide-react";
import { api, type GraphData } from "@/lib/api";

const RISK_STYLES: Record<string, { bg: string; border: string; text: string }> = {
  low: { bg: "#ecfdf5", border: "#6ee7b7", text: "#047857" },
  medium: { bg: "#fffbeb", border: "#fcd34d", text: "#b45309" },
  high: { bg: "#fef2f2", border: "#fca5a5", text: "#b91c1c" },
};

const TYPE_ICONS: Record<string, typeof User> = {
  customer: User,
  wallet: Wallet,
  mixer: Shuffle,
  counterparty: Building2,
};

function GraphNode({
  data,
}: {
  data: {
    label: string;
    subtitle: string;
    risk: string;
    nodeType: string;
    flagged: boolean;
  };
}) {
  const style = RISK_STYLES[data.risk] ?? RISK_STYLES.medium;
  const Icon = TYPE_ICONS[data.nodeType] ?? Wallet;

  return (
    <div
      className={`rounded-lg border-2 px-3 py-2 shadow-sm min-w-[140px] ${
        data.flagged ? "ring-2 ring-red-400 ring-offset-1" : ""
      }`}
      style={{ backgroundColor: style.bg, borderColor: style.border }}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-400 !w-2 !h-2" />
      <div className="flex items-start gap-2">
        <Icon className="h-4 w-4 shrink-0 mt-0.5" style={{ color: style.text }} />
        <div>
          <p className="text-xs font-semibold text-gray-900 leading-tight">{data.label}</p>
          <p className="text-[10px] text-gray-500 mt-0.5">{data.subtitle}</p>
          {data.flagged && (
            <span className="inline-flex items-center gap-0.5 mt-1 text-[10px] font-medium text-red-600">
              <AlertTriangle className="h-3 w-3" />
              Flagged
            </span>
          )}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-gray-400 !w-2 !h-2" />
    </div>
  );
}

const nodeTypes = { graphNode: GraphNode };

interface Props {
  alertId: string;
  highlightedNodes?: string[];
}

export function ConnectionsGraph({ alertId, highlightedNodes = [] }: Props) {
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .getGraph(alertId)
      .then(setGraph)
      .catch(() => setError("No connection graph available for this alert"))
      .finally(() => setLoading(false));
  }, [alertId]);

  const flaggedSet = useMemo(() => {
    const ids = new Set(graph?.flagged_node_ids ?? []);
    highlightedNodes.forEach((id) => ids.add(id));
    return ids;
  }, [graph, highlightedNodes]);

  const { nodes, edges } = useMemo(() => {
    if (!graph) return { nodes: [] as Node[], edges: [] as Edge[] };

    const nodes: Node[] = graph.nodes.map((n) => ({
      id: n.id,
      type: "graphNode",
      position: n.position,
      data: {
        label: n.label,
        subtitle: n.subtitle,
        risk: n.risk,
        nodeType: n.type,
        flagged: flaggedSet.has(n.id),
      },
    }));

    const edges: Edge[] = graph.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      animated: flaggedSet.has(e.source) || flaggedSet.has(e.target),
      style: {
        stroke: flaggedSet.has(e.source) || flaggedSet.has(e.target) ? "#ef4444" : "#94a3b8",
        strokeWidth: flaggedSet.has(e.source) || flaggedSet.has(e.target) ? 2 : 1,
      },
      labelStyle: { fontSize: 10, fill: "#64748b" },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b8", width: 16, height: 16 },
    }));

    return { nodes, edges };
  }, [graph, flaggedSet]);

  const onNodeClick = useCallback((_: MouseEvent, node: Node) => {
    setSelectedNode(node.id);
  }, []);

  if (loading) {
    return (
      <div className="flex h-[480px] items-center justify-center rounded-xl border border-gray-200 bg-white">
        <p className="text-sm text-gray-400">Loading connection graph...</p>
      </div>
    );
  }

  if (error || !graph) {
    return (
      <div className="flex h-[480px] items-center justify-center rounded-xl border border-gray-200 bg-white">
        <p className="text-sm text-gray-400">{error ?? "Graph unavailable"}</p>
      </div>
    );
  }

  const selected = graph.nodes.find((n) => n.id === selectedNode);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5">
        <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
        <p className="text-xs text-amber-800">
          Illustrative mock graph — not a certified on-chain data source
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
        <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-2.5">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
              Connection Graph
            </p>
            <p className="text-sm font-medium text-gray-900">
              {graph.customer_name} · {graph.nodes.length} nodes · {graph.edges.length} edges
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" /> Low risk
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full bg-amber-400" /> Medium
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full bg-red-400" /> High risk
            </span>
          </div>
        </div>

        <div className="h-[480px]">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodeClick={onNodeClick}
            fitView
            minZoom={0.4}
            maxZoom={1.5}
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={16} size={1} color="#e2e8f0" />
            <Controls showInteractive={false} />
            <MiniMap
              nodeColor={(n) => {
                const risk = (n.data as { risk?: string })?.risk ?? "medium";
                return RISK_STYLES[risk]?.border ?? "#94a3b8";
              }}
              maskColor="rgba(255,255,255,0.7)"
            />
          </ReactFlow>
        </div>

        {selected && (
          <div className="border-t border-gray-200 bg-gray-50 px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Selected Node</p>
            <p className="text-sm font-medium text-gray-900">{selected.label}</p>
            <p className="text-xs text-gray-500">{selected.subtitle} · {selected.type} · {selected.risk} risk</p>
          </div>
        )}
      </div>
    </div>
  );
}
