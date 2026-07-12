"use client";

import React from "react";
import { CheckCircle2, AlertTriangle, Info } from "lucide-react";

interface Node {
  id: string;
  label: string;
  type: "root" | "source" | "data";
  status: "INTACT" | "TAMPERED" | "UNVERIFIED";
  x: number;
  y: number;
}

interface Edge {
  source: string;
  target: string;
  status: "verified" | "flagged";
}

export function IntegrityGraph({ entityName, state }: { entityName: string, state: string }) {
  // Hardcoded nodes/edges for the relationship map to avoid distribution bars
  const nodes: Node[] = [
    { id: "entity", label: entityName || "MSME Entity", type: "root", status: "INTACT", x: 400, y: 50 },
    
    // Level 1: Data Sources
    { id: "gst", label: "GST Network", type: "source", status: "INTACT", x: 200, y: 150 },
    { id: "bank", label: "Banking (AA)", type: "source", status: state === "TAMPERED" ? "TAMPERED" : "INTACT", x: 400, y: 150 },
    { id: "mca", label: "MCA / EPFO", type: "source", status: "INTACT", x: 600, y: 150 },
    
    // Level 2: Data Elements
    { id: "gst_sales", label: "Sales Data", type: "data", status: "INTACT", x: 150, y: 250 },
    { id: "gst_itc", label: "ITC Claims", type: "data", status: "INTACT", x: 250, y: 250 },
    
    { id: "bank_tx", label: "Transactions", type: "data", status: state === "TAMPERED" ? "TAMPERED" : "INTACT", x: 350, y: 250 },
    { id: "bank_bal", label: "Balances", type: "data", status: state === "TAMPERED" ? "TAMPERED" : "INTACT", x: 450, y: 250 },
    
    { id: "mca_dir", label: "Directors", type: "data", status: "INTACT", x: 550, y: 250 },
    { id: "mca_pf", label: "PF Remittances", type: "data", status: "INTACT", x: 650, y: 250 },
  ];

  const edges: Edge[] = [
    { source: "entity", target: "gst", status: "verified" },
    { source: "entity", target: "bank", status: state === "TAMPERED" ? "flagged" : "verified" },
    { source: "entity", target: "mca", status: "verified" },
    
    { source: "gst", target: "gst_sales", status: "verified" },
    { source: "gst", target: "gst_itc", status: "verified" },
    
    { source: "bank", target: "bank_tx", status: state === "TAMPERED" ? "flagged" : "verified" },
    { source: "bank", target: "bank_bal", status: state === "TAMPERED" ? "flagged" : "verified" },
    
    { source: "mca", target: "mca_dir", status: "verified" },
    { source: "mca", target: "mca_pf", status: "verified" },
  ];

  const getNodeColor = (type: string, status: string) => {
    if (status === "TAMPERED") return "fill-red-900 stroke-red-500 text-red-500";
    if (status === "UNVERIFIED") return "fill-amber-900 stroke-amber-500 text-amber-500";
    if (type === "root") return "fill-indigo-900 stroke-indigo-500 text-indigo-400";
    if (type === "source") return "fill-teal-900 stroke-teal-500 text-teal-400";
    return "fill-slate-800 stroke-slate-500 text-slate-300";
  };

  return (
    <div className="bg-black/40 border border-white/10 rounded-xl p-6 relative overflow-hidden">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-white font-bold text-sm flex items-center gap-2">
            Entity Integrity Graph (Relationship Map)
          </h3>
          <p className="text-xs text-gray-400 mt-1">Cryptographic trace of evidence sources to core entity.</p>
        </div>
        <div className={`px-3 py-1 text-xs font-bold rounded-lg border ${
          state === "TAMPERED" ? "bg-red-500/10 text-red-400 border-red-500/20" : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
        }`}>
          {state === "TAMPERED" ? "INTEGRITY BREACH DETECTED" : "VERIFIED INTACT"}
        </div>
      </div>

      <div className="w-full h-[300px] relative mt-4 border border-white/5 bg-black/20 rounded-lg overflow-x-auto">
        <div className="min-w-[800px] h-full relative">
          <svg className="absolute inset-0 w-full h-full" style={{ minWidth: 800 }}>
            {/* Draw Edges */}
            {edges.map((edge, i) => {
              const src = nodes.find(n => n.id === edge.source);
              const tgt = nodes.find(n => n.id === edge.target);
              if (!src || !tgt) return null;
              
              const isFlagged = edge.status === "flagged";
              
              return (
                <path
                  key={i}
                  d={`M ${src.x} ${src.y + 20} L ${tgt.x} ${tgt.y - 20}`}
                  className={`${isFlagged ? 'stroke-red-500' : 'stroke-teal-500/30'} fill-none`}
                  strokeWidth={isFlagged ? 2 : 1.5}
                  strokeDasharray={isFlagged ? "4 4" : "none"}
                />
              );
            })}

            {/* Draw Nodes */}
            {nodes.map((node) => {
              const colors = getNodeColor(node.type, node.status);
              const width = 120;
              const height = 40;
              return (
                <g key={node.id} transform={`translate(${node.x - width/2}, ${node.y - height/2})`}>
                  <rect
                    width={width}
                    height={height}
                    rx={6}
                    className={`${colors} stroke-[1.5px]`}
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
                  {node.status === "TAMPERED" && (
                    <circle cx={width} cy={0} r={8} className="fill-red-500" />
                  )}
                  {node.status === "INTACT" && node.type !== "root" && (
                    <circle cx={width} cy={0} r={6} className="fill-emerald-500" />
                  )}
                </g>
              );
            })}
          </svg>
        </div>
      </div>
    </div>
  );
}
