"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { Scale, CheckCircle2, AlertTriangle, AlertCircle, FileSearch } from "lucide-react";

export default function ReconciliationTab({ caseId }: { caseId: string }) {
  const [reconData, setReconData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchRecon() {
      setLoading(true);
      const { data, status } = await apiFetch(`/api/cases/${caseId}/reconciliation`);
      if (status === 200) {
        setReconData(data);
      }
      setLoading(false);
    }
    fetchRecon();
  }, [caseId]);

  if (loading) {
    return <div className="text-center p-8 text-slate-400 font-mono text-sm">Loading Reconciliation Data...</div>;
  }

  if (!reconData) {
    return (
      <div className="p-4 bg-navy-800/50 rounded-xl border border-dashed border-white/10 text-center text-sm text-slate-400">
        Reconciliation data not available.
      </div>
    );
  }

  const renderStatusIcon = (status: string) => {
    switch(status) {
      case "MATCHED":
        return <CheckCircle2 className="w-5 h-5 text-emerald-400" />;
      case "VARIANCE":
        return <AlertTriangle className="w-5 h-5 text-amber-400" />;
      case "MISSING_EVIDENCE":
        return <FileSearch className="w-5 h-5 text-rose-400" />;
      case "REVIEW_REQUIRED":
        return <AlertCircle className="w-5 h-5 text-blue-400" />;
      default:
        return <span className="text-slate-400">-</span>;
    }
  };

  const renderStatusBadge = (status: string) => {
    switch(status) {
      case "MATCHED":
        return <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px] font-mono">MATCHED</span>;
      case "VARIANCE":
        return <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[10px] font-mono">VARIANCE</span>;
      case "MISSING_EVIDENCE":
        return <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30 text-[10px] font-mono">MISSING EVIDENCE</span>;
      case "REVIEW_REQUIRED":
        return <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30 text-[10px] font-mono">REVIEW REQUIRED</span>;
      default:
        return <span className="px-2 py-0.5 rounded bg-slate-500/20 text-slate-400 border border-slate-500/30 text-[10px] font-mono">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="glass-panel p-6 rounded-2xl border border-white/10 shadow-lg">
        <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-6">
          <Scale className="w-5 h-5 text-blue-400" />
          Deterministic Reconciliation Checks
        </h3>
        
        <div className="space-y-4">
          {reconData.checks?.map((check: any, i: number) => (
            <div key={i} className="p-4 rounded-xl bg-navy-800/80 border border-white/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 hover:bg-white/[0.02] transition-colors">
              <div className="flex items-start gap-4">
                <div className="mt-1">{renderStatusIcon(check.status)}</div>
                <div>
                  <div className="text-sm font-bold text-white mb-1">{check.rule_name}</div>
                  <div className="text-xs text-slate-400 max-w-xl">{check.description}</div>
                  {check.details && Object.keys(check.details).length > 0 && (
                    <div className="mt-2 text-[10px] font-mono text-slate-500">
                      {JSON.stringify(check.details)}
                    </div>
                  )}
                </div>
              </div>
              <div className="shrink-0">{renderStatusBadge(check.status)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
