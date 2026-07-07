"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { FileText, Database, ShieldAlert, CheckCircle2 } from "lucide-react";

const formatCurrency = (val: any) => {
  if (val === "-" || val === null || val === undefined) return "-";
  const num = Number(val);
  if (isNaN(num)) return "-";
  if (num === 0) return "₹0";
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)} Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)} L`;
  return `₹${num.toLocaleString("en-IN")}`;
};

export default function EvidenceTab({ caseId }: { caseId: string }) {
  const [gstRecords, setGstRecords] = useState<any[]>([]);
  const [bankRecords, setBankRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchEvidence() {
      setLoading(true);
      const [gstRes, bankRes] = await Promise.all([
        apiFetch(`/api/cases/${caseId}/evidence/gst`),
        apiFetch(`/api/cases/${caseId}/evidence/bank`)
      ]);
      if (gstRes.status === 200) setGstRecords(gstRes.data || []);
      if (bankRes.status === 200) setBankRecords(bankRes.data || []);
      setLoading(false);
    }
    fetchEvidence();
  }, [caseId]);

  if (loading) {
    return <div className="text-center p-8 text-slate-400 font-mono text-sm">Loading Evidence Data...</div>;
  }

  const renderProvenanceMarker = (mode: string) => {
    switch(mode) {
      case "SEEDED_PROTOTYPE":
        return <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30 text-[10px] font-mono">SEEDED (SANDBOX)</span>;
      case "CONNECTED_SOURCE":
        return <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px] font-mono"><CheckCircle2 className="w-3 h-3 inline mr-1" />VERIFIED SOURCE</span>;
      default:
        return <span className="px-2 py-0.5 rounded bg-slate-500/20 text-slate-400 border border-slate-500/30 text-[10px] font-mono">{mode}</span>;
    }
  }

  return (
    <div className="space-y-6">
      {/* GST Evidence Table */}
      <div className="glass-panel p-6 rounded-2xl border border-white/10 shadow-lg">
        <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
          <FileText className="w-5 h-5 text-pulse-400" />
          GST Filings (GSTR-3B)
        </h3>
        
        {gstRecords.length === 0 ? (
          <div className="p-4 bg-navy-800/50 rounded-xl border border-dashed border-white/10 text-center text-sm text-slate-400">
            No GST records found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs font-mono text-slate-400 bg-navy-800/80">
                <tr>
                  <th className="px-4 py-3 rounded-l-xl">Period</th>
                  <th className="px-4 py-3">Declared Revenue</th>
                  <th className="px-4 py-3">Tax Paid</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 rounded-r-xl">Provenance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {gstRecords.map((r, i) => (
                  <tr key={i} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-mono text-slate-300">{r.period}</td>
                    <td className="px-4 py-3 text-emerald-400 font-mono">{formatCurrency(r.declared_revenue)}</td>
                    <td className="px-4 py-3 text-rose-400 font-mono">{formatCurrency(r.tax_paid)}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 text-xs">{r.status}</span>
                    </td>
                    <td className="px-4 py-3">{renderProvenanceMarker(r.metadata?.ingestion_mode)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Bank Evidence Table */}
      <div className="glass-panel p-6 rounded-2xl border border-white/10 shadow-lg">
        <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
          <Database className="w-5 h-5 text-blue-400" />
          Primary Bank Account Transactions
        </h3>
        
        {bankRecords.length === 0 ? (
          <div className="p-4 bg-navy-800/50 rounded-xl border border-dashed border-white/10 text-center text-sm text-slate-400">
            No bank transactions found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs font-mono text-slate-400 bg-navy-800/80">
                <tr>
                  <th className="px-4 py-3 rounded-l-xl">Date</th>
                  <th className="px-4 py-3">Amount</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3 rounded-r-xl">Provenance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {bankRecords.map((r, i) => (
                  <tr key={i} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-mono text-slate-300">{r.date}</td>
                    <td className={`px-4 py-3 font-mono ${r.type === 'CREDIT' ? 'text-emerald-400' : 'text-slate-300'}`}>
                      {formatCurrency(r.amount)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${r.type === 'CREDIT' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                        {r.type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">{r.category || "-"}</td>
                    <td className="px-4 py-3">{renderProvenanceMarker(r.metadata?.ingestion_mode)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
