"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { CaseListItem, CaseDetailResponse, CreditTwinResponse } from "@/types";
import { apiFetch } from "@/lib/api";
import EvidenceTab from "../cases/[caseId]/tabs/EvidenceTab";
import ReconciliationTab from "../cases/[caseId]/tabs/ReconciliationTab";
import AssessmentHistoryTab from "../cases/[caseId]/tabs/AssessmentHistoryTab";
import {
  Sparkles, Building2, CheckCircle2, AlertTriangle, ArrowRight, Play, RefreshCw,
  Send, UserCheck, Check, ShieldCheck, Database, Scale, Activity, User, Clock, ArrowLeft
} from "lucide-react";
import Link from "next/link";
import { formatCurrency, humanise } from "@/lib/formatters";

export default function GuidedDemoPage() {
  const { user, demoLogin } = useAuth();
  const router = useRouter();

  const [caseData, setCaseData] = useState<CaseDetailResponse | null>(null);
  const [creditTwin, setCreditTwin] = useState<CreditTwinResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(1);
  const [evaluating, setEvaluating] = useState(false);
  const [switchingRole, setSwitchingRole] = useState(false);
  const [activeRole, setActiveRole] = useState<string | null>(null);

  const determineStep = (fullCase: CaseDetailResponse, role: string | undefined | null) => {
    if (fullCase.status === "HUMAN_APPROVED" || fullCase.status === "HUMAN_DECLINED") return 6;
    if (fullCase.analyst_recommendation) {
      return role === "SANCTIONING_AUTHORITY" ? 6 : 5;
    }
    if (fullCase.recommendation) return 4;
    if (fullCase.status === "ASSESSMENT_COMPLETED") return 4;
    return 1; // Default
  };

  const loadShaktiCase = async (currentRole?: string) => {
    setLoading(true);
    const { data: listData, status: listStatus } = await apiFetch<CaseListItem[]>("/api/cases/");
    if (listStatus === 200 && Array.isArray(listData)) {
      const match = listData.find((c) => c.business_id === "SHAKTI_PRECISION_001" || c.id === "SHAKTI_PRECISION_001" || c.business_name?.toLowerCase().includes("shakti"));
      if (match) {
        const { data: fullCase, status: caseStatus } = await apiFetch<CaseDetailResponse>(`/api/cases/${match.id}`);
        if (caseStatus === 200 && fullCase) {
          setCaseData(fullCase);
          setStep(determineStep(fullCase, currentRole || activeRole || user?.role));
          const { data: twinData, status: twinStatus } = await apiFetch<CreditTwinResponse>(`/api/cases/${match.id}/credit-twin`);
          if (twinStatus === 200 && twinData) {
            setCreditTwin(twinData);
          }
        } else {
          setError("Failed to load full case details.");
        }
      } else {
        setError("Shakti case not found in sandbox.");
      }
    } else {
      setError("Failed to load cases.");
    }
    setLoading(false);
  };

  useEffect(() => {
    if (user?.role) {
      setActiveRole(user.role);
    }
    loadShaktiCase();
  }, [user]);

  const handleRestartDemo = async () => {
    setEvaluating(true);
    const { status } = await apiFetch("/api/demo/reset", {
      method: "POST",
    });
    if (status === 200) {
      await loadShaktiCase();
    } else {
      setError("Failed to restart demo sandbox.");
    }
    setEvaluating(false);
  };

  const runEvaluation = async () => {
    if (!caseData?.id) return;
    setEvaluating(true);
    const idempotencyKey = crypto.randomUUID();
    const { status } = await apiFetch(`/api/cases/${caseData.id}/evaluate`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ expected_version: caseData.version || 1 }),
    });
    if (status === 200 || status === 201) {
      await loadShaktiCase();
      setStep(4);
    } else {
      setError("Assessment engine failed.");
    }
    setEvaluating(false);
  };

  const handleAnalystRecommendation = async () => {
    if (!caseData || !caseData.allowed_actions.submit_analyst_recommendation) return;
    if (activeRole !== "CREDIT_ANALYST") return;
    
    setEvaluating(true);
    const idempotencyKey = crypto.randomUUID();
    const limit = creditTwin?.binding_limit;
    const { status } = await apiFetch(`/api/cases/${caseData.id}/analyst-recommendation`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        recommendation: "RECOMMEND_ALTERNATIVE_STRUCTURE",
        reason: `Deterministic reconciliation successful. Recommend ${limit} alternative structure based on verified cash flows.`,
        expected_version: caseData.version || 1,
      }),
    });
    if (status === 200 || status === 201) {
      await loadShaktiCase();
    } else {
      setError("Recommendation failed.");
    }
    setEvaluating(false);
  };

  const switchToSanctioningAuthority = async () => {
    setSwitchingRole(true);
    const res = await demoLogin("SANCTIONING_AUTHORITY");
    if (res.success) {
      const { data: meData, status: meStatus } = await apiFetch<{role: string}>("/api/auth/me");
      if (meStatus === 200 && meData?.role === "SANCTIONING_AUTHORITY") {
         setActiveRole("SANCTIONING_AUTHORITY");
         await loadShaktiCase("SANCTIONING_AUTHORITY");
         setStep(6);
      } else {
         setError("Failed to verify SA role switch.");
      }
    } else {
      setError("Failed to switch roles.");
    }
    setSwitchingRole(false);
  };

  const handleSanctionDecision = async (decision: "APPROVED" | "REJECTED") => {
    if (!caseData || !caseData.allowed_actions.record_human_decision) return;
    if (activeRole !== "SANCTIONING_AUTHORITY") return;

    setEvaluating(true);
    const idempotencyKey = crypto.randomUUID();
    const limit = creditTwin?.binding_limit;
    const { status } = await apiFetch(`/api/cases/${caseData.id}/human-decision`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        decision: decision === "APPROVED" ? "APPROVE_ALTERNATIVE_STRUCTURE" : "DECLINE_ALTERNATIVE_STRUCTURE",
        approved_amount: limit,
        reason: `Approved alternative structure for ${limit}. Reconciled evidence supports repayment capacity. DSCR Sandbox V1 limits apply.`,
        expected_version: caseData.version || 1,
      }),
    });
    if (status === 200 || status === 201) {
      await loadShaktiCase();
    } else {
      setError("Sanction failed.");
    }
    setEvaluating(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center space-y-4 bg-brand-nav">
        <Sparkles className="w-10 h-10 text-brand-teal animate-bounce" />
        <p className="text-sm font-medium text-brand-teal uppercase tracking-wider">Loading Sandbox V1...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-brand-nav">
        <div className="bg-white p-8 rounded-lg max-w-md text-center shadow-xl">
          <AlertTriangle className="w-12 h-12 text-brand-red mx-auto mb-4" />
          <h2 className="text-xl font-bold text-light-text mb-2">Sandbox Error</h2>
          <p className="text-light-secondary text-sm mb-6">{error}</p>
          <div className="space-x-4">
             <button onClick={() => { setError(null); loadShaktiCase(); }} className="px-4 py-2 bg-brand-teal text-white rounded font-medium">Retry Connection</button>
             <Link href="/login" className="px-4 py-2 bg-light-bg text-light-text border border-light-border rounded font-medium hover:bg-gray-100">Back to Login</Link>
          </div>
        </div>
      </div>
    );
  }

  if (!caseData) return null;

  const steps = [
    { id: 1, label: "Business & request" },
    { id: 2, label: "Evidence coverage" },
    { id: 3, label: "Reconciliation" },
    { id: 4, label: "Credit Twin" },
    { id: 5, label: "Analyst recommendation" },
    { id: 6, label: "Human sanction & audit" },
  ];

  return (
    <div className="min-h-screen bg-brand-nav text-light-text p-4 pb-20">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between pt-4">
          <div className="flex gap-4 items-center">
             <Link href="/login" className="text-brand-teal hover:text-white flex items-center gap-2 text-sm font-bold transition-colors">
               <ArrowLeft className="w-4 h-4" /> Leave Sandbox
             </Link>
             <button onClick={handleRestartDemo} disabled={evaluating} className="text-brand-amber hover:text-white flex items-center gap-1 text-sm font-bold transition-colors">
               <RefreshCw className={`w-4 h-4 ${evaluating ? "animate-spin" : ""}`} /> Restart Sandbox
             </button>
          </div>
          <div className="flex items-center gap-3">
            <div className="px-3 py-1 bg-brand-softTeal text-brand-teal text-xs font-bold rounded border border-brand-teal">
              DSCR_SANDBOX_V1
            </div>
            <div className="px-3 py-1 bg-light-elevated text-light-secondary text-xs font-bold rounded flex items-center gap-2 border border-light-border">
              <User className="w-3.5 h-3.5" />
              {activeRole === 'CREDIT_ANALYST' ? 'Credit Analyst' : 'Sanctioning Authority'}
            </div>
          </div>
        </div>

        <div className="text-center py-6">
          <h1 className="text-3xl font-extrabold text-white mb-2">Live Case Evaluation</h1>
          <p className="text-light-border text-sm">Guided walkthrough of deterministic credit scoring and multi-actor governance</p>
        </div>

        <div className="mb-8">
          <div className="flex items-center justify-between relative">
            <div className="absolute left-0 right-0 top-1/2 h-0.5 bg-light-border -z-10 transform -translate-y-1/2"></div>
            {steps.map((s) => (
              <div key={s.id} className="flex flex-col items-center relative z-10 bg-brand-nav px-2">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all ${step >= s.id ? 'bg-brand-teal border-brand-teal text-white' : 'bg-light-bg border-light-border text-light-secondary'}`}>
                  {step > s.id ? <Check className="w-4 h-4" /> : s.id}
                </div>
                <span className={`text-[10px] sm:text-xs mt-2 font-medium max-w-[80px] text-center hidden sm:block ${step >= s.id ? 'text-brand-teal' : 'text-light-border'}`}>
                  {s.label}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-2xl overflow-hidden border border-light-border">
          {step === 1 && (
            <div className="p-8">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 bg-brand-softTeal text-brand-teal rounded-lg flex items-center justify-center">
                  <Building2 className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-light-text">{caseData.business?.legal_name || "Unknown"}</h2>
                  <p className="text-sm text-light-secondary font-mono">Business ID: {caseData.business?.business_id || "Unknown"}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                <div className="p-4 bg-light-bg rounded-lg border border-light-border">
                  <div className="text-xs text-light-secondary uppercase font-bold mb-1">Requested Amount</div>
                  <div className="text-lg font-mono font-bold text-light-text">{caseData.requested_amount ? `₹${caseData.requested_amount.toLocaleString("en-IN")}` : "Unavailable"}</div>
                </div>
                <div className="p-4 bg-light-bg rounded-lg border border-light-border">
                  <div className="text-xs text-light-secondary uppercase font-bold mb-1">Product</div>
                  <div className="text-lg font-bold text-light-text">{caseData.requested_product ? humanise(caseData.requested_product) : "Unavailable"}</div>
                </div>
                <div className="p-4 bg-light-bg rounded-lg border border-light-border">
                  <div className="text-xs text-light-secondary uppercase font-bold mb-1">Sector</div>
                  <div className="text-lg font-bold text-light-text">{caseData.business?.sector || "Unavailable"}</div>
                </div>
                <div className="p-4 bg-light-bg rounded-lg border border-light-border">
                  <div className="text-xs text-light-secondary uppercase font-bold mb-1">Status</div>
                  <div className="text-lg font-bold text-brand-amber">{humanise(caseData.status) || "Unavailable"}</div>
                </div>
              </div>
              <div className="flex justify-end border-t border-light-border pt-6">
                <button onClick={() => setStep(2)} className="px-6 py-3 bg-brand-teal hover:bg-brand-tealHover text-white rounded-lg font-bold flex items-center gap-2 transition-all">
                  Inspect Evidence Coverage <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <div className="p-6 border-b border-light-border bg-light-bg">
                <h2 className="text-xl font-bold text-light-text flex items-center gap-2">
                  <Database className="w-5 h-5 text-brand-teal" /> Evidence Coverage
                </h2>
                <p className="text-sm text-light-secondary">Verify connected data sources (GST, Bank Statements) before reconciliation.</p>
              </div>
              <div className="p-6">
                <div className="h-[400px] overflow-y-auto mb-6 border border-light-border rounded-lg bg-light-bg">
                  <EvidenceTab caseId={caseData.id} />
                </div>
                <div className="flex justify-between items-center border-t border-light-border pt-6">
                  <button onClick={() => setStep(1)} className="px-4 py-2 text-light-secondary font-bold hover:text-light-text transition-colors">Back</button>
                  <button onClick={() => setStep(3)} className="px-6 py-3 bg-brand-teal hover:bg-brand-tealHover text-white rounded-lg font-bold flex items-center gap-2 transition-all">
                    Proceed to Reconciliation <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="p-8">
              <div className="text-center max-w-lg mx-auto space-y-6">
                <Scale className="w-16 h-16 text-brand-teal mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-light-text">Run Deterministic Reconciliation</h2>
                <p className="text-light-secondary text-sm">
                  The assessment engine will extract features, compute reconciliation scores, and generate a deterministic Credit Twin based strictly on verified evidence.
                </p>
                <div className="pt-4">
                  <button 
                    onClick={runEvaluation} 
                    disabled={evaluating || !caseData.allowed_actions.run_assessment}
                    className="w-full py-4 bg-brand-teal hover:bg-brand-tealHover text-white rounded-lg font-bold flex items-center justify-center gap-2 transition-all text-lg shadow-lg disabled:opacity-50"
                  >
                    {evaluating ? <RefreshCw className="w-6 h-6 animate-spin" /> : <Play className="w-6 h-6" />}
                    {evaluating ? "Evaluating Evidence..." : "Run Assessment Engine"}
                  </button>
                </div>
                <div className="flex justify-between items-center pt-8">
                  <button onClick={() => setStep(2)} className="px-4 py-2 text-light-secondary font-bold hover:text-light-text transition-colors">Back</button>
                </div>
              </div>
            </div>
          )}

          {step === 4 && (
            <div>
              <div className="p-6 border-b border-light-border bg-light-bg">
                <h2 className="text-xl font-bold text-light-text flex items-center gap-2">
                  <Activity className="w-5 h-5 text-brand-teal" /> Computed Credit Twin
                </h2>
                <p className="text-sm text-light-secondary">Review the resulting reconciliation metrics and deterministic scores.</p>
              </div>
              <div className="p-6">
                <div className="h-[400px] overflow-y-auto mb-6 border border-light-border rounded-lg bg-light-bg">
                  <ReconciliationTab caseId={caseData.id} />
                </div>
                <div className="grid grid-cols-2 gap-4 mb-6">
                   <div className="p-4 bg-brand-softTeal border border-brand-teal rounded-lg text-center">
                     <div className="text-xs font-bold text-brand-teal uppercase mb-1">System Recommendation</div>
                     <div className="text-xl font-extrabold text-brand-teal">{creditTwin?.recommendation ? humanise(creditTwin.recommendation) : "Unavailable"}</div>
                   </div>
                   <div className="p-4 bg-brand-softTeal border border-brand-teal rounded-lg text-center">
                     <div className="text-xs font-bold text-brand-teal uppercase mb-1">Binding Support Limit</div>
                     <div className="text-xl font-extrabold font-mono text-brand-teal">
                       {creditTwin?.binding_limit !== null && creditTwin?.binding_limit !== undefined ? formatCurrency(creditTwin.binding_limit) : "Unavailable"}
                     </div>
                   </div>
                </div>
                <div className="flex justify-between items-center border-t border-light-border pt-6">
                  <button onClick={() => setStep(3)} className="px-4 py-2 text-light-secondary font-bold hover:text-light-text transition-colors">Back</button>
                  <button onClick={() => setStep(5)} className="px-6 py-3 bg-brand-teal hover:bg-brand-tealHover text-white rounded-lg font-bold flex items-center gap-2 transition-all">
                    Prepare Recommendation <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {step === 5 && (
            <div className="p-8">
              <div className="mb-6 flex items-center gap-3">
                <User className="w-8 h-8 text-brand-teal" />
                <div>
                  <h2 className="text-xl font-bold text-light-text">Analyst Recommendation</h2>
                  <p className="text-sm text-light-secondary">Forward case to Sanctioning Authority with your structured recommendation.</p>
                </div>
              </div>

              {caseData.analyst_recommendation ? (
                <div className="p-6 bg-brand-softTeal border border-brand-teal rounded-lg text-center space-y-6">
                  <CheckCircle2 className="w-12 h-12 text-brand-teal mx-auto" />
                  <div>
                    <h3 className="text-lg font-bold text-light-text mb-1">Recommendation Submitted</h3>
                    <p className="text-sm text-brand-teal font-medium">Forwarded to Sanctioning Authority</p>
                  </div>
                  <button 
                    onClick={switchToSanctioningAuthority}
                    disabled={switchingRole}
                    className="w-full py-3 bg-brand-amber hover:bg-amber-600 text-white rounded-lg font-bold flex items-center justify-center gap-2 transition-all shadow-md disabled:opacity-50"
                  >
                    {switchingRole ? <RefreshCw className="w-5 h-5 animate-spin" /> : <UserCheck className="w-5 h-5" />}
                    Continue as Sanctioning Authority
                  </button>
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="p-4 bg-light-bg border border-light-border rounded-lg">
                    <div className="text-xs font-bold text-light-secondary mb-2 uppercase">Action</div>
                    <div className="text-sm font-bold text-brand-teal">RECOMMEND ALTERNATIVE STRUCTURE</div>
                  </div>
                  <div className="p-4 bg-light-bg border border-light-border rounded-lg">
                    <div className="text-xs font-bold text-light-secondary mb-2 uppercase">Rationale</div>
                    <div className="text-sm text-light-text">Deterministic reconciliation successful. Recommend {creditTwin?.binding_limit ? formatCurrency(creditTwin.binding_limit) : "Unavailable"} alternative structure based on verified cash flows.</div>
                  </div>
                  <button 
                    onClick={handleAnalystRecommendation}
                    disabled={evaluating || creditTwin?.binding_limit === null || creditTwin?.binding_limit === undefined || creditTwin.binding_limit <= 0 || !caseData.allowed_actions.submit_analyst_recommendation || activeRole !== "CREDIT_ANALYST"}
                    className="w-full py-4 bg-brand-teal hover:bg-brand-tealHover text-white rounded-lg font-bold flex items-center justify-center gap-2 transition-all shadow-md disabled:opacity-50"
                  >
                    {evaluating ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                    Submit Recommendation
                  </button>
                </div>
              )}
            </div>
          )}

          {step === 6 && (
            <div className="p-8">
              <div className="mb-6 flex items-center gap-3">
                <UserCheck className="w-8 h-8 text-brand-amber" />
                <div>
                  <h2 className="text-xl font-bold text-light-text">Sanctioning Authority Gate</h2>
                  <p className="text-sm text-light-secondary">Review the analyst recommendation and execute the final mandate decision.</p>
                </div>
              </div>

              {caseData.status === "HUMAN_APPROVED" || caseData.status === "HUMAN_DECLINED" ? (
                <div className="space-y-6">
                  <div className="p-6 bg-brand-softTeal border border-brand-teal rounded-lg text-center">
                    <ShieldCheck className="w-12 h-12 text-brand-teal mx-auto mb-3" />
                    <h3 className="text-2xl font-bold text-brand-teal mb-1">SANCTION {caseData.status === "HUMAN_APPROVED" ? "APPROVED" : "DECLINED"}</h3>
                    <p className="text-sm text-light-secondary font-mono">Limit: {creditTwin?.binding_limit !== null && creditTwin?.binding_limit !== undefined ? formatCurrency(creditTwin.binding_limit) : "Unavailable"}</p>
                  </div>
                  <div className="pt-4 border-t border-light-border">
                    <h4 className="text-sm font-bold text-light-text mb-4 flex items-center gap-2">
                      <Clock className="w-4 h-4 text-light-secondary" /> Tamper-Evident Prototype Audit Chain
                    </h4>
                    <div className="h-[250px] overflow-y-auto border border-light-border rounded-lg bg-light-bg">
                      <AssessmentHistoryTab caseId={caseData.id} />
                    </div>
                  </div>
                  <div className="text-center pt-4">
                    <Link href="/login" className="text-brand-teal font-bold hover:underline">Return to Login</Link>
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="p-5 bg-brand-softAmber border border-brand-amber rounded-lg">
                    <div className="text-sm font-bold text-brand-amber mb-2 uppercase flex items-center justify-between">
                      <span>Recommendation Review</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="text-light-secondary">Requested Amount</div>
                      <div className="text-right font-mono font-medium">{caseData.requested_amount !== null && caseData.requested_amount !== undefined ? formatCurrency(caseData.requested_amount) : "Unavailable"}</div>
                      <div className="text-light-secondary">Supportable Amount</div>
                      <div className="text-right font-mono font-medium">{creditTwin?.binding_limit !== null && creditTwin?.binding_limit !== undefined ? formatCurrency(creditTwin.binding_limit) : "Unavailable"}</div>
                      <div className="text-light-secondary">DSCR</div>
                      <div className="text-right font-mono font-medium">{creditTwin?.dscr ? `${creditTwin.dscr}×` : "Unavailable"}</div>
                      <div className="text-light-secondary">Analyst Action</div>
                      <div className="text-right font-medium">{caseData.analyst_recommendation ? humanise(caseData.analyst_recommendation) : "Unavailable"}</div>
                      <div className="text-light-secondary">Mandate Status</div>
                      <div className="text-right font-medium text-brand-teal">Within Mandate</div>
                      <div className="text-light-secondary">Policy Version</div>
                      <div className="text-right font-mono text-xs mt-1">{creditTwin?.policy_version || "Unavailable"}</div>
                    </div>
                  </div>
                  
                  <button 
                    onClick={() => handleSanctionDecision("APPROVED")}
                    disabled={evaluating || creditTwin?.binding_limit === null || creditTwin?.binding_limit === undefined || creditTwin.binding_limit <= 0 || !caseData.allowed_actions.record_human_decision || activeRole !== "SANCTIONING_AUTHORITY"}
                    className="w-full py-4 bg-brand-amber hover:bg-amber-600 text-white rounded-lg font-bold flex items-center justify-center gap-2 transition-all shadow-md disabled:opacity-50"
                  >
                    {evaluating ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Check className="w-5 h-5" />}
                    Approve Alternative Structure
                  </button>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
