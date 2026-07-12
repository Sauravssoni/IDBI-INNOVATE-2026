"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { BarChart3, TrendingUp, AlertTriangle, ShieldCheck, Activity } from "lucide-react";

export default function PortfolioAssuranceLab() {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchMetrics() {
      const res = await apiFetch<any>("/api/portfolio/metrics");
      if (res.status === 200) {
        setMetrics(res.data);
      }
      setLoading(false);
    }
    fetchMetrics();
  }, []);

  if (loading) {
    return <div className="p-8">Loading Portfolio Assurance Lab...</div>;
  }

  if (!metrics) {
    return <div className="p-8">Failed to load metrics.</div>;
  }

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(val);
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-light-text flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-brand-teal" />
            Portfolio Assurance Lab
          </h1>
          <p className="text-light-secondary mt-2">Synthetic Risk Modeling & Stress Testing</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-card p-6 border border-light-border shadow-sm">
          <div className="text-sm text-light-secondary mb-2 flex items-center gap-2">
            <Activity className="w-4 h-4" /> Total Exposure
          </div>
          <div className="text-2xl font-mono text-brand-teal">{formatCurrency(metrics.overview.total_exposure)}</div>
        </div>
        <div className="glass-card p-6 border border-light-border shadow-sm">
          <div className="text-sm text-light-secondary mb-2 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" /> Weighted PD
          </div>
          <div className="text-2xl font-mono text-brand-red">{metrics.overview.weighted_average_pd}%</div>
        </div>
        <div className="glass-card p-6 border border-light-border shadow-sm">
          <div className="text-sm text-light-secondary mb-2 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4" /> Weighted LGD
          </div>
          <div className="text-2xl font-mono text-light-text">{metrics.overview.weighted_average_lgd}%</div>
        </div>
        <div className="glass-card p-6 border border-light-border shadow-sm">
          <div className="text-sm text-light-secondary mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" /> Value at Risk (99%)
          </div>
          <div className="text-2xl font-mono text-amber-500">{formatCurrency(metrics.overview.var_99)}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-6 border border-light-border shadow-sm">
          <h3 className="text-lg font-bold text-light-text mb-4">Sectoral Composition & Risk</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs font-mono text-light-secondary bg-light-bg">
                <tr>
                  <th className="px-4 py-3 rounded-l-xl">Sector</th>
                  <th className="px-4 py-3">Exposure</th>
                  <th className="px-4 py-3">Avg PD</th>
                  <th className="px-4 py-3 rounded-r-xl">Avg LGD</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-light-border">
                {metrics.composition.map((c: any, i: number) => (
                  <tr key={i} className="hover:bg-light-elevated">
                    <td className="px-4 py-3 font-mono text-light-text">{c.segment}</td>
                    <td className="px-4 py-3 text-brand-teal font-mono">{formatCurrency(c.exposure)}</td>
                    <td className="px-4 py-3 text-brand-red font-mono">{c.pd}%</td>
                    <td className="px-4 py-3 text-light-secondary font-mono">{c.lgd}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="glass-card p-6 border border-light-border shadow-sm">
          <h3 className="text-lg font-bold text-light-text mb-4">ECL Scenarios</h3>
          <div className="space-y-4">
            {Object.entries(metrics.ecl_scenarios).map(([name, data]: [string, any]) => (
              <div key={name} className="flex justify-between items-center p-4 bg-light-bg rounded-xl border border-light-border">
                <div>
                  <div className="font-mono text-sm capitalize text-light-text">{name} Scenario</div>
                  <div className="text-xs text-light-secondary">Provision Ratio: {data.provision_ratio}%</div>
                </div>
                <div className="text-lg font-mono text-brand-teal">{formatCurrency(data.ecl)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="glass-card p-6 border border-light-border shadow-sm">
        <h3 className="text-lg font-bold text-light-text mb-4">Active Risk Alerts</h3>
        <div className="space-y-3">
          {metrics.alerts.map((a: any, i: number) => (
            <div key={i} className={`p-4 rounded-xl border ${a.severity === 'high' ? 'bg-rose-50 border-rose-200 text-brand-red' : 'bg-amber-50 border-amber-200 text-amber-700'}`}>
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-bold uppercase mb-1">{a.severity} Priority</div>
                  <div className="text-sm">{a.message}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
