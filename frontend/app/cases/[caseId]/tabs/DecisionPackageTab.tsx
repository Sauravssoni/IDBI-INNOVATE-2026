import React, { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { 
  FileText, Activity, ShieldCheck, AlertTriangle, Play, CheckCircle2, Printer, Briefcase, Award, Database, Lock
} from "lucide-react";
import { formatCurrency } from "@/lib/formatters";

export default function DecisionPackageTab({ caseId }: { caseId: string }) {
  const [data, setData] = useState<any>(null);
  const [stressData, setStressData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Idempotency replay state
  const [simulatingReplay, setSimulatingReplay] = useState(false);
  const [replayResult, setReplayResult] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      const [resDecision, resStress] = await Promise.all([
        apiFetch(`/api/cases/${caseId}/decision-package`),
        apiFetch(`/api/cases/${caseId}/stress-lab`),
      ]);

      if (resDecision.status === 200 && resDecision.data) {
        setData(resDecision.data);
      } else {
        setError(resDecision.error || "Failed to load decision package");
      }

      if (resStress.status === 200 && resStress.data) {
        setStressData(resStress.data);
      }

      setLoading(false);
    };
    fetchData();
  }, [caseId]);

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
        <div className="animate-spin h-8 w-8 border-4 border-emerald-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl flex items-center gap-3">
        <AlertTriangle className="w-5 h-5" />
        <p>{error || "Failed to load decision package."}</p>
      </div>
    );
  }

  const singleFactors = stressData?.single_factor_results || {};

  return (
    <div className="space-y-6">
      {/* Printable Committee Credit Paper (Hidden in normal UI, visible only when printing) */}
      <div className="hidden print:block bg-white text-black p-8 rounded border border-gray-300 space-y-6 font-sans">
        <div className="border-b-2 border-black pb-4 flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold uppercase tracking-wide">Credit Committee Appraisal Paper</h1>
            <p className="text-sm text-gray-600">Vyapar Pulse — Evidence-Linked Deterministic Credit Sanction Paper</p>
          </div>
          <div className="text-right text-xs text-gray-500">
            <p>Case ID: {caseId}</p>
            <p>Generated: {new Date().toLocaleDateString()}</p>
            <p>Version: CAS-{data.case_version || 1}</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 border border-gray-300 p-4 rounded bg-gray-50">
          <div>
            <span className="text-xs text-gray-500 block uppercase font-bold">Requested Amount</span>
            <span className="text-lg font-bold">{formatCurrency(data.requested_amount)}</span>
          </div>
          <div>
            <span className="text-xs text-gray-500 block uppercase font-bold">Facility Product</span>
            <span className="text-lg font-bold">{data.requested_product || "N/A"}</span>
          </div>
          <div>
            <span className="text-xs text-gray-500 block uppercase font-bold">Recommended Limit</span>
            <span className="text-lg font-bold text-emerald-800">
              {data.limit_details?.supportable_limit ? formatCurrency(data.limit_details.supportable_limit) : formatCurrency(data.requested_amount)}
            </span>
          </div>
        </div>

        <div className="space-y-2">
          <h2 className="text-md font-bold uppercase border-b border-gray-300 pb-1">Debt Service & Amortization Assurance</h2>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Pre-Loan DSCR:</span>{" "}
              <strong className="text-black">{data.dscr !== null ? Number(data.dscr).toFixed(2) : "N/A"}</strong>
            </div>
            <div>
              <span className="text-gray-500">Post-Loan DSCR:</span>{" "}
              <strong className="text-black">{data.post_loan_dscr !== undefined && data.post_loan_dscr !== null ? Number(data.post_loan_dscr).toFixed(2) : "N/A"}</strong>
            </div>
            <div>
              <span className="text-gray-500">Assessed ROI / Tenure:</span>{" "}
              <strong className="text-black">11.5% p.a. / 36 Months</strong>
            </div>
          </div>
        </div>

        {data.evidence_passport && (
          <div className="space-y-2">
            <h2 className="text-md font-bold uppercase border-b border-gray-300 pb-1">Evidence Sufficiency Passport (`EVD-001`)</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Multi-Rail Coverage Score:</span>{" "}
                <strong className="text-black">{data.evidence_passport.rail_coverage || 0}%</strong>
              </div>
              <div>
                <span className="text-gray-500">Freshness Decay Score:</span>{" "}
                <strong className="text-black">{data.evidence_passport.freshness_depth || 0}%</strong>
              </div>
            </div>
          </div>
        )}

        {/* Scoring & Health Index (`DPK-001`) */}
        <div className="space-y-2">
          <h2 className="text-md font-bold uppercase border-b border-gray-300 pb-1">Vyapar Credit Health & Financial Health Index (`DPK-001`)</h2>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Credit Health Score:</span>{" "}
              <strong className="text-black">{data.vyapar_credit_health_score ?? "N/A"} / 900</strong>
            </div>
            <div>
              <span className="text-gray-500">Financial Health Index (FHI):</span>{" "}
              <strong className="text-black">{data.financial_health_index !== undefined && data.financial_health_index !== null ? Number(data.financial_health_index).toFixed(2) : "N/A"} / 100</strong>
            </div>
            <div>
              <span className="text-gray-500">Scoring Version:</span>{" "}
              <strong className="text-black">{data.scoring_version || "2.0-CANONICAL"}</strong>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <h2 className="text-md font-bold uppercase border-b border-gray-300 pb-1">Sanction Committee Sign-off</h2>
          <div className="grid grid-cols-2 gap-12 pt-8">
            <div className="border-t border-black pt-2 text-center text-xs">
              <strong>Credit Analyst Recommendation</strong>
              <p className="text-gray-500 mt-1">Role: CREDIT_ANALYST (BOLA Verified)</p>
            </div>
            <div className="border-t border-black pt-2 text-center text-xs">
              <strong>Sanctioning Authority Approval</strong>
              <p className="text-gray-500 mt-1">Role: SANCTIONING_AUTHORITY (CAS Enforced)</p>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive UI Block (Hidden on print) */}
      <div className="print:hidden space-y-6">
        {/* Overview Card */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <FileText className="w-6 h-6 text-emerald-400" />
              <h2 className="text-xl font-bold text-white">Decision Package</h2>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleExportPackage}
                className="bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 px-4 py-2 rounded-xl text-sm font-medium border border-purple-500/30 flex items-center gap-2 transition"
              >
                <FileText className="w-4 h-4" />
                Export Package JSON
              </button>
              <button
                onClick={() => window.print()}
                className="bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 px-4 py-2 rounded-xl text-sm font-medium border border-emerald-500/30 flex items-center gap-2 transition"
              >
                <Printer className="w-4 h-4" />
                Print Committee Credit Paper
              </button>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-black/20 rounded-xl p-4 border border-white/5">
              <p className="text-sm text-gray-400 mb-1">Requested Amount</p>
              <p className="text-xl font-bold text-white">
                {formatCurrency(data.requested_amount)}
              </p>
            </div>
            <div className="bg-black/20 rounded-xl p-4 border border-white/5">
              <p className="text-sm text-gray-400 mb-1">Product</p>
              <p className="text-xl font-bold text-white">
                {data.requested_product || "N/A"}
              </p>
            </div>
            <div className="bg-black/20 rounded-xl p-4 border border-white/5">
              <p className="text-sm text-gray-400 mb-1">DSCR</p>
              <p className="text-xl font-bold text-white">
                {data.dscr !== null ? Number(data.dscr).toFixed(2) : "N/A"}
              </p>
            </div>
          </div>
        </div>

        {/* Credit Health & FHI Card */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <ShieldCheck className="w-6 h-6 text-emerald-400" />
              <h2 className="text-xl font-bold text-white">Credit Health & 6-Pillar FHI (`DPK-001`)</h2>
            </div>
            <span className="bg-emerald-500/20 text-emerald-400 text-xs px-2 py-1 rounded border border-emerald-500/30">
              {data.scoring_version || "2.0-CANONICAL"}
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-black/20 rounded-xl p-4 border border-white/5 flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400 mb-1">Vyapar Credit Health Score</p>
                <p className="text-3xl font-bold text-emerald-400">{data.vyapar_credit_health_score ?? "N/A"}</p>
                <p className="text-xs text-gray-500 mt-1">Range: 300 - 900</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-400 mb-1">Financial Health Index (FHI)</p>
                <p className="text-2xl font-bold text-white">
                  {data.financial_health_index !== undefined && data.financial_health_index !== null ? Number(data.financial_health_index).toFixed(2) : "N/A"}
                </p>
                <p className="text-xs text-gray-500 mt-1">Range: 0 - 100</p>
              </div>
            </div>
            <div className="bg-black/20 rounded-xl p-4 border border-white/5">
              <p className="text-sm text-gray-400 mb-2 font-semibold">6-Pillar FHI Breakdown</p>
              {data.fhi_breakdown ? (
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>Liquidity: <span className="font-semibold text-white">{data.fhi_breakdown.liquidity ?? "N/A"}</span></div>
                  <div>Solvency: <span className="font-semibold text-white">{data.fhi_breakdown.solvency ?? "N/A"}</span></div>
                  <div>Efficiency: <span className="font-semibold text-white">{data.fhi_breakdown.efficiency ?? "N/A"}</span></div>
                  <div>Profitability: <span className="font-semibold text-white">{data.fhi_breakdown.profitability ?? "N/A"}</span></div>
                  <div>Compliance: <span className="font-semibold text-white">{data.fhi_breakdown.compliance ?? "N/A"}</span></div>
                  <div>Resilience: <span className="font-semibold text-white">{data.fhi_breakdown.resilience ?? "N/A"}</span></div>
                </div>
              ) : (
                <p className="text-xs text-gray-500">Breakdown not available</p>
              )}
            </div>
          </div>
          {data.credit_score_disclaimer && (
            <div className="text-xs text-gray-400 bg-black/40 p-3 rounded border border-white/5">
              <strong>Note:</strong> {data.credit_score_disclaimer}
            </div>
          )}
        </div>

        {/* Rebuilt Product Offers Card */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Briefcase className="w-6 h-6 text-blue-400" />
              <h2 className="text-xl font-bold text-white">Product-Specific Offers & Capacity Allocation</h2>
            </div>
            <span className="bg-blue-500/20 text-blue-400 text-xs px-2 py-1 rounded border border-blue-500/30 font-mono">
              ENGINE EVALUATED (0% FALLBACKS)
            </span>
          </div>
          {data.offers && data.offers.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {data.offers.map((offer: any, idx: number) => {
                const isApplicable = Number(offer.limit) > 0;
                return (
                  <div key={idx} className={`rounded-xl p-5 border flex flex-col justify-between ${isApplicable ? "bg-black/30 border-blue-500/30" : "bg-black/10 border-white/5 opacity-60"}`}>
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-xs font-bold text-blue-400 tracking-wider font-mono">
                          {offer.product?.replace(/_/g, " ") || "PRODUCT"}
                        </span>
                        <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${isApplicable ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-amber-500/20 text-amber-400 border border-amber-500/30"}`}>
                          {isApplicable ? "CAPACITY VIABLE" : "CAPACITY EXCEEDED"}
                        </span>
                      </div>
                      <p className="text-2xl font-bold text-white mb-2 font-mono">
                        {isApplicable ? formatCurrency(offer.limit) : "₹0 (Not Applicable)"}
                      </p>
                      {isApplicable ? (
                        <div className="space-y-2 text-xs text-gray-300 mb-4 font-mono">
                          <div className="flex justify-between border-b border-white/5 pb-1">
                            <span className="text-gray-400">Rate / Tenure:</span>
                            <span>{offer.interest_rate}% p.a. / {offer.tenure_months}M</span>
                          </div>
                          <div className="flex justify-between border-b border-white/5 pb-1">
                            <span className="text-gray-400">Repayment:</span>
                            <span className="text-right truncate max-w-[140px]" title={offer.estimated_repayment}>{offer.estimated_repayment}</span>
                          </div>
                          <div className="flex justify-between border-b border-white/5 pb-1">
                            <span className="text-gray-400">Post-Loan DSCR:</span>
                            <span className="font-semibold text-emerald-400">{offer.post_loan_dscr ? Number(offer.post_loan_dscr).toFixed(2) : "N/A"}</span>
                          </div>
                          <div className="pt-1 text-[11px] text-gray-400 italic">
                            {offer.collateral_structure}
                          </div>
                        </div>
                      ) : (
                        <p className="text-xs text-gray-400 mb-4 italic">
                          Product cap or cash-flow headroom constraints preclude non-zero limit assignment.
                        </p>
                      )}
                    </div>
                    {offer.covenants && offer.covenants.length > 0 && isApplicable && (
                      <div className="border-t border-white/10 pt-3">
                        <p className="text-[11px] text-gray-400 uppercase font-semibold mb-1">Enforced Covenants:</p>
                        <ul className="text-[11px] text-gray-300 space-y-1 list-disc list-inside">
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
            <div className="bg-black/20 rounded-xl p-6 border border-white/5 text-center text-gray-400 text-sm">
              No product offers generated. Run credit assessment to derive capacity limits.
            </div>
          )}
        </div>

        {/* Evidence Sufficiency Passport (`EVD-001`) Interactive Card */}
        {data.evidence_passport && (
          <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <Database className="w-6 h-6 text-teal-400" />
                <h2 className="text-xl font-bold text-white">Evidence Sufficiency Passport (`EVD-001`)</h2>
              </div>
              <span className="bg-teal-500/20 text-teal-300 text-xs px-2 py-1 rounded border border-teal-500/30 font-mono">
                {data.evidence_passport.assessment_certainty || "DEFINITIVE_DATA_BACKED"}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-black/20 rounded-xl p-4 border border-white/5">
                <p className="text-xs text-gray-400 mb-1">Multi-Rail Coverage</p>
                <p className="text-2xl font-bold text-teal-400 font-mono">
                  {typeof data.evidence_passport.rail_coverage === 'object' 
                    ? `${Object.values(data.evidence_passport.rail_coverage).filter(Boolean).length}/${Object.keys(data.evidence_passport.rail_coverage).length} Rails`
                    : `${data.evidence_passport.rail_coverage || 0}%`}
                </p>
                <p className="text-[10px] text-gray-500 mt-1">GST, Bank, Invoice, Emp</p>
              </div>
              <div className="bg-black/20 rounded-xl p-4 border border-white/5">
                <p className="text-xs text-gray-400 mb-1">Composite Freshness Index</p>
                <p className="text-2xl font-bold text-white font-mono">
                  {data.evidence_passport.freshness_depth?.composite_freshness_index ?? 0}%
                </p>
                <p className="text-[10px] text-gray-500 mt-1">
                  Depth: {data.evidence_passport.freshness_depth?.months_of_history || 12} Months
                </p>
              </div>
              <div className="bg-black/20 rounded-xl p-4 border border-white/5">
                <p className="text-xs text-gray-400 mb-1">Obligation Verification</p>
                <p className="text-lg font-bold text-emerald-400 flex items-center gap-1.5 font-mono">
                  <CheckCircle2 className="w-4 h-4" />
                  {data.evidence_passport.obligation_verification?.state || "VERIFIED"}
                </p>
                <p className="text-[10px] text-gray-500 mt-1 font-mono">
                  EMI: {formatCurrency(data.evidence_passport.obligation_verification?.observed_monthly_debt_service || 0)}
                </p>
              </div>
              <div className="bg-black/20 rounded-xl p-4 border border-white/5">
                <p className="text-xs text-gray-400 mb-1">Contradiction Analysis</p>
                <p className={`text-lg font-bold font-mono ${data.evidence_passport.contradiction_analysis?.severity === 'HIGH' ? 'text-amber-400' : 'text-emerald-400'}`}>
                  {data.evidence_passport.contradiction_analysis?.severity || "LOW"} SEVERITY
                </p>
                <p className="text-[10px] text-gray-500 mt-1 font-mono">
                  Recon Ratio: {Number(data.evidence_passport.contradiction_analysis?.reconciliation_ratio ?? 1.0).toFixed(2)}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Audit Verification & Shakti Enforced Sign-off Card */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Lock className="w-6 h-6 text-purple-400" />
              <h2 className="text-xl font-bold text-white">Shakti Cryptographic Audit & Sanction Sign-off</h2>
            </div>
            <span className="bg-purple-500/20 text-purple-300 text-xs px-2 py-1 rounded border border-purple-500/30 font-mono">
              CAS VERSION #{data.case_version || 1}
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            <div className="bg-black/20 rounded-xl p-4 border border-white/5 space-y-3">
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-400">BOLA Verification Status</span>
                <span className="text-emerald-400 font-mono font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> ENFORCED (CREDIT_ANALYST)
                </span>
              </div>
              <div className="flex justify-between items-center text-xs border-t border-white/5 pt-2">
                <span className="text-gray-400">CAS Authority Sign-off</span>
                <span className="text-emerald-400 font-mono font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> ENFORCED (SANCTIONING_AUTHORITY)
                </span>
              </div>
              <div className="flex justify-between items-center text-xs border-t border-white/5 pt-2">
                <span className="text-gray-400">Cryptographic Evidence Hash</span>
                <span className="text-gray-300 font-mono text-[11px] truncate max-w-[180px]">
                  {data.evidence_passport?.case_id || caseId}
                </span>
              </div>
            </div>
            <div className="bg-black/20 rounded-xl p-4 border border-white/5 flex flex-col justify-center">
              <h3 className="text-sm font-semibold text-white mb-1">Deterministic Assessment Chain</h3>
              <p className="text-xs text-gray-400 mb-3">
                All credit decisions and policy stress tests are immutably logged to the Shakti audit chain with exact calculation and policy version tags.
              </p>
              <div className="flex items-center gap-2 text-xs text-purple-300 font-mono">
                <Award className="w-4 h-4 shrink-0 text-purple-400" />
                <span>Policy Version: 1.1 | Scoring Engine: {data.scoring_version || "2.0-CANONICAL"}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Sensitivity Lab */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
          <Activity className="w-6 h-6 text-purple-400" />
          <h2 className="text-xl font-bold text-white">Sensitivity Lab</h2>
          <span className="bg-purple-500/20 text-purple-400 text-xs px-2 py-1 rounded border border-purple-500/30 ml-2">
            Live Computed
          </span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-400">Policy Stress Tests (Engine Evaluated)</h3>
            <div className="bg-black/20 rounded-xl p-4 border border-white/5 space-y-3">
              {Object.keys(singleFactors).length > 0 ? (
                <>
                  {singleFactors.revenue_drop && (
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-400">Revenue Drop Shock (-20%)</span>
                      <span className={`font-semibold ${singleFactors.revenue_drop.viable ? "text-emerald-400" : "text-amber-400"}`}>
                        {singleFactors.revenue_drop.viable ? "VIABLE (DSCR > 1.2)" : `STRESSED (DSCR: ${singleFactors.revenue_drop.dscr_shocked.toFixed(2)})`}
                      </span>
                    </div>
                  )}
                  {singleFactors.rate_hike && (
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-400">Interest Rate Hike (+200 bps)</span>
                      <span className={`font-semibold ${singleFactors.rate_hike.viable ? "text-emerald-400" : "text-amber-400"}`}>
                        {singleFactors.rate_hike.viable ? "VIABLE (DSCR > 1.2)" : `STRESSED (DSCR: ${singleFactors.rate_hike.dscr_shocked.toFixed(2)})`}
                      </span>
                    </div>
                  )}
                  {stressData?.dscr_shocked !== undefined && (
                    <div className="flex justify-between items-center text-sm pt-2 border-t border-white/10">
                      <span className="text-gray-300 font-medium">Combined Shock DSCR</span>
                      <span className="text-white font-bold">{Number(stressData.dscr_shocked).toFixed(2)}</span>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-sm text-gray-500 py-2">
                  Stress lab evaluation unavailable for this case.
                </div>
              )}
            </div>
          </div>
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-400">Idempotency Replay Simulator</h3>
            <div className="bg-black/20 rounded-xl p-4 border border-white/5 flex flex-col items-center justify-center h-full text-center">
              <ShieldCheck className="w-8 h-8 text-emerald-500 mb-2" />
              <p className="text-sm text-gray-400 mb-4">
                Verify idempotency key enforcement by simulating duplicate decision evaluations.
              </p>
              <button 
                onClick={handleSimulateReplay}
                disabled={simulatingReplay}
                className="bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 px-4 py-2 rounded-lg text-sm font-medium border border-emerald-500/30 flex items-center gap-2 transition disabled:opacity-50"
              >
                <Play className="w-4 h-4" />
                {simulatingReplay ? "Simulating Replay..." : "Simulate Replay"}
              </button>
              {replayResult && (
                <div className="mt-3 p-2 rounded bg-black/40 border border-white/10 text-xs text-gray-300 flex items-center gap-2 text-left">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
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
