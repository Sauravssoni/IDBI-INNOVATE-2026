"use client";

import React, { useState } from "react";
import { ShieldCheck, Play, CheckCircle2, AlertTriangle, RefreshCw } from "lucide-react";
import { apiFetch } from "@/lib/api";

export default function ValidationConsolePage() {
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<any>(null);

  const runValidations = async () => {
    setRunning(true);
    const res = await apiFetch("/api/demo/validations");
    if (res.status === 200 && res.data) {
      setResults(res.data);
    } else {
      console.error("Failed to run validations", res.error);
    }
    setRunning(false);
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Validation Console</h1>
        <p className="text-gray-400">
          Synthetic scenario and policy validation interface to assert role boundaries, missing-data degradation, and idempotency replay.
        </p>
      </div>

      <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <ShieldCheck className="w-6 h-6 text-brand-teal" />
            <h2 className="text-xl font-bold text-white">System Validations</h2>
          </div>
          <button
            onClick={runValidations}
            disabled={running}
            className="bg-brand-teal text-navy-900 px-4 py-2 rounded-lg text-sm font-bold hover:bg-brand-teal/90 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            {running ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {running ? "Executing..." : "Execute All Validations"}
          </button>
        </div>

        {results ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <ValidationCard title="Persona Separation" data={results.personaSeparation} />
            <ValidationCard title="Role-Boundary Matrix" data={results.roleBoundaryMatrix} />
            <ValidationCard title="Idempotency Replay" data={results.idempotencyReplay} />
          </div>
        ) : (
          <div className="h-48 flex items-center justify-center border-2 border-dashed border-white/10 rounded-xl">
            <p className="text-gray-500">Click "Execute All Validations" to run synthetic assertions.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function ValidationCard({ title, data }: { title: string; data: any }) {
  return (
    <div className="bg-black/20 rounded-xl p-4 border border-white/5">
      <h3 className="text-sm font-medium text-gray-400 mb-4">{title}</h3>
      <div className="flex items-end justify-between">
        <div>
          <p className="text-3xl font-bold text-white">
            {data.passed} <span className="text-lg text-gray-500 font-normal">/ {data.total}</span>
          </p>
          <p className="text-xs text-gray-500 mt-1">Executable Assertions</p>
        </div>
        <div className={`px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1 ${
          data.status === "PASS" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-red-500/20 text-red-400 border border-red-500/30"
        }`}>
          {data.status === "PASS" ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
          {data.status}
        </div>
      </div>
    </div>
  );
}
