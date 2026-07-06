"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  ShieldCheck,
  Lock,
  Mail,
  ArrowRight,
  UserCheck,
  Briefcase,
  TrendingUp,
  Settings,
  AlertCircle,
} from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const res = await login(email, password);
    if (res.success) {
      router.push("/");
    } else {
      setError(res.error || "Login failed. Please verify credentials.");
      setIsSubmitting(false);
    }
  };

  const selectDemoRole = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword("");
    setError(null);
  };

  const enableDemoShortcuts = process.env.NEXT_PUBLIC_ENABLE_DEMO_SHORTCUTS === "true";

  return (
    <div className="min-h-screen bg-navy-900 text-foreground flex flex-col justify-center items-center p-4 relative overflow-hidden">
      {/* Background ambient lighting */}
      <div className="absolute top-10 left-1/4 w-[500px] h-[500px] bg-pulse-500/10 rounded-full blur-3xl pointer-events-none animate-pulse" />
      <div className="absolute bottom-10 right-1/4 w-[450px] h-[450px] bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
      
      {/* Header Branding */}
      <div className="text-center mb-8 z-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-navy-800/80 border border-white/10 text-xs text-pulse-400 font-mono mb-3 shadow-lg">
          <ShieldCheck className="w-4 h-4 text-pulse-500" />
          <span>BUILT FOR IDBI INNOVATE 2026 • HACKATHON EDITION</span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white mb-2">
          Vyapar <span className="text-gradient">Pulse</span>
        </h1>
        <p className="text-slate-400 text-sm sm:text-base max-w-md mx-auto">
          AI-assisted credit assessment, BOLA Governance & Real-Time Decisioning Engine
        </p>
      </div>

      {/* Main Card */}
      <div className="glass-panel w-full max-w-lg p-8 rounded-2xl shadow-2xl border border-white/10 z-10">
        <h2 className="text-xl font-semibold text-white mb-6 flex items-center justify-between">
          <span>Sign in to Vyapar Pulse</span>
          <span className="text-xs font-mono text-slate-400 font-normal">CAS v1.1.3</span>
        </h2>

        {/* 1-Click Demo Role Selector */}
        {enableDemoShortcuts && (
          <div className="mb-6">
            <label className="block text-xs font-mono text-slate-400 uppercase tracking-wider mb-1">
              Quick Demo Login (Click to Fill Email)
            </label>
            <p className="text-[11px] text-amber-300/80 mb-2.5">
              Use the development credential provided in the evaluator guide.
            </p>
            <div className="grid grid-cols-2 gap-2.5">
              <button
                type="button"
                onClick={() => selectDemoRole("sa@bank.example")}
                className={`p-2.5 rounded-xl border text-left flex items-center gap-2.5 transition-all ${
                  email === "sa@bank.example"
                    ? "bg-amber-500/15 border-amber-500/50 text-amber-300 shadow-md shadow-amber-500/10"
                    : "bg-navy-800/50 border-white/5 text-slate-300 hover:border-white/20 hover:bg-navy-800"
                }`}
              >
                <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center text-amber-400 shrink-0">
                  <UserCheck className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-semibold truncate">Sanction Authority</div>
                  <div className="text-[10px] text-slate-400 font-mono">sa@bank.example</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => selectDemoRole("credit@bank.example")}
                className={`p-2.5 rounded-xl border text-left flex items-center gap-2.5 transition-all ${
                  email === "credit@bank.example"
                    ? "bg-blue-500/15 border-blue-500/50 text-blue-300 shadow-md shadow-blue-500/10"
                    : "bg-navy-800/50 border-white/5 text-slate-300 hover:border-white/20 hover:bg-navy-800"
                }`}
              >
                <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center text-blue-400 shrink-0">
                  <TrendingUp className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-semibold truncate">Credit Analyst</div>
                  <div className="text-[10px] text-slate-400 font-mono">credit@bank.example</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => selectDemoRole("rm@bank.example")}
                className={`p-2.5 rounded-xl border text-left flex items-center gap-2.5 transition-all ${
                  email === "rm@bank.example"
                    ? "bg-teal-500/15 border-teal-500/50 text-teal-300 shadow-md shadow-teal-500/10"
                    : "bg-navy-800/50 border-white/5 text-slate-300 hover:border-white/20 hover:bg-navy-800"
                }`}
              >
                <div className="w-8 h-8 rounded-lg bg-teal-500/20 flex items-center justify-center text-teal-400 shrink-0">
                  <Briefcase className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-semibold truncate">Relationship Mgr</div>
                  <div className="text-[10px] text-slate-400 font-mono">rm@bank.example</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => selectDemoRole("system@bank.example")}
                className={`p-2.5 rounded-xl border text-left flex items-center gap-2.5 transition-all ${
                  email === "system@bank.example"
                    ? "bg-purple-500/15 border-purple-500/50 text-purple-300 shadow-md shadow-purple-500/10"
                    : "bg-navy-800/50 border-white/5 text-slate-300 hover:border-white/20 hover:bg-navy-800"
                }`}
              >
                <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center text-purple-400 shrink-0">
                  <Settings className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-semibold truncate">System Admin</div>
                  <div className="text-[10px] text-slate-400 font-mono">system@bank.example</div>
                </div>
              </button>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-center gap-3 text-rose-300 text-sm animate-shake">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1.5">
              EMAIL ADDRESS
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Mail className="w-4 h-4" />
              </div>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-navy-800/80 border border-white/10 rounded-xl text-white placeholder-slate-500 text-sm focus:outline-none focus:border-pulse-500 focus:ring-1 focus:ring-pulse-500 transition-all"
                placeholder="user@bank.example"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1.5">
              PASSWORD
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-navy-800/80 border border-white/10 rounded-xl text-white placeholder-slate-500 text-sm focus:outline-none focus:border-pulse-500 focus:ring-1 focus:ring-pulse-500 transition-all"
                placeholder="••••••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-2 py-3 px-4 bg-gradient-to-r from-pulse-600 to-pulse-500 hover:from-pulse-500 hover:to-pulse-400 text-navy-900 font-bold rounded-xl shadow-lg shadow-pulse-500/25 flex items-center justify-center gap-2 transition-all disabled:opacity-50 cursor-pointer"
          >
            {isSubmitting ? (
              <span className="inline-block w-5 h-5 border-2 border-navy-900 border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <span>Sign In to Vyapar Pulse</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-6 pt-5 border-t border-white/5 text-center">
          <p className="text-xs text-slate-400">
            Protected by CAS & Role-Based BOLA Governance • Built for IDBI Innovate 2026
          </p>
        </div>
      </div>

      {/* Footer Info */}
      <div className="mt-8 text-center text-xs text-slate-400 z-10 font-mono space-y-1">
        <div>Built for IDBI Innovate 2026 • Hackathon prototype—not an official IDBI Bank production system</div>
        <div>Illustrative prototype policy thresholds • All Rights Reserved</div>
      </div>
    </div>
  );
}

