"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { 
  CheckCircle2, ShieldCheck, Database, Briefcase, ChevronRight, ChevronLeft, 
  ThumbsUp, ThumbsDown, UserCheck, AlertTriangle, FileText, Search, Activity, 
  Lock, RefreshCw, BarChart3, Clock, Scale, PlayCircle, Fingerprint
} from "lucide-react";
import { formatCurrency } from "@/lib/formatters";
import type { DecisionPackageResponse } from "@/lib/types";
import { IntegrityGraph } from "@/components/IntegrityGraph";

export default function DecisionRoomPage() {
  const { caseId } = useParams();
  const router = useRouter();
  
  const [data, setData] = useState<DecisionPackageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [currentStep, setCurrentStep] = useState(0);
  const [decision, setDecision] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [compareMode, setCompareMode] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await apiFetch<DecisionPackageResponse>(`/api/cases/${caseId}/decision-package`);
        if (res.status === 200 && res.data) {
          setData(res.data);
        } else {
          setError(res.error || "Failed to load decision package");
        }
      } catch (err: any) {
        setError(err.message || "Unknown error");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [caseId]);

  const steps = [
    { title: "Consent & KYC Validation", icon: Fingerprint, id: 0 },
    { title: "Udyam & Bureau Retrieval", icon: Search, id: 1 },
    { title: "GST Filing Extraction", icon: FileText, id: 2 },
    { title: "Bank Statement Analytics", icon: Database, id: 3 },
    { title: "Cash Flow & Buffer Assessment", icon: Activity, id: 4 },
    { title: "Turnover & Volatility Profiling", icon: BarChart3, id: 5 },
    { title: "Integrity & Fraud Graphing", icon: Lock, id: 6 },
    { title: "Working Capital Cycle Computation", icon: RefreshCw, id: 7 },
    { title: "Asset/LTV Validation", icon: Scale, id: 8 },
    { title: "Existing Repayment Burden", icon: Clock, id: 9 },
    { title: "Financial Health Index (FHI)", icon: ShieldCheck, id: 10 },
    { title: "Baseline Capacity Sizing", icon: Briefcase, id: 11 },
    { title: "Product Limit Engine", icon: Briefcase, id: 12 },
    { title: "Governing Stress Scenarios", icon: AlertTriangle, id: 13 },
    { title: "Reverse Stress Boundary Test", icon: PlayCircle, id: 14 },
    { title: "Human Supervisory Sign-off", icon: UserCheck, id: 15 }
  ];

  const submitDecision = async (status: "APPROVED" | "DECLINED") => {
    setSubmitting(true);
    try {
      const decisionEnum = status === "APPROVED" ? "APPROVE_AS_REQUESTED" : "DECLINE_AFTER_HUMAN_REVIEW";
      // Determine approved amount: Use requested amount, capped by limit
      let approvedAmount = data?.requested_amount;
      if (status === "APPROVED" && data?.assessment?.binding_limit) {
        approvedAmount = Math.min(data.requested_amount, Number(data.assessment.binding_limit));
      }
      
      const res = await apiFetch(`/api/cases/${caseId}/human-decision`, {
        method: "POST",
        headers: {
          "Idempotency-Key": crypto.randomUUID(),
          "X-Expected-Version": (data?.case_version || 0).toString(),
          "X-CSRF-Token": "" // For prototype
        },
        body: JSON.stringify({
          decision: decisionEnum,
          reason: `Decision Room: ${status}`,
          expected_version: data?.case_version || 0,
          approved_amount: approvedAmount
        })
      });
      if (res.status === 200) {
        setDecision(status);
        setTimeout(() => router.push(`/cases/${caseId}`), 2000);
      } else {
        alert("Failed to submit decision: " + (res.error || JSON.stringify(res.data)));
        setSubmitting(false);
      }
    } catch (err: any) {
      alert("Error: " + err.message);
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex justify-center items-center">
        <div className="animate-spin h-8 w-8 border-4 border-emerald-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-black flex justify-center items-center p-8">
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl flex items-center gap-3">
          <AlertTriangle className="w-5 h-5" />
          <p>{error || "Failed to load decision package."}</p>
        </div>
      </div>
    );
  }

  const renderGenericDataStep = (title: string, desc: string, dataKey: string) => (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white mb-2">{title}</h2>
      <p className="text-gray-400 mb-6">{desc}</p>
      <div className="bg-black/30 p-6 rounded-xl border border-white/5 font-mono text-sm text-gray-300 overflow-auto max-h-96">
        <pre>{JSON.stringify(data.features?.[dataKey] || {}, null, 2)}</pre>
      </div>
    </div>
  );

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">1. Consent & KYC Validation</h2>
            <p className="text-gray-400 mb-6">Verify entity consent and core KYC parameters.</p>
            <div className="bg-black/30 p-6 rounded-xl border border-white/5">
              <p className="mb-2"><strong>Entity:</strong> {data.business_name}</p>
                                        </div>
          </div>
        );
      case 1: return renderGenericDataStep("2. Udyam & Bureau Retrieval", "View retrieved statutory entity data.", "bureau_metrics");
      case 2: return renderGenericDataStep("3. GST Filing Extraction", "Analyzed GST filing frequency and revenue.", "gst_metrics");
      case 3: return renderGenericDataStep("4. Bank Statement Analytics", "Operational credits and debits from bank rails.", "bank_metrics");
      case 4:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">5. Cash Flow & Buffer Assessment</h2>
            <p className="text-gray-400 mb-6">Evaluate operating cash generation against fixed outflows.</p>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-black/30 p-4 rounded-xl border border-white/5">
                <p className="text-sm text-gray-400">Monthly Inflows</p>
                <p className="text-2xl font-bold text-white">{formatCurrency(Number(data.features?.bank_metrics?.operating_inflows_monthly || 0))}</p>
              </div>
              <div className="bg-black/30 p-4 rounded-xl border border-white/5">
                <p className="text-sm text-gray-400">Monthly Outflows</p>
                <p className="text-2xl font-bold text-white">{formatCurrency(Number(data.features?.bank_metrics?.operating_outflows_monthly || 0))}</p>
              </div>
            </div>
          </div>
        );
      case 5: return renderGenericDataStep("6. Turnover & Volatility Profiling", "Assess historical stability of turnover.", "gst_metrics");
      case 6:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">7. Integrity & Fraud Graphing</h2>
            <p className="text-gray-400 mb-6">Graph traversal results for conflict of interest and integrity markers.</p>
            <IntegrityGraph caseId={caseId as string} entityName={data.business_name} />
          </div>
        );
      case 7: return renderGenericDataStep("8. Working Capital Cycle Computation", "Evaluate receivable and payable days.", "receivable_metrics");
      case 8: return renderGenericDataStep("9. Asset/LTV Validation", "Evaluate unencumbered collateral buffers if applicable.", "collateral_metrics");
      case 9:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">10. Existing Repayment Burden</h2>
            <p className="text-gray-400 mb-6">Aggregate verifiable debt service obligations.</p>
            <div className="bg-black/30 p-4 rounded-xl border border-white/5">
              <p className="text-sm text-gray-400">Existing Monthly Debt Service</p>
              <p className="text-2xl font-bold text-white">{formatCurrency(Number(data.features?.bank_metrics?.verified_existing_debt_service_monthly || 0))}</p>
            </div>
          </div>
        );
      case 10:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">11. Financial Health Index (FHI)</h2>
            <p className="text-gray-400 mb-6">Evidence-conditioned conceptual scoring.</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-black/30 p-6 rounded-xl border border-white/5 text-center">
                <p className="text-sm text-gray-400 mb-2">Vyapar Credit Health Score</p>
                <p className="text-4xl font-bold text-emerald-400 font-mono">{data.vyapar_credit_health_score ?? "N/A"}</p>
                <p className="text-xs text-gray-500 mt-2">Range: 300 - 900</p>
              </div>
              <div className="bg-black/30 p-6 rounded-xl border border-white/5 text-center">
                <p className="text-sm text-gray-400 mb-2">Financial Health Index (FHI)</p>
                <p className="text-4xl font-bold text-white font-mono">
                  {data.financial_health_index !== undefined ? Number(data.financial_health_index).toFixed(2) : "N/A"}
                </p>
              </div>
            </div>
          </div>
        );
      case 11:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">12. Baseline Capacity Sizing</h2>
            <p className="text-gray-400 mb-6">Standard operational conditions Post-Loan DSCR and Limit sizing.</p>
            <div className="bg-black/30 p-6 rounded-xl border border-white/5">
              <p className="text-lg mb-2">Requested: {formatCurrency(data.requested_amount)}</p>
              <p className="text-lg">Baseline Supportable: {formatCurrency(Number(data.assessment?.supportable_amount || 0))}</p>
            </div>
          </div>
        );
      case 12:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">13. Product Limit Engine</h2>
            <p className="text-gray-400 mb-6">Product specific constraints applied.</p>
            <div className="bg-black/30 p-6 rounded-xl border border-white/5">
              <p className="text-lg mb-2 text-amber-400">Binding Constraint: {data.assessment?.binding_constraint?.constraint_type || "N/A"}</p>
              <p className="text-lg text-emerald-400">Product Binding Limit: {formatCurrency(Number(data.assessment?.binding_limit || data.assessment?.supportable_amount || 0))}</p>
            </div>
          </div>
        );
      case 13:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">14. Governing Stress Scenarios</h2>
            <p className="text-gray-400 mb-6">Review specific stress scenarios applied to capacity.</p>
            <div className="space-y-3">
              {data.assessment?.stress_results?.slice(0, 3).map((stress: any, idx: number) => (
                <div key={idx} className="bg-black/20 p-4 rounded-lg border border-red-500/20">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-sm font-bold text-white mb-1">{stress.scenario_name}</p>
                      <p className="text-sm text-gray-400">{stress.impact}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      case 14:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">15. Reverse Stress Boundary Test</h2>
            <p className="text-gray-400 mb-6">Boundary conditions to breach policy floor.</p>
            <div className="bg-black/30 p-6 rounded-xl border border-white/5 overflow-auto">
              {data.assessment?.stress_results?.find((s:any) => s.scenario_id === "REVERSE_STRESS") ? (
                <pre className="text-sm text-gray-300 font-mono">
                  {JSON.stringify(data.assessment.stress_results.find((s:any) => s.scenario_id === "REVERSE_STRESS").reverse_stress_details, null, 2)}
                </pre>
              ) : (
                <p className="text-gray-500 italic">No reverse stress details available.</p>
              )}
            </div>
          </div>
        );
      case 15:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">16. Final Sign-off</h2>
            <p className="text-gray-400 mb-6">Provide your ultimate decision for Case #{(caseId as string)?.slice(0, 8)}.</p>
            
            {decision ? (
              <div className={`p-8 rounded-xl border flex flex-col items-center text-center ${decision === 'APPROVED' ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                <CheckCircle2 className={`w-16 h-16 mb-4 ${decision === 'APPROVED' ? 'text-emerald-400' : 'text-red-400'}`} />
                <h3 className={`text-2xl font-bold ${decision === 'APPROVED' ? 'text-emerald-400' : 'text-red-400'}`}>
                  Case {decision}
                </h3>
                <p className="text-gray-400 mt-2">Redirecting to case page...</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-6">
                <button 
                  onClick={() => submitDecision("APPROVED")}
                  disabled={submitting}
                  className="flex flex-col items-center p-8 bg-emerald-500/10 border border-emerald-500/30 rounded-xl hover:bg-emerald-500/20 transition group disabled:opacity-50"
                >
                  <ThumbsUp className="w-12 h-12 text-emerald-500 mb-4 group-hover:scale-110 transition-transform" />
                  <span className="text-xl font-bold text-emerald-400">Approve</span>
                  <span className="text-sm text-emerald-500/70 mt-2">Sanction limits as computed</span>
                </button>
                <button 
                  onClick={() => submitDecision("DECLINED")}
                  disabled={submitting}
                  className="flex flex-col items-center p-8 bg-red-500/10 border border-red-500/30 rounded-xl hover:bg-red-500/20 transition group disabled:opacity-50"
                >
                  <ThumbsDown className="w-12 h-12 text-red-500 mb-4 group-hover:scale-110 transition-transform" />
                  <span className="text-xl font-bold text-red-400">Decline</span>
                  <span className="text-sm text-red-500/70 mt-2">Reject application</span>
                </button>
              </div>
            )}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-black text-gray-200">
      <div className="max-w-4xl mx-auto px-4 py-8">
        
        {/* Header */}
        <div className="flex justify-between items-end mb-8 border-b border-white/10 pb-6">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Credit Committee Decision Room</h1>
            <p className="text-gray-400">Guided evaluation journey for {data.business_name}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500">Case ID: <span className="font-mono text-gray-300">{caseId}</span></p>
            <p className="text-sm text-gray-500">Req. Amount: <span className="font-mono text-white font-bold">{formatCurrency(data.requested_amount)}</span></p>
          </div>
        </div>

        {/* 16-Step Stepper Header */}
        <div className="flex flex-wrap gap-2 mb-8 items-center justify-center">
            {steps.map((step, idx) => (
                <button
                    key={idx}
                    onClick={() => setCurrentStep(idx)}
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border transition ${
                        currentStep === idx 
                        ? 'bg-blue-500 border-blue-500 text-white' 
                        : currentStep > idx 
                        ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400' 
                        : 'bg-white/5 border-white/10 text-gray-500'
                    }`}
                    title={step.title}
                >
                    {idx + 1}
                </button>
            ))}
        </div>

        {/* Content */}
        <div className="bg-white/5 border border-white/10 rounded-3xl p-8 mb-8 min-h-[400px]">
          {renderStepContent()}
        </div>

        {/* Navigation */}
        <div className="flex justify-between">
          <button
            onClick={() => setCurrentStep(prev => Math.max(0, prev - 1))}
            disabled={currentStep === 0 || decision !== null}
            className="px-6 py-3 bg-black border border-white/20 rounded-xl text-white font-semibold hover:bg-white/5 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <ChevronLeft className="w-5 h-5" />
            Previous
          </button>
          
          <button
            onClick={() => setCurrentStep(prev => Math.min(steps.length - 1, prev + 1))}
            disabled={currentStep === steps.length - 1 || decision !== null}
            className="px-6 py-3 bg-blue-600 rounded-xl text-white font-semibold hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            Next Step
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>

      </div>
    </div>
  );
}
