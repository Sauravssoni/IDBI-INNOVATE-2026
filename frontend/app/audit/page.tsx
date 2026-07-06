"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { History, ShieldCheck, Lock, CheckCircle2, AlertCircle, RefreshCw, FileText } from "lucide-react";

export default function AuditTrailPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAuditLogs = async () => {
    setLoading(true);
    setError(null);
    const { data, status, error: fetchErr } = await apiFetch<any[]>("/api/audit/logs");
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
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-navy-800 border border-white/10 text-xs text-emerald-400 font-mono mb-2">
            <Lock className="w-3.5 h-3.5" />
            <span>TAMPER-EVIDENT AUDIT CHAIN • BUILT FOR IDBI INNOVATE 2026</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <History className="w-8 h-8 text-pulse-400" />
            <span>Audit Log & CAS Trail</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Sequential audit trail of credit evaluations, BOLA authorization checks, and sanction decisions.
          </p>
        </div>

        <button
          onClick={loadAuditLogs}
          disabled={loading}
          className="px-4 py-2.5 bg-navy-800 hover:bg-navy-700 text-white text-xs font-semibold rounded-xl border border-white/10 flex items-center gap-2 transition-all shadow-sm shrink-0 cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-pulse-400" : ""}`} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-center gap-3 text-rose-300 text-sm font-mono">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="glass-panel rounded-2xl border border-white/10 overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-12 text-center text-slate-400 font-mono text-xs animate-pulse">
            LOADING TAMPER-EVIDENT AUDIT TRAIL...
          </div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center text-slate-400 font-mono text-xs">
            No audit events recorded in current BOLA scope.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/10 bg-navy-800/50 text-[11px] font-mono uppercase text-slate-400 tracking-wider">
                  <th className="py-4 px-6">Event Ref & Timestamp</th>
                  <th className="py-4 px-6">Actor / Role</th>
                  <th className="py-4 px-6">Action Executed</th>
                  <th className="py-4 px-6">Target Resource</th>
                  <th className="py-4 px-6 text-right">Tamper-Evident Audit Hash</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-sm">
                {logs.map((log) => {
                  const actionStr = log.event_type || log.action || "UNKNOWN_EVENT";
                  const resourceStr = log.case_id ? `Case ${log.case_id}` : log.resource || "System";
                  const actorStr = log.actor_role ? `${log.actor} (${log.actor_role})` : log.actor || "System";
                  const hashStr = log.event_hash || log.hash || "N/A";

                  return (
                    <tr key={log.id} className="hover:bg-white/[0.02] transition-colors font-mono text-xs">
                      <td className="py-4 px-6">
                        <div className="font-bold text-white">{log.id}</div>
                        <div className="text-[10px] text-slate-400">{new Date(log.timestamp).toLocaleString("en-IN")}</div>
                      </td>
                      <td className="py-4 px-6 text-slate-300 font-sans font-medium">
                        {actorStr}
                      </td>
                      <td className="py-4 px-6">
                        <span className="px-2.5 py-1 rounded bg-pulse-500/10 text-pulse-400 border border-pulse-500/30 font-bold">
                          {actionStr}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-slate-300">
                        {resourceStr}
                      </td>
                      <td className="py-4 px-6 text-right text-[11px] text-slate-500 font-mono">
                        <span className="px-2 py-1 rounded bg-navy-900 border border-white/5 text-slate-400 select-all">
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
