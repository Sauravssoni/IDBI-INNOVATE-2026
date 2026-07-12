"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { 
  CheckCircle2, ShieldCheck, Database, Briefcase, ChevronRight, ChevronLeft, 
  ThumbsUp, ThumbsDown, UserCheck, AlertTriangle
} from "lucide-react";
import { formatCurrency } from "@/lib/formatters";
import type { DecisionPackageResponse } from "@/lib/types";

export default function DecisionRoomPage() {
  const { caseId } = useParams();
  const router = useRouter();
  
  const [data, setData] = useState<DecisionPackageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [currentStep, setCurrentStep] = useState(0);
  const [decision, setDecision] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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
    { title: "Evidence Sufficiency", icon: Database },
    { title: "Credit Health & FHI", icon: ShieldCheck },
    { title: "Capacity & Limits", icon: Briefcase },
    { title: "Sign-off", icon: UserCheck }
  ];

  const submitDecision = async (status: "APPROVED" | "DECLINED") => {
    setSubmitting(true);
    try {
      const res = await apiFetch(`/api/cases/${caseId}/status`, {
        method: "PUT",
        body: JSON.stringify({ status })
      });
      if (res.status === 200) {
        setDecision(status);
        setTimeout(() => router.push(`/cases/${caseId}`), 2000);
      } else {
        alert("Failed to submit decision: " + res.error);
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

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">1. Review Evidence Sufficiency</h2>
            <p className="text-gray-400 mb-6">Review the source data rails used to calculate this decision.</p>
            {data.evidence_passport ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-black/30 p-5 rounded-xl border border-white/5">
                  <p className="text-sm text-gray-400 mb-1">Evidence Tier</p>
                  <p className="text-xl font-bold text-teal-400 font-mono">
                    {data.evidence_passport.evidence_tier || "N/A"}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">{data.evidence_passport.tier_description}</p>
                </div>
                <div className="bg-black/30 p-5 rounded-xl border border-white/5">
                  <p className="text-sm text-gray-400 mb-1">Freshness Index</p>
                  <p className="text-xl font-bold text-white font-mono">
                    {data.evidence_passport.freshness_depth?.composite_freshness_index}%
                  </p>
                </div>
                <div className="bg-black/30 p-5 rounded-xl border border-white/5">
                  <p className="text-sm text-gray-400 mb-1">Contradiction Severity</p>
                  <p className={`text-xl font-bold font-mono ${data.evidence_passport.contradiction_analysis?.severity === 'HIGH' ? 'text-red-400' : 'text-emerald-400'}`}>
                    {data.evidence_passport.contradiction_analysis?.severity || "N/A"}
                  </p>
                </div>
                <div className="bg-black/30 p-5 rounded-xl border border-white/5">
                  <p className="text-sm text-gray-400 mb-1">Certainty Level</p>
                  <p className="text-xl font-bold text-teal-400 font-mono">
                    {data.assessment_certainty || "N/A"}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 italic">No Evidence Passport available.</p>
            )}
          </div>
        );
      case 1:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">2. Review Credit Health</h2>
            <p className="text-gray-400 mb-6">Analyze the financial health index and core credit scoring.</p>
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
                <p className="text-xs text-gray-500 mt-2">Range: 0 - 100</p>
              </div>
            </div>
          </div>
        );
      case 2:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">3. Capacity & Limits</h2>
            <p className="text-gray-400 mb-6">Review calculated product limits and engine recommendation.</p>
            <div className="bg-black/30 p-6 rounded-xl border border-white/5">
              <p className="text-sm text-gray-400 mb-1">Engine Recommendation</p>
              <p className={`text-2xl font-bold font-mono ${data.recommendation?.includes("APPROVE") ? 'text-emerald-400' : 'text-amber-400'}`}>
                {data.recommendation}
              </p>
            </div>
            
            <h3 className="text-lg font-bold text-white mt-8 mb-4">Product Offers</h3>
            <div className="grid grid-cols-1 gap-4">
              {data.offers?.map((offer, idx) => (
                <div key={idx} className="bg-black/30 p-5 rounded-xl border border-blue-500/30 flex justify-between items-center">
                  <div>
                    <p className="text-sm text-blue-400 font-bold font-mono mb-1">{offer.product_type?.replace(/_/g, ' ')}</p>
                    <p className="text-xl font-bold text-white font-mono">{formatCurrency(offer.amount)}</p>
                  </div>
                  <div className="text-right text-xs text-gray-400 space-y-1">
                    <p>ROI: {offer.interest_rate_pct}% p.a. | Tenure: {offer.tenure_months}M</p>
                    <p>Post-Loan DSCR: {Number(offer.post_loan_dscr).toFixed(2)}</p>
                  </div>
                </div>
              ))}
              {(!data.offers || data.offers.length === 0) && (
                <p className="text-gray-500 italic">No valid offers generated.</p>
              )}
            </div>
          </div>
        );
      case 3:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">4. Final Sign-off</h2>
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

        {/* Stepper */}
        <div className="flex items-center justify-between mb-12">
          {steps.map((step, idx) => {
            const Icon = step.icon;
            const isActive = currentStep === idx;
            const isPast = currentStep > idx;
            
            return (
              <div key={idx} className="flex flex-col items-center flex-1 relative">
                {idx !== 0 && (
                  <div className={`absolute left-0 w-[calc(100%-2rem)] h-[2px] top-5 -ml-[calc(50%-1rem)] ${isPast ? 'bg-emerald-500' : 'bg-white/10'}`} />
                )}
                <div className={`w-10 h-10 rounded-full flex items-center justify-center z-10 border-2 transition-colors duration-300
                  ${isActive ? 'bg-blue-500/20 border-blue-500 text-blue-400' : 
                    isPast ? 'bg-emerald-500 border-emerald-500 text-black' : 
                    'bg-black border-white/20 text-gray-500'}`}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <p className={`text-xs mt-3 font-semibold ${isActive ? 'text-blue-400' : isPast ? 'text-emerald-400' : 'text-gray-500'}`}>
                  {step.title}
                </p>
              </div>
            );
          })}
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
