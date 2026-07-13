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
  const [stressData, setStressData] = useState<any | null>(null);
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
          // Fetch stress data concurrently
          apiFetch(`/api/cases/${caseId}/stress-lab`).then(stressRes => {
            if (stressRes.status === 200) {
              setStressData(stressRes.data);
            }
          });
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
    { title: "Passport", icon: Fingerprint, id: 0 },
    { title: "Financial Health", icon: Activity, id: 1 },
    { title: "Product Comparison", icon: BarChart3, id: 2 },
    { title: "Limit Bridge", icon: Briefcase, id: 3 },
    { title: "Stress & Reverse", icon: PlayCircle, id: 4 },
    { title: "Bankability", icon: ShieldCheck, id: 5 },
    { title: "Human Decision", icon: UserCheck, id: 6 },
    { title: "Decision Package", icon: Database, id: 7 }
  ];

  const submitDecision = async (status: "APPROVED" | "DECLINED") => {
    setSubmitting(true);
    try {
      const decisionEnum = status === "APPROVED" ? "APPROVE_AS_REQUESTED" : "DECLINE_AFTER_HUMAN_REVIEW";
      let approvedAmount = data?.requested_amount;
      if (status === "APPROVED" && data?.assessment?.binding_limit) {
        approvedAmount = Math.min(data.requested_amount, Number(data.assessment.binding_limit));
      } else if (status === "APPROVED" && data?.assessment?.supportable_amount) {
        approvedAmount = Math.min(data.requested_amount, Number(data.assessment.supportable_amount));
      }
      
      const res = await apiFetch(`/api/cases/${caseId}/human-decision`, {
        method: "POST",
        headers: {
          "Idempotency-Key": crypto.randomUUID(),
          "X-Expected-Version": (data?.case_version || 0).toString(),
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

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">1. Borrower, Request and Evidence Passport</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-black/30 p-4 rounded-xl border border-white/5">
                <p className="text-sm text-gray-400">Borrower</p>
                <p className="text-xl font-bold text-white">{data.business_name}</p>
              </div>
              <div className="bg-black/30 p-4 rounded-xl border border-white/5">
                <p className="text-sm text-gray-400">Requested Facility</p>
                <p className="text-xl font-bold text-white">{formatCurrency(data.requested_amount)} - {data.assessment?.requested_product}</p>
              </div>
              <div className="bg-black/30 p-4 rounded-xl border border-white/5">
                <p className="text-sm text-gray-400">Evidence Tier</p>
                <p className="text-xl font-bold text-emerald-400">{data.assessment?.evidence_passport?.evidence_tier || "N/A"}</p>
                <p className="text-xs text-gray-500 mt-1">{data.assessment?.evidence_passport?.tier_description}</p>
              </div>
              <div className="bg-black/30 p-4 rounded-xl border border-white/5">
                <p className="text-sm text-gray-400">Integrity State</p>
                <p className="text-xl font-bold text-white">{data.assessment?.integrity_state || "INTACT"}</p>
              </div>
            </div>
            <h3 className="text-lg font-bold text-white mt-8 mb-4">Integrity Graph</h3>
            <div className="h-[400px]">
              <IntegrityGraph caseId={caseId as string} entityName={data.business_name} />
            </div>
          </div>
        );
      case 1:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">2. Financial Health and Contribution Waterfall</h2>
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-black/30 p-6 rounded-xl border border-white/5 text-center">
                <p className="text-sm text-gray-400 mb-2">Vyapar Credit Health</p>
                <p className="text-4xl font-bold text-emerald-400 font-mono">{data.assessment?.vyapar_credit_health_score ?? "N/A"}</p>
              </div>
              <div className="bg-black/30 p-6 rounded-xl border border-white/5 text-center">
                <p className="text-sm text-gray-400 mb-2">Financial Health Index (FHI)</p>
                <p className="text-4xl font-bold text-white font-mono">
                  {data.assessment?.financial_health_index !== undefined && data.assessment?.financial_health_index !== null ? Number(data.assessment.financial_health_index).toFixed(2) : "N/A"}
                </p>
              </div>
            </div>
            <div className="space-y-4">
              <h3 className="text-lg font-bold text-white mt-4">Six Pillars</h3>
              {data.assessment?.six_pillars?.map((p: any, i: number) => (
                <div key={i} className="flex justify-between items-center p-4 bg-black/20 rounded-lg border border-white/5">
                  <div>
                    <p className="font-bold text-white">{p.name}</p>
                    <p className="text-sm text-gray-400">{p.health_status}</p>
                  </div>
                  <div className="text-2xl font-mono text-emerald-400">{p.score}</div>
                </div>
              ))}
            </div>
          </div>
        );
      case 2:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">3. Four-Product Comparison</h2>
            <div className="grid grid-cols-2 gap-4">
              {data.assessment?.product_capacities && Object.values(data.assessment.product_capacities).map((pc: any, i: number) => (
                <div key={i} className="bg-black/30 p-4 rounded-xl border border-white/5">
                  <p className="text-sm text-gray-400">{pc.product || pc.product_name}</p>
                  <p className="text-2xl font-bold text-white">{formatCurrency(Number(pc.binding_limit || pc.capacity))}</p>
                </div>
              ))}
              {(!data.assessment?.product_capacities || Object.keys(data.assessment.product_capacities).length === 0) && (
                <p className="text-gray-500">Product capacities missing.</p>
              )}
            </div>
          </div>
        );
      case 3:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">4. Limit Bridge</h2>
            <p className="text-gray-400">Waterfall of caps bridging from requested amount to final supportable limit.</p>
            <div className="bg-black/30 p-6 rounded-xl border border-white/5">
              {data.assessment?.limit_bridge?.stages ? (
                <div className="space-y-4">
                  {data.assessment.limit_bridge.stages.map((stage: any, i: number) => (
                    <div key={i} className={`flex justify-between items-center pb-2 border-b border-white/5 ${stage.applied ? 'opacity-100' : 'opacity-50'}`}>
                      <div>
                        <p className="text-white font-bold">{stage.stage_id}</p>
                        <p className="text-xs text-gray-400">{stage.explanation}</p>
                        <p className="text-xs text-emerald-500 mt-1 font-mono">{stage.formula}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-bold text-white">{formatCurrency(stage.calculated_value)}</p>
                        {stage.applied && <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded">APPLIED</span>}
                      </div>
                    </div>
                  ))}
                  <div className="pt-4 flex justify-between items-center bg-emerald-500/10 p-4 rounded-lg mt-4 border border-emerald-500/30">
                     <div>
                       <p className="text-emerald-400 font-bold text-lg">Final Supportable Amount</p>
                       <p className="text-xs text-gray-400">Binding: {data.assessment.limit_bridge.binding_constraint}</p>
                     </div>
                     <p className="text-2xl font-bold text-emerald-400">{formatCurrency(data.assessment.limit_bridge.final_supportable_amount)}</p>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500">Limit bridge data not available.</p>
              )}
            </div>
          </div>
        );
      case 4:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">5. Stress and Reverse Stress</h2>
            <p className="text-gray-400">Authoritative down-side resilience checks.</p>
            {!stressData ? (
              <p className="text-gray-500">Loading stress scenarios...</p>
            ) : (
              <div className="space-y-6">
                 <div className="grid grid-cols-2 gap-4">
                   <div className="bg-black/30 p-4 rounded-xl border border-white/5">
                     <p className="text-sm text-gray-400">Overall Stress Status</p>
                     <p className={`text-xl font-bold ${stressData.overall_stress_status === 'PASS' ? 'text-emerald-400' : stressData.overall_stress_status === 'FAIL' ? 'text-red-400' : 'text-amber-400'}`}>{stressData.overall_stress_status}</p>
                   </div>
                 </div>
                 <h3 className="text-lg font-bold text-white mt-4">Scenarios</h3>
                 <div className="space-y-3 max-h-[400px] overflow-auto pr-2">
                   {stressData.scenarios?.map((scen: any, idx: number) => (
                     <div key={idx} className="bg-black/20 p-4 rounded-lg border border-white/5">
                       <div className="flex justify-between items-start">
                         <div>
                           <p className="text-md font-bold text-white">{scen.name || scen.scenario_name}</p>
                           <p className="text-sm text-gray-400">{scen.description || scen.impact}</p>
                         </div>
                         <div className="text-right">
                           <p className={`text-lg font-mono font-bold ${scen.status === 'PASS' || scen.status === 'SECURE' ? 'text-emerald-400' : scen.status === 'FAIL' || scen.status === 'DISTRESSED' ? 'text-red-400' : 'text-amber-400'}`}>{scen.status}</p>
                           {scen.recomputed_dscr !== undefined && <p className="text-xs text-gray-500">DSCR: {Number(scen.recomputed_dscr).toFixed(2)}x</p>}
                         </div>
                       </div>
                       {scen.scenario_id === "REVERSE_STRESS" && scen.reverse_stress_details && (
                         <div className="mt-4 p-3 bg-red-500/10 rounded border border-red-500/20">
                           <p className="text-sm text-white mb-2 font-bold">Reverse Stress Details</p>
                           <pre className="text-xs text-red-300 font-mono overflow-auto">{JSON.stringify(scen.reverse_stress_details, null, 2)}</pre>
                         </div>
                       )}
                     </div>
                   ))}
                 </div>
              </div>
            )}
          </div>
        );
      case 5:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">6. Bankability and Analyst Recommendation</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-black/30 p-6 rounded-xl border border-white/5">
                <p className="text-sm text-gray-400 mb-2">Analyst Recommendation</p>
                <p className="text-xl font-bold text-white">{data.assessment?.analyst_recommendation || "PENDING"}</p>
              </div>
              <div className="bg-black/30 p-6 rounded-xl border border-white/5">
                <p className="text-sm text-gray-400 mb-2">Policy Recommendation</p>
                <p className="text-xl font-bold text-white">{data.assessment?.policy_recommendation || "N/A"}</p>
              </div>
            </div>
            <h3 className="text-lg font-bold text-white mt-4">Bankability Interventions</h3>
            {data.assessment?.bankability_interventions?.map((inv: any, i: number) => (
              <div key={i} className="bg-blue-500/10 p-4 rounded-xl border border-blue-500/20">
                <p className="text-blue-400 font-bold">{inv.intervention_type}</p>
                <p className="text-sm text-gray-300 mt-1">{inv.description}</p>
              </div>
            ))}
          </div>
        );
      case 6:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">7. SA Mandate and Human Decision</h2>
            <p className="text-gray-400 mb-6">Final Sign-off.</p>
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
      case 7:
        return (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white mb-2">8. Decision Package, Verification and Replay</h2>
            <div className="bg-black/30 p-6 rounded-xl border border-white/5 font-mono text-xs text-gray-400 overflow-auto h-96">
              <pre>{JSON.stringify(data.assessment || {}, null, 2)}</pre>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-black text-gray-200 flex flex-col">
      <div className="max-w-5xl mx-auto w-full px-4 py-8 flex-1 flex flex-col">
        
        {/* Header */}
        <div className="flex justify-between items-end mb-8 border-b border-white/10 pb-6 shrink-0">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Credit Committee Decision Room</h1>
            <p className="text-gray-400">Guided evaluation journey for {data.business_name}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500">Case ID: <span className="font-mono text-gray-300">{caseId}</span></p>
            <p className="text-sm text-gray-500">Req. Amount: <span className="font-mono text-white font-bold">{formatCurrency(data.requested_amount)}</span></p>
          </div>
        </div>

        {/* 8-Step Stepper Header */}
        <div className="flex mb-8 shrink-0 relative px-4">
            <div className="absolute top-1/2 left-8 right-8 h-0.5 bg-white/10 -translate-y-1/2 z-0"></div>
            {steps.map((step, idx) => {
              const Icon = step.icon;
              const isActive = currentStep === idx;
              const isPast = currentStep > idx;
              return (
                <div key={idx} className="flex-1 flex flex-col items-center relative z-10">
                  <button
                      onClick={() => setCurrentStep(idx)}
                      className={`w-12 h-12 rounded-full flex items-center justify-center border-2 transition-all ${
                          isActive
                          ? 'bg-blue-900 border-blue-500 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.5)]' 
                          : isPast
                          ? 'bg-emerald-900/50 border-emerald-500/50 text-emerald-400' 
                          : 'bg-black border-white/20 text-gray-600 hover:border-white/40'
                      }`}
                      title={step.title}
                  >
                      <Icon className="w-5 h-5" />
                  </button>
                  <p className={`mt-2 text-xs font-semibold whitespace-nowrap ${isActive ? 'text-blue-400' : isPast ? 'text-emerald-400/80' : 'text-gray-600'}`}>
                    {step.title}
                  </p>
                </div>
              );
            })}
        </div>

        {/* Content */}
        <div className="bg-white/5 border border-white/10 rounded-3xl p-8 mb-8 flex-1 flex flex-col min-h-[500px]">
          {renderStepContent()}
        </div>

        {/* Navigation */}
        <div className="flex justify-between shrink-0">
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
            Next Section
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>

      </div>
    </div>
  );
}
