"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { Clock, CheckCircle2, User, PlayCircle, FileText } from "lucide-react";

export default function AssessmentHistoryTab({ caseId }: { caseId: string }) {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchHistory() {
      setLoading(true);
      const { data, status } = await apiFetch(`/api/cases/${caseId}/assessment-history`);
      if (status === 200) {
        setHistory(data);
      }
      setLoading(false);
    }
    fetchHistory();
  }, [caseId]);

  if (loading) {
    return <div className="text-center p-8 text-slate-400 font-mono text-sm">Loading Assessment History...</div>;
  }

  if (history.length === 0) {
    return (
      <div className="p-4 bg-navy-800/50 rounded-xl border border-dashed border-white/10 text-center text-sm text-slate-400">
        No assessment history found.
      </div>
    );
  }

  const renderEventIcon = (eventType: string) => {
    switch (eventType) {
      case "SYSTEM_EVALUATION":
        return <PlayCircle className="w-5 h-5 text-pulse-400" />;
      case "ANALYST_RECOMMENDATION":
        return <FileText className="w-5 h-5 text-blue-400" />;
      case "HUMAN_DECISION":
        return <CheckCircle2 className="w-5 h-5 text-emerald-400" />;
      default:
        return <Clock className="w-5 h-5 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="glass-panel p-6 rounded-2xl border border-white/10 shadow-lg">
        <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-6">
          <Clock className="w-5 h-5 text-pulse-400" />
          Assessment History
        </h3>
        
        <div className="space-y-6">
          {history.map((event, idx) => (
            <div key={idx} className="relative flex gap-4">
              {/* Timeline line */}
              {idx !== history.length - 1 && (
                <div className="absolute left-6 top-10 bottom-[-24px] w-0.5 bg-white/10" />
              )}
              
              <div className="w-12 h-12 rounded-full bg-navy-800 border border-white/10 flex items-center justify-center shrink-0 z-10">
                {renderEventIcon(event.event_type)}
              </div>
              
              <div className="flex-1 bg-navy-800/60 border border-white/5 p-4 rounded-xl hover:bg-white/[0.02] transition-colors">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                  <div className="text-sm font-bold text-white">
                    {event.event_type.replace(/_/g, " ")}
                  </div>
                  <div className="text-xs font-mono text-slate-400 bg-navy-900 px-2 py-1 rounded">
                    {new Date(event.created_at).toLocaleString()}
                  </div>
                </div>
                
                <div className="text-xs text-slate-300 space-y-2">
                  <div className="flex items-center gap-2 text-[11px] font-mono">
                    <User className="w-3 h-3" />
                    <span>{event.actor}</span>
                    <span className="px-1.5 py-0.5 bg-white/5 rounded text-slate-400">{event.actor_role}</span>
                  </div>
                  
                  {event.reason && (
                    <div className="p-2 bg-navy-900/50 rounded-lg border border-white/5 italic">
                      "{event.reason}"
                    </div>
                  )}
                  
                  {event.metadata_json && Object.keys(event.metadata_json).length > 0 && (
                    <div className="mt-2 text-[10px] font-mono text-slate-500 overflow-x-auto">
                      <pre>{JSON.stringify(event.metadata_json, null, 2)}</pre>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
