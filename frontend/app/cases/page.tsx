"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
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
  RefreshCw,
} from "lucide-react";

const humaniseEnum = (str: string) => {
  if (!str) return "-";
  return str.split('_').map(word => word.charAt(0) + word.slice(1).toLowerCase()).join(' ');
};

interface CaseItem {
  id: string;
  business_id: string;
  status: string;
  requested_amount: number;
  business_name: string;
  requested_product?: string;
  facility_type?: string;
}

export default function CaseInventoryPage() {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const { user } = useAuth();

  const loadCases = async () => {
    setLoading(true);
    setError(null);
    const { data, status, error: fetchErr } = await apiFetch<CaseItem[]>("/api/cases/");
    if (status === 200 && Array.isArray(data)) {
      setCases(data);
    } else {
      setError(fetchErr || "Failed to load case inventory.");
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
      case "CONDITIONAL_OFFER":
        return {
          label: humaniseEnum(statusStr),
          color: "bg-brand-softTeal border-brand-teal text-brand-teal",
          icon: CheckCircle2,
        };
      case "REJECTED":
      case "DECLINED":
        return {
          label: humaniseEnum(statusStr),
          color: "bg-brand-softRed border-brand-red text-brand-red",
          icon: XCircle,
        };
      case "UNDER_REVIEW":
      case "ESCALATED":
      case "ENHANCED_DUE_DILIGENCE":
      case "ADDITIONAL_EVIDENCE_REQUIRED":
        return {
          label: humaniseEnum(statusStr),
          color: "bg-brand-softAmber border-brand-amber text-brand-amber",
          icon: Clock,
        };
      default:
        return {
          label: humaniseEnum(statusStr) || "Initiated",
          color: "bg-light-elevated border-light-border text-light-secondary",
          icon: Clock,
        };
    }
  };

  const filteredCases = cases.filter((c) => {
    const matchesSearch =
      c.business_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.requested_product?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.facility_type?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "ALL" || c.status?.toUpperCase() === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getActionLabel = (role?: string) => {
    if (role === "CREDIT_ANALYST") return "Evaluate";
    if (role === "SANCTIONING_AUTHORITY") return "Review Case";
    return "View Case";
  };

  if (user?.role === "SYSTEM_ADMIN") {
    return (
      <div className="flex items-center justify-center h-64 text-light-muted">
        System Administrators do not have access to case inventory.
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-light-elevated border border-light-border text-xs text-light-secondary mb-2">
            <ShieldCheck className="w-3.5 h-3.5 text-brand-teal" />
            <span>ROLE SCOPED VIEW</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-light-text flex items-center gap-3 tracking-tight">
            <FolderKanban className="w-8 h-8 text-brand-teal" />
            <span>SME Case Inventory</span>
          </h1>
          <p className="text-light-secondary text-sm mt-1">
            Real-time pipeline of loan applications within your assigned authorization scope.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadCases}
            disabled={loading}
            className="px-4 py-2 bg-white hover:bg-light-elevated text-light-text text-sm font-medium rounded-lg border border-light-border flex items-center gap-2 transition-all shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-brand-teal" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-card p-4 rounded-xl border border-light-border flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-light-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search company name, product..."
            className="w-full pl-10 pr-4 py-2 bg-light-bg border border-light-border rounded-lg text-sm text-light-text placeholder-light-muted focus:outline-none focus:border-brand-teal focus:ring-1 focus:ring-brand-teal transition-all"
          />
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
          <Filter className="w-4 h-4 text-light-secondary shrink-0 mr-1 hidden sm:inline" />
          {["ALL", "INITIATED", "SUBMITTED", "PENDING", "RECOMMENDED", "SANCTIONED", "REJECTED"].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all shrink-0 ${
                statusFilter === status
                  ? "bg-brand-teal text-white shadow-sm"
                  : "bg-light-bg text-light-secondary hover:text-light-text hover:bg-light-elevated border border-light-border"
              }`}
            >
              {status === "ALL" ? "All" : humaniseEnum(status)}
            </button>
          ))}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 bg-brand-softRed border border-brand-red rounded-xl flex items-center gap-3 text-brand-red text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Case List Table / Cards */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="glass-card p-6 rounded-xl border border-light-border animate-pulse flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-light-elevated" />
                <div className="space-y-2">
                  <div className="w-48 h-4 bg-light-elevated rounded" />
                  <div className="w-32 h-3 bg-light-elevated rounded" />
                </div>
              </div>
              <div className="w-24 h-8 bg-light-elevated rounded-lg" />
            </div>
          ))}
        </div>
      ) : filteredCases.length === 0 ? (
        <div className="glass-card p-12 text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-light-bg mx-auto flex items-center justify-center text-light-muted border border-light-border">
            <FolderKanban className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-light-text">No Cases Found</h3>
          <p className="text-sm text-light-secondary max-w-md mx-auto">
            {searchQuery || statusFilter !== "ALL"
              ? "No credit cases match your current filter criteria."
              : "No cases are currently assigned within your scope."}
          </p>
          {(searchQuery || statusFilter !== "ALL") && (
            <button
              onClick={() => {
                setSearchQuery("");
                setStatusFilter("ALL");
              }}
              className="px-4 py-2 bg-white text-light-text hover:bg-light-elevated text-sm font-medium rounded-lg border border-light-border transition-all"
            >
              Reset Filters
            </button>
          )}
        </div>
      ) : (
        <div className="glass-card overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-light-border bg-light-bg text-xs uppercase text-light-secondary font-medium">
                  <th className="py-4 px-6">SME Business & Ref</th>
                  <th className="py-4 px-6">Requested Product</th>
                  <th className="py-4 px-6">Amount</th>
                  <th className="py-4 px-6">Status & Scope</th>
                  <th className="py-4 px-6 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-light-border text-sm bg-white">
                {filteredCases.map((c) => {
                  const statusInfo = getStatusBadge(c.status);
                  const StatusIcon = statusInfo.icon;

                  return (
                    <tr
                      key={c.id}
                      className="hover:bg-light-bg transition-colors group"
                    >
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-3.5">
                          <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 font-bold text-sm bg-light-elevated text-brand-teal border border-light-border">
                            <Building2 className="w-5 h-5" />
                          </div>
                          <div>
                            <div className="font-bold text-light-text flex items-center gap-2">
                              <span>{c.business_name || "SME Borrower"}</span>
                            </div>
                            <div className="text-xs font-mono text-light-muted">
                              REF: {c.id.slice(0, 8)}...{c.id.slice(-4)}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <span className="inline-flex items-center px-2.5 py-1 rounded border border-light-border bg-light-elevated text-[11px] font-medium text-light-secondary">
                          {c.facility_type ? humaniseEnum(c.facility_type) : (c.requested_product || "-")}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <span className="font-bold text-light-text font-mono">
                          {formatCurrency(c.requested_amount)}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-medium border ${statusInfo.color}`}>
                          <StatusIcon className="w-3.5 h-3.5" />
                          <span>{statusInfo.label}</span>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <Link
                          href={`/cases/${c.id}`}
                          className="inline-flex items-center gap-1 px-4 py-2 rounded-lg bg-white hover:bg-light-elevated text-sm font-medium text-brand-teal border border-light-border transition-all shadow-sm"
                        >
                          <span>{getActionLabel(user?.role)}</span>
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
