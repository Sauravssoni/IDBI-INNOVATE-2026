"use client";

import React, { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { formatCurrency } from "@/lib/formatters";
import { ShieldCheck, TrendingUp, AlertCircle, FileText, CheckCircle2 } from "lucide-react";

export default function ApplicantViewPage() {
  const { caseId } = useParams();
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await apiFetch<any>(`/api/cases/${caseId}/applicant-view`);
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
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Vyapar Pulse Status</h1>
          <p className="text-slate-500">Status: {data.status}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <p className="text-sm text-slate-500 font-medium mb-1">Decision Context (English)</p>
            <p className="text-slate-800">{data.english_text}</p>
            <div className="mt-4">
              <p className="text-sm text-slate-500 font-medium mb-1">Decision Context (Hindi)</p>
              <p className="text-slate-800">{data.hindi_text}</p>
            </div>
          </div>
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <p className="text-sm text-slate-500 font-medium mb-1">Sanctioned Amount</p>
            <div className="text-3xl font-bold text-brand-teal font-mono mt-1">
              {data.sanctioned_amount_after_human_decision ? formatCurrency(Number(data.sanctioned_amount_after_human_decision)) : "Pending or Not Approved"}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <h2 className="text-lg font-bold text-slate-800 mb-4">Positive Factors</h2>
            <ul className="list-disc pl-5 space-y-2">
              {data.positive_factors?.map((f: string, i: number) => <li key={i}>{f}</li>)}
            </ul>
          </div>
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <h2 className="text-lg font-bold text-slate-800 mb-4">Safe Adverse Factors</h2>
            <ul className="list-disc pl-5 space-y-2">
              {data.safe_adverse_factors?.map((f: string, i: number) => <li key={i}>{f}</li>)}
            </ul>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <h2 className="text-lg font-bold text-slate-800 mb-4">Bankability Actions</h2>
            <ul className="list-disc pl-5 space-y-2">
              {data.bankability_actions?.map((f: string, i: number) => <li key={i}>{f}</li>)}
            </ul>
          </div>
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <h2 className="text-lg font-bold text-slate-800 mb-4">30/60/90 Day Milestones</h2>
            <ul className="list-disc pl-5 space-y-2">
              {data.milestones_30_60_90?.map((f: string, i: number) => <li key={i}>{f}</li>)}
            </ul>
          </div>
        </div>
        
        {data.missing_evidence?.length > 0 && (
          <div className="bg-red-50 p-6 rounded-2xl shadow-sm border border-red-200 mb-8">
            <h2 className="text-lg font-bold text-red-800 mb-4 flex items-center gap-2">
              <AlertCircle className="w-5 h-5" /> Missing Mandatory Evidence
            </h2>
            <ul className="list-disc pl-5 space-y-2 text-red-700">
              {data.missing_evidence.map((f: string, i: number) => <li key={i}>{f}</li>)}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
