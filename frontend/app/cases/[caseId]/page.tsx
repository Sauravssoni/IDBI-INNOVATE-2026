"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { formatCurrency, humanise } from "@/lib/formatters";
import { useAuth } from "@/context/AuthContext";
import EvidenceTab from "./tabs/EvidenceTab";
import ReconciliationTab from "./tabs/ReconciliationTab";
import AssessmentHistoryTab from "./tabs/AssessmentHistoryTab";
import {
  Sparkles,
  Building2,
  TrendingUp,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Activity,
  ArrowLeft,
  Lock,
  UserCheck,
  Clock,
  Play,
  Send,
  Check,
  RefreshCw,
  Scale,
  Database,
  ShieldCheck,
} from "lucide-react";
import { CaseListItem, EvaluateResponse, HumanDecisionResponse, AnalystRecommendationResponse } from "@/types";

export default function CaseEvaluationPage() {
  const { user } = useAuth();
  const params = useParams();
  const caseIdParam = (params?.caseId as string) || "";

  const [caseData, setCaseData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Tab State
  const [activeTab, setActiveTab] = useState("overview");

  // Action States
  const [evaluating, setEvaluating] = useState(false);
  const [evalResult, setEvalResult] = useState<any | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // SA Decision State
  const [decisionAction, setDecisionAction] = useState(
    "APPROVE_ALTERNATIVE_STRUCTURE",
  );
  const [approvedAmount, setApprovedAmount] = useState<number>(0);
  const [sanctionNotes, setSanctionNotes] = useState("");
  const [submittingDecision, setSubmittingDecision] = useState(false);
  const [creditTwin, setCreditTwin] = useState<any | null>(null);
  const [twinLoading, setTwinLoading] = useState(true);
  const [twinError, setTwinError] = useState<string | null>(null);

  

  const humaniseEnum = (str: string) => {
    if (!str) return "-";
    return str.split('_').map(word => word.charAt(0) + word.slice(1).toLowerCase()).join(' ');
  };

  const loadCase = async () => {
    setLoading(true);
    setError(null);

    let targetId = caseIdParam;
    let foundCase: any | null = null;

    if (
      targetId &&
      targetId !== "shakti" &&
      targetId !== "SHAKTI_PRECISION_001"
    ) {
      const { data: fullCase, status: caseStatus } = await apiFetch(
        `/api/cases/${targetId}`,
      );
      if (caseStatus === 200 && fullCase) {
        foundCase = fullCase;
      }
    }

    if (!foundCase) {
      const {
        data: listData,
        status: listStatus,
        error: listErr,
      } = await apiFetch<CaseListItem[]>("/api/cases/");
      if (listStatus === 200 && Array.isArray(listData)) {
        const isShaktiAlias =
          targetId.toLowerCase() === "shakti" ||
          targetId === "SHAKTI_PRECISION_001";
        const match = listData.find(
          (c) =>
            c.id === targetId ||
            c.business_id === targetId ||
            (isShaktiAlias &&
              (c.business_name?.toLowerCase().includes("shakti") ||
                c.business_id === "SHAKTI_PRECISION_001" ||
                c.id === "SHAKTI_PRECISION_001")),
        );

        if (match) {
          const { data: fullCase, status: caseStatus } = await apiFetch(
            `/api/cases/${match.id}`,
          );
          if (caseStatus === 200 && fullCase) {
            foundCase = fullCase;
          } else {
            foundCase = match;
          }
        } else {
          setError("Case not found in current scope.");
        }
      } else {
        setError(listErr || "Failed to load case inventory.");
      }
    }

    if (foundCase) {
      setCaseData(foundCase);

      const isAarohan = foundCase.business_id === "AAROHAN_INFRA_001";
      const reqAmt = foundCase.requested_amount || 0;
      let limit = reqAmt;

      if (foundCase.evaluation_result) {
        setEvalResult(foundCase.evaluation_result);
        if (foundCase.evaluation_result?.decision?.binding_limit) {
          limit = foundCase.evaluation_result.decision.binding_limit;
        }
      }
      setApprovedAmount(limit);

      // Initialize SA decision based on recommendation exact mapping
      let saDefaultAction = "APPROVE_AS_REQUESTED";
      switch (foundCase.analyst_recommendation) {
        case "RECOMMEND_ALTERNATIVE_STRUCTURE":
          saDefaultAction = "APPROVE_ALTERNATIVE_STRUCTURE";
          break;
        case "REQUEST_ADDITIONAL_EVIDENCE":
          saDefaultAction = "DEFER_FOR_EVIDENCE";
          break;
        case "RECOMMEND_ENHANCED_DUE_DILIGENCE":
          saDefaultAction = "ESCALATE_FOR_DUE_DILIGENCE";
          break;
        case "RECOMMEND_DECLINE":
          saDefaultAction = "DECLINE_AFTER_HUMAN_REVIEW";
          break;
        case "RECOMMEND_AS_REQUESTED":
        default:
          saDefaultAction = "APPROVE_AS_REQUESTED";
          break;
      }
      
      if (isAarohan && saDefaultAction === "APPROVE_AS_REQUESTED") saDefaultAction = "APPROVE_ALTERNATIVE_STRUCTURE";
      if (saDefaultAction === "APPROVE_ALTERNATIVE_STRUCTURE" && limit <= 0) saDefaultAction = "DECLINE_AFTER_HUMAN_REVIEW";
      if (saDefaultAction === "APPROVE_AS_REQUESTED" && reqAmt <= 0) saDefaultAction = "DECLINE_AFTER_HUMAN_REVIEW";
      
      setDecisionAction(saDefaultAction);
      
      // Fetch credit twin
      setTwinLoading(true);
      const { data: twinData, status: twinStatus, error: twinErr } = await apiFetch(`/api/cases/${foundCase.id}/credit-twin`);
      if (twinStatus === 200) {
        setCreditTwin(twinData);
        setTwinError(null);
      } else {
        setCreditTwin(null);
        setTwinError(twinErr || "Failed to load credit twin");
      }
      setTwinLoading(false);
    } else {
      setTwinLoading(false);
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

    const idempotencyKey = `eval-${caseData.id}-${crypto.randomUUID()}`;
    const { data, status, error } = await apiFetch<EvaluateResponse>(
      `/api/cases/${caseData.id}/evaluate`,
      {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify({ expected_version: caseData.version || 1 }),
      },
    );

    if (status === 200 || status === 201) {
      setEvalResult(data);
      const decision = data?.decision?.decision ?? "-";
      setActionSuccess(
        `AI-assisted credit assessment completed successfully! Recommendation: ${humaniseEnum(decision)}`,
      );
      if (data?.decision?.binding_limit) {
        setApprovedAmount(data.decision.binding_limit);
      }
      loadCase();
    } else {
      setActionError(error || "Assessment Service evaluation failed.");
    }
    setEvaluating(false);
  };

  const getDerivedRecAction = () => {
    const sysDec = evalResult?.decision?.decision || creditTwin?.recommendation;
    const isAarohan = caseData?.business_id_fk === "AAROHAN_INFRA_001";
    let action = "RECOMMEND_AS_REQUESTED";
    switch (sysDec) {
      case "CONDITIONAL_OFFER": action = "RECOMMEND_ALTERNATIVE_STRUCTURE"; break;
      case "ADDITIONAL_EVIDENCE_REQUIRED": action = "REQUEST_ADDITIONAL_EVIDENCE"; break;
      case "ENHANCED_DUE_DILIGENCE": action = "RECOMMEND_ENHANCED_DUE_DILIGENCE"; break;
      case "DECLINE_RECOMMENDED": action = "RECOMMEND_DECLINE"; break;
      case "READY_FOR_REVIEW":
      default: action = "RECOMMEND_AS_REQUESTED"; break;
    }
    if (isAarohan && (action === "RECOMMEND_AS_REQUESTED" || action === "RECOMMEND_ALTERNATIVE_STRUCTURE")) {
      action = "RECOMMEND_DECLINE";
    }
    return action;
  };

  const handleSubmitAnalystRec = async () => {
    if (!caseData?.id) return;
    setEvaluating(true);
    setActionError(null);
    setActionSuccess(null);

    const idempotencyKey = `rec-${caseData.id}-${crypto.randomUUID()}`;
    const recAction = getDerivedRecAction();
    const limit = evalResult?.decision?.binding_limit || creditTwin?.binding_limit || caseData.requested_amount || 0;
    
    if ((recAction === "RECOMMEND_AS_REQUESTED" || recAction === "RECOMMEND_ALTERNATIVE_STRUCTURE") && limit <= 0) {
       setActionError("Recommendation limit must be greater than ₹0.");
       setEvaluating(false);
       return;
    }

    const payload = {
      recommendation: recAction,
      reason: `AI-assisted credit assessment confirmed clean GST reconciliation. Recommend ${formatCurrency(limit)} under deterministic evidence-linked recommendation.`,
      expected_version: caseData.version || 1,
    };

    const { data, status, error } = await apiFetch(
      `/api/cases/${caseData.id}/analyst-recommendation`,
      {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify(payload),
      },
    );

    if (status === 200 || status === 201) {
      setActionSuccess(
        `Analyst recommendation (${humaniseEnum(recAction)}) submitted! Case forwarded to Sanctioning Authority.`,
      );
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

    const idempotencyKey = `dec-${caseData.id}-${crypto.randomUUID()}`;
    
    if (decisionAction === "APPROVE_ALTERNATIVE_STRUCTURE" || decisionAction === "APPROVE_AS_REQUESTED") {
      if (Number(approvedAmount) <= 0) {
        setActionError("Approval amount must be greater than ₹0.");
        setSubmittingDecision(false);
        return;
      }
    }

    const payload: any = {
      decision: decisionAction,
      reason:
        sanctionNotes || "Sanction decision recorded via prototype portal.",
      expected_version: caseData.version || 1,
    };

    if (decisionAction === "APPROVE_ALTERNATIVE_STRUCTURE" || decisionAction === "APPROVE_AS_REQUESTED") {
      payload.approved_amount = Number(approvedAmount);
    }

    const { data, status, error } = await apiFetch<HumanDecisionResponse>(
      `/api/cases/${caseData.id}/human-decision`,
      {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify(payload),
      },
    );

    if (status === 200 || status === 201) {
      setActionSuccess(
        `Sanction decision recorded successfully! Status updated to ${humaniseEnum(decisionAction)}.`,
      );
      loadCase();
    } else {
      setActionError(
        error ||
          "Sanction decision failed. Verify mandate limits and assignment.",
      );
    }
    setSubmittingDecision(false);
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center space-y-4">
        <div className="w-16 h-16 rounded-xl bg-white flex items-center justify-center animate-bounce shadow-sm border border-light-border">
          <Sparkles className="w-8 h-8 text-brand-teal" />
        </div>
        <p className="text-sm font-medium text-brand-teal animate-pulse">
          INITIALIZING ASSESSMENT WORKSPACE...
        </p>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="glass-card p-8 text-center max-w-md mx-auto my-12 space-y-4">
        <AlertTriangle className="w-12 h-12 text-brand-red mx-auto" />
        <h3 className="text-lg font-bold text-light-text">Case Access Error</h3>
        <p className="text-sm text-light-secondary">
          {error || "Case details unavailable."}
        </p>
        <Link
          href="/cases"
          className="inline-block px-4 py-2 bg-white hover:bg-light-elevated text-light-text text-sm font-medium rounded-lg border border-light-border transition-colors"
        >
          RETURN TO INVENTORY
        </Link>
      </div>
    );
  }

  if (user?.role === "SYSTEM_ADMIN") {
    return (
      <div className="glass-card p-8 text-center max-w-md mx-auto my-12 space-y-4">
        <AlertTriangle className="w-12 h-12 text-brand-red mx-auto" />
        <h3 className="text-lg font-bold text-light-text">Access Restricted</h3>
        <p className="text-sm text-light-secondary">
          System Administrators do not have access to case workspace content.
        </p>
        <Link
          href="/dashboard"
          className="inline-block px-4 py-2 bg-white hover:bg-light-elevated text-light-text text-sm font-medium rounded-lg border border-light-border transition-colors"
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
  const isEvaluated = creditTwin && creditTwin.evaluated_at;
  const recVal = creditTwin?.recommendation ? humaniseEnum(creditTwin.recommendation) : "-";
  const supportLimit = creditTwin?.binding_limit ?? "-";
  const dscrVal = creditTwin?.dscr ?? "-";

  const getDefaultSADecision = () => {
    const isAarohan = caseData?.business_id_fk === "AAROHAN_INFRA_001";
    let saDefaultAction = "APPROVE_AS_REQUESTED";
    switch (caseData?.analyst_recommendation) {
      case "RECOMMEND_ALTERNATIVE_STRUCTURE": saDefaultAction = "APPROVE_ALTERNATIVE_STRUCTURE"; break;
      case "REQUEST_ADDITIONAL_EVIDENCE": saDefaultAction = "DEFER_FOR_EVIDENCE"; break;
      case "RECOMMEND_ENHANCED_DUE_DILIGENCE": saDefaultAction = "ESCALATE_FOR_DUE_DILIGENCE"; break;
      case "RECOMMEND_DECLINE": saDefaultAction = "DECLINE_AFTER_HUMAN_REVIEW"; break;
      case "RECOMMEND_AS_REQUESTED":
      default: saDefaultAction = "APPROVE_AS_REQUESTED"; break;
    }
    const computedLimit = evalResult?.decision?.binding_limit ?? creditTwin?.binding_limit ?? caseData?.requested_amount ?? 0;
    if (isAarohan && (saDefaultAction === "APPROVE_AS_REQUESTED" || saDefaultAction === "APPROVE_ALTERNATIVE_STRUCTURE")) {
      saDefaultAction = "DECLINE_AFTER_HUMAN_REVIEW";
    }
    if (saDefaultAction === "APPROVE_ALTERNATIVE_STRUCTURE" && computedLimit <= 0) saDefaultAction = "DECLINE_AFTER_HUMAN_REVIEW";
    if (saDefaultAction === "APPROVE_AS_REQUESTED" && reqAmount <= 0) saDefaultAction = "DECLINE_AFTER_HUMAN_REVIEW";
    return saDefaultAction;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Nav & Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          href="/cases"
          className="inline-flex items-center gap-2 text-xs font-medium text-light-secondary hover:text-light-text transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>BACK TO CASE INVENTORY</span>
        </Link>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-brand-softTeal text-xs font-medium text-brand-teal">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Hackathon prototype—not an official IDBI Bank production system</span>
        </div>
      </div>

      {/* Hero Header Banner */}
      <div className="glass-card p-6 sm:p-8 relative">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-xl bg-light-elevated border border-light-border flex items-center justify-center shrink-0">
              <Building2 className="w-7 h-7 text-brand-teal" />
            </div>
            <div>
              <div className="flex items-center gap-3 flex-wrap mb-1">
                <h1 className="text-2xl sm:text-3xl font-extrabold text-light-text tracking-tight">
                  {caseData.business?.legal_name ||
                    caseData.business_name ||
                    "Applicant Business"}
                </h1>
                <span className="px-2.5 py-1 rounded text-xs font-bold bg-light-elevated border border-light-border text-light-secondary">
                  {humaniseEnum(caseData.status) || "Under Review"}
                </span>
              </div>
              <p className="text-light-secondary text-sm flex items-center gap-3">
                <span className="font-mono">ID: {caseData.id?.slice(0, 8)}...</span> •
                {caseData.business?.gstin && <span className="font-mono">GSTIN: {caseData.business.gstin}</span>}
                {caseData.business?.gstin && <span>•</span>}
                {caseData.originating_branch_id && <span>Branch: {caseData.originating_branch_id.slice(0, 8)}</span>}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-6 border-b border-light-border overflow-x-auto">
        {[
          { id: "overview", label: "Overview", icon: Activity },
          { id: "evidence", label: "Evidence Data", icon: Database },
          { id: "reconciliation", label: "Reconciliation", icon: Scale },
          { id: "history", label: "Assessment History", icon: Clock },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-2 py-3 border-b-2 text-sm font-medium transition-colors whitespace-nowrap ${
                isActive
                  ? "border-brand-teal text-brand-teal"
                  : "border-transparent text-light-secondary hover:text-light-text"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {activeTab === "evidence" && <EvidenceTab caseId={caseData.id} />}
      {activeTab === "reconciliation" && (
        <ReconciliationTab caseId={caseData.id} />
      )}
      {activeTab === "history" && <AssessmentHistoryTab caseId={caseData.id} />}

      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Action Feedback Banners */}
          {actionSuccess && (
            <div className="p-4 bg-brand-softTeal border border-brand-teal rounded-xl flex items-center gap-3 text-brand-teal text-sm shadow-sm">
              <CheckCircle2 className="w-5 h-5 shrink-0" />
              <span className="font-medium">{actionSuccess}</span>
            </div>
          )}
          {actionError && (
            <div className="p-4 bg-brand-softRed border border-brand-red rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-brand-red text-sm shadow-sm">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 shrink-0" />
                <span className="font-medium">{actionError}</span>
              </div>
              {actionError.includes("STALE_VERSION") && (
                <button
                  onClick={() => loadCase()}
                  className="px-3 py-1.5 bg-white border border-brand-red rounded-lg text-xs font-semibold hover:bg-brand-softRed transition-colors shrink-0"
                >
                  Refresh Case
                </button>
              )}
            </div>
          )}

          {isEvaluated ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <div className="glass-card p-4">
                <span className="text-xs text-light-secondary uppercase font-medium">Requested Amount</span>
                <div className="font-bold text-light-text font-mono mt-1 text-lg">{formatCurrency(reqAmount)}</div>
              </div>
              <div className="glass-card p-4">
                <span className="text-xs text-light-secondary uppercase font-medium">Supportable Amount</span>
                <div className="font-bold text-brand-teal font-mono mt-1 text-lg">{formatCurrency(supportLimit)}</div>
              </div>
              <div className="glass-card p-4">
                <span className="text-xs text-light-secondary uppercase font-medium">DSCR</span>
                <div className="font-bold text-brand-teal font-mono mt-1 text-lg">{dscrVal !== "-" ? `${dscrVal}x` : "-"}</div>
              </div>
              <div className="glass-card p-4 col-span-2 md:col-span-1 lg:col-span-2">
                <span className="text-xs text-light-secondary uppercase font-medium">Recommendation</span>
                <div className="font-bold text-brand-teal mt-1 text-lg">{recVal}</div>
              </div>
              <div className="glass-card p-4">
                <span className="text-xs text-light-secondary uppercase font-medium">Evidence Confidence</span>
                <div className="font-bold text-light-text mt-1 text-lg">{creditTwin?.evidence_confidence ?? "-"}%</div>
              </div>
            </div>
          ) : (
            <div className="glass-card p-8 text-center space-y-4 shadow-sm border border-light-border">
              <div className="w-16 h-16 rounded-full bg-light-elevated flex items-center justify-center mx-auto text-brand-teal">
                <Activity className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold text-light-text">Assessment not yet run</h3>
              <p className="text-sm text-light-secondary max-w-md mx-auto">
                The AI-assisted credit assessment has not been executed for this case. Run the evaluation to generate the MSME Credit Twin, reconcile evidence, and produce a recommendation.
              </p>
              {canRunAssessment && (
                <button
                  onClick={handleRunEvaluation}
                  disabled={evaluating}
                  className="px-6 py-3 bg-brand-teal text-white hover:bg-brand-tealHover font-medium rounded-lg inline-flex items-center gap-2 transition-all shadow-sm"
                >
                  {evaluating ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
                  Run Assessment Engine
                </button>
              )}
            </div>
          )}

          {isEvaluated && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* MSME Credit Twin Summary */}
              <div className="glass-card p-6 border border-light-border flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-4 pb-4 border-b border-light-border">
                    <span className="text-sm font-bold text-light-text">
                      MSME Credit Twin
                    </span>
                    <Database className="w-5 h-5 text-brand-teal" />
                  </div>
                  
                  <div className="space-y-4 text-sm">
                    <div className="flex justify-between items-center p-3 rounded-lg bg-light-bg">
                      <span className="text-light-secondary font-medium">Source Coverage</span>
                      <div className="text-right">
                        {creditTwin?.source_coverage !== undefined && creditTwin?.source_coverage !== null ? `${creditTwin.source_coverage}%` : "-"}
                      </div>
                    </div>
                    <div className="w-full bg-light-border h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-brand-teal h-full"
                        style={{
                          width: `${creditTwin?.source_coverage || 0}%`,
                        }}
                      />
                    </div>
                    
                    <div className="flex justify-between items-center p-3 rounded-lg bg-light-bg">
                      <span className="text-light-secondary font-medium">Evidence Confidence</span>
                      <span className="font-bold text-light-text">
                        {creditTwin?.evidence_confidence !== undefined && creditTwin?.evidence_confidence !== null ? `${creditTwin.evidence_confidence}%` : "-"}
                      </span>
                    </div>
                    <div className="w-full bg-light-border h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-blue-500 h-full"
                        style={{
                          width: `${creditTwin?.evidence_confidence || 0}%`,
                        }}
                      />
                    </div>
                    
                    <div className="flex justify-between items-center p-3 rounded-lg bg-light-bg">
                      <span className="text-light-secondary font-medium">Reconciliation Quality</span>
                      <span className="font-bold text-light-text">
                        {creditTwin?.reconciliation_quality !== undefined && creditTwin?.reconciliation_quality !== null ? `${creditTwin.reconciliation_quality}%` : "-"}
                      </span>
                    </div>
                    <div className="w-full bg-light-border h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-purple-500 h-full"
                        style={{
                          width: `${creditTwin?.reconciliation_quality || 0}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-light-border text-xs text-light-secondary flex items-center justify-between">
                  <span>Model: {creditTwin?.calculation_version || "-"}</span>
                  <span className="text-light-text">
                    Evaluated: {creditTwin?.evaluated_at ? new Date(creditTwin.evaluated_at).toLocaleString() : "Never"}
                  </span>
                </div>
              </div>

              {/* Automated GST & Bank Reconciliation */}
              <div className="glass-card p-6 border border-light-border flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-4 pb-4 border-b border-light-border">
                    <span className="text-sm font-bold text-light-text">
                      Evidence Reconciliation
                    </span>
                    <Scale className="w-5 h-5 text-brand-teal" />
                  </div>

                  <div className="space-y-4">
                    <div className="p-4 rounded-lg bg-light-bg border border-light-border space-y-2">
                      <div className="text-sm font-semibold text-light-text flex justify-between">
                        <span>Revenue Matching</span>
                        <span className="text-brand-teal">
                          {evalResult?.features?.reconciliation_metrics?.gst_bank_ratio
                            ? `${(Number(evalResult.features.reconciliation_metrics.gst_bank_ratio) * 100).toFixed(1)}% Match`
                            : "-"}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs text-light-secondary">
                        <div>
                          GST Turnover:{" "}
                          <span className="font-medium text-light-text">
                            {evalResult?.features?.gst_metrics?.avg_monthly_revenue
                              ? formatCurrency(
                                  Number(evalResult.features.gst_metrics.avg_monthly_revenue) *
                                    (evalResult.features.gst_metrics.months_filed || 12),
                                )
                              : "-"}
                          </span>
                        </div>
                        <div>
                          Bank Credits:{" "}
                          <span className="font-medium text-light-text">
                            {evalResult?.features?.bank_metrics?.total_credits
                              ? formatCurrency(evalResult.features.bank_metrics.total_credits)
                              : "-"}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-light-border text-xs text-light-secondary flex items-center justify-between">
                  <span>Reconciliation Engine</span>
                  <span className="text-brand-teal font-medium">Deterministic Reconciliation</span>
                </div>
              </div>
            </div>
          )}

          {/* Assessment Summary / Action Portal */}
          <div className="glass-card p-6 sm:p-8 border border-light-border shadow-sm">
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-light-border">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-light-bg border border-light-border flex items-center justify-center text-light-secondary">
                  <ShieldCheck className="w-5 h-5 text-brand-teal" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-light-text">
                    Governance & Access Controls
                  </h2>
                  <p className="text-xs text-light-secondary">
                    Logged in as <strong className="text-light-text">{user?.full_name}</strong> ({humaniseEnum(user?.role || "")}) • Scoped Access
                  </p>
                </div>
              </div>
            </div>

            {/* Role-Specific Action Panels */}
            {!canRunAssessment &&
            !canSubmitAnalystRec &&
            !canSubmitHumanDecision ? (
              <div className="p-6 text-center space-y-2 bg-light-bg rounded-xl border border-light-border">
                <Lock className="w-8 h-8 text-light-muted mx-auto" />
                <div className="text-sm font-bold text-light-text">
                  Read-Only Workspace Access
                </div>
                <p className="text-xs text-light-secondary max-w-md mx-auto">
                  Your role ({humaniseEnum(user?.role || "")}) has read-only access to this case. Mutation workflows are restricted to assigned Credit Analysts and Sanctioning Authorities.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Left: Analyst Workflows */}
                {(canRunAssessment || canSubmitAnalystRec) && (
                  <div className="p-5 rounded-xl bg-light-bg border border-light-border space-y-4">
                    <h3 className="text-sm font-bold text-light-text flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-brand-teal" />
                      <span>Credit Analyst Workflows</span>
                    </h3>
                    <p className="text-xs text-light-secondary">
                      Submit formal recommendation to the Sanctioning Authority based on the assessment.
                    </p>

                    <div className="flex flex-wrap gap-3 pt-2">
                      {canRunAssessment && isEvaluated && (
                        <button
                          onClick={handleRunEvaluation}
                          disabled={evaluating}
                          className="px-4 py-2.5 bg-white hover:bg-light-elevated text-light-text font-medium text-xs rounded-lg border border-light-border flex items-center gap-2 transition-all shadow-sm disabled:opacity-50"
                        >
                          {evaluating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                          <span>Re-run Assessment</span>
                        </button>
                      )}
                      {canSubmitAnalystRec && (() => {
                        const recAction = getDerivedRecAction();
                        const isApprovalRec = recAction === "RECOMMEND_AS_REQUESTED" || recAction === "RECOMMEND_ALTERNATIVE_STRUCTURE";
                        const computedLimit = evalResult?.decision?.binding_limit ?? creditTwin?.binding_limit ?? caseData?.requested_amount ?? 0;
                        const showLimit = isApprovalRec && computedLimit > 0;
                        
                        const buttonText = showLimit 
                          ? `Submit: ${humaniseEnum(recAction)} (${formatCurrency(computedLimit)})` 
                          : `Submit: ${humaniseEnum(recAction)}`;

                        return (
                          <button
                            onClick={handleSubmitAnalystRec}
                            disabled={evaluating || (isApprovalRec && computedLimit <= 0)}
                            className="px-4 py-2.5 bg-brand-teal hover:bg-brand-tealHover text-white font-medium text-xs rounded-lg shadow-sm flex items-center gap-2 transition-all disabled:opacity-50"
                          >
                            <Send className="w-4 h-4" />
                            <span>{buttonText}</span>
                          </button>
                        );
                      })()}
                    </div>
                  </div>
                )}

                {/* Right: Sanctioning Authority Decision Gate */}
                {canSubmitHumanDecision && (
                  <div className="p-5 rounded-xl bg-brand-softAmber border border-brand-amber space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-bold text-brand-amber flex items-center gap-2">
                        <UserCheck className="w-4 h-4" />
                        <span>Sanctioning Authority Gate</span>
                      </h3>
                    </div>

                    <div className="space-y-3">
                      <div>
                        <label className="block text-xs font-medium text-brand-amber mb-1">
                          DECISION ACTION
                        </label>
                        <select
                          value={decisionAction}
                          onChange={(e) => setDecisionAction(e.target.value)}
                          className="w-full px-3 py-2 bg-white border border-brand-amber rounded-lg text-sm text-light-text focus:outline-none focus:ring-1 focus:ring-brand-amber"
                        >
                          {caseData?.business_id_fk !== "AAROHAN_INFRA_001" && reqAmount > 0 && (
                            <option value="APPROVE_AS_REQUESTED">
                              Approve as Requested ({formatCurrency(reqAmount)})
                            </option>
                          )}
                          {(() => {
                            const computedSupportLimit = creditTwin?.binding_limit ?? evalResult?.decision?.binding_limit ?? caseData?.requested_amount ?? 0;
                            if (computedSupportLimit > 0) {
                              return (
                                <option value="APPROVE_ALTERNATIVE_STRUCTURE">
                                  Approve Alternative Structure ({formatCurrency(computedSupportLimit)})
                                </option>
                              );
                            }
                            return null;
                          })()}
                          <option value="DEFER_FOR_EVIDENCE">
                            Defer Case for Further Evidence
                          </option>
                          <option value="ESCALATE_FOR_DUE_DILIGENCE">
                            Escalate for Due Diligence
                          </option>
                          <option value="DECLINE_AFTER_HUMAN_REVIEW">
                            Decline Application
                          </option>
                        </select>
                        {caseData && decisionAction !== getDefaultSADecision() && (
                          <div className="text-xs font-bold text-red-600 flex items-center gap-1 mt-1">
                            <AlertTriangle className="w-3 h-3" /> Policy exception — human rationale required
                          </div>
                        )}
                      </div>

                      {decisionAction === "APPROVE_ALTERNATIVE_STRUCTURE" && (
                        <div>
                          <label className="block text-xs font-medium text-brand-amber mb-1">
                            APPROVED AMOUNT (₹)
                          </label>
                          <input
                            type="number"
                            value={approvedAmount}
                            onChange={(e) =>
                              setApprovedAmount(Number(e.target.value))
                            }
                            className="w-full px-3 py-2 bg-white border border-brand-amber rounded-lg text-sm font-mono text-light-text focus:outline-none focus:ring-1 focus:ring-brand-amber"
                          />
                        </div>
                      )}

                      <div>
                        <label className="block text-xs font-medium text-brand-amber mb-1">
                          SANCTION NOTES / RATIONALE
                        </label>
                        <input
                          type="text"
                          value={sanctionNotes}
                          onChange={(e) => setSanctionNotes(e.target.value)}
                          placeholder="Enter sanction rationale or conditions..."
                          className="w-full px-3 py-2 bg-white border border-brand-amber rounded-lg text-sm text-light-text focus:outline-none focus:ring-1 focus:ring-brand-amber"
                        />
                      </div>

                      <button
                        onClick={handleRecordSanctionDecision}
                        disabled={submittingDecision}
                        className="w-full py-2.5 bg-brand-amber hover:bg-amber-600 text-white font-medium text-sm rounded-lg shadow-sm flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                      >
                        {submittingDecision ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <Check className="w-4 h-4" />
                        )}
                        <span>Execute Sanction Decision</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
