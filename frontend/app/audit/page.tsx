"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { History, ShieldCheck, Lock, CheckCircle2, AlertCircle, RefreshCw, FileText } from "lucide-react";
import { PortfolioAuditItem } from "@/types";

export default function AuditTrailPage() {
  const [logs, setLogs] = useState<PortfolioAuditItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAuditLogs = async () => {
    setLoading(true);
    setError(null);
    const { data, status, error: fetchErr } = await apiFetch<PortfolioAuditItem[]>("/api/audit/logs");
    if (status === 200 && Array.isArray(data)) {
      setLogs(data);
    } else {
      setError(fetchErr || "Failed to load audit logs.");
      setLogs([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadAuditLogs();
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-softTeal border border-brand-teal text-xs text-brand-teal font-bold mb-2">
            <Lock className="w-3.5 h-3.5" />
            <span>TAMPER-EVIDENT AUDIT CHAIN • BUILT FOR IDBI INNOVATE 2026</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-light-text tracking-tight flex items-center gap-3">
            <History className="w-8 h-8 text-brand-teal" />
            <span>Audit Log & CAS Trail</span>
          </h1>
          <p className="text-light-secondary text-sm mt-1">
            Sequential audit trail of credit evaluations, BOLA authorization checks, and sanction decisions.
          </p>
        </div>

        <button
          onClick={loadAuditLogs}
          disabled={loading}
          className="px-4 py-2.5 bg-white hover:bg-light-elevated text-light-text text-sm font-medium rounded-lg border border-light-border flex items-center gap-2 transition-all shadow-sm shrink-0"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-brand-teal" : ""}`} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {error && (
        <div className="p-4 bg-brand-softRed border border-brand-red rounded-lg flex items-center gap-3 text-brand-red text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="bg-white rounded-xl border border-light-border overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-12 text-center text-light-secondary font-medium text-sm animate-pulse">
            LOADING TAMPER-EVIDENT AUDIT TRAIL...
          </div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center text-light-secondary font-medium text-sm">
            No audit events recorded in current BOLA scope.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-light-border bg-light-bg text-xs font-bold uppercase text-light-secondary tracking-wider">
                  <th className="py-4 px-6">Event Ref & Timestamp</th>
                  <th className="py-4 px-6">Actor / Role</th>
                  <th className="py-4 px-6">Action Executed</th>
                  <th className="py-4 px-6">Target Resource</th>
                  <th className="py-4 px-6 text-right">Tamper-Evident Audit Hash</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-light-border text-sm">
                {logs.map((log) => {
                  const actionStr = log.event_type || "UNKNOWN_EVENT";
                  const resourceStr = log.case_id ? `Case ${log.case_id}` : "System";
                  const actorStr = log.actor || "System";
                  const hashStr = log.event_hash || "N/A";

                  return (
                    <tr key={log.id} className="hover:bg-light-bg transition-colors">
                      <td className="py-4 px-6">
                        <div className="font-bold text-light-text">{log.id}</div>
                        <div className="text-xs text-light-secondary">{log.created_at ? new Date(log.created_at as string).toLocaleString("en-IN") : "-"}</div>
                      </td>
                      <td className="py-4 px-6 text-light-text font-medium">
                        {actorStr}
                      </td>
                      <td className="py-4 px-6">
                        <span className="px-2.5 py-1 rounded bg-brand-softTeal text-brand-teal border border-brand-teal font-bold text-xs uppercase">
                          {actionStr}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-light-text font-medium">
                        {resourceStr}
                      </td>
                      <td className="py-4 px-6 text-right text-xs text-light-secondary font-mono">
                        <span className="px-2 py-1 rounded bg-light-elevated border border-light-border select-all">
                          {hashStr.length > 24 ? `${hashStr.slice(0, 16)}...${hashStr.slice(-8)}` : hashStr}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
