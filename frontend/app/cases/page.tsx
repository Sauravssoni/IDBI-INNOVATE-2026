"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import {
  FolderKanban,
  Search,
  Filter,
  ArrowUpRight,
  ShieldCheck,
  AlertCircle,
  Building2,
  CheckCircle2,
  Clock,
  XCircle,
  Sparkles,
  RefreshCw,
} from "lucide-react";

interface CaseItem {
  id: string;
  business_id: string;
  status: string;
  requested_amount: number;
  business_name: string;
  requested_product?: string;
}

export default function CaseInventoryPage() {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const loadCases = async () => {
    setLoading(true);
    setError(null);
    const { data, status, error: fetchErr } = await apiFetch<CaseItem[]>("/api/cases/");
    if (status === 200 && Array.isArray(data)) {
      setCases(data);
    } else {
      setError(fetchErr || "Failed to load case inventory from BOLA endpoint.");
    }
    setLoading(false);
  };

  useEffect(() => {
    loadCases();
  }, []);

  const formatCurrency = (amount?: number) => {
    if (!amount && amount !== 0) return "₹0";
    if (amount >= 10000000) {
      return `₹${(amount / 10000000).toFixed(2)} Cr`;
    }
    if (amount >= 100000) {
      return `₹${(amount / 100000).toFixed(2)} L`;
    }
    return `₹${amount.toLocaleString("en-IN")}`;
  };

  const getStatusBadge = (statusStr: string) => {
    switch (statusStr?.toUpperCase()) {
      case "SANCTIONED":
      case "APPROVED":
        return {
          label: "Sanctioned",
          color: "bg-emerald-500/15 border-emerald-500/40 text-emerald-300",
          icon: CheckCircle2,
        };
      case "REJECTED":
      case "DECLINED":
        return {
          label: "Declined",
          color: "bg-rose-500/15 border-rose-500/40 text-rose-300",
          icon: XCircle,
        };
      case "UNDER_REVIEW":
      case "ESCALATED":
        return {
          label: "In Review / SA",
          color: "bg-amber-500/15 border-amber-500/40 text-amber-300",
          icon: Clock,
        };
      default:
        return {
          label: statusStr || "Initiated",
          color: "bg-blue-500/15 border-blue-500/40 text-blue-300",
          icon: Clock,
        };
    }
  };

  const filteredCases = cases.filter((c) => {
    const matchesSearch =
      c.business_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.requested_product?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "ALL" || c.status?.toUpperCase() === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-navy-800 border border-white/10 text-xs text-slate-300 font-mono mb-2">
            <ShieldCheck className="w-3.5 h-3.5 text-pulse-400" />
            <span>BOLA GOVERNANCE ENABLED • ROLE SCOPED VIEW</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <FolderKanban className="w-8 h-8 text-pulse-400" />
            <span>SME Case Inventory</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Real-time pipeline of loan applications within your geographic and authorization boundaries.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadCases}
            disabled={loading}
            className="px-4 py-2.5 bg-navy-800 hover:bg-navy-700 text-white text-xs font-semibold rounded-xl border border-white/10 flex items-center gap-2 transition-all shadow-sm cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-pulse-400" : ""}`} />
            <span>Refresh Pipeline</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-panel p-4 rounded-2xl border border-white/10 flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search company name, product..."
            className="w-full pl-10 pr-4 py-2 bg-navy-800/80 border border-white/10 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-pulse-500 focus:ring-1 focus:ring-pulse-500 transition-all"
          />
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
          <Filter className="w-4 h-4 text-slate-400 shrink-0 mr-1 hidden sm:inline" />
          {["ALL", "INITIATED", "UNDER_REVIEW", "SANCTIONED", "REJECTED"].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all shrink-0 ${
                statusFilter === status
                  ? "bg-pulse-500 text-navy-900 font-bold shadow-sm"
                  : "bg-navy-800/60 text-slate-400 hover:text-white hover:bg-navy-800 border border-white/5"
              }`}
            >
              {status.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-center gap-3 text-rose-300 text-sm">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Case List Table / Cards */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="glass-card p-6 rounded-2xl border border-white/5 animate-pulse flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-navy-800" />
                <div className="space-y-2">
                  <div className="w-48 h-4 bg-navy-800 rounded" />
                  <div className="w-32 h-3 bg-navy-800 rounded" />
                </div>
              </div>
              <div className="w-24 h-8 bg-navy-800 rounded-xl" />
            </div>
          ))}
        </div>
      ) : filteredCases.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl border border-white/10 text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-navy-800 mx-auto flex items-center justify-center text-slate-500 border border-white/5">
            <FolderKanban className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-white">No Cases Found</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto">
            {searchQuery || statusFilter !== "ALL"
              ? "No credit cases match your current filter criteria."
              : "No cases are currently assigned within your BOLA geographic or mandate scope."}
          </p>
          {(searchQuery || statusFilter !== "ALL") && (
            <button
              onClick={() => {
                setSearchQuery("");
                setStatusFilter("ALL");
              }}
              className="px-4 py-2 bg-navy-800 text-pulse-400 hover:text-white text-xs font-semibold rounded-xl border border-white/10 transition-all"
            >
              Reset Filters
            </button>
          )}
        </div>
      ) : (
        <div className="glass-panel rounded-2xl border border-white/10 overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/10 bg-navy-800/50 text-[11px] font-mono uppercase text-slate-400 tracking-wider">
                  <th className="py-4 px-6">SME Business & Ref</th>
                  <th className="py-4 px-6">Requested Product</th>
                  <th className="py-4 px-6">Amount</th>
                  <th className="py-4 px-6">Status & BOLA Scope</th>
                  <th className="py-4 px-6 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-sm">
                {filteredCases.map((c) => {
                  const statusInfo = getStatusBadge(c.status);
                  const StatusIcon = statusInfo.icon;

                  return (
                    <tr
                      key={c.id}
                      className="hover:bg-white/[0.02] transition-colors group"
                    >
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-3.5">
                          <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 font-bold text-sm bg-navy-800 text-slate-300 border border-white/5">
                            <Building2 className="w-5 h-5 text-pulse-400" />
                          </div>
                          <div>
                            <div className="font-bold text-white flex items-center gap-2">
                              <span>{c.business_name || "SME Borrower"}</span>
                            </div>
                            <div className="text-[11px] font-mono text-slate-400">
                              REF: {c.id.slice(0, 8)}...{c.id.slice(-4)}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <span className="inline-flex items-center px-2.5 py-1 rounded-lg bg-navy-800/80 border border-white/5 text-xs font-mono text-slate-300">
                          {c.requested_product || "-"}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <span className="font-bold text-white font-mono">
                          {formatCurrency(c.requested_amount)}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-semibold ${statusInfo.color}`}>
                          <StatusIcon className="w-3.5 h-3.5" />
                          <span>{statusInfo.label}</span>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <Link
                          href={`/cases/${c.id}`}
                          className="inline-flex items-center gap-1 px-3.5 py-2 rounded-xl bg-navy-800 hover:bg-pulse-500 hover:text-navy-900 text-xs font-bold text-slate-300 border border-white/10 hover:border-pulse-500 transition-all shadow-sm group-hover:scale-105"
                        >
                          <span>Evaluate</span>
                          <ArrowUpRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
