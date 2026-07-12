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
    { title: "Evidence Sufficiency", icon: Database },
    { title: "Credit Health & FHI", icon: ShieldCheck },
    { title: "Capacity & Limits", icon: Briefcase },
    { title: "Sign-off", icon: UserCheck }
  ];

  const submitDecision = async (status: "APPROVED" | "DECLINED") => {
    setSubmitting(true);
    try {
      const decisionEnum = status === "APPROVED" ? "APPROVE_AS_REQUESTED" : "DECLINE_AFTER_HUMAN_REVIEW";
      const res = await apiFetch(`/api/cases/${caseId}/human-decision`, {
        method: "POST",
        headers: {
          "Idempotency-Key": crypto.randomUUID()
        },
        body: JSON.stringify({
          decision: decisionEnum,
          reason: `Decision Room: ${status}`,
          expected_version: data?.case_version || 0
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
            
            <div className="mt-8">
              <IntegrityGraph 
                entityName={data.business_name} 
                state={(data as any).integrity_state === "TAMPERED" ? "TAMPERED" : (data as any).integrity_state === "UNVERIFIED" ? "UNVERIFIED" : "INTACT"} 
              />
            </div>
          </div>
        );
      case 1:
        return (
          <div className="space-y-6">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-2xl font-bold text-white mb-2">2. Review Credit Health</h2>
                <p className="text-gray-400 mb-6">Analyze the financial health index and core credit scoring.</p>
              </div>
              <button 
                onClick={() => setCompareMode(!compareMode)}
                className={`px-4 py-2 rounded-lg text-sm font-bold border transition-colors ${compareMode ? 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30' : 'bg-white/5 text-gray-400 border-white/10 hover:bg-white/10'}`}
              >
                {compareMode ? 'Exit Compare Mode' : 'Compare Traditional vs Vyapar'}
              </button>
            </div>
            
            {compareMode && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div className="bg-white/5 p-6 rounded-xl border border-white/10 text-center opacity-70">
                  <p className="text-sm text-gray-400 mb-2">Traditional Bureau Score</p>
                  <p className="text-4xl font-bold text-amber-400 font-mono">612</p>
                  <p className="text-xs text-gray-500 mt-2">Thin-file / Unscoreable</p>
                </div>
                <div className="bg-emerald-500/10 p-6 rounded-xl border border-emerald-500/30 text-center relative overflow-hidden">
                  <div className="absolute top-0 right-0 bg-emerald-500 text-black text-[10px] font-bold px-2 py-1 rounded-bl-lg">VYAPAR PULSE</div>
                  <p className="text-sm text-emerald-500/80 mb-2">Vyapar Credit Health Score</p>
                  <p className="text-4xl font-bold text-emerald-400 font-mono">{data.vyapar_credit_health_score ?? "N/A"}</p>
                  <p className="text-xs text-emerald-500/60 mt-2">+{(Number(data.vyapar_credit_health_score) || 750) - 612} pts Evidence Lift</p>
                </div>
              </div>
            )}

            {!compareMode && (
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
            )}

            {/* Evidence-Linked Score Waterfall */}
            {data.assessment?.six_pillars && (
              <div className="mt-8">
                <h3 className="text-lg font-bold text-white mb-4">Evidence-Linked Score Waterfall</h3>
                <div className="space-y-3">
                  {data.assessment.six_pillars.map((pillar, idx) => (
                    <div key={idx} className="bg-black/20 p-4 rounded-lg border border-white/5 flex flex-col">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm text-gray-300 font-medium">{pillar.name}</span>
                        <div className="flex items-center gap-4">
                          <span className={`text-xs px-2 py-1 rounded-full ${
                            pillar.health_status === 'HEALTHY' ? 'bg-emerald-500/20 text-emerald-400' :
                            pillar.health_status === 'WARNING' ? 'bg-amber-500/20 text-amber-400' :
                            'bg-red-500/20 text-red-400'
                          }`}>
                            {pillar.health_status}
                          </span>
                          <span className="text-lg font-mono font-bold text-white w-12 text-right">
                            {pillar.score}
                          </span>
                        </div>
                      </div>
                      
                      {/* Evidence Linkage Details */}
                      {((pillar as any).positive_reason_codes?.length > 0 || (pillar as any).adverse_reason_codes?.length > 0) && (
                        <div className="mt-2 text-xs border-t border-white/5 pt-2 grid grid-cols-1 md:grid-cols-2 gap-4">
                          {((pillar as any).positive_reason_codes?.length > 0) && (
                            <div>
                              <p className="text-emerald-400/80 mb-1 font-semibold">Positive Drivers:</p>
                              <ul className="list-disc list-inside text-gray-400">
                                {(pillar as any).positive_reason_codes.map((code: string, i: number) => (
                                  <li key={i}>{code}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {((pillar as any).adverse_reason_codes?.length > 0) && (
                            <div>
                              <p className="text-amber-400/80 mb-1 font-semibold">Adverse Drivers:</p>
                              <ul className="list-disc list-inside text-gray-400">
                                {(pillar as any).adverse_reason_codes.map((code: string, i: number) => (
                                  <li key={i}>{code}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                      
                      {((pillar as any).evidence_ids?.length > 0) && (
                        <div className="mt-2 text-[10px] text-gray-500">
                          Evidence: {(pillar as any).evidence_ids.join(", ")}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      case 2:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">3. Capacity & Limits</h2>
            <p className="text-gray-400 mb-6">Review calculated product limits and engine recommendation.</p>

            {/* Score-to-Limit Bridge */}
            {data.assessment?.supportable_amount !== undefined && data.assessment?.supportable_amount !== null && (
              <div className="bg-black/30 p-6 rounded-xl border border-white/5 mb-6">
                <h3 className="text-lg font-bold text-white mb-4">Score-to-Limit Bridge</h3>
                <div className="space-y-4">
                  <div className="flex justify-between items-center border-b border-white/5 pb-2">
                    <span className="text-sm text-gray-400">Financial Health Index (Score)</span>
                    <span className="text-lg font-mono text-white">{data.financial_health_index !== undefined ? Number(data.financial_health_index).toFixed(2) : "N/A"}</span>
                  </div>

                  <div className="flex justify-between items-center border-b border-white/5 pb-2">
                    <span className="text-sm text-gray-400">Requested Amount</span>
                    <span className="text-lg font-mono text-white">{formatCurrency(data.requested_amount)}</span>
                  </div>
                  
                  <div className="flex justify-between items-center border-b border-white/5 pb-2">
                    <span className="text-sm text-gray-400">Current DSCR</span>
                    <span className="text-lg font-mono text-white">{data.assessment.current_dscr ? Number(data.assessment.current_dscr).toFixed(2) : "N/A"}x</span>
                  </div>
                  
                  <div className="flex justify-between items-center border-b border-white/5 pb-2">
                    <span className="text-sm text-gray-400">Post-Loan DSCR</span>
                    <span className="text-lg font-mono text-white">{data.assessment.post_loan_dscr ? Number(data.assessment.post_loan_dscr).toFixed(2) : "N/A"}x</span>
                  </div>
                  
                  <div className="flex justify-between items-center border-b border-white/5 pb-2">
                    <span className="text-sm text-gray-400">Stressed DSCR</span>
                    <span className="text-lg font-mono text-white">{data.assessment.stressed_dscr ? Number(data.assessment.stressed_dscr).toFixed(2) : "N/A"}x</span>
                  </div>
                  
                  {data.assessment.binding_constraint && (
                    <div className="flex justify-between items-center border-b border-white/5 pb-2">
                      <span className="text-sm text-gray-400">Binding Constraint</span>
                      <span className="text-xs text-amber-400 bg-amber-400/10 px-2 py-1 rounded max-w-[50%] text-right truncate" title={data.assessment.binding_constraint.reason}>
                        {data.assessment.binding_constraint.constraint_type}
                      </span>
                    </div>
                  )}

                  <div className="flex justify-between items-center pt-2">
                    <span className="text-md font-bold text-blue-400">Supportable Amount</span>
                    <span className="text-2xl font-bold font-mono text-blue-400">{formatCurrency(Number(data.assessment.supportable_amount))}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Stress Testing Results */}
            {data.assessment?.stress_results && data.assessment.stress_results.length > 0 && (
              <div className="bg-black/30 p-6 rounded-xl border border-white/5 mb-6">
                <h3 className="text-lg font-bold text-white mb-4">Stress Testing Results</h3>
                <div className="space-y-3">
                  {data.assessment.stress_results.map((stress: any, idx: number) => (
                    <div key={idx} className="bg-black/20 p-4 rounded-lg border border-red-500/20">
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="text-sm font-bold text-white mb-1">{stress.scenario_name}</p>
                          <p className="text-sm text-gray-400">{stress.impact}</p>
                        </div>
                        <span className="text-xs px-2 py-1 bg-red-500/10 text-red-400 rounded">
                          Simulated
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

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
