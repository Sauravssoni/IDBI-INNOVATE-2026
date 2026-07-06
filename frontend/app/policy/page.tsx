"use client";

import React from "react";
import { ShieldAlert, Cpu, CheckCircle2, Lock, Sliders, AlertTriangle } from "lucide-react";

export default function PolicyEnginePage() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-navy-800 border border-white/10 text-xs text-pulse-400 font-mono mb-2">
          <Cpu className="w-3.5 h-3.5" />
          <span>CAS v1.1.3 • DETERMINISTIC POLICY ENGINE</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
          <ShieldAlert className="w-8 h-8 text-pulse-400" />
          <span>Credit Policy & Risk Rules Engine</span>
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Configurable decision parameters, debt-service thresholds, and automated fraud flags.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card p-6 rounded-2xl border border-white/10 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">DSCR Thresholds</span>
            <Sliders className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">&ge; 1.35x</div>
          <p className="text-xs text-slate-400">
            Minimum Debt Service Coverage Ratio required for deterministic evidence-linked recommendation and human-reviewed sanction decision.
          </p>
        </div>

        <div className="glass-card p-6 rounded-2xl border border-white/10 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Circular Trading Guard</span>
            <Lock className="w-4 h-4 text-pulse-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">Active (0 Tol)</div>
          <p className="text-xs text-slate-400">
            Real-time graph analysis across GST vendor/customer networks to block shell loops.
          </p>
        </div>

        <div className="glass-card p-6 rounded-2xl border border-white/10 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Gearing Cap</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">&le; 3.00x</div>
          <p className="text-xs text-slate-400">
            Maximum Total Debt / Equity ratio permitted without mandatory Sanction Authority escalation.
          </p>
        </div>
      </div>

      <div className="glass-panel p-8 rounded-2xl border border-white/10 text-center space-y-3">
        <CheckCircle2 className="w-12 h-12 text-pulse-400 mx-auto" />
        <h3 className="text-lg font-bold text-white">Built for IDBI Innovate 2026 Policy Matrix Active</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Illustrative prototype policy thresholds for AI-assisted credit assessment. Hackathon prototype—not an official IDBI Bank production system.
        </p>
      </div>
    </div>
  );
}
