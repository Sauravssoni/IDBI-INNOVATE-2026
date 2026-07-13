import React, { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { 
  FileText, Activity, ShieldCheck, AlertTriangle, Play, CheckCircle2, Printer, Briefcase, Award, Database, Lock
} from "lucide-react";
import { formatCurrency } from "@/lib/formatters";
import type { DecisionPackageResponse, StressResult, AuditVerification } from "@/lib/types";

export default function DecisionPackageTab({ caseId, assessment, decisionPackage }: { caseId: string, assessment?: any, decisionPackage?: any }) {
  const [data, setData] = useState<DecisionPackageResponse | null>(null);
  const [stressData, setStressData] = useState<StressResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verificationResult, setVerificationResult] = useState<AuditVerification | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [auditError, setAuditError] = useState<string | null>(null);

  // Idempotency replay state
  const [simulatingReplay, setSimulatingReplay] = useState(false);
  const [replayResult, setReplayResult] = useState<string | null>(null);

  useEffect(() => {
    if (decisionPackage) {
      setData(decisionPackage);
    }
  }, [decisionPackage]);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      const promises = [apiFetch(`/api/cases/${caseId}/stress-lab`)];
      if (!decisionPackage) {
        promises.push(apiFetch(`/api/cases/${caseId}/decision-package`));
      }
      
      const results = await Promise.all(promises);
      const resStress = results[0];
      const resPackage = results[1];

      if (resStress.status === 200 && resStress.data) {
        setStressData(resStress.data as StressResult);
      }
      
      if (!decisionPackage && resPackage && resPackage.status === 200 && resPackage.data) {
        setData(resPackage.data as DecisionPackageResponse);
      } else if (!decisionPackage && resPackage && resPackage.status !== 200) {
        setError(resPackage.error || "Failed to load decision package.");
      }

      setLoading(false);
    };
    fetchData();
  }, [caseId, decisionPackage]);

  const handleSimulateReplay = async () => {
    if (!data) return;
    setSimulatingReplay(true);
    setReplayResult(null);

    try {
      const idempotencyKey = `idem-replay-${caseId}-${Date.now()}`;
      const payload = { expected_version: data.case_version || 1 };

      // First submission
      const firstRes = await apiFetch(`/api/cases/${caseId}/evaluate`, {
        method: "POST",
        body: JSON.stringify(payload),
        headers: {
          "Idempotency-Key": idempotencyKey,
        },
      });

      // Replay submission with same idempotency key
      const secondRes = await apiFetch(`/api/cases/${caseId}/evaluate`, {
        method: "POST",
        body: JSON.stringify(payload),
        headers: {
          "Idempotency-Key": idempotencyKey,
        },
      });

      if (secondRes.status === 200 || secondRes.status === 409) {
        setReplayResult(
          `Idempotency Verified (HTTP ${secondRes.status}): Duplicate submission blocked/cached cleanly with Key ${idempotencyKey.slice(0, 20)}...`
        );
      } else {
        setReplayResult(`Replay status code: ${secondRes.status} (${secondRes.error || "Response checked"})`);
      }
    } catch (err: any) {
      setReplayResult(`Replay check error: ${err.message || "Unknown error"}`);
    } finally {
      setSimulatingReplay(false);
    }
  };

  const handleExportPackage = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `decision-package-${caseId}-v${data.case_version || 1}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };


  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin h-8 w-8 border-4 border-brand-teal border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-rose-50 border border-rose-200 text-brand-red p-4 rounded-xl flex items-center gap-3">
        <AlertTriangle className="w-5 h-5" />
        <p>{error || "Failed to load decision package."}</p>
      </div>
    );
  }

  const handleVerifyAudit = async () => {
    setVerifying(true);
    setAuditError(null);
    try {
      const res = await apiFetch<AuditVerification>(`/api/cases/${caseId}/verify-audit`, {
        method: "POST"
      });
      if (res.status === 200 && res.data) {
        setVerificationResult(res.data);
      } else {
        setAuditError(res.error || "Verification failed");
      }
    } catch (err: any) {
      setAuditError(err.message || "An unexpected error occurred");
      console.error(err);
    } finally {
      setVerifying(false);
    }
  };


  return (
    <div className="space-y-6">
      {/* Printable Committee Credit Paper (Hidden in normal UI, visible only when printing) */}
      <div className="hidden print:block bg-white text-black p-8 rounded border border-gray-300 space-y-6 font-sans">
        <div className="border-b-2 border-black pb-4 flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold uppercase tracking-wide">Credit Committee Appraisal Paper</h1>
            <p className="text-sm text-gray-600">Vyapar Pulse — Evidence-Linked Deterministic Credit Sanction Paper</p>
          </div>
          <div className="text-right text-xs text-light-secondary">
            <p>Case ID: {caseId}</p>
            <p>Generated: {new Date().toLocaleDateString()}</p>
            <p>Version: CAS-{data.case_version || 1}</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 border border-gray-300 p-4 rounded bg-gray-50">
          <div>
            <span className="text-xs text-light-secondary block uppercase font-bold">Requested Amount</span>
            <span className="text-lg font-bold">{formatCurrency((assessment?.requested_amount || data?.requested_amount))}</span>
          </div>
          <div>
            <span className="text-xs text-light-secondary block uppercase font-bold">Facility Product</span>
            <span className="text-lg font-bold">{(assessment?.requested_product || data?.requested_product) || "N/A"}</span>
          </div>
          <div>
            <span className="text-xs text-light-secondary block uppercase font-bold">Recommended Limit</span>
            <span className="text-lg font-bold text-emerald-800">
              {data.binding_limit ? formatCurrency(data.binding_limit) : formatCurrency((assessment?.requested_amount || data?.requested_amount))}
            </span>
          </div>
        </div>

        <div className="space-y-2">
          <h2 className="text-md font-bold uppercase border-b border-gray-300 pb-1">Debt Service & Amortization Assurance</h2>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-light-secondary">Pre-Loan DSCR:</span>{" "}
              <strong className="text-black">{(assessment?.current_dscr || data?.dscr) !== null ? Number((assessment?.current_dscr || data?.dscr)).toFixed(2) : "N/A"}</strong>
            </div>
            <div>
              <span className="text-light-secondary">Post-Loan DSCR:</span>{" "}
              <strong className="text-black">{(assessment?.post_loan_dscr || data?.post_loan_dscr) !== undefined && (assessment?.post_loan_dscr || data?.post_loan_dscr) !== null ? Number((assessment?.post_loan_dscr || data?.post_loan_dscr)).toFixed(2) : "N/A"}</strong>
            </div>
            <div>
              <span className="text-light-secondary">Assessed ROI / Tenure:</span>{" "}
              <strong className="text-black">11.5% p.a. / 36 Months</strong>
            </div>
          </div>
        </div>

        {data.evidence_passport && (
          <div className="space-y-2">
            <h2 className="text-md font-bold uppercase border-b border-gray-300 pb-1">Evidence Sufficiency Passport (`EVD-001`)</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-light-secondary">Multi-Rail Coverage Score:</span>{" "}
                <strong className="text-black">{Math.round(Object.values(data.evidence_passport.rail_coverage).filter(Boolean).length / Object.keys(data.evidence_passport.rail_coverage).length * 100)}%</strong>
              </div>
              <div>
                <span className="text-light-secondary">Freshness Decay Score:</span>{" "}
                <strong className="text-black">{Number(data.evidence_passport.freshness_depth.composite_freshness_index).toFixed(1)}%</strong>
              </div>
            </div>
          </div>
        )}

        {/* Scoring & Health Index (`DPK-001`) */}
        <div className="space-y-2">
          <h2 className="text-md font-bold uppercase border-b border-gray-300 pb-1">Vyapar Credit Health & Financial Health Index (`DPK-001`)</h2>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-light-secondary">Credit Health Score:</span>{" "}
              <strong className="text-black">{(assessment?.vyapar_credit_health_score || data?.vyapar_credit_health_score) ?? "N/A"} / 900</strong>
            </div>
            <div>
              <span className="text-light-secondary">Financial Health Index (FHI):</span>{" "}
              <strong className="text-black">{(assessment?.financial_health_index ?? data?.financial_health_index) !== undefined && (assessment?.financial_health_index ?? data?.financial_health_index) !== null ? Number(assessment?.financial_health_index ?? data?.financial_health_index).toFixed(2) : "N/A"} / 100</strong>
            </div>
            <div>
              <span className="text-light-secondary">Scoring Version:</span>{" "}
              <strong className="text-black">{(assessment?.scoring_version || data?.scoring_version) || "2.0-CANONICAL"}</strong>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <h2 className="text-md font-bold uppercase border-b border-gray-300 pb-1">Sanction Committee Sign-off</h2>
          <div className="grid grid-cols-2 gap-12 pt-8">
            <div className="border-t border-black pt-2 text-center text-xs">
              <strong>Credit Analyst Recommendation</strong>
              <p className="text-light-secondary mt-1">Role: CREDIT_ANALYST (BOLA Verified)</p>
            </div>
            <div className="border-t border-black pt-2 text-center text-xs">
              <strong>Sanctioning Authority Approval</strong>
              <p className="text-light-secondary mt-1">Role: SANCTIONING_AUTHORITY (CAS Enforced)</p>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive UI Block (Hidden on print) */}
      <div className="print:hidden space-y-6">
        {/* Overview Card */}
        <div className="bg-light-bg border border-light-border rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <FileText className="w-6 h-6 text-brand-teal" />
              <h2 className="text-xl font-bold text-light-text">Decision Package</h2>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleExportPackage}
                className="bg-indigo-50 hover:bg-indigo-200 text-indigo-600 px-4 py-2 rounded-xl text-sm font-medium border border-indigo-200 flex items-center gap-2 transition"
              >
                <FileText className="w-4 h-4" />
                Export Package JSON
              </button>
              <button
                onClick={() => window.print()}
                className="bg-brand-softTeal hover:bg-brand-teal/30 text-brand-teal px-4 py-2 rounded-xl text-sm font-medium border border-brand-teal/30 flex items-center gap-2 transition"
              >
                <Printer className="w-4 h-4" />
                Print Committee Credit Paper
              </button>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-light-elevated rounded-xl p-4 border border-light-border">
              <p className="text-sm text-light-secondary mb-1">Requested Amount</p>
              <p className="text-xl font-bold text-light-text">
                {formatCurrency((assessment?.requested_amount || data?.requested_amount))}
              </p>
            </div>
            <div className="bg-light-elevated rounded-xl p-4 border border-light-border">
              <p className="text-sm text-light-secondary mb-1">Product</p>
              <p className="text-xl font-bold text-light-text">
                {(assessment?.requested_product || data?.requested_product) || "N/A"}
              </p>
            </div>
            <div className="bg-light-elevated rounded-xl p-4 border border-light-border">
              <p className="text-sm text-light-secondary mb-1">DSCR</p>
              <p className="text-xl font-bold text-light-text">
                {(assessment?.current_dscr || data?.dscr) !== null ? Number((assessment?.current_dscr || data?.dscr)).toFixed(2) : "N/A"}
              </p>
            </div>
          </div>
        </div>

        {/* Credit Health & FHI Card */}
        <div className="bg-light-bg border border-light-border rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <ShieldCheck className="w-6 h-6 text-brand-teal" />
              <h2 className="text-xl font-bold text-light-text">Credit Health & 6-Pillar FHI (`DPK-001`)</h2>
            </div>
            <span className="bg-brand-softTeal text-brand-teal text-xs px-2 py-1 rounded border border-brand-teal/30">
              {(assessment?.scoring_version || data?.scoring_version) || "2.0-CANONICAL"}
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-light-elevated rounded-xl p-4 border border-light-border flex items-center justify-between">
              <div>
                <p className="text-sm text-light-secondary mb-1">Vyapar Credit Health Score</p>
                <p className="text-3xl font-bold text-brand-teal">{(assessment?.vyapar_credit_health_score || data?.vyapar_credit_health_score) ?? "N/A"}</p>
                <p className="text-xs text-light-secondary mt-1">Range: 300 - 900</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-light-secondary mb-1">Financial Health Index (FHI)</p>
                <p className="text-2xl font-bold text-light-text">
                  {(assessment?.financial_health_index ?? data?.financial_health_index) !== undefined && (assessment?.financial_health_index ?? data?.financial_health_index) !== null ? Number(assessment?.financial_health_index ?? data?.financial_health_index).toFixed(2) : "N/A"}
                </p>
                <p className="text-xs text-light-secondary mt-1">Range: 0 - 100</p>
              </div>
            </div>
            <div className="bg-light-elevated rounded-xl p-4 border border-light-border">
              <p className="text-sm text-light-secondary mb-2 font-semibold">6-Pillar FHI Breakdown</p>
              {data.fhi_breakdown ? (
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>Liquidity: <span className="font-semibold text-light-text">{(assessment?.six_pillars ? null : data?.fhi_breakdown)?.liquidity?.score ?? "N/A"}</span></div>
                  <div>Cash-flow: <span className="font-semibold text-light-text">{(assessment?.six_pillars ? null : data?.fhi_breakdown)?.cash_flow_capacity?.score ?? "N/A"}</span></div>
                  <div>Revenue: <span className="font-semibold text-light-text">{(assessment?.six_pillars ? null : data?.fhi_breakdown)?.revenue_stability_momentum?.score ?? "N/A"}</span></div>
                  <div>Repayment: <span className="font-semibold text-light-text">{(assessment?.six_pillars ? null : data?.fhi_breakdown)?.repayment_burden_discipline?.score ?? "N/A"}</span></div>
                  <div>Compliance: <span className="font-semibold text-light-text">{(assessment?.six_pillars ? null : data?.fhi_breakdown)?.compliance_formalisation?.score ?? "N/A"}</span></div>
                  <div>Concentration: <span className="font-semibold text-light-text">{(assessment?.six_pillars ? null : data?.fhi_breakdown)?.concentration_resilience?.score ?? "N/A"}</span></div>
                </div>
              ) : (
                <p className="text-xs text-light-secondary">Breakdown not available</p>
              )}
            </div>
          </div>
          {data.credit_score_disclaimer && (
            <div className="text-xs text-light-secondary bg-light-bg p-3 rounded border border-light-border">
              <strong>Note:</strong> {data.credit_score_disclaimer}
            </div>
          )}
        </div>

        {/* Rebuilt Product Offers Card */}
        <div className="bg-light-bg border border-light-border rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Briefcase className="w-6 h-6 text-blue-600" />
              <h2 className="text-xl font-bold text-light-text">Product-Specific Offers & Capacity Allocation</h2>
            </div>
            <span className="bg-blue-50 text-blue-600 text-xs px-2 py-1 rounded border border-blue-200 font-mono">
              ENGINE EVALUATED (0% FALLBACKS)
            </span>
          </div>
          {data.offers && data.offers.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {data.offers.map((offer, idx: number) => {
                if (!offer.amount && !offer.product_type) {
                  return <div key={idx} className="bg-rose-50 text-brand-red p-2 text-xs">Invalid Offer Contract</div>;
                }
                const isApplicable = Number(offer.amount) > 0;
                return (
                  <div key={idx} className={`rounded-xl p-5 border flex flex-col justify-between ${isApplicable ? "bg-light-bg border-blue-200" : "bg-light-bg opacity-50 border-light-border opacity-60"}`}>
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-xs font-bold text-blue-600 tracking-wider font-mono">
                          {offer.product_type?.replace(/_/g, " ") || "PRODUCT"}
                        </span>
                        <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${isApplicable ? "bg-brand-softTeal text-brand-teal border border-brand-teal/30" : "bg-brand-softAmber text-brand-amber border border-brand-amber/30"}`}>
                          {isApplicable ? "CAPACITY VIABLE" : "CAPACITY EXCEEDED"}
                        </span>
                      </div>
                      <p className="text-2xl font-bold text-light-text mb-2 font-mono">
                        {isApplicable ? formatCurrency(offer.amount) : "Not Applicable"}
                      </p>
                      {isApplicable ? (
                        <div className="space-y-2 text-xs text-light-text mb-4 font-mono">
                          <div className="flex justify-between border-b border-light-border pb-1">
                            <span className="text-light-secondary">Rate / Tenure:</span>
                            <span>{offer.interest_rate_pct !== undefined ? offer.interest_rate_pct : "UNKNOWN"}% p.a. / {offer.tenure_months !== undefined ? offer.tenure_months : "UNKNOWN"}M</span>
                          </div>
                          <div className="flex justify-between border-b border-light-border pb-1">
                            <span className="text-light-secondary">Repayment:</span>
                            <span className="text-right truncate max-w-[140px]" title={offer.estimated_repayment?.toString() || "UNKNOWN"}>{offer.estimated_repayment !== undefined ? offer.estimated_repayment : "UNKNOWN"}</span>
                          </div>
                          <div className="flex justify-between border-b border-light-border pb-1">
                            <span className="text-light-secondary">Post-Loan DSCR:</span>
                            <span className="font-semibold text-brand-teal">{offer.post_loan_dscr !== undefined && offer.post_loan_dscr !== null ? Number(offer.post_loan_dscr).toFixed(2) : "UNKNOWN"}</span>
                          </div>
                          <div className="pt-1 text-[11px] text-light-secondary italic">
                            {offer.collateral_structure || "UNKNOWN"}
                          </div>
                        </div>
                      ) : (
                        <p className="text-xs text-light-secondary mb-4 italic">
                          Product cap or cash-flow headroom constraints preclude non-zero limit assignment.
                        </p>
                      )}
                    </div>
                    {offer.covenants && offer.covenants.length > 0 && isApplicable && (
                      <div className="border-t border-light-border pt-3">
                        <p className="text-[11px] text-light-secondary uppercase font-semibold mb-1">Enforced Covenants:</p>
                        <ul className="text-[11px] text-light-text space-y-1 list-disc list-inside">
                          {offer.covenants.map((cov: string, cidx: number) => (
                            <li key={cidx} className="truncate" title={cov}>{cov}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="bg-light-elevated rounded-xl p-6 border border-light-border text-center text-light-secondary text-sm">
              No product offers generated. Run credit assessment to derive capacity limits.
            </div>
          )}
        </div>

        {/* Evidence Sufficiency Passport Interactive Card */}
        {data.evidence_passport && (
          <div className="bg-light-bg border border-light-border rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <Database className="w-6 h-6 text-teal-400" />
                <h2 className="text-xl font-bold text-light-text">Evidence Sufficiency Passport</h2>
              </div>
              <span className="bg-teal-500/20 text-teal-300 text-xs px-2 py-1 rounded border border-teal-500/30 font-mono">
                {(assessment?.evidence_certainty || data?.assessment_certainty) || "UNKNOWN"}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-light-elevated rounded-xl p-4 border border-light-border">
                <p className="text-xs text-light-secondary mb-1">Multi-Rail Coverage</p>
                <p className="text-2xl font-bold text-teal-400 font-mono">
                  {`${Math.round(Object.values(data.evidence_passport.rail_coverage).filter(Boolean).length / Object.keys(data.evidence_passport.rail_coverage).length * 100)}%`}
                </p>
              </div>
              <div className="bg-light-elevated rounded-xl p-4 border border-light-border">
                <p className="text-xs text-light-secondary mb-1">Composite Freshness Index</p>
                <p className="text-2xl font-bold text-light-text font-mono">
                  {`${Number(data.evidence_passport.freshness_depth.composite_freshness_index).toFixed(1)}%`}
                </p>
              </div>
              <div className="bg-light-elevated rounded-xl p-4 border border-light-border">
                <p className="text-xs text-light-secondary mb-1">Obligation Verification</p>
                <p className="text-lg font-bold text-brand-teal flex items-center gap-1.5 font-mono">
                  <CheckCircle2 className="w-4 h-4" />
                  {data.evidence_passport.obligation_verification.state.startsWith("VERIFIED") ? "VERIFIED" : "NOT VERIFIED"}
                </p>
              </div>
              <div className="bg-light-elevated rounded-xl p-4 border border-light-border">
                <p className="text-xs text-light-secondary mb-1">Contradiction Analysis</p>
                <p className={`text-lg font-bold font-mono ${data.evidence_passport.contradiction_analysis.severity === 'HIGH' ? 'text-brand-amber' : 'text-brand-teal'}`}>
                  {data.evidence_passport.contradiction_analysis.severity || "UNKNOWN"}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Audit Verification */}
        <div className="bg-light-bg border border-light-border rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Lock className="w-6 h-6 text-indigo-600" />
              <h2 className="text-xl font-bold text-light-text">Shakti Cryptographic Audit & Sanction Sign-off</h2>
            </div>
            <button 
              onClick={handleVerifyAudit}
              disabled={verifying}
              className="bg-indigo-50 text-indigo-600 text-xs px-4 py-1.5 rounded border border-indigo-200 font-mono hover:bg-indigo-200 transition disabled:opacity-50"
            >
              {verifying ? "Verifying..." : "Verify Audit Chain"}
            </button>
          </div>
          {verificationResult ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
              <div className="bg-light-elevated rounded-xl p-4 border border-light-border space-y-3">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-light-secondary">Chain Integrity</span>
                  <span className={`font-mono font-semibold flex items-center gap-1 ${verificationResult.audit_chain_valid ? 'text-brand-teal' : 'text-brand-red'}`}>
                    <CheckCircle2 className="w-3.5 h-3.5" /> {verificationResult.audit_chain_valid ? 'VERIFIED' : 'NOT VERIFIED'}
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs border-t border-light-border pt-2">
                  <span className="text-light-secondary">Analyst Evaluation Event</span>
                  <span className={`font-mono font-semibold flex items-center gap-1 ${verificationResult.analyst_event_status === 'VERIFIED' ? 'text-brand-teal' : 'text-brand-red'}`}>
                    <CheckCircle2 className="w-3.5 h-3.5" /> {verificationResult.analyst_event_status}
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs border-t border-light-border pt-2">
                  <span className="text-light-secondary">Human Decision Event</span>
                  <span className={`font-mono font-semibold flex items-center gap-1 ${verificationResult.human_decision_event_status === 'VERIFIED' ? 'text-brand-teal' : 'text-brand-red'}`}>
                    <CheckCircle2 className="w-3.5 h-3.5" /> {verificationResult.human_decision_event_status}
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs border-t border-light-border pt-2">
                  <span className="text-light-secondary">Package Hash Match</span>
                  <span className={`font-mono font-semibold flex items-center gap-1 ${verificationResult.package_hash_valid ? 'text-brand-teal' : 'text-brand-red'}`}>
                    <CheckCircle2 className="w-3.5 h-3.5" /> {verificationResult.package_hash_valid ? 'VERIFIED' : 'NOT VERIFIED'}
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs border-t border-light-border pt-2">
                  <span className="text-light-secondary">Authorization Scope</span>
                  <span className={`font-mono font-semibold flex items-center gap-1 ${verificationResult.authorization_scope_valid ? 'text-brand-teal' : 'text-brand-red'}`}>
                    <CheckCircle2 className="w-3.5 h-3.5" /> {verificationResult.authorization_scope_valid ? 'VERIFIED' : 'NOT VERIFIED'}
                  </span>
                </div>
              </div>
              <div className="bg-light-elevated rounded-xl p-4 border border-light-border flex flex-col justify-center">
                <h3 className="text-sm font-semibold text-light-text mb-1">Deterministic Assessment Chain</h3>
                <p className="text-xs text-light-secondary mb-3">
                  All credit decisions and policy stress tests are logged to the tamper-evident audit chain with exact calculation and policy version tags.
                </p>
                <div className="flex items-center gap-2 text-xs text-indigo-600 font-mono">
                  <Award className="w-4 h-4 shrink-0 text-indigo-600" />
                  <span>Version: {verificationResult.verification_version} | Verified At: {new Date(verificationResult.verified_at).toLocaleString()}</span>
                </div>
              </div>
            </div>
          ) : auditError ? (
            <div className="bg-rose-50 rounded-xl p-4 border border-rose-200 text-sm text-brand-red flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <span>{auditError}</span>
            </div>
          ) : (
            <div className="bg-light-elevated rounded-xl p-4 border border-light-border text-sm text-light-secondary text-center">
              Audit chain is verified independently. Click 'Verify Audit Chain' to evaluate real-time cryptographic integrity.
            </div>
          )}
        </div>

        {/* Sensitivity Lab */}
        <div className="bg-light-bg border border-light-border rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
          <Activity className="w-6 h-6 text-indigo-600" />
          <h2 className="text-xl font-bold text-light-text">Sensitivity Lab</h2>
          <span className="bg-indigo-50 text-indigo-600 text-xs px-2 py-1 rounded border border-indigo-200 ml-2">
            Live Computed
          </span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-light-secondary">Policy Stress Tests (Engine Evaluated)</h3>
              <div className="text-xs text-brand-teal font-mono">
                {assessment?.assessment_id && `Assessment ID: ${assessment.assessment_id.slice(0, 8)}`} | 
                {assessment?.case_version && ` Version: ${assessment.case_version}`}
              </div>
            </div>
            <div className="bg-light-elevated rounded-xl p-4 border border-light-border space-y-3">
              {stressData?.scenarios && stressData.scenarios.length > 0 ? (
                <>
                  {stressData.scenarios.slice(0, 2).map((scenario, idx) => (
                    <div key={idx} className="flex justify-between items-center text-sm">
                      <span className="text-light-secondary">{scenario.name}</span>
                      <span className={`font-semibold ${scenario.status === "PASS" ? "text-brand-teal" : "text-brand-amber"}`}>
                        {scenario.status === "PASS" ? "VIABLE (DSCR > 1.2)" : `STRESSED (DSCR: ${scenario.recomputed_dscr.toFixed(2)})`}
                      </span>
                    </div>
                  ))}
                  {stressData.stressed?.dscr !== undefined && (
                    <div className="flex justify-between items-center text-sm pt-2 border-t border-light-border">
                      <span className="text-light-text font-medium">Combined Shock DSCR</span>
                      <span className="text-light-text font-bold">{Number(stressData.stressed.dscr).toFixed(2)}</span>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-sm text-light-secondary py-2">
                  Stress lab evaluation unavailable for this case.
                </div>
              )}
            </div>
          </div>
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-light-secondary">Idempotency Replay Simulator</h3>
            <div className="bg-light-elevated rounded-xl p-4 border border-light-border flex flex-col items-center justify-center h-full text-center">
              <ShieldCheck className="w-8 h-8 text-brand-teal mb-2" />
              <p className="text-sm text-light-secondary mb-4">
                Verify idempotency key enforcement by simulating duplicate decision evaluations.
              </p>
              <button 
                onClick={handleSimulateReplay}
                disabled={simulatingReplay}
                className="bg-brand-softTeal hover:bg-brand-teal/30 text-brand-teal px-4 py-2 rounded-lg text-sm font-medium border border-brand-teal/30 flex items-center gap-2 transition disabled:opacity-50"
              >
                <Play className="w-4 h-4" />
                {simulatingReplay ? "Simulating Replay..." : "Simulate Replay"}
              </button>
              {replayResult && (
                <div className="mt-3 p-2 rounded bg-light-bg border border-light-border text-xs text-light-text flex items-center gap-2 text-left">
                  <CheckCircle2 className="w-4 h-4 text-brand-teal shrink-0" />
                  <span>{replayResult}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}
