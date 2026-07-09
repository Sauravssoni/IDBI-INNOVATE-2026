"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { Clock, CheckCircle2, User, PlayCircle, FileText, AlertCircle } from "lucide-react";
import { AssessmentHistoryItem } from "@/types";

export default function AssessmentHistoryTab({ caseId }: { caseId: string }) {
  const [history, setHistory] = useState<AssessmentHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchHistory() {
      setLoading(true);
      setError(null);
      const { data, status, error: fetchErr } = await apiFetch<AssessmentHistoryItem[]>(`/api/cases/${caseId}/assessment-history`);
      if (status === 200 && Array.isArray(data)) {
        setHistory(data);
      } else {
        setError(fetchErr || "Failed to load assessment history. Please try again later.");
      }
      setLoading(false);
    }
    fetchHistory();
  }, [caseId]);

  if (loading) {
    return <div className="text-center p-8 text-light-secondary font-mono text-sm flex items-center justify-center gap-2"><Clock className="w-4 h-4 animate-spin" /> Loading Assessment History...</div>;
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 text-brand-red rounded-xl border border-red-100 flex items-center justify-center gap-2 text-sm">
        <AlertCircle className="w-5 h-5" />
        {error}
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="p-4 bg-light-bg rounded-xl border border-dashed border-light-border text-center text-sm text-light-secondary">
        No assessment history found.
      </div>
    );
  }

  const renderEventIcon = (eventType: string) => {
    switch (eventType) {
      case "SYSTEM_EVALUATION":
        return <PlayCircle className="w-5 h-5 text-brand-teal" />;
      case "ANALYST_RECOMMENDATION":
        return <FileText className="w-5 h-5 text-brand-teal" />;
      case "HUMAN_DECISION":
        return <CheckCircle2 className="w-5 h-5 text-emerald-600" />;
      default:
        return <Clock className="w-5 h-5 text-light-secondary" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="glass-card p-6 border border-light-border shadow-sm">
        <h3 className="text-lg font-bold text-light-text flex items-center gap-2 mb-6">
          <Clock className="w-5 h-5 text-brand-teal" />
          Assessment History
        </h3>
        
        <div className="space-y-6">
          {history.map((event, idx) => (
            <div key={idx} className="relative flex gap-4">
              {/* Timeline line */}
              {idx !== history.length - 1 && (
                <div className="absolute left-6 top-10 bottom-[-24px] w-0.5 bg-light-border" />
              )}
              
              <div className="w-12 h-12 rounded-full bg-light-bg border border-light-border flex items-center justify-center shrink-0 z-10">
                {renderEventIcon(event.event_type)}
              </div>
              
              <div className="flex-1 bg-light-elevated border border-light-border p-4 rounded-xl hover:bg-light-bg transition-colors shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                  <div className="text-sm font-bold text-light-text">
                    {event.event_type ? event.event_type.replace(/_/g, " ") : "UNKNOWN"}
                  </div>
                  <div className="text-xs font-mono text-light-secondary bg-light-bg border border-light-border px-2 py-1 rounded">
                    {event.created_at ? new Date(event.created_at).toLocaleString() : "-"}
                  </div>
                </div>
                
                <div className="text-xs text-light-text space-y-2">
                  <div className="flex items-center gap-2 text-[11px] font-mono">
                    <User className="w-3 h-3 text-light-secondary" />
                    <span>{event.actor}</span>
                    <span className="px-1.5 py-0.5 bg-light-bg border border-light-border rounded text-light-secondary">{event.actor_role}</span>
                  </div>
                  
                  {event.reason && (
                    <div className="p-2 bg-light-bg rounded-lg border border-light-border italic text-light-secondary">
                      "{event.reason}"
                    </div>
                  )}
                  
                  {event.recommendation && (
                    <div className="mt-2 text-[10px] font-mono text-light-muted overflow-x-auto">
                      <pre>
                        {JSON.stringify(
                          {
                            recommendation: event.recommendation,
                            binding_limit: event.binding_limit,
                            dscr: event.dscr,
                            policy_version: event.policy_version,
                            calculation_version: event.calculation_version,
                          },
                          null,
                          2
                        )}
                      </pre>
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
