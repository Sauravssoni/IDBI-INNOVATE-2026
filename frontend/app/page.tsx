"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/api";
import {
  Sparkles,
  Clock,
  AlertTriangle,
  FolderKanban,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  FileText,
  Activity,
  Users,
  Building2,
  BarChart3,
  RefreshCw,
} from "lucide-react";

const formatCurrency = (val: any) => {
  if (val === undefined || val === null || val === "") return "-";
  const num = typeof val === "string" ? parseFloat(val) : Number(val);
  if (isNaN(num)) return String(val);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(num);
};

export default function DashboardPage() {
  const { user } = useAuth();
  const [cases, setCases] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadCases = async () => {
    setLoading(true);
    const [casesRes, summaryRes] = await Promise.all([
      apiFetch<any[]>("/api/cases"),
      apiFetch<any>("/api/cases/summary"),
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

  const pendingCount = summary?.awaiting_human_decision ?? cases.filter(
    (c) => c.status === "IN_REVIEW" || c.status === "SUBMITTED" || c.status === "PENDING"
  ).length;

  const shaktiCase = cases.find(
    (c) =>
      c.business_name?.toLowerCase().includes("shakti") ||
      c.id === "SHAKTI_PRECISION_001" ||
      c.id === "shakti"
  );

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Welcome Banner */}
      <div className="glass-panel p-6 sm:p-8 rounded-2xl relative overflow-hidden shadow-sm">

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-navy-700 text-xs text-pulse-500 mb-3">
              <Sparkles className="w-3.5 h-3.5" />
              <span>IDBI INNOVATE 2026 • CONTROLLED PROTOTYPE ENVIRONMENT</span>
            </div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-white tracking-tight">
              Welcome back, <span className="text-gradient">{user?.full_name || "Banker"}</span>
            </h1>
            <p className="text-slate-400 text-sm sm:text-base mt-1 max-w-2xl">
              Vyapar Pulse AI-assisted credit assessment and risk evaluation dashboard. BOLA access controls and tamper-evident prototype audit chain are active.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              onClick={loadCases}
              disabled={loading}
              className="px-4 py-3 bg-navy-800 hover:bg-navy-700 text-white font-semibold text-sm rounded-xl border border-white/10 flex items-center gap-2 transition-all shadow-sm cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-pulse-400" : ""}`} />
              <span>Refresh</span>
            </button>
            {user?.role !== "SYSTEM_ADMIN" && (
              <Link
                href="/cases"
                className="px-5 py-3 bg-pulse-500 hover:bg-pulse-600 text-white font-bold text-sm rounded-xl border border-pulse-400 flex items-center gap-2 transition-all"
              >
                <FolderKanban className="w-4 h-4" />
                <span>Case Inventory</span>
              </Link>
            )}
          </div>
        </div>

        {/* Mini Stats Bar inside Hero */}
        {user?.role !== "SYSTEM_ADMIN" && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-8 pt-6 border-t border-bank-border relative z-10">
            <div>
              <div className="text-xs text-bank-secondary">SCOPED APPLICATIONS</div>
              <div className="text-xl sm:text-2xl font-bold text-white mt-0.5">
                {loading ? "..." : totalCasesCount}
              </div>
              <div className="text-[11px] text-pulse-500">
                {loading ? "..." : formatCurrency(totalPipelineAmount)} Pipeline
              </div>
            </div>
            <div>
              <div className="text-xs text-bank-secondary">EVIDENCE COVERAGE</div>
              <div className="text-xl sm:text-2xl font-bold text-white mt-0.5">Connected</div>
              <div className="text-[11px] text-bank-muted">GST & Bank integrations</div>
            </div>
            <div>
              <div className="text-xs text-bank-secondary">POLICY ENGINE STATUS</div>
              <div className="text-xl sm:text-2xl font-bold text-white mt-0.5">Active</div>
              <div className="text-[11px] text-bank-muted">CAS evaluating cases</div>
            </div>
            <div>
              <div className="text-xs text-bank-secondary">BOLA ENFORCEMENT</div>
              <div className="text-xl sm:text-2xl font-bold text-white mt-0.5">Active</div>
              <div className="text-[11px] text-pulse-500">Mandate limits applied</div>
            </div>
          </div>
        )}
      </div>

      {/* 4 Key Metric Cards */}
      {user?.role !== "SYSTEM_ADMIN" && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-card p-5 rounded-2xl border border-white/10 hover:border-pulse-500/40 transition-all group">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-bank-secondary uppercase tracking-wider">Total Inventory</span>
              <div className="w-10 h-10 rounded-xl bg-navy-700 flex items-center justify-center text-pulse-500">
                <FolderKanban className="w-5 h-5" />
              </div>
            </div>
            <div className="text-2xl font-bold text-white">
              {loading ? "..." : `${totalCasesCount} Cases`}
            </div>
            <div className="text-xs text-bank-muted mt-2 flex items-center gap-1.5">
              <span>Active Pipeline</span>
            </div>
          </div>



          <div className="glass-card p-5 rounded-2xl border border-white/10 hover:border-amber-500/40 transition-all group">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-bank-secondary uppercase tracking-wider">Pending Sanction</span>
              <div className="w-10 h-10 rounded-xl bg-navy-700 flex items-center justify-center text-bank-warning">
                <Clock className="w-5 h-5" />
              </div>
            </div>
            <div className="text-2xl font-bold text-white">
              {loading ? "..." : `${pendingCount} Cases`}
            </div>
            <div className="text-xs text-bank-muted mt-2 flex items-center gap-1.5">
              <span>Requires Review</span>
            </div>
          </div>

          <div className="glass-card p-5 rounded-2xl border border-white/10 hover:border-pulse-500/40 transition-all group">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-bank-secondary uppercase tracking-wider">Memo Preparation</span>
              <div className="w-10 h-10 rounded-xl bg-navy-700 flex items-center justify-center text-pulse-500">
                <Activity className="w-5 h-5" />
              </div>
            </div>
            <div className="text-2xl font-bold text-white">Evidence-linked</div>
            <div className="text-xs text-bank-muted mt-2 flex items-center gap-1.5">
              <span>Summary</span>
            </div>
          </div>
        </div>
      )}

      {/* Featured Hackathon Case & System Architecture Banner */}
      <div className={`grid grid-cols-1 ${user?.role !== "SYSTEM_ADMIN" ? "lg:grid-cols-3" : ""} gap-6`}>
        {/* Case Highlight Card */}
        {user?.role !== "SYSTEM_ADMIN" && shaktiCase && (
          <div className="lg:col-span-2 glass-panel p-6 sm:p-8 rounded-2xl relative shadow-sm">
            <div className="absolute top-0 right-0 px-4 py-1 bg-navy-600 text-pulse-500 font-bold text-xs rounded-bl-xl shadow-sm border-l border-b border-bank-border">
              Featured Case Study
            </div>

            <div className="flex items-start gap-4 mb-6">
              <div className="w-12 h-12 rounded-lg bg-navy-700 flex items-center justify-center text-white shrink-0 border border-bank-border">
                <Building2 className="w-6 h-6 text-pulse-500" />
              </div>
              <div>
                <div className="text-xs font-mono text-pulse-400 uppercase tracking-wider">
                  IDBI CASE REF: {shaktiCase.id}
                </div>
                <h2 className="text-xl sm:text-2xl font-extrabold text-white mt-1">
                  {shaktiCase.business_name}
                </h2>
                <p className="text-slate-400 text-sm mt-0.5">
                  {shaktiCase.branch_name || "Branch"}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 p-4 rounded-xl bg-navy-900/60 border border-white/5 mb-6">
              <div>
                <div className="text-[10px] font-mono text-slate-400">REQUESTED LIMIT</div>
                <div className="text-base sm:text-lg font-bold text-white mt-0.5">
                  {formatCurrency(shaktiCase.requested_amount)}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-bank-secondary">SUPPORTABLE LIMIT</div>
                <div className="text-base sm:text-lg font-bold text-pulse-500 mt-0.5 font-mono">
                  {shaktiCase.evaluation_result?.binding_limit || shaktiCase.evaluation_result?.supportable_limit
                    ? formatCurrency(shaktiCase.evaluation_result.binding_limit || shaktiCase.evaluation_result.supportable_limit)
                    : "-"}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-mono text-slate-400">RECOMMENDATION</div>
                <div className="text-xs sm:text-sm font-bold text-pulse-400 mt-1 font-mono">
                  {shaktiCase.evaluation_result?.recommendation || shaktiCase.evaluation_result?.decision?.decision || "-"}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
              <div className="flex items-center gap-2 text-xs text-bank-secondary">
                <CheckCircle2 className="w-4 h-4 text-pulse-500 shrink-0" />
                <span>Evidence-linked credit assessment with tamper-evident prototype audit chain</span>
              </div>
              <Link
                href={`/cases/${shaktiCase.id}`}
                className="px-5 py-2.5 bg-pulse-500 text-white hover:bg-pulse-600 font-bold text-xs rounded-lg flex items-center gap-2 transition-all shadow-sm"
              >
                <span>View Case Details</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        )}

        {/* Quick BOLA & Audit Info Card */}
        <div className="glass-panel p-6 sm:p-8 rounded-2xl flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-lg bg-navy-700 flex items-center justify-center text-bank-info mb-4">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">BOLA Security Architecture</h3>
            <p className="text-xs text-slate-400 leading-relaxed mb-4">
              Vyapar Pulse implements enterprise Broken Object Level Authorization (BOLA). Users can only access, evaluate, or sanction credit cases within their assigned regional/branch scopes and authorization limits.
            </p>
            <ul className="space-y-2 text-xs text-slate-300 font-mono">
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-pulse-400" />
                <span>RM Scope: Branch origination & KYC</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                <span>Analyst Scope: Credit & CAS Evaluation</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                <span>SA Scope: Mandate-capped Approvals</span>
              </li>
            </ul>
          </div>

          <div className="mt-6 pt-4 border-t border-bank-border flex items-center justify-between text-xs">
            <span className="text-bank-secondary">Audit Status:</span>
            <span className="text-pulse-500 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> Tamper-Evident Prototype Audit Chain
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
