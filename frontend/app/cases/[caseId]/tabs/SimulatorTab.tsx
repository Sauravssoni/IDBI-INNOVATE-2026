"use client";

import React, { useState } from "react";
import { apiFetch } from "@/lib/api";
import { SimulatorResponse } from "@/types";
import { Calculator, Play, AlertTriangle, CheckCircle2 } from "lucide-react";

export default function SimulatorTab({ caseId }: { caseId: string }) {
  const [productType, setProductType] = useState("WORKING_CAPITAL_LINE");
  const [amount, setAmount] = useState(1000000);
  const [tenure, setTenure] = useState(36);
  const [rate, setRate] = useState(10.5);
  const [simResult, setSimResult] = useState<SimulatorResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSimulate = async () => {
    setLoading(true);
    const res = await apiFetch<SimulatorResponse>(`/api/cases/${caseId}/simulate`, {
      method: "POST",
      body: JSON.stringify({
        product_type: productType,
        amount,
        tenure_months: tenure,
        interest_rate: rate
      })
    });
    if (res.status === 200 && res.data) {
      setSimResult(res.data);
    }
    setLoading(false);
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(val);
  };

  return (
    <div className="space-y-6">
      <div className="glass-card p-6 border border-light-border shadow-sm">
        <h3 className="text-lg font-bold text-light-text flex items-center gap-2 mb-6">
          <Calculator className="w-5 h-5 text-brand-teal" />
          Product Structure Simulator
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div>
            <label className="block text-xs font-bold text-light-secondary uppercase mb-1">Product Type</label>
            <select 
              value={productType}
              onChange={(e) => setProductType(e.target.value)}
              className="w-full bg-light-bg border border-light-border rounded-lg px-3 py-2 text-sm focus:ring-1 focus:ring-brand-teal"
            >
              <option value="WORKING_CAPITAL_LINE">Working Capital Line</option>
              <option value="TERM_LOAN">Term Loan</option>
              <option value="INVOICE_DISCOUNTING">Invoice Discounting</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-bold text-light-secondary uppercase mb-1">Amount (₹)</label>
            <input 
              type="number" 
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              className="w-full bg-light-bg border border-light-border rounded-lg px-3 py-2 text-sm focus:ring-1 focus:ring-brand-teal"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-light-secondary uppercase mb-1">Tenure (Months)</label>
            <input 
              type="number" 
              value={tenure}
              onChange={(e) => setTenure(Number(e.target.value))}
              className="w-full bg-light-bg border border-light-border rounded-lg px-3 py-2 text-sm focus:ring-1 focus:ring-brand-teal"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-light-secondary uppercase mb-1">Interest Rate (%)</label>
            <input 
              type="number" 
              step="0.1"
              value={rate}
              onChange={(e) => setRate(Number(e.target.value))}
              className="w-full bg-light-bg border border-light-border rounded-lg px-3 py-2 text-sm focus:ring-1 focus:ring-brand-teal"
            />
          </div>
        </div>
        
        <button 
          onClick={handleSimulate}
          disabled={loading}
          className="flex items-center gap-2 bg-brand-teal hover:bg-brand-teal/90 text-white px-4 py-2 rounded-lg text-sm font-bold transition-colors disabled:opacity-50"
        >
          <Play className="w-4 h-4" />
          {loading ? "Simulating..." : "Run Simulation"}
        </button>
      </div>

      {simResult && !simResult.error && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="glass-card p-6 border border-light-border shadow-sm">
            <h4 className="text-sm font-bold text-light-secondary uppercase mb-4">Simulation Results</h4>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-light-bg rounded-lg border border-light-border">
                <span className="text-light-text font-medium">Simulated EMI</span>
                <span className="text-brand-teal font-mono font-bold text-lg">{formatCurrency(simResult.simulated_emi)}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-light-bg rounded-lg border border-light-border">
                <span className="text-light-text font-medium">Simulated DSCR</span>
                <span className={`font-mono font-bold text-lg ${simResult.simulated_dscr >= 1.25 ? 'text-emerald-500' : 'text-brand-red'}`}>
                  {simResult.simulated_dscr.toFixed(2)}x
                </span>
              </div>
            </div>
          </div>
          
          <div className="glass-card p-6 border border-light-border shadow-sm">
            <h4 className="text-sm font-bold text-light-secondary uppercase mb-4">Policy Check</h4>
            {simResult.viable ? (
              <div className="flex items-center gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-700">
                <CheckCircle2 className="w-6 h-6 shrink-0" />
                <div>
                  <div className="font-bold">Structure Viable</div>
                  <div className="text-sm">Passes all primary policy constraints.</div>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-3 p-4 bg-rose-50 border border-rose-200 rounded-lg text-brand-red">
                <AlertTriangle className="w-6 h-6 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold mb-1">Policy Breaches Detected</div>
                  <ul className="text-sm list-disc pl-4 space-y-1">
                    {simResult.policy_breaches.map((b: string, i: number) => (
                      <li key={i}>{b}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      
      {simResult && simResult.error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg text-brand-red text-sm font-medium">
          {simResult.error}
        </div>
      )}
    </div>
  );
}
