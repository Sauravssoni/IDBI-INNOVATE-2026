"use client";

import React, { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { ShieldCheck, Activity, Lock } from "lucide-react";

export const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user && pathname !== "/login") {
      router.push("/login");
    }
  }, [user, loading, router, pathname]);

  if (loading) {
    return (
      <div className="min-h-screen bg-navy-900 flex flex-col items-center justify-center p-6 text-foreground relative overflow-hidden">
        {/* Background glow effects */}
        <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-pulse-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/3 right-1/4 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse" />

        <div className="glass-panel p-8 rounded-2xl border border-white/10 max-w-md w-full flex flex-col items-center text-center relative z-10 shadow-2xl">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-pulse-600 to-navy-700 flex items-center justify-center mb-6 shadow-lg shadow-pulse-500/20 border border-pulse-400/30 animate-bounce">
            <Activity className="w-8 h-8 text-pulse-400" />
          </div>

          <h2 className="text-xl font-bold tracking-wide text-white mb-2 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-pulse-400 inline" />
            IDBI INNOVATE 2026
          </h2>
          <p className="text-sm font-semibold text-gradient mb-4">
            Vyapar Pulse • Next-Gen Credit Assessment Engine
          </p>
          
          <div className="w-full bg-navy-800 h-2 rounded-full overflow-hidden mb-4 border border-white/5">
            <div className="bg-gradient-to-r from-pulse-500 to-blue-500 h-full w-2/3 animate-pulse rounded-full" />
          </div>

          <p className="text-xs text-slate-400 flex items-center gap-1.5 font-mono">
            <Lock className="w-3.5 h-3.5 text-pulse-400" />
            Validating BOLA Authorization & CAS Session...
          </p>
        </div>
      </div>
    );
  }

  if (!user && pathname !== "/login") {
    return null;
  }

  return <>{children}</>;
};
