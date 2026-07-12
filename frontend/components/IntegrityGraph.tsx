"use client";

import React, { useState, useEffect } from "react";
import { AlertTriangle, Info, CheckCircle2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface IntegrityNode {
  id: string;
  label: string;
  type: string;
}

interface IntegrityEdge {
  source: string;
  target: string;
  relationship: string;
  matched_identifiers: string[];
}

interface IntegrityGraphResult {
  status: string;
  reason_code: string;
  severity: string;
  relationship_path: string[];
  matched_identifiers: string[];
  technical_explanation: string;
  analyst_explanation: string;
  evidence_ids: string[];
  synthetic_demonstration: boolean;
  nodes: IntegrityNode[];
  edges: IntegrityEdge[];
}

export function IntegrityGraph({ caseId, entityName }: { caseId: string, entityName: string }) {
  const [data, setData] = useState<IntegrityGraphResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchGraph() {
      try {
        const res = await apiFetch<IntegrityGraphResult>(`/api/cases/${caseId}/integrity-graph`);
        if (res.status === 200 && res.data) {
          setData(res.data);
        } else {
          setError(res.error || "Failed to load integrity graph");
        }
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    fetchGraph();
  }, [caseId]);

  if (loading) {
    return <div className="animate-pulse h-64 bg-white/5 rounded-xl border border-white/10" />;
  }

  if (error || !data) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl flex items-center gap-3">
        <AlertTriangle className="w-5 h-5" />
        <p>Could not load Integrity Graph: {error}</p>
      </div>
    );
  }

  const getNodeColor = (type: string) => {
    if (type === "BUSINESS") return "fill-indigo-900 stroke-indigo-500 text-indigo-400";
    if (type === "PERSON") return "fill-teal-900 stroke-teal-500 text-teal-400";
    if (type === "BANK_ACCOUNT") return "fill-amber-900 stroke-amber-500 text-amber-500";
    return "fill-slate-800 stroke-slate-500 text-slate-300";
  };

  const isFlagged = data.status === "REVIEW" || data.status === "BLOCKED";

  // Simple hardcoded layout for the synthetic nodes for demonstration
  // In a real app we would use d3 or a layout engine
  const nodePositions: Record<string, { x: number, y: number }> = {};
  data.nodes.forEach((n, i) => {
    if (n.type === "PERSON") { nodePositions[n.id] = { x: 200, y: 100 }; }
    else if (n.label === entityName || n.id.startsWith("BIZ-") && i === 0) { nodePositions[n.id] = { x: 400, y: 100 }; }
    else if (n.type === "BUSINESS") { nodePositions[n.id] = { x: 600, y: 100 }; }
    else if (n.type === "BANK_ACCOUNT") { nodePositions[n.id] = { x: 500, y: 250 }; }
    else { nodePositions[n.id] = { x: 100 + i * 150, y: 150 }; }
  });

  return (
    <div className="bg-black/40 border border-white/10 rounded-xl p-6 relative overflow-hidden">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-white font-bold text-sm flex items-center gap-2">
            Entity Relationship Integrity Overlay
          </h3>
          <p className="text-xs text-gray-400 mt-1">Cross-referencing entities, directors, and accounts.</p>
        </div>
        <div className={`px-3 py-1 text-xs font-bold rounded-lg border flex items-center gap-2 ${
          isFlagged ? "bg-amber-500/10 text-amber-400 border-amber-500/20" : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
        }`}>
          {isFlagged ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
          {data.status === "REVIEW" ? "REVIEW REQUIRED" : data.status === "BLOCKED" ? "BLOCKED" : "CLEAR"}
        </div>
      </div>

      {isFlagged && (
        <div className="mb-4 bg-amber-500/5 border border-amber-500/10 rounded-lg p-4">
          <p className="text-sm text-amber-200 font-bold mb-1">Reason: {data.reason_code}</p>
          <p className="text-xs text-amber-200/70 mb-2">{data.analyst_explanation}</p>
          <div className="flex gap-2">
            {data.matched_identifiers.map(id => (
              <span key={id} className="bg-amber-500/20 text-amber-300 text-[10px] px-2 py-0.5 rounded">Matched: {id}</span>
            ))}
          </div>
        </div>
      )}

      <div className="w-full h-[350px] relative border border-white/5 bg-black/20 rounded-lg overflow-x-auto">
        <div className="min-w-[800px] h-full relative">
          <svg className="absolute inset-0 w-full h-full" style={{ minWidth: 800 }}>
            {data.edges.map((edge, i) => {
              const src = nodePositions[edge.source];
              const tgt = nodePositions[edge.target];
              if (!src || !tgt) return null;
              
              const isFlaggedEdge = isFlagged && (edge.relationship === "SHARES_BANK_ACCOUNT" || edge.relationship === "RELATED_PARTY");
              
              return (
                <path
                  key={i}
                  d={`M ${src.x} ${src.y + 20} L ${tgt.x} ${tgt.y - 20}`}
                  className={`${isFlaggedEdge ? 'stroke-amber-500' : 'stroke-teal-500/30'} fill-none`}
                  strokeWidth={isFlaggedEdge ? 2 : 1.5}
                  strokeDasharray={isFlaggedEdge ? "4 4" : "none"}
                />
              );
            })}

            {data.nodes.map((node) => {
              const pos = nodePositions[node.id] || { x: 0, y: 0 };
              const colors = getNodeColor(node.type);
              const width = 140;
              const height = 40;
              const isFlaggedNode = isFlagged && data.relationship_path.includes(node.id);
              
              return (
                <g key={node.id} transform={`translate(${pos.x - width/2}, ${pos.y - height/2})`}>
                  <rect
                    width={width}
                    height={height}
                    rx={6}
                    className={`${colors} ${isFlaggedNode ? 'stroke-amber-500 stroke-2' : 'stroke-[1.5px]'}`}
                  />
                  <text
                    x={width / 2}
                    y={height / 2}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    className={`text-[11px] font-mono font-bold ${colors.split(' ')[2]}`}
                    fill="currentColor"
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>
    </div>
  );
}
