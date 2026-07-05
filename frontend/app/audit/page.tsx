"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { History, ShieldCheck, Lock, CheckCircle2, AlertCircle, RefreshCw, FileText } from "lucide-react";

export default function AuditTrailPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPreview, setIsPreview] = useState(false);

  const loadAuditLogs = async () => {
    setLoading(true);
    setError(null);
    setIsPreview(false);
    const { data, status, error: fetchErr } = await apiFetch<any[]>("/api/audit/logs");
    if (status === 200 && Array.isArray(data) && data.length > 0) {
      setLogs(data);
    } else {
      // If endpoint not accessible or empty, fallback to preview/planned demo records
      setIsPreview(true);
      setLogs([
        {
          id: "AUD-8821",
          timestamp: new Date().toISOString(),
          actor: "sa@bank.example",
          actor_role: "SANCTION_AUTHORITY",
          event_type: "MANDATE_VERIFICATION_PASS",
          resource: "Case SHAKTI_001",
          event_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
        {
          id: "AUD-8820",
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          actor: "credit@bank.example",
          actor_role: "CREDIT_ANALYST",
          event_type: "CAS_EVALUATION_EXECUTE",
          resource: "Case SHAKTI_001",
          event_hash: "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
        },
        {
          id: "AUD-8819",
          timestamp: new Date(Date.now() - 7200000).toISOString(),
          actor: "system@bank.example",
          actor_role: "SYSTEM_ADMIN",
          event_type: "BOLA_SCOPE_ENFORCE",
          resource: "Region RJ-JAIPUR",
          event_hash: "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e",
        },
      ]);
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
          className="px-4 py-2.5 bg-navy-800 hover:bg-navy-700 text-white text-xs font-semibold rounded-xl border border-white/10 flex items-center gap-2 transition-all shadow-sm shrink-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-pulse-400" : ""}`} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {isPreview && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center gap-3 text-amber-300 text-xs font-mono">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
          <span>[PREVIEW / PLANNED DEMO DATA] Displaying prototype audit events (Live database trail currently empty or offline).</span>
        </div>
      )}

      <div className="glass-panel rounded-2xl border border-white/10 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/10 bg-navy-800/50 text-[11px] font-mono uppercase text-slate-400 tracking-wider">
                <th className="py-4 px-6">Event Ref & Timestamp</th>
                <th className="py-4 px-6">Actor / Role</th>
                <th className="py-4 px-6">Action Executed</th>
                <th className="py-4 px-6">Target Resource</th>
                <th className="py-4 px-6 text-right">SHA-256 Cryptographic Seal</th>
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
      </div>
    </div>
  );
}
