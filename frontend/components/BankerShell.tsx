"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard,
  FolderKanban,
  Sparkles,
  ShieldCheck,
  LogOut,
  Bell,
  Search,
  CheckCircle2,
  Menu,
  X,
  UserCheck,
  TrendingUp,
  Briefcase,
  Settings,
  ShieldAlert,
  History,
} from "lucide-react";

export const BankerShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const getRoleBadge = (role?: string) => {
    switch (role) {
      case "SANCTIONING_AUTHORITY":
        return {
          label: "Sanction Authority",
          color: "bg-amber-500/15 border-amber-500/40 text-amber-300",
          icon: UserCheck,
        };
      case "CREDIT_ANALYST":
        return {
          label: "Credit Analyst",
          color: "bg-blue-500/15 border-blue-500/40 text-blue-300",
          icon: TrendingUp,
        };
      case "RELATIONSHIP_MANAGER":
        return {
          label: "Relationship Mgr",
          color: "bg-teal-500/15 border-teal-500/40 text-teal-300",
          icon: Briefcase,
        };
      case "SYSTEM_ADMIN":
        return {
          label: "System Admin",
          color: "bg-purple-500/15 border-purple-500/40 text-purple-300",
          icon: Settings,
        };
      case "RISK_ADMIN":
        return {
          label: "Risk Admin",
          color: "bg-rose-500/15 border-rose-500/40 text-rose-300",
          icon: ShieldAlert,
        };
      default:
        return {
          label: role || "Banker",
          color: "bg-slate-500/15 border-slate-500/40 text-slate-300",
          icon: ShieldCheck,
        };
    }
  };

  const roleInfo = getRoleBadge(user?.role);
  const RoleIcon = roleInfo.icon;

  type NavItem = {
    label: string;
    href: string;
    icon: React.ElementType;
    badge?: string;
    highlight?: boolean;
  };

  const getNavItemsForRole = (role?: string): NavItem[] => {
    const allItems: NavItem[] = [
      { label: "Dashboard", href: "/", icon: LayoutDashboard },
      { label: "Case Inventory", href: "/cases", icon: FolderKanban },
      { label: "Policy & Risk Engine", href: "/policy", icon: ShieldAlert, badge: "AI" },
      { label: "Audit Log & CAS Trail", href: "/audit", icon: History },
    ];

    if (role === "SYSTEM_ADMIN") {
      return allItems.filter((item) => item.href === "/");
    }
    if (role === "RELATIONSHIP_MANAGER") {
      return allItems.filter((item) => item.href !== "/policy" && item.href !== "/audit");
    }
    if (role === "AUDITOR") {
      return allItems.filter((item) => item.href !== "/policy");
    }
    if (role === "CREDIT_ANALYST" || role === "SANCTIONING_AUTHORITY") {
      return allItems.filter((item) => item.href !== "/audit");
    }
    return allItems;
  };

  const navItems = getNavItemsForRole(user?.role);

  return (
    <div className="min-h-screen bg-light-bg text-light-text flex flex-col">
      {/* Top Navbar */}
      <header className="h-16 border-b border-white/10 bg-navy-900/90 backdrop-blur-md sticky top-0 z-40 px-4 lg:px-8 flex items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="lg:hidden p-2 text-slate-400 hover:text-white rounded-lg hover:bg-white/5"
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-pulse-600 to-navy-700 flex items-center justify-center shadow-md shadow-pulse-500/20 border border-pulse-400/30">
              <ShieldCheck className="w-5 h-5 text-pulse-400" />
            </div>
            <div>
              <span className="font-extrabold text-lg tracking-tight text-white block leading-none">
                Vyapar <span className="text-gradient">Pulse</span>
              </span>
              <span className="text-[10px] font-mono text-pulse-400 uppercase tracking-widest block mt-0.5">
                IDBI INNOVATE 2026
              </span>
            </div>
          </Link>
        </div>

        {/* Search / Command Bar */}
        <div className="hidden md:flex flex-1 max-w-md mx-4">
          <div className="relative w-full">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search business ID, legal name, GSTIN or case #..."
              className="w-full pl-10 pr-4 py-1.5 bg-navy-800/80 border border-white/10 rounded-full text-xs text-white placeholder-slate-500 focus:outline-none focus:border-pulse-500 focus:ring-1 focus:ring-pulse-500 transition-all"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-slate-500 bg-white/5 px-1.5 py-0.5 rounded border border-white/5">
              ⌘K
            </span>
          </div>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-3">
          {/* System Health Pill */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-navy-800 border border-white/10 text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-pulse-500 animate-pulse" />
            <span className="text-slate-300">Assessment Service</span>
            <span className="text-pulse-400 font-semibold">Available</span>
          </div>

          {/* User Role Badge */}
          {user && (
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-semibold shadow-sm ${roleInfo.color}`}>
              <RoleIcon className="w-3.5 h-3.5 shrink-0" />
              <span className="hidden md:inline">{user.full_name}</span>
              <span className="font-mono text-[11px] opacity-90">({roleInfo.label})</span>
            </div>
          )}

          {/* Logout Button */}
          <button
            onClick={logout}
            title="Sign out of Vyapar Pulse"
            className="p-2 rounded-xl bg-navy-800 hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 border border-white/5 hover:border-rose-500/30 transition-all"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Body Layout */}
      <div className="flex flex-1 relative">
        {/* Sidebar */}
        <aside
          className={`fixed lg:sticky top-16 z-30 w-64 h-[calc(100vh-4rem)] bg-navy-900/95 lg:bg-navy-900 border-r border-white/10 flex flex-col justify-between transition-transform duration-200 ease-in-out ${
            sidebarOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full lg:translate-x-0"
          }`}
        >
          <div className="p-4 space-y-1 overflow-y-auto">
            <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider px-3 py-2">
              Navigation & Workflows
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all ${
                    isActive
                      ? "bg-gradient-to-r from-pulse-600/20 to-transparent text-pulse-400 border-l-2 border-pulse-500 font-semibold shadow-sm"
                      : item.highlight
                      ? "text-amber-300 hover:bg-amber-500/10 border border-amber-500/20"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`w-4 h-4 ${isActive ? "text-pulse-400" : item.highlight ? "text-amber-400" : "text-slate-400"}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-pulse-500/20 text-pulse-300 border border-pulse-500/30">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>

          {/* Bottom Security Banner */}
          <div className="p-4 border-t border-white/5 bg-navy-800/40 m-3 rounded-xl border">
            <div className="flex items-center gap-2 text-xs font-semibold text-white mb-1">
              <CheckCircle2 className="w-4 h-4 text-pulse-400 shrink-0" />
              <span>Governance & Access Controls</span>
            </div>
            <p className="text-[10px] text-slate-400 leading-relaxed font-mono">
              Role-Scoped Access enforced. Tamper-evident prototype audit chain.
            </p>
          </div>
        </aside>

        {/* Overlay for mobile sidebar */}
        {sidebarOpen && (
          <div
            onClick={() => setSidebarOpen(false)}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-20 lg:hidden"
          />
        )}

        {/* Main Content Area */}
        <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8 overflow-y-auto flex flex-col justify-between">
          <div>{children}</div>
          <footer className="mt-12 pt-6 border-t border-white/10 text-center text-xs text-slate-400 font-mono space-y-1">
            <div>Built for IDBI Innovate 2026 • Hackathon prototype—not an official IDBI Bank production system</div>
            <div>Illustrative prototype policy thresholds • Tamper-evident prototype audit chain</div>
          </footer>
        </main>
      </div>
    </div>
  );
};
