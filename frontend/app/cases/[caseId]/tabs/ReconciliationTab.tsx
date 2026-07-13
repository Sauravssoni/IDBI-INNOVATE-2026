"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { Scale, CheckCircle2, AlertTriangle, AlertCircle, FileSearch } from "lucide-react";

import { ReconciliationResponse, ReconciliationCheck } from "@/types";

export default function ReconciliationTab({ caseId }: { caseId: string }) {
  const [reconData, setReconData] = useState<ReconciliationResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const formatCurrency = (amount: number | string | undefined | null) => {
    if (amount === undefined || amount === null) return "₹0";
    const num = typeof amount === "string" ? parseFloat(amount) : amount;
    if (isNaN(num)) return amount;
    if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)} crore`;
    if (num >= 100000) return `₹${(num / 100000).toFixed(2)} lakh`;
    return `₹${num.toLocaleString("en-IN")}`;
  };

  useEffect(() => {
    async function fetchRecon() {
      setLoading(true);
      const { data, status } = await apiFetch<ReconciliationResponse>(`/api/cases/${caseId}/reconciliation`);
      if (status === 200 && data) {
        setReconData(data);
      }
      setLoading(false);
    }
    fetchRecon();
  }, [caseId]);

  if (loading) {
    return <div className="text-center p-8 text-light-secondary font-mono text-sm">Loading Reconciliation Data...</div>;
  }

  if (!reconData) {
    return (
      <div className="p-4 bg-light-bg rounded-xl border border-dashed border-light-border text-center text-sm text-light-secondary">
        Reconciliation data not available.
      </div>
    );
  }

  const renderStatusIcon = (status: string) => {
    switch(status) {
      case "MATCHED":
        return <CheckCircle2 className="w-5 h-5 text-emerald-600" />;
      case "VARIANCE":
        return <AlertTriangle className="w-5 h-5 text-brand-amber" />;
      case "MISSING_EVIDENCE":
        return <FileSearch className="w-5 h-5 text-brand-red" />;
      case "REVIEW_REQUIRED":
        return <AlertCircle className="w-5 h-5 text-brand-teal" />;
      default:
        return <span className="text-light-secondary">-</span>;
    }
  };

  const renderStatusBadge = (status: string) => {
    switch(status) {
      case "MATCHED":
        return <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-600 border border-emerald-200 text-[10px] font-mono">MATCHED</span>;
      case "VARIANCE":
        return <span className="px-2 py-0.5 rounded bg-brand-softAmber text-brand-amber border border-brand-amber/30 text-[10px] font-mono">VARIANCE</span>;
      case "MISSING_EVIDENCE":
        return <span className="px-2 py-0.5 rounded bg-brand-softRed text-brand-red border border-brand-red/30 text-[10px] font-mono">MISSING EVIDENCE</span>;
      case "REVIEW_REQUIRED":
        return <span className="px-2 py-0.5 rounded bg-brand-softTeal text-brand-teal border border-brand-teal/30 text-[10px] font-mono">REVIEW REQUIRED</span>;
      default:
        return <span className="px-2 py-0.5 rounded bg-light-elevated text-light-secondary border border-light-border text-[10px] font-mono">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="glass-card p-6 border border-light-border shadow-sm">
        <h3 className="text-lg font-bold text-light-text flex items-center gap-2 mb-6">
          <Scale className="w-5 h-5 text-brand-teal" />
          Deterministic Reconciliation Checks
        </h3>
        
        <div className="space-y-4">
          {reconData.checks?.map((check: ReconciliationCheck, i: number) => (
            <div key={i} className="p-4 rounded-xl bg-light-bg border border-light-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 hover:bg-light-elevated transition-colors">
              <div className="flex items-start gap-4">
                <div className="mt-1">{renderStatusIcon(check.status)}</div>
                <div>
                  <div className="text-sm font-bold text-light-text mb-1">{check.name}</div>
                  <div className="text-xs text-light-secondary max-w-xl">{check.explanation}</div>
                  {(check.observed_value !== undefined || check.reference_value !== undefined) && check.observed_value !== null && (
                    <div className="mt-2 text-[10px] font-mono text-light-muted">
                      Observed: {formatCurrency(check.observed_value)} | Reference: {formatCurrency(check.reference_value)} | Variance: {formatCurrency(check.variance_amount)} ({check.variance_percentage}%)
                    </div>
                  )}
                  {check.evidence_references && check.evidence_references.length > 0 && (
                    <div className="mt-1 text-[10px] font-mono text-light-muted">
                      Refs: {check.evidence_references.length} evidence items
                    </div>
                  )}
                </div>
              </div>
              <div className="shrink-0 flex flex-col items-end gap-1">
                {renderStatusBadge(check.status)}
                <span className="text-[9px] text-light-secondary font-mono">v{check.rule_version}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
