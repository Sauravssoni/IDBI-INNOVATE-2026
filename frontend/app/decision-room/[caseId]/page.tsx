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
import type { VerificationResult, ReplayResult, StressResponse, HumanContext } from "@/types";
import { IntegrityGraph } from "@/components/IntegrityGraph";

const PERSONAS = [
  { key: "SHAKTI_PRECISION_001", label: "Shakti — assessable/approvable" },
  { key: "NAVPRERNA_TECH_001", label: "Navprerna — insufficient evidence" },
  { key: "RANGREZ_TEXTILES_001", label: "Rangrez — contradiction/integrity review" },
  { key: "NIRMAAN_INFRA_001", label: "Nirmaan — negative cash/decline" }
];

export default function DecisionRoomPage() {
  const { caseId } = useParams();
  const router = useRouter();
  
  const [decisionPackage, setDecisionPackage] = useState<DecisionPackageResponse | null>(null);
  const [sealedPackageMetadata, setSealedPackageMetadata] = useState<Record<string, unknown> | null>(null);
  const data = decisionPackage;
  const setData = setDecisionPackage;

  const [stressData, setStressData] = useState<StressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [humanContext, setHumanContext] = useState<HumanContext | null>(null);
  
  const [currentStep, setCurrentStep] = useState(0);
  const [decision, setDecision] = useState<string | null>(null);
  const [isOffline, setIsOffline] = useState(false);
  
  // Human Sanction Form State
  const [approvedAmount, setApprovedAmount] = useState<string>("");
  const [reason, setReason] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [sanctionError, setSanctionError] = useState<string | null>(null);

  // Verification & Replay State
  const [packageId, setPackageId] = useState<string | null>(null);
  const [packageHash, setPackageHash] = useState<string | null>(null);
  const [sealing, setSealing] = useState(false);
  const [sealError, setSealError] = useState<string | null>(null);

  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null);
  const [verificationError, setVerificationError] = useState<string | null>(null);

  const [replaying, setReplaying] = useState(false);
  const [replayResult, setReplayResult] = useState<ReplayResult | null>(null);
  const [replayError, setReplayError] = useState<string | null>(null);

  // For Persona Switcher
  const [allCases, setAllCases] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        const casesRes = await apiFetch<Record<string, unknown>[]>("/api/cases");
        if (casesRes.status === 200 && casesRes.data) {
          setAllCases(casesRes.data);
          if (casesRes.offline) setIsOffline(true);
        }

        // Call GET to get the full unsealed decision view required by the page. Do not POST or seal on page load.
        const res = await apiFetch<DecisionPackageResponse>(`/api/cases/${caseId}/decision-package`, { method: "GET" });
        if (res.status === 200 && res.data) {
          setDecisionPackage(res.data);
          if (res.offline) setIsOffline(true);
          if (res.data.package_id) {
            setPackageId(res.data.package_id);
            if (res.data.package_hash) setPackageHash(res.data.package_hash);
            setSealedPackageMetadata({
              package_id: res.data.package_id,
              package_hash: res.data.package_hash,
              case_version: res.data.case_version,
            });
          }
          // Fetch stress data concurrently
          apiFetch(`/api/cases/${caseId}/stress-lab`).then(stressRes => {
            if (stressRes.status === 200) {
              setStressData(stressRes.data as import('@/types').StressResponse);
            }
          });
          apiFetch(`/api/cases/${caseId}/human-decision-context`).then(hcRes => {
            if (hcRes.status === 200 && hcRes.data) {
              setHumanContext(hcRes.data as import('@/types').HumanContext);
            }
          });
        } else {
          setError(res.error || "Failed to load decision package");
        }
      } catch (err: unknown) {
        setError((err as Error).message || "Unknown error");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [caseId]);

  const handlePersonaSwitch = (bizId: string) => {
    const targetCase = allCases.find((c: Record<string, unknown>) => c.business_id === bizId);
    if (targetCase) {
      router.push(`/decision-room/${targetCase.id}`);
    } else {
      alert(`Persona case not found for business ID: ${bizId}`);
    }
  };

  const submitDecision = async (status: string) => {
    setSubmitting(true);
    setSanctionError(null);
    try {
      const res = await apiFetch(`/api/cases/${caseId}/human-decision`, {
        method: "POST",
        headers: {
          "Idempotency-Key": crypto.randomUUID(),
          "X-Expected-Version": (data?.case_version || 0).toString(),
        },
        body: JSON.stringify({
          decision: status,
          reason: reason,
          expected_version: data?.case_version || 0,
          approved_amount: Number(approvedAmount)
        })
      });
      if (res.status === 200) {
        setDecision(status);
        // Remain on the Decision Room after sanction so the judge can seal, verify and replay continuously.
      } else {
        setSanctionError(res.error || JSON.stringify(res.data));
      }
    } catch (err: unknown) {
      setSanctionError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSeal = async () => {
    setSealing(true);
    setSealError(null);
    try {
      const res = await apiFetch(`/api/cases/${caseId}/decision-package`, { method: "POST" });
      if (res.status === 200 && res.data) {
        const sealRes = res.data as Record<string, unknown>;
        const newPkgId = (sealRes.package_id as string) || (sealRes.id as string);
        const newPkgHash = sealRes.package_hash as string;
        setSealedPackageMetadata(sealRes);
        if (newPkgId) setPackageId(newPkgId);
        if (newPkgHash) setPackageHash(newPkgHash);
      } else {
        setSealError(res.error || "Failed to seal package");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setSealError(msg || "Error sealing package");
    } finally {
      setSealing(false);
    }
  };

  const handleVerify = async () => {
    if (!packageId || packageId === "undefined") {
      setVerificationError("Decision package has not been sealed yet. Complete a terminal decision and seal the package before verifying or replaying.");
      return;
    }
    setVerifying(true);
    setVerificationError(null);
    setVerificationResult(null);
    try {
      const res = await apiFetch<VerificationResult>(`/api/cases/${caseId}/verify-package/${packageId}`, { 
        method: "POST",
        headers: {
          "X-Expected-Version": (data?.case_version || 0).toString(),
        }
      });
      if (res.status === 200 && res.data) {
        setVerificationResult(res.data as import('@/types').VerificationResult);
      } else {
        setVerificationError(res.error || "Verification failed");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setVerificationError(msg || "Error verifying package signature");
    } finally {
      setVerifying(false);
    }
  };

  const handleReplay = async () => {
    if (!packageId || packageId === "undefined") {
      setReplayError("Decision package has not been sealed yet. Complete a terminal decision and seal the package before verifying or replaying.");
      return;
    }
    setReplaying(true);
    setReplayError(null);
    setReplayResult(null);
    try {
      const res = await apiFetch<ReplayResult>(`/api/cases/${caseId}/replay-package/${packageId}`, { 
        method: "POST",
        headers: {
          "X-Expected-Version": (data?.case_version || 0).toString(),
        }
      });
      if (res.status === 200 && res.data) {
        setReplayResult(res.data as import('@/types').ReplayResult);
      } else {
        setReplayError(res.error || "Replay failed");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setReplayError(msg || "Error executing replay");
    } finally {
      setReplaying(false);
    }
  };

  const steps = [
    { title: "Evidence and Integrity", icon: Fingerprint, id: 0 },
    { title: "Financial Health Waterfall", icon: Activity, id: 1 },
    { title: "Product Comparison", icon: BarChart3, id: 2 },
    { title: "Limit Bridge", icon: Briefcase, id: 3 },
    { title: "Stress and Reverse Stress", icon: PlayCircle, id: 4 },
    { title: "Bankability and Analyst Recommendation", icon: ShieldCheck, id: 5 },
    { title: "Human Sanction", icon: UserCheck, id: 6 },
    { title: "Package Verification and Replay", icon: Database, id: 7 }
  ];

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

  // Helper variables for "Above the fold"
  const assessment = data.assessment || {};
  const evidenceTier = assessment.evidence_passport?.evidence_tier || "N/A";
  const assessmentCertainty = assessment.assessment_certainty || "N/A";
  const integrityState = assessment.integrity_state || "N/A";
  const fhi = assessment.financial_health_index !== undefined ? Number(assessment.financial_health_index).toFixed(2) : "N/A";
  const vyaparScore = assessment.vyapar_credit_health_score ?? "N/A";
  const currentDSCR = assessment.current_dscr ? Number(assessment.current_dscr).toFixed(2) + "x" : "N/A";
  const postLoanDSCR = assessment.post_loan_dscr ? Number(assessment.post_loan_dscr).toFixed(2) + "x" : "N/A";
  const supportableAmt = assessment.limit_bridge?.final_supportable_amount || assessment.supportable_amount || 0;
  const bindingConstraint = assessment.limit_bridge?.binding_constraint || assessment.binding_constraint || "N/A";
  const stressVerdict = stressData?.overall_stress_status || "PENDING";
  const policyRec = assessment.policy_recommendation || "N/A";
  const analystRec = assessment.analyst_recommendation || "PENDING";
  const humanState = data.human_action || "PENDING";

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-gray-200 flex flex-col font-sans">
      {/* 
        =======================================================================
        ABOVE THE FOLD - SUMMARY GRID + PERSONA SWITCHER
        =======================================================================
      */}
      <div className="bg-black border-b border-white/10 px-4 sm:px-6 lg:px-8 py-6 shrink-0">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center mb-6 gap-4">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-3xl font-bold text-white mb-1">Command Centre</h1>
                {isOffline && (
                  <span className="bg-red-500/20 text-red-400 text-xs font-bold px-2 py-1 rounded border border-red-500/30">
                    OFFLINE SNAPSHOT — READ ONLY
                  </span>
                )}
              </div>
              <p className="text-gray-400">Credit Committee evaluation for {data.business_name}</p>
            </div>
            
            <div className="bg-white/5 border border-white/10 rounded-lg p-2 flex items-center gap-3">
              <span className="text-sm text-gray-400">Demo Persona:</span>
              <select 
                className="bg-black text-white border border-white/20 rounded px-3 py-1.5 text-sm font-medium focus:outline-none focus:border-emerald-500"
                onChange={(e) => handlePersonaSwitch(e.target.value)}
                value={String(allCases.find(c => c.id === caseId)?.business_id || "")}
              >
                <option value="" disabled>Select Persona</option>
                {PERSONAS.map(p => (
                  <option key={p.key} value={p.key}>{p.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-4 border border-white/10 rounded-xl p-4 bg-white/[0.02]">
            <div>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Borrower</p>
              <p className="font-bold text-white truncate text-sm" title={data.business_name}>{data.business_name}</p>
            </div>
            <div>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Product</p>
              <p className="font-bold text-white text-sm">{data.requested_product}</p>
            </div>
            <div>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Requested</p>
              <p className="font-bold text-blue-400 text-sm">{formatCurrency(data.requested_amount)}</p>
            </div>
            <div>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Supportable</p>
              <p className="font-bold text-emerald-400 text-sm">{formatCurrency(supportableAmt)}</p>
            </div>
            <div>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Evidence / Cert</p>
              <p className="font-bold text-white text-sm truncate">{evidenceTier} / {assessmentCertainty}</p>
            </div>
            <div>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Integrity / FHI</p>
              <p className="font-bold text-white text-sm">{integrityState} / {fhi}</p>
            </div>
            <div>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">DSCR (Pre/Post)</p>
              <p className="font-bold text-white text-sm">{currentDSCR} / {postLoanDSCR}</p>
            </div>
            <div>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Score</p>
              <p className="font-bold text-emerald-400 text-sm">{vyaparScore}</p>
            </div>
          </div>
          
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mt-4 border border-white/10 rounded-xl p-4 bg-white/[0.02]">
             <div className="col-span-2">
                <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Binding Constraint</p>
                <p className="font-bold text-red-400 text-sm truncate">{String(bindingConstraint)}</p>
             </div>
             <div>
                <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Stress Verdict</p>
                <p className={`font-bold text-sm ${stressVerdict === 'PASS' ? 'text-emerald-400' : 'text-red-400'}`}>{stressVerdict}</p>
             </div>
             <div>
                <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Analyst Rec</p>
                <p className="font-bold text-blue-400 text-sm truncate">{analystRec}</p>
             </div>
             <div>
                <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Decision State</p>
                <p className="font-bold text-white text-sm">{humanState}</p>
             </div>
          </div>
        </div>
      </div>

      {/* 
        =======================================================================
        MAIN VISUAL STRUCTURE (4 ZONES)
        =======================================================================
      */}
      <div className="flex-1 flex flex-col lg:flex-row max-w-[1600px] w-full mx-auto overflow-hidden">
        
        {/* LEFT: Guided Navigation */}
        <div className="lg:w-64 bg-black/50 border-r border-white/10 p-4 overflow-y-auto shrink-0 flex flex-col gap-2">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4 px-2">Decision Flow</h3>
          {steps.map((step, idx) => {
            const Icon = step.icon;
            const isActive = currentStep === idx;
            return (
              <button
                key={idx}
                onClick={() => setCurrentStep(idx)}
                className={`flex items-center gap-3 w-full text-left px-4 py-3 rounded-xl transition-all ${
                  isActive 
                    ? 'bg-blue-600 text-white font-bold shadow-lg shadow-blue-900/20' 
                    : 'text-gray-400 hover:bg-white/5 hover:text-white'
                }`}
              >
                <Icon className={`w-5 h-5 ${isActive ? 'text-white' : 'text-gray-500'}`} />
                <span className="text-sm">{step.id + 1}. {step.title}</span>
              </button>
            );
          })}
        </div>

        {/* CENTRE: Analytical View */}
        <div className="flex-1 bg-[#0a0a0a] p-6 lg:p-8 overflow-y-auto">
          {currentStep === 0 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h2 className="text-2xl font-bold text-white mb-4">Evidence and Integrity</h2>
              <div className="grid grid-cols-2 gap-4 mb-6">
                 <div className="bg-white/5 p-4 rounded-xl border border-white/10">
                   <p className="text-xs text-gray-400 mb-1">Evidence Passport Tier</p>
                   <p className="text-lg font-bold text-emerald-400">{evidenceTier}</p>
                   <p className="text-xs text-gray-500 mt-1">{assessment.evidence_passport?.tier_description}</p>
                 </div>
                 <div className="bg-white/5 p-4 rounded-xl border border-white/10">
                   <p className="text-xs text-gray-400 mb-1">Integrity State</p>
                   <p className="text-lg font-bold text-white">{integrityState}</p>
                 </div>
              </div>
              <div className="h-[500px] border border-white/10 rounded-xl overflow-hidden bg-black relative">
                {integrityState === "INTEGRITY_REVIEW_REQUIRED" && (
                   <div className="absolute top-4 left-4 z-10 bg-red-500 text-white text-xs font-bold px-3 py-1 rounded shadow-lg flex items-center gap-2">
                     <AlertTriangle className="w-4 h-4"/>
                     SEEDED DEMONSTRATION RELATIONSHIPS
                   </div>
                )}
                <IntegrityGraph caseId={caseId as string} entityName={data.business_name} />
              </div>
            </div>
          )}

          {currentStep === 1 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h2 className="text-2xl font-bold text-white mb-4">Financial Health Waterfall</h2>
              <div className="bg-white/5 p-6 rounded-xl border border-white/10">
                 <div className="flex justify-between items-center mb-8 border-b border-white/10 pb-6">
                   <div>
                     <p className="text-gray-400 text-sm">Vyapar Credit Health Score</p>
                     <p className="text-5xl font-bold text-emerald-400 font-mono mt-1">{vyaparScore}</p>
                   </div>
                   <div className="text-right">
                     <p className="text-gray-400 text-sm">Financial Health Index (FHI)</p>
                     <p className="text-5xl font-bold text-white font-mono mt-1">{fhi}</p>
                   </div>
                 </div>
                 <div className="space-y-4">
                  {assessment.six_pillars?.map((p: import('@/lib/types').FinancialHealthPillarResponse, i: number) => (
                    <div key={i} className="flex justify-between items-center p-4 bg-black/40 rounded-lg border border-white/5 hover:bg-black/60 transition">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                           <p className="font-bold text-white">{p.name}</p>
                           {p.health_status === 'STRONG' && <span className="w-2 h-2 rounded-full bg-emerald-500"></span>}
                           {p.health_status === 'MODERATE' && <span className="w-2 h-2 rounded-full bg-blue-500"></span>}
                           {p.health_status === 'WEAK' && <span className="w-2 h-2 rounded-full bg-amber-500"></span>}
                           {p.health_status === 'CRITICAL' && <span className="w-2 h-2 rounded-full bg-red-500"></span>}
                        </div>
                        <p className="text-xs text-gray-400 mt-1">{p.health_status}</p>
                      </div>
                      <div className="text-2xl font-mono text-white text-right w-24">
                        {p.score > 0 ? `+${p.score}` : p.score}
                      </div>
                    </div>
                  ))}
                 </div>
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h2 className="text-2xl font-bold text-white mb-4">Four-Product Comparison</h2>
              <div className="overflow-x-auto border border-white/10 rounded-xl bg-white/5">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-white/10 bg-black/50">
                      <th className="p-4 text-xs uppercase tracking-wider text-gray-500 font-bold">Product</th>
                      <th className="p-4 text-xs uppercase tracking-wider text-gray-500 font-bold text-right">Capacity limit</th>
                      <th className="p-4 text-xs uppercase tracking-wider text-gray-500 font-bold">Binding Constraint</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assessment.product_capacities ? Object.values(assessment.product_capacities).map((pc: import('@/lib/types').LimitDetail, i: number) => (
                      <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                        <td className="p-4 font-bold text-white">{pc.product || pc.product}</td>
                        <td className="p-4 font-bold text-emerald-400 text-right">{formatCurrency(Number(pc.binding_limit || pc.max_capacity))}</td>
                        <td className="p-4 text-xs text-red-400 font-mono">{pc.reason_codes?.[0] || "N/A"}</td>
                      </tr>
                    )) : (
                      <tr><td colSpan={3} className="p-4 text-gray-500 text-center">No data available</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {currentStep === 3 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h2 className="text-2xl font-bold text-white mb-4">Limit Bridge</h2>
              <div className="bg-white/5 p-6 rounded-xl border border-white/10">
                {assessment.limit_bridge?.stages ? (
                  <div className="space-y-4">
                    {((assessment.limit_bridge?.stages || []) as Record<string, unknown>[]).map((stage: { label?: string, amount?: number, impact_type?: string, reason?: string, rationale?: string, applied?: boolean, stage_id?: string, explanation?: string, formula?: string, calculated_value?: number }, i: number) => (
                      <div key={i} className={`flex justify-between items-start pb-4 border-b border-white/5 ${stage.applied ? 'opacity-100' : 'opacity-50'}`}>
                        <div className="flex-1 pr-4">
                          <p className="text-white font-bold flex items-center gap-2">
                             {stage.stage_id}
                             {stage.applied && <span className="text-[10px] bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded border border-blue-500/30">APPLIED CAP</span>}
                          </p>
                          <p className="text-sm text-gray-400 mt-1">{stage.explanation}</p>
                          <p className="text-xs text-emerald-500/70 mt-2 font-mono bg-black/50 p-2 rounded inline-block">{stage.formula}</p>
                        </div>
                        <div className="text-right shrink-0">
                          <p className="text-xl font-bold text-white font-mono">{formatCurrency(stage.calculated_value)}</p>
                        </div>
                      </div>
                    ))}
                    <div className="pt-2 flex justify-between items-center mt-2">
                       <div>
                         <p className="text-emerald-400 font-bold text-xl">Final Supportable Amount</p>
                         <p className="text-xs text-red-400 mt-1">Constrained by: {String(assessment.limit_bridge.binding_constraint)}</p>
                       </div>
                       <p className="text-3xl font-bold text-emerald-400 font-mono">{formatCurrency(assessment.limit_bridge.final_supportable_amount)}</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-gray-500">Limit bridge data not available.</p>
                )}
              </div>
            </div>
          )}

          {currentStep === 4 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h2 className="text-2xl font-bold text-white mb-4">Stress and Reverse Stress</h2>
              {!stressData ? (
                <p className="text-gray-500">Loading stress scenarios...</p>
              ) : (
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                   <div className="space-y-4">
                     <h3 className="text-lg font-bold text-gray-400">Stress Matrix</h3>
                     {stressData.scenarios?.filter((s: import('@/types/index').StressResponse['scenarios'][0]) => s.scenario_id !== 'REVERSE_STRESS').map((scen: import('@/types/index').StressResponse['scenarios'][0], idx: number) => {
                       const isPass = scen.status === 'PASS' || scen.status === 'SECURE';
                       return (
                         <div key={idx} className={`p-4 rounded-xl border ${isPass ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-red-500/5 border-red-500/20'}`}>
                           <div className="flex justify-between items-center mb-2">
                             <p className="font-bold text-white">{scen.name || scen.scenario_name}</p>
                             <span className={`px-2 py-1 text-xs font-bold rounded ${isPass ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                               {scen.status}
                             </span>
                           </div>
                           <p className="text-sm text-gray-400 mb-2">{scen.description || scen.impact}</p>
                           {scen.recomputed_dscr !== undefined && (
                             <p className="text-xs font-mono text-gray-500">Recomputed DSCR: <span className="text-white">{Number(scen.recomputed_dscr).toFixed(2)}x</span></p>
                           )}
                         </div>
                       )
                     })}
                   </div>
                   
                   <div className="space-y-4">
                     <h3 className="text-lg font-bold text-gray-400">Reverse Stress Boundaries</h3>
                     {stressData.scenarios?.filter((s: import('@/types/index').StressResponse['scenarios'][0]) => s.scenario_id === 'REVERSE_STRESS').map((scen: import('@/types/index').StressResponse['scenarios'][0], idx: number) => (
                       <div key={idx} className="bg-black border border-amber-500/30 p-5 rounded-xl">
                         <div className="flex items-center gap-2 mb-4">
                           <AlertTriangle className="w-5 h-5 text-amber-500"/>
                           <p className="font-bold text-amber-500">Breaking Points</p>
                         </div>
                         <p className="text-sm text-gray-400 mb-4">{scen.description || "Boundaries at which DSCR falls below 1.0"}</p>
                         {scen.reverse_stress_details && (
                           <div className="space-y-3">
                              {Object.entries(scen.reverse_stress_details).map(([key, val], i) => (
                                <div key={i} className="flex justify-between items-center border-b border-white/5 pb-2">
                                  <span className="text-sm text-gray-300 capitalize">{key.replace(/_/g, ' ')}</span>
                                  <span className="font-mono text-red-400 text-sm font-bold">{val}</span>
                                </div>
                              ))}
                           </div>
                         )}
                       </div>
                     ))}
                   </div>
                </div>
              )}
            </div>
          )}

          {currentStep === 5 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h2 className="text-2xl font-bold text-white mb-4">Bankability and Analyst Recommendation</h2>
              
              <div className="grid grid-cols-2 gap-4 mb-6">
                 <div className="bg-blue-900/20 border border-blue-500/30 p-6 rounded-xl">
                   <p className="text-xs text-blue-400 font-bold uppercase tracking-wider mb-2">Analyst Recommendation</p>
                   <p className="text-2xl font-bold text-white">{analystRec}</p>
                 </div>
                 <div className="bg-emerald-900/20 border border-emerald-500/30 p-6 rounded-xl">
                   <p className="text-xs text-emerald-400 font-bold uppercase tracking-wider mb-2">Policy Recommendation</p>
                   <p className="text-2xl font-bold text-white">{policyRec}</p>
                 </div>
              </div>

              <h3 className="text-lg font-bold text-gray-400 mb-4">Bankability Interventions (Before / After)</h3>
              <div className="space-y-4">
                {assessment.bankability_interventions?.map((inv: import("@/lib/types").BankabilityIntervention, i: number) => (
                  <div key={i} className="bg-white/5 p-5 rounded-xl border border-white/10">
                    <p className="text-white font-bold mb-2 flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-500" />
                      {inv.intervention_type}
                    </p>
                    <p className="text-sm text-gray-300">{inv.description}</p>
                  </div>
                ))}
                {(!assessment.bankability_interventions || assessment.bankability_interventions.length === 0) && (
                  <p className="text-gray-500 italic">No structural interventions required.</p>
                )}
              </div>
            </div>
          )}

          {currentStep === 6 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-3xl mx-auto">
              <h2 className="text-2xl font-bold text-white mb-6">Human Sanction</h2>
              
              <div className="grid grid-cols-2 gap-4 mb-8">
                <div className="bg-black border border-white/10 p-4 rounded-xl">
                  <p className="text-xs text-gray-500 mb-1">Requested Amount</p>
                  <p className="text-lg font-bold text-white font-mono">{formatCurrency(data.requested_amount)}</p>
                </div>
                <div className="bg-black border border-emerald-500/30 p-4 rounded-xl">
                  <p className="text-xs text-emerald-500/70 mb-1">Supportable Amount</p>
                  <p className="text-lg font-bold text-emerald-400 font-mono">{formatCurrency(supportableAmt)}</p>
                </div>
                <div className="bg-black border border-white/10 p-4 rounded-xl">
                  <p className="text-xs text-gray-500 mb-1">Mandate Ceiling</p>
                  <p className="text-sm font-bold text-gray-300 font-mono">{humanContext?.mandate_ceiling ? formatCurrency(humanContext.mandate_ceiling) : "MANDATE NOT AVAILABLE — APPROVAL DISABLED"}</p>
                </div>
                <div className="bg-black border border-white/10 p-4 rounded-xl">
                  <p className="text-xs text-gray-500 mb-1">Analyst Rec / Case Version</p>
                  <p className="text-lg font-bold text-blue-400 text-sm truncate">{analystRec} / v{data.case_version}</p>
                </div>
              </div>

              {decision ? (
                <div className={`p-8 rounded-xl border flex flex-col items-center text-center ${decision === 'APPROVE_AS_REQUESTED' ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                  <CheckCircle2 className={`w-16 h-16 mb-4 ${decision === 'APPROVE_AS_REQUESTED' ? 'text-emerald-400' : 'text-red-400'}`} />
                  <h3 className={`text-2xl font-bold ${decision === 'APPROVE_AS_REQUESTED' ? 'text-emerald-400' : 'text-red-400'}`}>
                    Decision Recorded
                  </h3>
                  <p className="text-gray-400 mt-2">Redirecting...</p>
                </div>
              ) : (
                <div className="bg-white/5 border border-white/10 rounded-xl p-6">
                  {sanctionError && (
                    <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm flex items-start gap-3">
                      <AlertTriangle className="w-5 h-5 shrink-0" />
                      <div className="break-all font-mono whitespace-pre-wrap">{sanctionError}</div>
                    </div>
                  )}

                  <div className="space-y-4 mb-8">
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Approved Amount (INR)</label>
                      <input 
                        type="number"
                        value={approvedAmount}
                        onChange={(e) => setApprovedAmount(e.target.value)}
                        placeholder={`e.g. ${supportableAmt}`}
                        className="w-full bg-black border border-white/20 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-emerald-500 font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Decision Reason / Notes</label>
                      <textarea 
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        placeholder="Provide formal rationale..."
                        className="w-full bg-black border border-white/20 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-emerald-500 h-24 resize-none"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <button 
                      onClick={() => submitDecision(Number(approvedAmount) === data.requested_amount ? "APPROVE_AS_REQUESTED" : "APPROVE_ALTERNATIVE_STRUCTURE")}
                      disabled={submitting || !approvedAmount || !reason || !humanContext?.maximum_permitted_amount || isOffline}
                      className="px-6 py-4 bg-emerald-600 rounded-lg text-white font-bold hover:bg-emerald-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2"
                    >
                      <ThumbsUp className="w-5 h-5" />
                      Sanction Approve
                    </button>
                    <button 
                      onClick={() => submitDecision("DECLINE_AFTER_HUMAN_REVIEW")}
                      disabled={submitting || !reason || isOffline}
                      className="px-6 py-4 bg-red-600 rounded-lg text-white font-bold hover:bg-red-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2"
                    >
                      <ThumbsDown className="w-5 h-5" />
                      Decline
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {currentStep === 7 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h2 className="text-2xl font-bold text-white mb-4">Package Verification and Replay</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                 <div className="bg-black border border-white/10 p-5 rounded-xl">
                   <p className="text-xs text-gray-500 mb-2">Package Hash (SHA-256)</p>
                   <p className="font-mono text-xs text-emerald-400 break-all">{data.package_hash}</p>
                 </div>
                 <div className="bg-black border border-white/10 p-5 rounded-xl">
                   <p className="text-xs text-gray-500 mb-2">Policy Version</p>
                   <p className="font-mono text-sm text-white">{data.policy_version}</p>
                 </div>
                 <div className="bg-black border border-white/10 p-5 rounded-xl">
                   <p className="text-xs text-gray-500 mb-2">Calculation Engine</p>
                   <p className="font-mono text-sm text-white">{data.calculation_version}</p>
                 </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                 <div className="bg-white/5 border border-white/10 rounded-xl p-5">
                   <h3 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
                     <ShieldCheck className="w-5 h-5 text-blue-400" /> Verify Seal
                   </h3>
                   {!packageId ? (
                     <>
                       <button 
                         onClick={handleSeal}
                         disabled={sealing}
                         className="px-4 py-2 bg-blue-600 rounded-lg text-white font-bold hover:bg-blue-700 transition disabled:opacity-50 text-sm mb-4"
                       >
                         {sealing ? "Sealing..." : "Seal Package"}
                       </button>
                       {sealError && <p className="text-red-400 text-sm">{sealError}</p>}
                     </>
                   ) : (
                     <>
                       <button 
                         onClick={handleVerify}
                         disabled={verifying}
                         className="px-4 py-2 bg-blue-600 rounded-lg text-white font-bold hover:bg-blue-700 transition disabled:opacity-50 text-sm mb-4"
                       >
                         {verifying ? "Verifying..." : "Verify Package Signature"}
                       </button>
                       {verificationError && <p className="text-red-400 text-sm">{verificationError}</p>}
                     </>
                   )}
                   {verificationResult && (
                     <div className="p-3 bg-black rounded-lg border border-white/10 text-sm font-mono space-y-2">
                       <p className={`font-bold ${verificationResult.valid ? "text-emerald-400" : "text-red-400"}`}>
                         {verificationResult.valid ? "Verified — Cryptographic Seal Intact" : "Seal Mismatch — Canonical Hash Changed"}
                       </p>
                       <p className="text-gray-400 break-all text-xs">Expected Hash: {verificationResult.expected_hash}</p>
                       <p className="text-gray-400 break-all text-xs">Actual Hash: {verificationResult.actual_hash}</p>
                       {verificationResult.valid && data?.audit_chain && Array.isArray(data.audit_chain) && (
                         <div className="mt-4 pt-3 border-t border-white/10">
                           <p className="text-xs font-bold text-white mb-2">Chronological Audit Trail:</p>
                           <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                             {[...data.audit_chain]
                               .sort((a, b) => (new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime()))
                               .map((evt, idx) => (
                                 <div key={idx} className="text-[11px] bg-white/5 p-2 rounded flex flex-col gap-1">
                                   <div className="flex justify-between items-center text-gray-300">
                                     <span className="font-semibold text-blue-300">{evt.event_type}</span>
                                     <span className="text-gray-500">{evt.created_at ? new Date(evt.created_at).toLocaleString() : ""}</span>
                                   </div>
                                   <div className="text-gray-400">Actor: <span className="text-gray-300">{evt.actor}</span></div>
                                   {evt.event_hash && <div className="text-gray-500 font-mono text-[9px] truncate">Hash: {evt.event_hash}</div>}
                                 </div>
                               ))}
                           </div>
                         </div>
                       )}
                     </div>
                   )}
                 </div>

                 <div className="bg-white/5 border border-white/10 rounded-xl p-5">
                   <h3 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
                     <RefreshCw className="w-5 h-5 text-purple-400" /> Independent Replay
                   </h3>
                   <button 
                     onClick={handleReplay}
                     disabled={replaying || !packageId}
                     className="px-4 py-2 bg-purple-600 rounded-lg text-white font-bold hover:bg-purple-700 transition disabled:opacity-50 text-sm mb-4"
                   >
                     {replaying ? "Replaying..." : "Execute Full Engine Replay"}
                   </button>
                   {replayError && <p className="text-red-400 text-sm">{replayError}</p>}
                   {replayResult && (
                     <div className="p-3 bg-black rounded-lg border border-white/10 text-sm font-mono space-y-2">
                       <p className="text-emerald-400 font-bold">Replay: {replayResult.status === "INDEPENDENTLY_REPRODUCED" ? "REPLAY MATCHED" : (replayResult.status === "VERSION_UNAVAILABLE" ? "VERSION UNAVAILABLE" : (replayResult.status === "FEATURE_SNAPSHOT_INCOMPLETE" ? "FEATURE SNAPSHOT INCOMPLETE" : "REPLAY MISMATCHED"))}</p>
                       {replayResult.differences && Object.keys(replayResult.differences).length > 0 && (
                         <p className="text-red-400 text-xs">Differences: {JSON.stringify(replayResult.differences)}</p>
                       )}
                     </div>
                   )}
                 </div>
              </div>

              <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                <div className="bg-black/50 px-4 py-3 border-b border-white/10 flex justify-between items-center cursor-pointer">
                  <p className="font-bold text-white text-sm">Technical Payload Disclosure</p>
                </div>
                <div className="p-4 bg-[#0a0a0a] max-h-96 overflow-y-auto">
                  <pre className="text-[10px] text-gray-500 font-mono whitespace-pre-wrap">
                    {JSON.stringify(data, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT: Decision Summary & Critical Alerts */}
        <div className="lg:w-72 bg-black/50 border-l border-white/10 p-6 overflow-y-auto shrink-0">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4">Critical Alerts</h3>
          <div className="space-y-3 mb-8">
            {data.monitoring_status?.alerts?.map((alert: { status?: string, rule_name?: string, detail?: string, severity?: string, message?: string, date?: string }, i: number) => (
              <div key={i} className={`p-3 rounded-lg border text-xs ${alert.status === 'TRIGGERED' ? 'bg-red-500/10 border-red-500/30' : 'bg-white/5 border-white/10'}`}>
                <p className={`font-bold ${alert.status === 'TRIGGERED' ? 'text-red-400' : 'text-gray-300'}`}>{alert.rule_name}</p>
                <p className="text-gray-500 mt-1">{alert.detail}</p>
              </div>
            ))}
            {(!data.monitoring_status?.alerts || data.monitoring_status.alerts.length === 0) && (
              <p className="text-xs text-gray-500 italic">No monitoring alerts generated.</p>
            )}
          </div>

          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4">Summary</h3>
          <div className="space-y-4 text-sm">
             <div>
               <p className="text-gray-500">Case Version</p>
               <p className="font-mono text-white">{data.case_version}</p>
             </div>
             <div>
               <p className="text-gray-500">Last Modified</p>
               <p className="font-mono text-white">{new Date(data.generated_at || new Date().toISOString()).toLocaleString()}</p>
             </div>
          </div>
        </div>
      </div>

      {/* 
        =======================================================================
        BOTTOM: Provenance / Policy / Package Status
        =======================================================================
      */}
      <div className="bg-black border-t border-white/10 p-4 shrink-0 text-xs text-gray-500 flex justify-between items-center px-8">
        <div className="flex gap-6 items-center">
          <span className="flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-emerald-500" /> {verificationResult ? (verificationResult.valid === true ? "PACKAGE HASH VERIFIED" : "PACKAGE HASH MISMATCH") : (packageId ? "PACKAGE SEALED — NOT VERIFIED" : "PACKAGE NOT SEALED")}</span>
          <span className="flex items-center gap-2"><RefreshCw className="w-4 h-4 text-purple-500" /> {replayResult ? (replayResult.status === "INDEPENDENTLY_REPRODUCED" ? "REPLAY MATCHED" : "REPLAY MISMATCHED") : "REPLAY NOT RUN"}</span>
          <span className="flex items-center gap-2"><FileText className="w-4 h-4" /> Policy: {data.policy_version}</span>
        </div>
        <div className="font-mono text-gray-600">
          Hash: {data.package_hash?.substring(0, 16)}...
        </div>
      </div>
    </div>
  );
}
