"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/api";
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
      if (res.error?.includes("Failed to fetch") || res.error?.includes("Network request failed") || res.error?.includes("unavailable")) {
        setError("Vyapar Pulse API is unavailable. Start the backend service or verify NEXT_PUBLIC_API_URL.");
      } else {
        setError(res.error || "Login failed. Please verify credentials.");
      }
      setIsSubmitting(false);
    }
  };

  const selectDemoRole = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword("");
    setError(null);
  };

  React.useEffect(() => {
    const checkHealth = async () => {
      try {
        const { status, error: fetchErr } = await apiFetch("/health");
        if (status !== 200) {
          setError("Vyapar Pulse API is unavailable. Start the backend service or verify NEXT_PUBLIC_API_URL.");
        }
      } catch (err) {
        setError("Vyapar Pulse API is unavailable. Start the backend service or verify NEXT_PUBLIC_API_URL.");
      }
    };
    checkHealth();
  }, []);

  const enableDemoShortcuts = process.env.NEXT_PUBLIC_ENABLE_DEMO_SHORTCUTS === "true";

  return (
    <div className="min-h-screen bg-brand-nav text-light-text flex flex-col justify-center items-center p-4 relative overflow-hidden">
      
      {/* Header Branding */}
      <div className="text-center mb-8 z-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-navHover border border-light-border/20 text-xs text-brand-teal font-mono mb-3 shadow-lg font-bold">
          <ShieldCheck className="w-4 h-4 text-brand-teal" />
          <span>BUILT FOR IDBI INNOVATE 2026 • HACKATHON EDITION</span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white mb-2">
          Vyapar <span className="text-brand-teal">Pulse</span>
        </h1>
        <p className="text-light-border text-sm sm:text-base max-w-md mx-auto">
          Evidence-linked MSME credit assessment and governed human decision support
        </p>
      </div>

      {/* Main Card */}
      <div className="bg-white w-full max-w-lg p-8 rounded-lg shadow-2xl border border-light-border z-10">
        <h2 className="text-xl font-bold text-light-text mb-6 flex items-center justify-between">
          <span>Sign in to Vyapar Pulse</span>
          <span className="text-xs text-light-secondary font-medium bg-light-bg px-2 py-1 rounded">Prototype release 1.1.3</span>
        </h2>

        {/* 1-Click Demo Role Selector */}
        {enableDemoShortcuts && (
          <div className="mb-6">
            <label className="block text-xs font-bold text-light-text uppercase tracking-wider mb-1">
              Quick Demo Login (Click to Fill Email)
            </label>
            <p className="text-xs text-light-secondary font-medium mb-3">
              Use the development credential provided in the evaluator guide.
            </p>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => selectDemoRole("sa@bank.example")}
                className={`p-3 rounded-lg border text-left flex items-center gap-3 transition-all ${
                  email === "sa@bank.example"
                    ? "bg-brand-softAmber border-brand-amber text-brand-amber shadow-sm"
                    : "bg-light-bg border-light-border text-light-text hover:border-brand-amber hover:bg-brand-softAmber"
                }`}
              >
                <div className="w-8 h-8 rounded bg-white flex items-center justify-center text-brand-amber shrink-0 border border-brand-amber/20">
                  <UserCheck className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-bold truncate">Sanction Auth</div>
                  <div className="text-[10px] text-light-secondary font-mono">sa@bank.example</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => selectDemoRole("credit@bank.example")}
                className={`p-3 rounded-lg border text-left flex items-center gap-3 transition-all ${
                  email === "credit@bank.example"
                    ? "bg-brand-softTeal border-brand-teal text-brand-teal shadow-sm"
                    : "bg-light-bg border-light-border text-light-text hover:border-brand-teal hover:bg-brand-softTeal"
                }`}
              >
                <div className="w-8 h-8 rounded bg-white flex items-center justify-center text-brand-teal shrink-0 border border-brand-teal/20">
                  <TrendingUp className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-bold truncate">Credit Analyst</div>
                  <div className="text-[10px] text-light-secondary font-mono">credit@bank.example</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => selectDemoRole("rm@bank.example")}
                className={`p-3 rounded-lg border text-left flex items-center gap-3 transition-all ${
                  email === "rm@bank.example"
                    ? "bg-brand-softTeal border-brand-teal text-brand-teal shadow-sm"
                    : "bg-light-bg border-light-border text-light-text hover:border-brand-teal hover:bg-brand-softTeal"
                }`}
              >
                <div className="w-8 h-8 rounded bg-white flex items-center justify-center text-brand-teal shrink-0 border border-brand-teal/20">
                  <Briefcase className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-bold truncate">Relationship Mgr</div>
                  <div className="text-[10px] text-light-secondary font-mono">rm@bank.example</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => selectDemoRole("system@bank.example")}
                className={`p-3 rounded-lg border text-left flex items-center gap-3 transition-all ${
                  email === "system@bank.example"
                    ? "bg-light-elevated border-light-secondary text-light-text shadow-sm"
                    : "bg-light-bg border-light-border text-light-text hover:border-light-secondary hover:bg-light-elevated"
                }`}
              >
                <div className="w-8 h-8 rounded bg-white flex items-center justify-center text-light-secondary shrink-0 border border-light-border">
                  <Settings className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-bold truncate">System Admin</div>
                  <div className="text-[10px] text-light-secondary font-mono">system@bank.example</div>
                </div>
              </button>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-brand-softRed border border-brand-red rounded-lg flex items-center gap-3 text-brand-red text-sm font-medium">
            <AlertCircle className="w-5 h-5 text-brand-red shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleLogin} className="space-y-5">
          <div>
            <label className="block text-xs font-bold text-light-text mb-1.5 uppercase">
              Email Address
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-light-muted">
                <Mail className="w-4 h-4" />
              </div>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-light-bg border border-light-border rounded-lg text-light-text placeholder-light-muted text-sm focus:outline-none focus:border-brand-teal focus:ring-1 focus:ring-brand-teal transition-all font-medium"
                placeholder="user@bank.example"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-light-text mb-1.5 uppercase">
              Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-light-muted">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-light-bg border border-light-border rounded-lg text-light-text placeholder-light-muted text-sm focus:outline-none focus:border-brand-teal focus:ring-1 focus:ring-brand-teal transition-all font-medium"
                placeholder="••••••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-4 py-3 px-4 bg-brand-teal hover:bg-brand-tealHover text-white font-bold rounded-lg border border-brand-tealHover flex items-center justify-center gap-2 transition-all disabled:opacity-50 cursor-pointer shadow-sm"
          >
            {isSubmitting ? (
              <span className="inline-block w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <span>Sign In to Vyapar Pulse</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-6 pt-5 border-t border-light-border text-center">
          <p className="text-xs text-light-secondary font-medium">
            Protected by CAS & Role-Based BOLA Governance • Built for IDBI Innovate 2026
          </p>
        </div>
      </div>

      {/* Footer Info */}
      <div className="mt-8 text-center text-xs text-light-border z-10 font-mono space-y-2 opacity-80">
        <div>Built for IDBI Innovate 2026 • Hackathon prototype—not an official IDBI Bank production system</div>
        <div>Illustrative prototype policy thresholds • All Rights Reserved</div>
      </div>
    </div>
  );
}
