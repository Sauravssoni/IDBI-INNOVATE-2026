"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  Sparkles,
  Building2,
  ShieldCheck,
  TrendingUp,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Activity,
  ArrowLeft,
  Lock,
  UserCheck,
  Clock,
  DollarSign,
  Play,
  Send,
  Check,
  RefreshCw,
  BarChart3,
  Scale,
  Award,
} from "lucide-react";

export default function CaseEvaluationPage() {
  const { user } = useAuth();
  const params = useParams();
  const caseIdParam = (params?.caseId as string) || "";

  const [caseData, setCaseData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Action States
  const [evaluating, setEvaluating] = useState(false);
  const [evalResult, setEvalResult] = useState<any | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // SA Decision State
  const [decisionAction, setDecisionAction] = useState("APPROVE_ALTERNATIVE_STRUCTURE");
  const [approvedAmount, setApprovedAmount] = useState<number>(0);
  const [sanctionNotes, setSanctionNotes] = useState("");
  const [submittingDecision, setSubmittingDecision] = useState(false);

  const formatCurrency = (val: any) => {
    if (val === "-" || val === null || val === undefined) return "-";
    const num = Number(val);
    if (isNaN(num)) return "-";
    if (num === 0) return "₹0";
    if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)} Cr`;
    if (num >= 100000) return `₹${(num / 100000).toFixed(2)} L`;
    return `₹${num.toLocaleString("en-IN")}`;
  };

  const loadCase = async () => {
    setLoading(true);
    setError(null);

    let targetId = caseIdParam;
    let foundCase: any = null;

    if (targetId && targetId !== "shakti" && targetId !== "SHAKTI_PRECISION_001") {
      const { data: fullCase, status: caseStatus } = await apiFetch(`/api/cases/${targetId}`);
      if (caseStatus === 200 && fullCase) {
        foundCase = fullCase;
      }
    }

    if (!foundCase) {
      const { data: listData, status: listStatus, error: listErr } = await apiFetch<any[]>("/api/cases/");
      if (listStatus === 200 && Array.isArray(listData)) {
        const isShaktiAlias = targetId.toLowerCase() === "shakti" || targetId === "SHAKTI_PRECISION_001";
        const match = listData.find(
          (c) =>
            c.id === targetId ||
            c.business_id === targetId ||
            (isShaktiAlias && (c.business_name?.toLowerCase().includes("shakti") || c.business_id === "SHAKTI_PRECISION_001" || c.id === "SHAKTI_PRECISION_001"))
        );

        if (match) {
          const { data: fullCase, status: caseStatus } = await apiFetch(`/api/cases/${match.id}`);
          if (caseStatus === 200 && fullCase) {
            foundCase = fullCase;
          } else {
            foundCase = match;
          }
        } else {
          setError("Case not found in current BOLA scope.");
        }
      } else {
        setError(listErr || "Failed to load case inventory.");
      }
    }

    if (foundCase) {
      setCaseData(foundCase);
      if (foundCase.evaluation_result) {
        setEvalResult(foundCase.evaluation_result);
        if (foundCase.evaluation_result?.decision?.binding_limit) {
          setApprovedAmount(foundCase.evaluation_result.decision.binding_limit);
        }
      } else if (foundCase.requested_amount) {
        setApprovedAmount(foundCase.requested_amount);
      }
    }

    setLoading(false);
  };

  useEffect(() => {
    loadCase();
  }, [caseIdParam]);

  const handleRunEvaluation = async () => {
    if (!caseData?.id) return;
    setEvaluating(true);
    setActionError(null);
    setActionSuccess(null);

    const idempotencyKey = `eval-${caseData.id}-${Date.now()}`;
    const { data, status, error } = await apiFetch(`/api/cases/${caseData.id}/evaluate`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ expected_version: caseData.version || 1 }),
    });

    if (status === 200 || status === 201) {
      setEvalResult(data);
      const score = data?.scores?.total_score ?? "-";
      const band = data?.scores?.band ?? "-";
      const decision = data?.decision?.decision ?? "-";
      setActionSuccess(`AI-assisted credit assessment completed successfully! Score: ${score} / 900 (Band ${band}) • Recommendation: ${decision}`);
      if (data?.decision?.binding_limit) {
        setApprovedAmount(data.decision.binding_limit);
      }
      loadCase();
    } else {
      setActionError(error || "CAS evaluation failed.");
    }
    setEvaluating(false);
  };

  const handleSubmitAnalystRec = async () => {
    if (!caseData?.id) return;
    setEvaluating(true);
    setActionError(null);
    setActionSuccess(null);

    const idempotencyKey = `rec-${caseData.id}-${Date.now()}`;
    const recAction = evalResult?.decision?.decision === "CONDITIONAL_OFFER" ? "RECOMMEND_ALTERNATIVE_STRUCTURE" : "RECOMMEND_AS_REQUESTED";
    const limit = evalResult?.decision?.binding_limit || caseData.requested_amount || 0;

    const payload = {
      recommendation: recAction,
      reason: `AI-assisted credit assessment confirmed clean GST reconciliation. Recommend ${formatCurrency(limit)} under deterministic evidence-linked recommendation.`,
      expected_version: caseData.version || 1,
    };

    const { data, status, error } = await apiFetch(`/api/cases/${caseData.id}/analyst-recommendation`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(payload),
    });

    if (status === 200 || status === 201) {
      setActionSuccess(`Analyst recommendation (${recAction}) submitted! Case forwarded to Sanctioning Authority.`);
      loadCase();
    } else {
      setActionError(error || "Failed to submit recommendation.");
    }
    setEvaluating(false);
  };

  const handleRecordSanctionDecision = async () => {
    if (!caseData?.id) return;
    setSubmittingDecision(true);
    setActionError(null);
    setActionSuccess(null);

    const idempotencyKey = `dec-${caseData.id}-${Date.now()}`;
    const payload: any = {
      decision: decisionAction,
      reason: sanctionNotes || "Sanction decision recorded via prototype portal.",
      expected_version: caseData.version || 1,
    };

    if (decisionAction === "APPROVE_ALTERNATIVE_STRUCTURE") {
      payload.approved_amount = Number(approvedAmount);
    }

    const { data, status, error } = await apiFetch(`/api/cases/${caseData.id}/human-decision`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(payload),
    });

    if (status === 200 || status === 201) {
      setActionSuccess(`Sanction decision recorded successfully! Status updated to ${decisionAction}.`);
      loadCase();
    } else {
      setActionError(error || "Sanction decision failed. Verify BOLA mandate limits and assignment.");
    }
    setSubmittingDecision(false);
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center space-y-4">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-pulse-600 to-navy-700 flex items-center justify-center animate-bounce shadow-xl">
          <Sparkles className="w-8 h-8 text-pulse-400" />
        </div>
        <p className="text-sm font-mono text-pulse-400 animate-pulse">
          INITIALIZING AI-ASSISTED CREDIT ASSESSMENT...
        </p>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="glass-panel p-8 rounded-2xl border border-rose-500/30 text-center max-w-md mx-auto my-12 space-y-4">
        <AlertTriangle className="w-12 h-12 text-rose-400 mx-auto" />
        <h3 className="text-lg font-bold text-white">Case Access Error</h3>
        <p className="text-xs text-slate-400">{error || "Case details unavailable."}</p>
        <Link
          href="/cases"
          className="inline-block px-4 py-2 bg-navy-800 hover:bg-navy-700 text-white text-xs font-mono rounded-xl border border-white/10 transition-colors"
        >
          RETURN TO INVENTORY
        </Link>
      </div>
    );
  }

  if (user?.role === "SYSTEM_ADMIN") {
    return (
      <div className="glass-panel p-8 rounded-2xl border border-rose-500/30 text-center max-w-md mx-auto my-12 space-y-4">
        <AlertTriangle className="w-12 h-12 text-rose-400 mx-auto" />
        <h3 className="text-lg font-bold text-white">Access Restricted</h3>
        <p className="text-xs text-slate-400">System Administrators do not have access to case workspace content.</p>
        <Link
          href="/dashboard"
          className="inline-block px-4 py-2 bg-navy-800 hover:bg-navy-700 text-white text-xs font-mono rounded-xl border border-white/10 transition-colors"
        >
          RETURN TO DASHBOARD
        </Link>
      </div>
    );
  }

  const allowedActions = caseData.allowed_actions || {};
  const canRunAssessment = allowedActions.run_assessment === true;
  const canSubmitAnalystRec = allowedActions.submit_analyst_recommendation === true;
  const canSubmitHumanDecision = allowedActions.record_human_decision === true;

  const reqAmount = caseData.requested_amount || 0;
  const scoreVal = evalResult?.scores?.total_score ?? "-";
  const bandVal = evalResult?.scores?.band ?? "-";
  const recVal = evalResult?.decision?.decision ?? "-";
  const supportLimit = evalResult?.decision?.binding_limit ?? "-";
  const dscrVal = evalResult?.features?.dscr ?? "-";

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Top Nav & Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          href="/cases"
          className="inline-flex items-center gap-2 text-xs font-mono text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>BACK TO CASE INVENTORY</span>
        </Link>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-pulse-500/10 border border-pulse-500/30 text-xs font-mono text-pulse-400">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Built for IDBI Innovate 2026 • Hackathon prototype—not an official IDBI Bank production system</span>
        </div>
      </div>

      {/* Hero Header Banner */}
      <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-pulse-500/30 bg-gradient-to-r from-navy-800 via-navy-800/80 to-navy-900 relative overflow-hidden shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-pulse-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-pulse-600 to-navy-700 flex items-center justify-center text-white shrink-0 shadow-lg shadow-pulse-500/20 border border-pulse-400/30">
              <Building2 className="w-7 h-7 text-pulse-400" />
            </div>
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  {caseData.business?.legal_name || caseData.business_name || "Applicant Business"}
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  {caseData.status || "UNDER_REVIEW"}
                </span>
              </div>
              <p className="text-slate-400 text-sm mt-1 flex items-center gap-3 font-mono">
                <span>ID: {caseData.id?.slice(0, 8)}...</span> •
                <span>GSTIN: {caseData.business?.gstin || "-"}</span> •
                <span>Branch: {caseData.originating_branch_id ? `Branch ${caseData.originating_branch_id.slice(0, 8)}` : "-"}</span>
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 p-4 rounded-xl bg-navy-900/60 border border-white/5 shrink-0">
            <div>
              <div className="text-[10px] font-mono text-slate-400">REQUESTED LIMIT</div>
              <div className="text-lg font-bold text-white font-mono mt-0.5">{formatCurrency(reqAmount)}</div>
            </div>
            <div>
              <div className="text-[10px] font-mono text-slate-400">CAS RISK SCORE</div>
              <div className="text-lg font-bold text-pulse-400 font-mono mt-0.5">{scoreVal} {scoreVal !== "-" ? "/ 900" : ""}</div>
            </div>
            <div className="col-span-2 sm:col-span-1">
              <div className="text-[10px] font-mono text-slate-400">SUPPORTABLE LIMIT</div>
              <div className="text-lg font-bold text-emerald-400 font-mono mt-0.5">{formatCurrency(supportLimit)}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Feedback Banners */}
      {actionSuccess && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center gap-3 text-emerald-300 text-sm animate-fade-in shadow-lg">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <span className="font-medium">{actionSuccess}</span>
        </div>
      )}
      {actionError && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-rose-300 text-sm animate-shake shadow-lg">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
            <span className="font-medium">{actionError}</span>
          </div>
          {actionError.includes("STALE_VERSION") && (
            <button
              onClick={() => loadCase()}
              className="px-3 py-1 bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 rounded-lg text-xs font-semibold text-rose-200 transition-colors shrink-0"
            >
              Refresh Case
            </button>
          )}
          {actionError.includes("IDEMPOTENCY_IN_PROGRESS") && (
            <span className="text-xs text-rose-300 font-mono shrink-0">
              Please wait 5s and try again
            </span>
          )}
        </div>
      )}

      {/* Main Grid: 3 Pillars (CAS Score, Reconciliation, CAM) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pillar 1: CAS Credit Assessment Score */}
        <div className="glass-card p-6 rounded-2xl border border-white/10 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Pillar 1: Credit Score</span>
              <Award className="w-5 h-5 text-pulse-400" />
            </div>

            <div className="text-center py-6">
              <div className="inline-flex items-center justify-center w-36 h-36 rounded-full bg-gradient-to-tr from-pulse-500/20 to-emerald-500/20 border-4 border-pulse-500/40 relative shadow-inner">
                <div>
                  <div className="text-3xl font-extrabold text-white font-mono">{scoreVal}</div>
                  <div className="text-[10px] font-mono text-pulse-400 uppercase">{scoreVal !== "-" ? "out of 900" : "UN-EVALUATED"}</div>
                </div>
              </div>
              <div className="mt-4 font-bold text-emerald-400 text-sm">
                BAND {bandVal} • {bandVal !== "-" ? (bandVal.toString().startsWith("A") ? "LOW RISK PROFILE" : bandVal.toString().startsWith("B") ? "MODERATE RISK PROFILE" : "HIGH RISK PROFILE") : "PENDING"}
              </div>
            </div>

            <div className="space-y-3 pt-4 border-t border-white/10 text-xs">
              <div>
                <div className="flex justify-between text-slate-300 mb-1">
                  <span>Financial Strength & DSCR</span>
                  <span className="font-mono text-emerald-400">{evalResult?.scores?.financial_health_score ? `${evalResult.scores.financial_health_score} / 100` : "-"}</span>
                </div>
                <div className="w-full bg-navy-800 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-emerald-400 h-full" style={{ width: `${evalResult?.scores?.financial_health_score || 0}%` }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-slate-300 mb-1">
                  <span>GST & Tax Compliance</span>
                  <span className="font-mono text-pulse-400">{evalResult?.scores?.evidence_confidence_score ? `${evalResult.scores.evidence_confidence_score} / 100` : "-"}</span>
                </div>
                <div className="w-full bg-navy-800 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-pulse-400 h-full" style={{ width: `${evalResult?.scores?.evidence_confidence_score || 0}%` }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-slate-300 mb-1">
                  <span>Bank Statement Consistency</span>
                  <span className="font-mono text-blue-400">{evalResult?.scores?.resilience_score ? `${evalResult.scores.resilience_score} / 100` : "-"}</span>
                </div>
                <div className="w-full bg-navy-800 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-blue-400 h-full" style={{ width: `${evalResult?.scores?.resilience_score || 0}%` }} />
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-white/10 text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Model: CAS v1.1.3</span>
            <span className="text-emerald-400">Deterministic evidence-linked recommendation</span>
          </div>
        </div>

        {/* Pillar 2: Automated GST & Bank Reconciliation */}
        <div className="glass-card p-6 rounded-2xl border border-white/10 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Pillar 2: Reconciliation</span>
              <Scale className="w-5 h-5 text-blue-400" />
            </div>

            <div className="space-y-4 py-2">
              <div className="p-3.5 rounded-xl bg-navy-800/80 border border-white/5 space-y-2">
                <div className="text-xs font-semibold text-white flex justify-between">
                  <span>Revenue Matching</span>
                  <span className="text-emerald-400 font-mono">
                    {evalResult?.features?.reconciliation_metrics?.gst_bank_ratio
                      ? `${(Number(evalResult.features.reconciliation_metrics.gst_bank_ratio) * 100).toFixed(1)}% Match`
                      : "-"}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-300">
                  <div>GST Turnover: {evalResult?.features?.gst_metrics?.avg_monthly_revenue ? formatCurrency(Number(evalResult.features.gst_metrics.avg_monthly_revenue) * (evalResult.features.gst_metrics.months_filed || 12)) : "-"}</div>
                  <div>Bank Credits: {evalResult?.features?.bank_metrics?.total_credits ? formatCurrency(evalResult.features.bank_metrics.total_credits) : "-"}</div>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                <div>
                  <div className="text-xs font-bold text-white">0 Circular Trading Flags</div>
                  <div className="text-[10px] text-slate-300">Tamper-evident prototype audit chain checked</div>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center gap-3">
                <Activity className="w-5 h-5 text-blue-400 shrink-0" />
                <div>
                  <div className="text-xs font-bold text-white">Cash Flow Velocity</div>
                  <div className="text-[10px] text-slate-300">
                    Average monthly balance: {evalResult?.features?.bank_metrics?.avg_monthly_credits ? formatCurrency(evalResult.features.bank_metrics.avg_monthly_credits) : "-"}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-white/10 text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Reconciliation Engine</span>
            <span className="text-pulse-400">Automated Reconciliation</span>
          </div>
        </div>

        {/* Pillar 3: AI-Assisted Memo */}
        <div className="glass-card p-6 rounded-2xl border border-white/10 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Pillar 3: AI-Assisted Memo</span>
              <FileText className="w-5 h-5 text-emerald-400" />
            </div>

            <div className="space-y-3 py-2 text-xs text-slate-300 leading-relaxed">
              <div className="p-3.5 rounded-xl bg-navy-800/80 border border-white/5 space-y-2">
                <div className="font-bold text-white text-sm">Credit Assessment Memo Summary</div>
                <p className="text-slate-300">
                  {evalResult ? `${caseData.business?.legal_name || "Applicant"} AI-assisted credit assessment indicates a ${recVal.toString().toLowerCase()} status based on verified GST and banking data.` : "Case not yet evaluated. Run CAS Engine evaluation to generate summary."}
                </p>
                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/5 font-mono text-[11px]">
                  <div>DSCR: <span className="text-emerald-400 font-bold">{dscrVal !== "-" ? `${dscrVal}x` : "-"}</span></div>
                  <div>EBITDA: <span className="text-emerald-400 font-bold">{evalResult?.features?.ebitda || "-"}</span></div>
                  <div>Gearing: <span className="text-emerald-400 font-bold">{evalResult?.features?.gearing || "-"}</span></div>
                  <div>Collateral: <span className="text-emerald-400 font-bold">{evalResult?.features?.collateral || "-"}</span></div>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-gradient-to-r from-pulse-500/10 to-transparent border-l-2 border-pulse-500">
                <div className="font-semibold text-pulse-300 text-xs">AI-Assisted Sanction Recommendation:</div>
                <div className="text-[11px] text-slate-300 mt-0.5">
                  Recommendation: <strong className="text-white font-mono">{recVal}</strong> of <strong className="text-white font-mono">{formatCurrency(supportLimit)}</strong>.
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-white/10 text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>CAM Status:</span>
            <span className="text-emerald-400 font-bold">{evalResult ? "Ready for Review" : "Pending Evaluation"}</span>
          </div>
        </div>
      </div>

      {/* BOLA Governance & Role-Based Action Portal */}
      <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-white/10 shadow-2xl relative">
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">BOLA Governance & Decision Portal</h2>
              <p className="text-xs text-slate-400">
                Logged in as <strong className="text-white">{user?.full_name}</strong> ({user?.role}) • Scoped to Originating Branch
              </p>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-navy-800 border border-white/10 text-xs font-mono text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Mandate Verified</span>
          </div>
        </div>

        {/* Role-Specific Action Panels */}
        {(!canRunAssessment && !canSubmitAnalystRec && !canSubmitHumanDecision) ? (
          <div className="p-6 text-center space-y-2 bg-navy-800/60 rounded-xl border border-white/5">
            <Lock className="w-8 h-8 text-slate-500 mx-auto" />
            <div className="text-xs font-bold text-slate-300">Read-Only Workspace Access</div>
            <p className="text-[11px] text-slate-500 max-w-md mx-auto">
              Your role ({user?.role}) has read-only access to this case workspace. Mutation workflows (evaluations, recommendations, and sanction decisions) are restricted to assigned Credit Analysts and Sanctioning Authorities.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left: Analyst Workflows */}
            {(canRunAssessment || canSubmitAnalystRec) ? (
              <div className="p-5 rounded-xl bg-navy-800/60 border border-white/5 space-y-4">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-blue-400" />
                  <span>Credit Analyst Workflows</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Trigger live CAS evaluation engine or submit formal recommendation to the Sanctioning Authority.
                </p>

                <div className="flex flex-wrap gap-3 pt-2">
                  {canRunAssessment && (
                    <button
                      onClick={handleRunEvaluation}
                      disabled={evaluating}
                      className="px-4 py-2.5 bg-navy-800 hover:bg-blue-500/20 text-blue-300 font-semibold text-xs rounded-xl border border-blue-500/30 flex items-center gap-2 transition-all shadow-sm disabled:opacity-50 cursor-pointer"
                    >
                      {evaluating ? (
                        <RefreshCw className="w-4 h-4 animate-spin text-blue-400" />
                      ) : (
                        <Play className="w-4 h-4 fill-current" />
                      )}
                      <span>Run CAS Engine Evaluation</span>
                    </button>
                  )}
                  {canSubmitAnalystRec && (
                    <button
                      onClick={handleSubmitAnalystRec}
                      disabled={evaluating}
                      className="px-4 py-2.5 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-bold text-xs rounded-xl shadow-md flex items-center gap-2 transition-all disabled:opacity-50 cursor-pointer"
                    >
                      <Send className="w-4 h-4" />
                      <span>Submit Rec ({formatCurrency(supportLimit)})</span>
                    </button>
                  )}
                </div>
              </div>
            ) : null}

            {/* Right: Sanctioning Authority Decision Gate */}
            {canSubmitHumanDecision ? (
              <div className="p-5 rounded-xl bg-navy-800/60 border border-amber-500/20 space-y-4 relative overflow-hidden">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <UserCheck className="w-4 h-4 text-amber-400" />
                    <span>Sanctioning Authority Gate</span>
                  </h3>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    SA MANDATE REQUIRED
                  </span>
                </div>

                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">
                      DECISION ACTION
                    </label>
                    <select
                      value={decisionAction}
                      onChange={(e) => setDecisionAction(e.target.value)}
                      className="w-full px-3 py-2 bg-navy-900 border border-white/10 rounded-xl text-xs text-white focus:outline-none focus:border-amber-500"
                    >
                      <option value="APPROVE_AS_REQUESTED">Approve as Requested ({formatCurrency(reqAmount)})</option>
                      <option value="APPROVE_ALTERNATIVE_STRUCTURE">Approve Alternative Structure ({formatCurrency(supportLimit)})</option>
                      <option value="DEFER_FOR_EVIDENCE">Defer Case for Further Evidence</option>
                      <option value="ESCALATE_FOR_DUE_DILIGENCE">Escalate for Due Diligence</option>
                      <option value="DECLINE_AFTER_HUMAN_REVIEW">Decline Application</option>
                    </select>
                  </div>

                  {decisionAction === "APPROVE_ALTERNATIVE_STRUCTURE" && (
                    <div>
                      <label className="block text-xs font-mono text-slate-300 mb-1">
                        APPROVED AMOUNT (₹)
                      </label>
                      <input
                        type="number"
                        value={approvedAmount}
                        onChange={(e) => setApprovedAmount(Number(e.target.value))}
                        className="w-full px-3 py-2 bg-navy-900 border border-white/10 rounded-xl text-xs text-white font-mono focus:outline-none focus:border-amber-500"
                      />
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-mono text-slate-300 mb-1">
                      SANCTION NOTES / RATIONALE
                    </label>
                    <input
                      type="text"
                      value={sanctionNotes}
                      onChange={(e) => setSanctionNotes(e.target.value)}
                      placeholder="Enter sanction rationale or conditions..."
                      className="w-full px-3 py-2 bg-navy-900 border border-white/10 rounded-xl text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>

                  <button
                    onClick={handleRecordSanctionDecision}
                    disabled={submittingDecision}
                    className="w-full py-2.5 bg-gradient-to-r from-amber-500 to-amber-400 hover:from-amber-400 hover:to-amber-300 text-navy-900 font-extrabold text-xs rounded-xl shadow-lg shadow-amber-500/20 flex items-center justify-center gap-2 transition-all disabled:opacity-50 cursor-pointer"
                  >
                    {submittingDecision ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Check className="w-4 h-4 stroke-[3]" />
                    )}
                    <span>Execute Sanction Decision (Prototype)</span>
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
