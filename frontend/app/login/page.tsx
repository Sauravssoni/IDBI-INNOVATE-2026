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
  AlertCircle,
  RefreshCw,
  Search,
  PlayCircle
} from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [serviceStatus, setServiceStatus] = useState<"checking" | "available" | "unavailable">("checking");
  const [showEmailLogin, setShowEmailLogin] = useState(false);

  const { login, demoLogin } = useAuth();
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
        setServiceStatus("unavailable");
      } else {
        setError("Email or password is incorrect.");
      }
      setIsSubmitting(false);
    }
  };

  const handleDemoLogin = async (role: string) => {
    setError(null);
    setIsSubmitting(true);
    const res = await demoLogin(role);
    if (res.success) {
      router.push("/");
    } else {
      if (res.error?.includes("Failed to fetch") || res.error?.includes("Network request failed") || res.error?.includes("unavailable")) {
        setServiceStatus("unavailable");
      } else {
        setError(res.error || "Guided demo access is unavailable in this environment.");
      }
      setIsSubmitting(false);
    }
  };

  const startJourney = async () => {
    setError(null);
    setIsSubmitting(true);
    const res = await demoLogin("CREDIT_ANALYST");
    if (res.success) {
      router.push("/demo");
    } else {
      if (res.error?.includes("Failed to fetch") || res.error?.includes("Network request failed") || res.error?.includes("unavailable")) {
        setServiceStatus("unavailable");
      } else {
        setError(res.error || "Guided demo access is unavailable in this environment.");
      }
      setIsSubmitting(false);
    }
  };

  const checkHealth = async () => {
    setServiceStatus("checking");
    try {
      const { status } = await apiFetch("/health");
      if (status !== 200) {
        setServiceStatus("unavailable");
      } else {
        setServiceStatus("available");
      }
    } catch (err) {
      setServiceStatus("unavailable");
    }
  };

  React.useEffect(() => {
    checkHealth();
  }, []);

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
        
        {serviceStatus === "unavailable" ? (
          <div className="text-center py-6">
            <div className="w-16 h-16 bg-brand-softRed rounded-full flex items-center justify-center mx-auto mb-4 border border-brand-red">
              <AlertCircle className="w-8 h-8 text-brand-red" />
            </div>
            <h2 className="text-xl font-bold text-light-text mb-2">Service Unavailable</h2>
            <p className="text-sm text-light-secondary mb-8">
              Vyapar Pulse API is unavailable. Retry or verify the service URL.
            </p>
            <button
              onClick={checkHealth}
              className="w-full py-3 px-4 bg-light-bg hover:bg-light-elevated text-light-text font-bold rounded-lg border border-light-border flex items-center justify-center gap-2 transition-all shadow-sm"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Retry Connection</span>
            </button>
          </div>
        ) : (
          <>
            <h2 className="text-xl font-bold text-light-text flex items-center justify-between mb-6">
              <span>{showEmailLogin ? "Sign in to Vyapar Pulse" : "Demo Access"}</span>
              <span className="text-xs text-light-secondary font-medium bg-light-bg px-2 py-1 rounded">Prototype release 1.1.3</span>
            </h2>

            {error && (
              <div className="mb-6 p-4 bg-brand-softRed border border-brand-red rounded-lg flex items-center gap-3 text-brand-red text-sm font-medium">
                <AlertCircle className="w-5 h-5 text-brand-red shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {!showEmailLogin ? (
              <div className="space-y-6">
                <div className="bg-brand-softTeal border border-brand-teal rounded-lg p-5">
                  <h3 className="text-sm font-bold text-brand-teal uppercase tracking-wider mb-2 flex items-center gap-2">
                    <PlayCircle className="w-5 h-5" />
                    Guided Live Demo
                  </h3>
                  <p className="text-sm text-light-text font-medium mb-4">
                    Experience the complete analyst-to-sanction journey with live API reconciliation and actual data twins.
                  </p>
                  <button
                    onClick={startJourney}
                    disabled={isSubmitting}
                    className="w-full py-3 px-4 bg-brand-teal hover:bg-brand-tealHover text-white font-bold rounded-lg flex items-center justify-center gap-2 transition-all disabled:opacity-50 shadow-sm"
                  >
                    {isSubmitting ? (
                      <span className="inline-block w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <>
                        <span>Start 3-Minute Credit Journey</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </div>

                <div>
                  <h3 className="text-xs font-bold text-light-secondary uppercase tracking-wider mb-3">
                    Explore Specific Roles
                  </h3>
                  <div className="grid grid-cols-1 gap-3">
                    <button
                      onClick={() => handleDemoLogin("CREDIT_ANALYST")}
                      disabled={isSubmitting}
                      className="p-3 bg-light-bg border border-light-border hover:border-brand-teal hover:bg-brand-softTeal text-left rounded-lg transition-all flex items-center gap-3"
                    >
                      <div className="w-8 h-8 rounded bg-white flex items-center justify-center text-brand-teal shrink-0 border border-brand-teal/20">
                        <TrendingUp className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <div className="text-sm font-bold text-light-text">Credit Analyst</div>
                        <div className="text-[11px] text-light-secondary">Evaluate evidence and recommend a structure</div>
                      </div>
                    </button>
                    <button
                      onClick={() => handleDemoLogin("SANCTIONING_AUTHORITY")}
                      disabled={isSubmitting}
                      className="p-3 bg-light-bg border border-light-border hover:border-brand-amber hover:bg-brand-softAmber text-left rounded-lg transition-all flex items-center gap-3"
                    >
                      <div className="w-8 h-8 rounded bg-white flex items-center justify-center text-brand-amber shrink-0 border border-brand-amber/20">
                        <UserCheck className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <div className="text-sm font-bold text-light-text">Sanctioning Authority</div>
                        <div className="text-[11px] text-light-secondary">Review the analyst recommendation and decide</div>
                      </div>
                    </button>
                    <button
                      onClick={() => handleDemoLogin("RELATIONSHIP_MANAGER")}
                      disabled={isSubmitting}
                      className="p-3 bg-light-bg border border-light-border hover:border-brand-teal hover:bg-brand-softTeal text-left rounded-lg transition-all flex items-center gap-3"
                    >
                      <div className="w-8 h-8 rounded bg-white flex items-center justify-center text-brand-teal shrink-0 border border-brand-teal/20">
                        <Briefcase className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <div className="text-sm font-bold text-light-text">Relationship Manager</div>
                        <div className="text-[11px] text-light-secondary">View originated cases and final outcomes</div>
                      </div>
                    </button>
                    <button
                      onClick={() => handleDemoLogin("AUDITOR")}
                      disabled={isSubmitting}
                      className="p-3 bg-light-bg border border-light-border hover:border-light-secondary hover:bg-light-elevated text-left rounded-lg transition-all flex items-center gap-3"
                    >
                      <div className="w-8 h-8 rounded bg-white flex items-center justify-center text-light-secondary shrink-0 border border-light-border">
                        <Search className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <div className="text-sm font-bold text-light-text">Auditor</div>
                        <div className="text-[11px] text-light-secondary">Inspect versioned decision history</div>
                      </div>
                    </button>
                  </div>
                </div>

                <div className="text-center pt-2">
                  <button 
                    onClick={() => { setShowEmailLogin(true); setError(null); }}
                    className="text-sm font-bold text-brand-teal hover:underline"
                  >
                    Use email and password instead
                  </button>
                </div>
              </div>
            ) : (
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
                
                <div className="text-center pt-2">
                  <button 
                    type="button"
                    onClick={() => { setShowEmailLogin(false); setError(null); }}
                    className="text-sm font-bold text-light-secondary hover:text-light-text hover:underline"
                  >
                    Return to Demo Access
                  </button>
                </div>
              </form>
            )}

            <div className="mt-6 pt-5 border-t border-light-border text-center">
              <p className="text-xs text-light-secondary font-medium">
                Synthetic Sandbox • Protected by CAS & Role-Based BOLA Governance
              </p>
            </div>
          </>
        )}
      </div>

      {/* Footer Info */}
      <div className="mt-8 text-center text-xs text-light-border z-10 font-mono space-y-2 opacity-80">
        <div>Built for IDBI Innovate 2026 • Hackathon prototype—not an official IDBI Bank production system</div>
        <div>Illustrative prototype policy thresholds • All Rights Reserved</div>
      </div>
    </div>
  );
}
