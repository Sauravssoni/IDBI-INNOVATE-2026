import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { AlertTriangle, TrendingDown, Activity, CheckCircle2 } from "lucide-react";

export default function MonitoringTab({ caseId }: { caseId: string }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      const res = await apiFetch(`/api/cases/${caseId}/monitoring`);
      if (res.status === 200 && res.data) {
        setData(res.data);
      }
      setLoading(false);
    }
    loadData();
  }, [caseId]);

  if (loading) {
    return <div className="p-8 text-center text-light-secondary">Loading Monitoring Signals...</div>;
  }

  if (!data) {
    return <div className="p-8 text-center text-brand-red">Failed to load monitoring data.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="glass-card p-6 border border-light-border shadow-sm flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-light-text mb-1">Early Warning & Monitoring Journey</h2>
          <p className="text-sm text-light-secondary">Continuous post-assessment tracking of vital financial indicators.</p>
        </div>
        <div className={`px-4 py-2 rounded-lg font-bold text-sm border ${
          data.overall_risk_state === 'ELEVATED_WATCHLIST' ? 'bg-rose-50 border-rose-200 text-brand-red' : 'bg-emerald-50 border-emerald-200 text-emerald-700'
        }`}>
          {data.overall_risk_state === 'ELEVATED_WATCHLIST' ? 'ELEVATED WATCHLIST' : 'STABLE RISK'}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {data.deterioration_alerts?.map((alert: any, idx: number) => (
          <div key={idx} className={`glass-card p-5 border shadow-sm ${
            alert.status === 'TRIGGERED' ? 'border-brand-red bg-rose-50' : 'border-light-border bg-white'
          }`}>
            <div className="flex justify-between items-start mb-3">
              <h3 className="font-bold text-light-text flex items-center gap-2">
                {alert.status === 'TRIGGERED' ? <AlertTriangle className="w-4 h-4 text-brand-red" /> : <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
                {alert.rule_name}
              </h3>
              <span className={`text-xs px-2 py-1 rounded-full font-bold ${
                alert.status === 'TRIGGERED' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-500'
              }`}>
                {alert.alert_code}
              </span>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between border-b border-light-border pb-1">
                <span className="text-light-secondary">Threshold:</span>
                <span className="text-light-text font-mono">{alert.threshold}</span>
              </div>
              <div className="flex justify-between border-b border-light-border pb-1">
                <span className="text-light-secondary">Observed:</span>
                <span className={`font-mono font-bold ${alert.status === 'TRIGGERED' ? 'text-brand-red' : 'text-emerald-600'}`}>
                  {alert.observed_metric}
                </span>
              </div>
              <p className="text-xs text-light-secondary mt-3 bg-light-bg p-2 rounded">{alert.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
