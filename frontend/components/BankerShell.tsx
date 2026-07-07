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
          color: "bg-brand-softAmber border-brand-amber text-brand-amber",
          icon: UserCheck,
        };
      case "CREDIT_ANALYST":
        return {
          label: "Credit Analyst",
          color: "bg-brand-softTeal border-brand-teal text-brand-teal",
          icon: TrendingUp,
        };
      case "RELATIONSHIP_MANAGER":
        return {
          label: "Relationship Mgr",
          color: "bg-brand-softTeal border-brand-teal text-brand-teal",
          icon: Briefcase,
        };
      case "SYSTEM_ADMIN":
        return {
          label: "System Admin",
          color: "bg-light-elevated border-light-secondary text-light-secondary",
          icon: Settings,
        };
      case "RISK_ADMIN":
        return {
          label: "Risk Admin",
          color: "bg-brand-softRed border-brand-red text-brand-red",
          icon: ShieldAlert,
        };
      default:
        return {
          label: role || "Banker",
          color: "bg-light-elevated border-light-border text-light-text",
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
      <header className="h-16 border-b border-light-border bg-brand-nav sticky top-0 z-40 px-4 lg:px-8 flex items-center justify-between gap-4 shadow-sm text-white">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="lg:hidden p-2 text-white/70 hover:text-white rounded-lg hover:bg-white/10"
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-white flex items-center justify-center shadow-sm border border-brand-teal/30">
              <ShieldCheck className="w-5 h-5 text-brand-teal" />
            </div>
            <div>
              <span className="font-extrabold text-lg tracking-tight text-white block leading-none">
                Vyapar <span className="text-brand-teal">Pulse</span>
              </span>
              <span className="text-[10px] font-bold text-white/60 uppercase tracking-widest block mt-0.5">
                IDBI INNOVATE 2026
              </span>
            </div>
          </Link>
        </div>

        {/* Search / Command Bar */}
        <div className="hidden md:flex flex-1 max-w-md mx-4">
          <div className="relative w-full">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-white/50" />
            <input
              type="text"
              placeholder="Search business ID, legal name, GSTIN or case #..."
              className="w-full pl-10 pr-4 py-2 bg-white/10 border border-white/20 rounded-lg text-sm text-white placeholder-white/50 focus:outline-none focus:border-brand-teal focus:ring-1 focus:ring-brand-teal transition-all"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold text-white/50 bg-white/10 px-1.5 py-0.5 rounded border border-white/10">
              ⌘K
            </span>
          </div>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-3">
          {/* System Health Pill */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/10 border border-white/20 text-xs font-bold">
            <span className="w-2 h-2 rounded-full bg-brand-teal animate-pulse" />
            <span className="text-white">Assessment Service</span>
          </div>

          {/* User Role Badge */}
          {user && (
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-bold shadow-sm ${roleInfo.color} bg-white`}>
              <RoleIcon className="w-3.5 h-3.5 shrink-0" />
              <span className="hidden md:inline">{user.full_name}</span>
              <span className="text-[11px] opacity-80">({roleInfo.label})</span>
            </div>
          )}

          {/* Logout Button */}
          <button
            onClick={logout}
            title="Sign out of Vyapar Pulse"
            className="p-2 rounded-lg bg-white/10 hover:bg-brand-red/20 text-white/70 hover:text-brand-softRed border border-white/10 hover:border-brand-red/40 transition-all"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Body Layout */}
      <div className="flex flex-1 relative">
        {/* Sidebar */}
        <aside
          className={`fixed lg:sticky top-16 z-30 w-64 h-[calc(100vh-4rem)] bg-brand-nav border-r border-light-border flex flex-col justify-between transition-transform duration-200 ease-in-out ${
            sidebarOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full lg:translate-x-0"
          }`}
        >
          <div className="p-4 space-y-2 overflow-y-auto">
            <div className="text-[10px] font-bold text-white/50 uppercase tracking-wider px-3 py-2">
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
                  className={`flex items-center justify-between px-3.5 py-3 rounded-lg text-sm font-bold transition-all ${
                    isActive
                      ? "bg-white/10 text-white border-l-4 border-brand-teal shadow-sm"
                      : item.highlight
                      ? "text-brand-amber hover:bg-white/5"
                      : "text-white/70 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`w-4 h-4 ${isActive ? "text-brand-teal" : item.highlight ? "text-brand-amber" : "text-white/50"}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-white/10 text-white border border-white/20">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>

          {/* Bottom Security Banner */}
          <div className="p-4 border-t border-white/10 bg-white/5 m-4 rounded-lg border flex-shrink-0">
            <div className="flex items-center gap-2 text-sm font-bold text-white mb-2">
              <CheckCircle2 className="w-4 h-4 text-brand-teal shrink-0" />
              <span>Governance & Access</span>
            </div>
            <p className="text-xs text-white/70 leading-relaxed font-medium">
              Role-Scoped Access enforced. Tamper-evident prototype audit chain.
            </p>
          </div>
        </aside>

        {/* Overlay for mobile sidebar */}
        {sidebarOpen && (
          <div
            onClick={() => setSidebarOpen(false)}
            className="fixed inset-0 bg-brand-nav/60 backdrop-blur-sm z-20 lg:hidden"
          />
        )}

        {/* Main Content Area */}
        <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8 overflow-y-auto flex flex-col justify-between">
          <div>{children}</div>
          <footer className="mt-12 pt-6 border-t border-light-border text-center text-sm text-light-muted font-medium space-y-1">
            <div>Built for IDBI Innovate 2026 • Hackathon prototype—not an official IDBI Bank production system</div>
            <div>Illustrative prototype policy thresholds • Tamper-evident prototype audit chain</div>
          </footer>
        </main>
      </div>
    </div>
  );
};
