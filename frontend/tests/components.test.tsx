import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import DashboardPage from "../app/page";
import CaseEvaluationPage from "../app/cases/[caseId]/page";

// Mock Next.js Link and navigation
vi.mock("next/link", () => ({
  default: ({ children, href }: any) => <a href={href}>{children}</a>,
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useParams: () => ({ caseId: "CASE-001" }),
}));

// Mock AuthContext
const mockUseAuth = vi.fn();
vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock apiFetch
const mockApiFetch = vi.fn();
vi.mock("../lib/api", () => ({
  apiFetch: (...args: any[]) => mockApiFetch(...args),
}));

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      user: { id: "usr-1", full_name: "Test Analyst", role: "CREDIT_ANALYST" },
    });
  });

  it("renders without fabricated crore amounts or demo fallbacks when cases are empty", async () => {
    mockApiFetch.mockImplementation(async (url: string) => {
      if (url === "/api/cases/summary") {
        return {
          status: 200,
          data: {
            total_requested_amount: 0,
            total_supportable_limit: 0,
            total_cases: 0,
            status_counts: {},
          },
        };
      }
      return { status: 200, data: [] };
    });

    render(<DashboardPage />);

    expect(screen.getByText(/MSME Credit Assessment Workspace/i)).toBeInTheDocument();
    expect(screen.getByText(/Credit Analyst Scope/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByText(/₹14\.8 Cr/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/₹8\.45 Cr/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/100% Auto/i)).not.toBeInTheDocument();
      expect(screen.getByText(/SCOPED APPLICATIONS/i)).toBeInTheDocument();
    });
  });

  it("renders live backend values without fabricated metrics", async () => {
    mockApiFetch.mockImplementation(async (url: string) => {
      if (url === "/api/cases/summary") {
        return {
          status: 200,
          data: {
            total_requested_amount: 5000000,
            total_supportable_limit: 3500000,
            total_cases: 1,
            status_counts: { IN_REVIEW: 1 },
          },
        };
      }
      return {
        status: 200,
        data: [
          {
            id: "CASE-101",
            business_name: "Shakti Precision Components",
            requested_amount: 5000000,
            status: "IN_REVIEW",
            evaluation_result: {
              supportable_limit: 3500000,
              recommendation: "CONDITIONAL_OFFER",
            },
          },
        ],
      };
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getAllByText(/₹50\.00 lakh/i).length).toBeGreaterThan(0);
      expect(screen.queryByText(/₹14\.8 Cr/i)).not.toBeInTheDocument();
    }, { timeout: 4000 });
  }, 10000);
});

describe("CaseEvaluationPage - Role Gating and Read-Only Load", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does NOT call POST /evaluate on page load (read-only case opening)", async () => {
    mockUseAuth.mockReturnValue({
      user: { id: "usr-1", full_name: "Test Analyst", role: "CREDIT_ANALYST" },
    });
    mockApiFetch.mockResolvedValue({
      status: 200,
      data: {
        id: "CASE-001",
        business_name: "Test Borrower",
        requested_amount: 5000000,
        status: "SUBMITTED",
        allowed_actions: { run_assessment: { allowed: true } },
      },
    });

    render(<CaseEvaluationPage />);

    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalled();
      const calls = mockApiFetch.mock.calls;
      const hasPost = calls.some((c) => c[1]?.method === "POST");
      expect(hasPost).toBe(false);
    });
  });

  it("enforces action visibility: CREDIT_ANALYST sees Run Assessment button", async () => {
    mockUseAuth.mockReturnValue({
      user: { id: "usr-1", full_name: "Analyst User", role: "CREDIT_ANALYST" },
    });
    mockApiFetch.mockResolvedValue({
      status: 200,
      data: {
        id: "CASE-001",
        business_name: "SME Corp",
        requested_amount: 5000000,
        allowed_actions: {
          run_assessment: { allowed: true },
          submit_analyst_recommendation: { allowed: true },
        },
      },
    });

    render(<CaseEvaluationPage />);

    await waitFor(() => {
      expect(screen.getByText("Run Assessment Engine")).toBeInTheDocument();
    });
  });

  it("enforces action visibility: RELATIONSHIP_MANAGER cannot see Run Assessment or sanction controls", async () => {
    mockUseAuth.mockReturnValue({
      user: { id: "usr-2", full_name: "RM User", role: "RELATIONSHIP_MANAGER" },
    });
    mockApiFetch.mockResolvedValue({
      status: 200,
      data: {
        id: "CASE-001",
        business_name: "SME Corp",
        requested_amount: 5000000,
        allowed_actions: { run_assessment: { allowed: false, blocked_reason_code: "ACTION_NOT_ALLOWED", message: "Not allowed" }, submit_analyst_recommendation: { allowed: false, blocked_reason_code: "ACTION_NOT_ALLOWED", message: "Not allowed" }, record_human_decision: { allowed: false, blocked_reason_code: "ACTION_NOT_ALLOWED", message: "Not allowed" } },
      },
    });

    render(<CaseEvaluationPage />);

    await waitFor(() => {
      expect(
        screen.queryByText("Run Assessment Engine"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText(/Sanctioning Authority Decision/i),
      ).not.toBeInTheDocument();
    });
  });

  it("displays STALE_VERSION refresh guidance when conflict occurs", async () => {
    mockUseAuth.mockReturnValue({
      user: { id: "usr-1", full_name: "Analyst User", role: "CREDIT_ANALYST" },
    });
    mockApiFetch.mockImplementation(async (url: string, opts?: RequestInit) => {
      if (opts?.method === "POST") {
        return {
          status: 409,
          error: "STALE_VERSION: Case version conflict. Refresh required.",
          data: {
            code: "STALE_VERSION",
            message: "Case version conflict. Refresh required.",
          },
        };
      }
      return {
        status: 200,
        data: {
          id: "CASE-001",
          business_name: "SME Corp",
          requested_amount: 5000000,
          version: 1,
          allowed_actions: { run_assessment: { allowed: true } },
        },
      };
    });

    render(<CaseEvaluationPage />);

    await waitFor(() => {
      expect(screen.getByText("Run Assessment Engine")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Run Assessment Engine"));

    await waitFor(() => {
      expect(
        screen.getByText(
          /STALE_VERSION: Case version conflict\. Refresh required\./i,
        ),
      ).toBeInTheDocument();
      expect(screen.getByText(/Refresh Case/i)).toBeInTheDocument();
    });
  });

  it("displays IDEMPOTENCY_IN_PROGRESS retry guidance when concurrent request occurs", async () => {
    mockUseAuth.mockReturnValue({
      user: { id: "usr-1", full_name: "Analyst User", role: "CREDIT_ANALYST" },
    });
    mockApiFetch.mockImplementation(async (url: string, opts?: RequestInit) => {
      if (opts?.method === "POST") {
        return {
          status: 409,
          error:
            "IDEMPOTENCY_IN_PROGRESS: An identical request is currently being processed.",
          data: {
            code: "IDEMPOTENCY_IN_PROGRESS",
            message: "An identical request is currently being processed.",
            retryable: true,
            retry_after_seconds: 5,
          },
        };
      }
      return {
        status: 200,
        data: {
          id: "CASE-001",
          business_name: "SME Corp",
          requested_amount: 5000000,
          version: 1,
          allowed_actions: { run_assessment: { allowed: true } },
        },
      };
    });

    render(<CaseEvaluationPage />);

    await waitFor(() => {
      expect(screen.getByText("Run Assessment Engine")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Run Assessment Engine"));

    await waitFor(() => {
      expect(screen.getByText(/IDEMPOTENCY_IN_PROGRESS/i)).toBeInTheDocument();
    });
  });

  it("renders tab navigation and switches between tabs", async () => {
    mockUseAuth.mockReturnValue({
      user: { id: "usr-1", full_name: "Analyst User", role: "CREDIT_ANALYST" },
    });
    mockApiFetch.mockImplementation(async (url: string) => {
      if (url === "/api/cases/CASE-001/evidence/gst") {
        return { status: 200, data: [] };
      }
      if (url === "/api/cases/CASE-001/evidence/bank") {
        return { status: 200, data: [] };
      }
      if (url === "/api/cases/CASE-001/evidence/invoices") {
        return { status: 200, data: [] };
      }
      if (url === "/api/cases/CASE-001/evidence/employment") {
        return { status: 200, data: [] };
      }
      if (url === "/api/cases/CASE-001/evidence/obligations") {
        return { status: 200, data: [] };
      }
      if (url === "/api/cases/CASE-001/reconciliation") {
        return { status: 200, data: { status: "PENDING" } };
      }
      if (url === "/api/cases/CASE-001/audit") {
        return { status: 200, data: [] };
      }
      return {
        status: 200,
        data: {
          id: "CASE-001",
          business_name: "SME Corp",
          requested_amount: 5000000,
          version: 1,
          allowed_actions: { run_assessment: { allowed: true } },
        },
      };
    });

    render(<CaseEvaluationPage />);

    await waitFor(() => {
      expect(screen.getByText("Evidence Data")).toBeInTheDocument();
    });

    // Check Overview is visible
    expect(screen.getByText(/MSME Credit Twin/i)).toBeInTheDocument();

    // Click Evidence
    fireEvent.click(screen.getByText("Evidence Data"));
    await waitFor(() => {
      expect(
        screen.queryByText(/MSME Credit Twin/i),
      ).not.toBeInTheDocument();
      expect(screen.getByText("GST Filings (GSTR-3B)")).toBeInTheDocument();
      expect(screen.getByText("Primary Bank Account Transactions")).toBeInTheDocument();
    });

    // Click Reconciliation
    fireEvent.click(screen.getByText("Reconciliation"));
    await waitFor(() => {
      expect(screen.getByText("Deterministic Reconciliation Checks")).toBeInTheDocument();
    });

    // Click Assessment History
    fireEvent.click(screen.getByText("Assessment History"));
    await waitFor(() => {
      expect(screen.getByText("No assessment history found.")).toBeInTheDocument();
    });
  });
});
