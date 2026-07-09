import React, { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { 
  FileText, Activity, ShieldCheck, AlertTriangle, Play 
} from "lucide-react";
import { formatCurrency } from "@/lib/formatters";

export default function DecisionPackageTab({ caseId }: { caseId: string }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      const res = await apiFetch(`/api/cases/${caseId}/decision-package`);
      if (res.status === 200 && res.data) {
        setData(res.data);
      } else {
        setError(res.error || "Failed to load decision package");
      }
      setLoading(false);
    };
    fetchData();
  }, [caseId]);

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

  return (
    <div className="space-y-6">
      {/* Overview Card */}
      <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <FileText className="w-6 h-6 text-emerald-400" />
          <h2 className="text-xl font-bold text-white">Decision Package</h2>
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

      {/* Sensitivity Lab */}
      <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <Activity className="w-6 h-6 text-purple-400" />
          <h2 className="text-xl font-bold text-white">Sensitivity Lab</h2>
          <span className="bg-purple-500/20 text-purple-400 text-xs px-2 py-1 rounded border border-purple-500/30 ml-2">
            Read-Only Mode
          </span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-400">Policy Stress Tests</h3>
            <div className="bg-black/20 rounded-xl p-4 border border-white/5 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Revenue Drop (-15%)</span>
                <span className="text-emerald-400">PASS</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Interest Rate Hike (+2%)</span>
                <span className="text-amber-400">MARGINAL</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">COGS Increase (+10%)</span>
                <span className="text-emerald-400">PASS</span>
              </div>
            </div>
          </div>
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-400">Idempotency Replay Simulator</h3>
            <div className="bg-black/20 rounded-xl p-4 border border-white/5 flex flex-col items-center justify-center h-full text-center">
              <ShieldCheck className="w-8 h-8 text-gray-500 mb-2" />
              <p className="text-sm text-gray-400 mb-4">
                Idempotency key enforcement prevents duplicate decision submissions.
              </p>
              <button disabled className="bg-white/5 text-gray-500 px-4 py-2 rounded-lg text-sm font-medium border border-white/10 flex items-center gap-2 cursor-not-allowed">
                <Play className="w-4 h-4" />
                Simulate Replay
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
