"use client";

import React, { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { formatCurrency } from "@/lib/formatters";
import { ShieldCheck, TrendingUp, AlertCircle, FileText, CheckCircle2 } from "lucide-react";
import type { DecisionPackageResponse } from "@/lib/types";

export default function ApplicantViewPage() {
  const { caseId } = useParams();
  const [data, setData] = useState<DecisionPackageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await apiFetch<DecisionPackageResponse>(`/api/cases/${caseId}/decision-package`);
        if (res.status === 200 && res.data) {
          setData(res.data);
        } else {
          setError(res.error || "Failed to load applicant details");
        }
      } catch (err: any) {
        setError(err.message || "Unknown error");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [caseId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] flex justify-center items-center">
        <div className="animate-spin h-8 w-8 border-4 border-brand-teal border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] flex justify-center items-center p-8">
        <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-xl flex items-center gap-3">
          <AlertCircle className="w-5 h-5" />
          <p>{error || "Failed to load details."}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Vyapar Pulse Dashboard</h1>
          <p className="text-slate-500">Welcome, {data.business_name}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <p className="text-sm text-slate-500 font-medium mb-1">Credit Health Score</p>
            <div className="flex items-end gap-2">
              <span className="text-4xl font-bold text-brand-teal font-mono">{data.vyapar_credit_health_score || "-"}</span>
              <span className="text-sm text-slate-400 mb-1">/ 900</span>
            </div>
            <p className="text-xs text-slate-400 mt-2">Based on your live digital footprint</p>
          </div>

          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <p className="text-sm text-slate-500 font-medium mb-1">Assessed Capacity</p>
            <div className="text-3xl font-bold text-slate-800 font-mono mt-1">
              {data.binding_limit ? formatCurrency(Number(data.binding_limit)) : "-"}
            </div>
            <p className="text-xs text-slate-400 mt-2">For {String(data.requested_product).replace(/_/g, ' ')}</p>
          </div>

          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <p className="text-sm text-slate-500 font-medium mb-1">Application Status</p>
            <div className="mt-2">
              <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold ${
                data.recommendation?.includes('APPROVE') ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
              }`}>
                {data.recommendation?.includes('APPROVE') ? <CheckCircle2 className="w-4 h-4" /> : <TrendingUp className="w-4 h-4" />}
                {data.recommendation?.replace(/_/g, ' ') || "In Progress"}
              </span>
            </div>
          </div>
        </div>

        {data.hindi_summary && (
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 mb-8">
            <div className="flex items-center gap-3 mb-4 border-b border-slate-100 pb-4">
              <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center">
                <ShieldCheck className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-800">Your Bankability Overview (आपकी स्थिति)</h2>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <p className="text-sm font-bold text-slate-700 mb-2">Decision Context</p>
                <p className="text-slate-600 text-sm">{data.hindi_summary.reason_explanation}</p>
                <p className="text-slate-500 text-xs mt-2 italic">Status: {data.hindi_summary.decision_label}</p>
              </div>
              
              {data.hindi_summary.bankability_path_actions && data.hindi_summary.bankability_path_actions.length > 0 && (
                <div>
                  <p className="text-sm font-bold text-slate-700 mb-2">Path to Better Limits</p>
                  <ul className="space-y-2">
                    {data.hindi_summary.bankability_path_actions.map((act: string, i: number) => (
                      <li key={i} className="text-sm text-slate-600 flex items-start gap-2">
                        <span className="text-brand-teal mt-0.5">•</span> {act}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
        
        {data.offers && data.offers.length > 0 && (
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5 text-brand-teal" /> Recommended Product Offers
            </h2>
            <div className="space-y-4">
              {data.offers.map((offer, idx) => (
                <div key={idx} className="p-4 rounded-xl border border-slate-100 bg-slate-50 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                  <div>
                    <h3 className="font-bold text-slate-800">{offer.product_type?.replace(/_/g, ' ')}</h3>
                    <p className="text-sm text-slate-500">ROI: {offer.interest_rate_pct}% p.a. • Tenure: {offer.tenure_months}M</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xl font-bold text-brand-teal font-mono">{formatCurrency(offer.amount)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
