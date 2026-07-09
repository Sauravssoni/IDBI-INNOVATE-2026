"use client";

import React from "react";
import { ShieldAlert, Cpu, CheckCircle2, Lock, Sliders, AlertTriangle, FileText, UserCheck, Calculator } from "lucide-react";

export default function PolicyEnginePage() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6">
      <div className="bg-white rounded-xl shadow-sm border border-light-border p-8 mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-softTeal border border-brand-teal text-xs text-brand-teal font-mono mb-4">
          <Cpu className="w-3.5 h-3.5" />
          <span>CAS v1.1.3 • DETERMINISTIC POLICY ENGINE</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-light-text tracking-tight flex items-center gap-3">
          <ShieldAlert className="w-8 h-8 text-brand-teal" />
          <span>Credit Policy & Risk Rules Engine</span>
        </h1>
        <p className="text-light-secondary text-sm mt-2">
          Configurable decision parameters and debt-service thresholds.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-light-border space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-light-secondary uppercase tracking-wider">Consent</span>
            <Lock className="w-4 h-4 text-brand-teal" />
          </div>
          <div className="text-xl font-bold text-light-text font-mono">Valid Required</div>
          <p className="text-xs text-light-secondary font-medium">
            No data processing without verifiable digital consent.
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-light-border space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-light-secondary uppercase tracking-wider">Evidence Confidence</span>
            <FileText className="w-4 h-4 text-brand-teal" />
          </div>
          <div className="text-xl font-bold text-light-text font-mono">&ge; 40</div>
          <p className="text-xs text-light-secondary font-medium">
            Minimum confidence threshold for acceptable digital evidence.
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-light-border space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-light-secondary uppercase tracking-wider">DSCR Thresholds</span>
            <Sliders className="w-4 h-4 text-brand-teal" />
          </div>
          <div className="text-xl font-bold text-light-text font-mono">&ge; 1.15x</div>
          <p className="text-xs text-light-secondary font-medium">
            Minimum Debt Service Coverage Ratio required for deterministic recommendation.
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-light-border space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-light-secondary uppercase tracking-wider">Integrity Flag</span>
            <AlertTriangle className="w-4 h-4 text-brand-amber" />
          </div>
          <div className="text-xl font-bold text-light-text font-mono">Enhanced DD</div>
          <p className="text-xs text-light-secondary font-medium">
            Failed integrity checks immediately mandate Enhanced Due Diligence (EDD).
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-light-border space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-light-secondary uppercase tracking-wider">Amount Check</span>
            <Calculator className="w-4 h-4 text-brand-teal" />
          </div>
          <div className="text-xl font-bold text-light-text font-mono">Req &le; Supportable</div>
          <p className="text-xs text-light-secondary font-medium">
            Requested amount must not exceed the calculated supportable amount for unconditional approval.
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-light-border space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-light-secondary uppercase tracking-wider">Sanction</span>
            <UserCheck className="w-4 h-4 text-brand-teal" />
          </div>
          <div className="text-xl font-bold text-light-text font-mono">Human Required</div>
          <p className="text-xs text-light-secondary font-medium">
            A human Sanctioning Authority must explicitly review and approve all sanctions.
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-light-border space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-light-secondary uppercase tracking-wider">Policy Version</span>
            <Cpu className="w-4 h-4 text-brand-teal" />
          </div>
          <div className="text-xl font-bold text-light-text font-mono">1.1</div>
          <p className="text-xs text-light-secondary font-medium">
            Strict versioning of evaluation policy matrix.
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-light-border space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-light-secondary uppercase tracking-wider">Calc Version</span>
            <Calculator className="w-4 h-4 text-brand-teal" />
          </div>
          <div className="text-xl font-bold text-light-text font-mono">2.0</div>
          <p className="text-xs text-light-secondary font-medium">
            Strict versioning of financial twin calculation engine.
          </p>
        </div>
      </div>

      <div className="bg-brand-nav p-8 rounded-xl border border-light-border text-center space-y-3 mt-8">
        <CheckCircle2 className="w-12 h-12 text-brand-teal mx-auto" />
        <h3 className="text-lg font-bold text-white">Built for IDBI Innovate 2026 Policy Matrix Active</h3>
        <p className="text-xs text-light-secondary max-w-md mx-auto">
          Illustrative prototype policy thresholds for AI-assisted credit assessment. Hackathon prototype—not an official IDBI Bank production system.
        </p>
      </div>
    </div>
  );
}
