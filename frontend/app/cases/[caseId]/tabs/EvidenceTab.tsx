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
  const [invoiceRecords, setInvoiceRecords] = useState<any[]>([]);
  const [employmentRecords, setEmploymentRecords] = useState<any[]>([]);
  const [obligationRecords, setObligationRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchEvidence() {
      setLoading(true);
      const [gstRes, bankRes, invoiceRes, empRes, obRes] = await Promise.all([
        apiFetch(`/api/cases/${caseId}/evidence/gst`),
        apiFetch(`/api/cases/${caseId}/evidence/bank`),
        apiFetch(`/api/cases/${caseId}/evidence/invoices`),
        apiFetch(`/api/cases/${caseId}/evidence/employment`),
        apiFetch(`/api/cases/${caseId}/evidence/obligations`)
      ]);
      if (gstRes.status === 200) setGstRecords(gstRes.data || []);
      if (bankRes.status === 200) setBankRecords(bankRes.data || []);
      if (invoiceRes.status === 200) setInvoiceRecords(invoiceRes.data || []);
      if (empRes.status === 200) setEmploymentRecords(empRes.data || []);
      if (obRes.status === 200) setObligationRecords(obRes.data || []);
      setLoading(false);
    }
    fetchEvidence();
  }, [caseId]);

  if (loading) {
    return <div className="text-center p-8 text-light-secondary font-mono text-sm">Loading Evidence Data...</div>;
  }

  const renderProvenanceMarker = (metadata: any) => {
    const mode = metadata?.ingestion_mode;
    if (!mode) return <span className="px-2 py-0.5 rounded bg-light-elevated text-light-secondary border border-light-border text-xs font-mono">UNKNOWN</span>;
    switch(mode) {
      case "SEEDED_PROTOTYPE":
        return <span className="px-2 py-0.5 rounded bg-brand-softTeal text-brand-teal border border-brand-teal/30 text-[10px] font-mono">SEEDED (SANDBOX)</span>;
      case "CONNECTED_SOURCE":
        return <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-600 border border-emerald-200 text-[10px] font-mono"><CheckCircle2 className="w-3 h-3 inline mr-1" />VERIFIED SOURCE</span>;
      case "UPLOADED_DOCUMENT":
        return <span className="px-2 py-0.5 rounded bg-brand-softAmber text-brand-amber border border-brand-amber/30 text-[10px] font-mono">UPLOADED</span>;
      default:
        return <span className="px-2 py-0.5 rounded bg-light-elevated text-light-secondary border border-light-border text-[10px] font-mono">{mode}</span>;
    }
  }

  return (
    <div className="space-y-6">
      {/* GST Evidence Table */}
      <div className="glass-card p-6 border border-light-border shadow-sm">
        <h3 className="text-lg font-bold text-light-text flex items-center gap-2 mb-4">
          <FileText className="w-5 h-5 text-brand-teal" />
          GST Filings (GSTR-3B)
        </h3>
        
        {gstRecords.length === 0 ? (
          <div className="p-4 bg-light-bg rounded-xl border border-dashed border-light-border text-center text-sm text-light-secondary">
            No GST records found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs font-mono text-light-secondary bg-light-bg">
                <tr>
                  <th className="px-4 py-3 rounded-l-xl">Period</th>
                  <th className="px-4 py-3">Declared Revenue</th>
                  <th className="px-4 py-3">Tax Paid</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 rounded-r-xl">Provenance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-light-border">
                {gstRecords.map((r, i) => (
                  <tr key={i} className="hover:bg-light-elevated transition-colors">
                    <td className="px-4 py-3 font-mono text-light-text">{r.period}</td>
                    <td className="px-4 py-3 text-brand-teal font-mono">{formatCurrency(r.declared_revenue)}</td>
                    <td className="px-4 py-3 text-brand-red font-mono">{formatCurrency(r.tax_paid)}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 rounded bg-emerald-50 text-emerald-600 text-xs">{r.status}</span>
                    </td>
                    <td className="px-4 py-3">{renderProvenanceMarker(r.metadata)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Bank Evidence Table */}
      <div className="glass-card p-6 border border-light-border shadow-sm">
        <h3 className="text-lg font-bold text-light-text flex items-center gap-2 mb-4">
          <Database className="w-5 h-5 text-brand-teal" />
          Primary Bank Account Transactions
        </h3>
        
        {bankRecords.length === 0 ? (
          <div className="p-4 bg-light-bg rounded-xl border border-dashed border-light-border text-center text-sm text-light-secondary">
            No bank transactions found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs font-mono text-light-secondary bg-light-bg">
                <tr>
                  <th className="px-4 py-3 rounded-l-xl">Date</th>
                  <th className="px-4 py-3">Amount</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3 rounded-r-xl">Provenance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-light-border">
                {bankRecords.map((r, i) => (
                  <tr key={i} className="hover:bg-light-elevated transition-colors">
                    <td className="px-4 py-3 font-mono text-light-text">{r.date}</td>
                    <td className={`px-4 py-3 font-mono ${r.type === 'CREDIT' ? 'text-brand-teal' : 'text-light-text'}`}>
                      {formatCurrency(r.amount)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${r.type === 'CREDIT' ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-brand-red'}`}>
                        {r.type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-light-secondary">{r.category || "-"}</td>
                    <td className="px-4 py-3">{renderProvenanceMarker(r.metadata)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Invoices Evidence Table */}
      <div className="glass-card p-6 border border-light-border shadow-sm">
        <h3 className="text-lg font-bold text-light-text flex items-center gap-2 mb-4">
          <FileText className="w-5 h-5 text-brand-teal" />
          Invoices
        </h3>
        
        {invoiceRecords.length === 0 ? (
          <div className="p-4 bg-light-bg rounded-xl border border-dashed border-light-border text-center text-sm text-light-secondary">
            No invoices found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs font-mono text-light-secondary bg-light-bg">
                <tr>
                  <th className="px-4 py-3 rounded-l-xl">Date</th>
                  <th className="px-4 py-3">Counterparty</th>
                  <th className="px-4 py-3">Amount</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 rounded-r-xl">Provenance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-light-border">
                {invoiceRecords.map((r, i) => (
                  <tr key={i} className="hover:bg-light-elevated transition-colors">
                    <td className="px-4 py-3 font-mono text-light-text">{r.date}</td>
                    <td className="px-4 py-3 text-light-text font-mono">{r.counterparty}</td>
                    <td className="px-4 py-3 text-brand-teal font-mono">{formatCurrency(r.amount)}</td>
                    <td className="px-4 py-3 text-light-secondary">{r.status}</td>
                    <td className="px-4 py-3">{renderProvenanceMarker(r.metadata)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Employment Evidence Table */}
      <div className="glass-card p-6 border border-light-border shadow-sm">
        <h3 className="text-lg font-bold text-light-text flex items-center gap-2 mb-4">
          <FileText className="w-5 h-5 text-brand-teal" />
          Employment (EPFO)
        </h3>
        
        {employmentRecords.length === 0 ? (
          <div className="p-4 bg-light-bg rounded-xl border border-dashed border-light-border text-center text-sm text-light-secondary">
            No employment records found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs font-mono text-light-secondary bg-light-bg">
                <tr>
                  <th className="px-4 py-3 rounded-l-xl">Period</th>
                  <th className="px-4 py-3">Employee Count</th>
                  <th className="px-4 py-3">PF Remittance</th>
                  <th className="px-4 py-3 rounded-r-xl">Provenance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-light-border">
                {employmentRecords.map((r, i) => (
                  <tr key={i} className="hover:bg-light-elevated transition-colors">
                    <td className="px-4 py-3 font-mono text-light-text">{r.period}</td>
                    <td className="px-4 py-3 text-light-text font-mono">{r.employee_count}</td>
                    <td className="px-4 py-3 text-brand-teal font-mono">{formatCurrency(r.pf_remittance)}</td>
                    <td className="px-4 py-3">{renderProvenanceMarker(r.metadata)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Obligations Evidence Table */}
      <div className="glass-card p-6 border border-light-border shadow-sm">
        <h3 className="text-lg font-bold text-light-text flex items-center gap-2 mb-4">
          <ShieldAlert className="w-5 h-5 text-brand-teal" />
          Credit Obligations (Bureau)
        </h3>
        
        {obligationRecords.length === 0 ? (
          <div className="p-4 bg-light-bg rounded-xl border border-dashed border-light-border text-center text-sm text-light-secondary">
            No active obligations found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs font-mono text-light-secondary bg-light-bg">
                <tr>
                  <th className="px-4 py-3 rounded-l-xl">Lender</th>
                  <th className="px-4 py-3">Facility Type</th>
                  <th className="px-4 py-3">Outstanding Balance</th>
                  <th className="px-4 py-3">Monthly EMI</th>
                  <th className="px-4 py-3 rounded-r-xl">Provenance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-light-border">
                {obligationRecords.map((r, i) => (
                  <tr key={i} className="hover:bg-light-elevated transition-colors">
                    <td className="px-4 py-3 font-mono text-light-text">{r.lender}</td>
                    <td className="px-4 py-3 text-light-text">{r.facility_type}</td>
                    <td className="px-4 py-3 text-brand-red font-mono">{formatCurrency(r.outstanding_balance)}</td>
                    <td className="px-4 py-3 text-brand-red font-mono">{formatCurrency(r.monthly_emi)}</td>
                    <td className="px-4 py-3">{renderProvenanceMarker(r.metadata)}</td>
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
