"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/api";
import { formatCurrency, humanise } from "@/lib/formatters";
import {
  FolderKanban,
  Clock,
  Activity,
  ShieldCheck,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
} from "lucide-react";



const humaniseEnum = (str: string) => {
  if (!str) return "-";
  return str.split('_').map(word => word.charAt(0) + word.slice(1).toLowerCase()).join(' ');
};

export default function DashboardPage() {
  const { user } = useAuth();
  const [cases, setCases] = useState<unknown[]>([]);
  const [summary, setSummary] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  const loadCases = async () => {
    setLoading(true);
    const [casesRes, summaryRes] = await Promise.all([
      apiFetch<unknown[]>("/api/cases"),
      apiFetch<unknown>("/api/cases/summary"),
    ]);
    if (casesRes.status === 200 && Array.isArray(casesRes.data)) {
      setCases(casesRes.data);
    } else {
      setCases([]);
    }
    if (summaryRes.status === 200 && summaryRes.data) {
      setSummary(summaryRes.data);
    } else {
      setSummary(null);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadCases();
  }, []);

  const totalPipelineAmount = summary?.total_requested_amount ?? cases.reduce(
    (sum, c) => sum + (Number(c.requested_amount) || 0),
    0
  );

  const totalCasesCount = summary?.active_cases ?? cases.length;

  const analystReviewCount = summary?.awaiting_analyst ?? cases.filter(
    (c) => ["INITIATED", "EVIDENCE_GATHERING"].includes(c.status)
  ).length;

  const sanctionReviewCount = summary?.awaiting_human_decision ?? cases.filter(
    (c) => c.status === "DECISION_PENDING"
  ).length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Compact Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-light-text tracking-tight">
            MSME Credit Assessment Workspace
          </h1>
          <p className="text-light-secondary text-sm mt-1">
            {user?.role ? humaniseEnum(user.role) : "Banker"} Scope • Role-scoped application pipeline
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadCases}
            disabled={loading}
            className="px-4 py-2 bg-white text-light-text font-medium text-sm rounded-lg border border-light-border hover:bg-light-elevated transition-all shadow-sm flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-brand-teal" : ""}`} />
            <span>Refresh</span>
          </button>
          {user?.role !== "SYSTEM_ADMIN" && (
            <Link
              href="/cases"
              className="px-4 py-2 bg-brand-teal hover:bg-brand-tealHover text-white font-medium text-sm rounded-lg transition-all shadow-sm flex items-center gap-2"
            >
              <FolderKanban className="w-4 h-4" />
              <span>Case Inventory</span>
            </Link>
          )}
        </div>
      </div>

      {/* Primary Dashboard Content - 4 Metric Cards */}
      {user?.role !== "SYSTEM_ADMIN" && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-card p-5 group">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-light-secondary font-medium uppercase tracking-wider">Scoped Applications</span>
              <FolderKanban className="w-5 h-5 text-brand-teal" />
            </div>
            <div className="text-2xl font-bold text-light-text">
              {loading ? "..." : totalCasesCount}
            </div>
            <div className="text-xs text-light-muted mt-1">
              {loading ? "..." : formatCurrency(totalPipelineAmount)} Pipeline
            </div>
          </div>

          <div className="glass-card p-5 group">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-light-secondary font-medium uppercase tracking-wider">Pending Analyst Review</span>
              <Clock className="w-5 h-5 text-brand-amber" />
            </div>
            <div className="text-2xl font-bold text-light-text">
              {loading ? "..." : analystReviewCount}
            </div>
            <div className="text-xs text-light-muted mt-1">
              Requires evaluation
            </div>
          </div>

          <div className="glass-card p-5 group">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-light-secondary font-medium uppercase tracking-wider">Pending Sanction</span>
              <Activity className="w-5 h-5 text-brand-red" />
            </div>
            <div className="text-2xl font-bold text-light-text">
              {loading ? "..." : sanctionReviewCount}
            </div>
            <div className="text-xs text-light-muted mt-1">
              Requires sanctioning authority
            </div>
          </div>

          <div className="glass-card p-5 group">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-light-secondary font-medium uppercase tracking-wider">Evidence Coverage</span>
              <ShieldCheck className="w-5 h-5 text-brand-teal" />
            </div>
            <div className="text-sm font-bold text-light-text leading-tight mt-1">
              GST, Bank, EPFO and invoice evidence available
            </div>
            <div className="text-xs text-light-muted mt-1">
              Sandbox dataset
            </div>
          </div>
        </div>
      )}

      {/* Main Grid for Table & Governance */}
      <div className={`grid grid-cols-1 ${user?.role !== "SYSTEM_ADMIN" ? "lg:grid-cols-3" : ""} gap-6`}>
        {/* Application Pipeline Table */}
        {user?.role !== "SYSTEM_ADMIN" && (
          <div className="lg:col-span-2 glass-card overflow-hidden">
            <div className="p-4 sm:p-5 border-b border-light-border bg-light-elevated flex items-center justify-between">
              <h2 className="text-lg font-bold text-light-text">Role-scoped application pipeline</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-light-bg text-light-secondary text-xs uppercase font-medium">
                  <tr>
                    <th className="px-5 py-3">Business</th>
                    <th className="px-5 py-3">Facility</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-light-border bg-white">
                  {loading ? (
                    <tr><td colSpan={4} className="px-5 py-8 text-center text-light-muted">Loading pipeline...</td></tr>
                  ) : cases.length === 0 ? (
                    <tr><td colSpan={4} className="px-5 py-8 text-center text-light-muted">No cases in your scope.</td></tr>
                  ) : (
                    cases.slice(0, 5).map((c) => (
                      <tr key={c.id} className="hover:bg-light-bg transition-colors">
                        <td className="px-5 py-4">
                          <div className="font-bold text-light-text">{c.business_name}</div>
                          <div className="text-xs text-light-muted mt-0.5">{c.id}</div>
                        </td>
                        <td className="px-5 py-4">
                          <div className="font-medium text-light-text">{humaniseEnum(c.facility_type)}</div>
                          <div className="text-xs text-light-muted mt-0.5">{formatCurrency(c.requested_amount)}</div>
                        </td>
                        <td className="px-5 py-4">
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-light-elevated border border-light-border text-light-secondary">
                            {humaniseEnum(c.status)}
                          </span>
                        </td>
                        <td className="px-5 py-4 text-right">
                          <Link href={`/cases/${c.id}`} className="text-brand-teal hover:text-brand-tealHover font-medium text-xs flex items-center justify-end gap-1">
                            Open <ArrowRight className="w-3 h-3" />
                          </Link>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            {cases.length > 5 && (
              <div className="p-3 bg-light-bg text-center border-t border-light-border">
                <Link href="/cases" className="text-xs font-medium text-light-secondary hover:text-light-text">
                  View all {cases.length} cases
                </Link>
              </div>
            )}
          </div>
        )}

        {/* Compact Governance & Access Controls */}
        <div className="glass-card p-5 sm:p-6 flex flex-col">
          <div className="w-10 h-10 rounded-lg bg-light-elevated border border-light-border flex items-center justify-center text-brand-teal mb-4">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-light-text mb-2">Governance & Access Controls</h3>
          <p className="text-xs text-light-secondary leading-relaxed mb-4">
            Vyapar Pulse implements enterprise Role-Scoped Access. Users can only access, evaluate, or sanction credit cases within their assigned scopes.
          </p>
          <ul className="space-y-3 text-xs text-light-secondary font-medium">
            <li className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-brand-softTeal text-brand-teal flex items-center justify-center shrink-0">RM</div>
              <span>Branch origination & KYC</span>
            </li>
            <li className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-brand-softAmber text-brand-amber flex items-center justify-center shrink-0">CA</div>
              <span>Credit & Assessment Evaluation</span>
            </li>
            <li className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-brand-softRed text-brand-red flex items-center justify-center shrink-0">SA</div>
              <span>Mandate-capped Approvals</span>
            </li>
          </ul>

          <div className="mt-auto pt-5 border-t border-light-border flex items-center justify-between text-xs">
            <span className="text-light-muted">Audit Status:</span>
            <span className="text-brand-teal flex items-center gap-1 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" /> Tamper-Evident Chain
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
