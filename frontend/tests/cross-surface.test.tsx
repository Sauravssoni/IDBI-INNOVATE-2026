import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import CaseEvaluationPage from '../app/cases/[caseId]/page';

const mockUseParams = vi.fn().mockReturnValue({ caseId: 'CASE-123' });
const mockUsePathname = vi.fn().mockReturnValue('/');
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useParams: () => mockUseParams(),
  usePathname: () => mockUsePathname(),
}));

const mockUseAuth = vi.fn();
vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

const mockApiFetch = vi.fn();
vi.mock('../lib/api', () => ({
  apiFetch: (...args: any[]) => mockApiFetch(...args),
}));

describe('Cross-Surface Consistency', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders consistent data across summary and decision package for a real case', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'usr-1', full_name: 'Analyst', role: 'CREDIT_ANALYST' },
    });

    // Mock the main case data which includes the decision package nested inside or loaded similarly.
    const mockCase = {
      id: 'CASE-123',
      business_name: 'Stark Industries',
      requested_amount: 10000000,
      total_score: 820,
      evaluated_at: new Date().toISOString(),
      evaluation_result: {
        decision: {
          recommendation: 'APPROVE',
          binding_limit: 8500000,
        }
      },
      decision: {
        decision: 'APPROVE',
        binding_limit: 8500000,
      },
      offers: [
        {
          product_type: 'TERM_LOAN',
          amount: 8500000,
          interest_rate_pct: 12.0,
          tenure_months: 60,
        }
      ],
      evidence_passport: {
        case_id: 'CASE-100',
        business_id: 'B-100',
        consent_status: 'VALID',
        consent_scope: 'ALL',
        rail_coverage: { gst: true, account_aggregator: true, invoices: true, epfo: true, cibil: true },
        freshness_depth: {
          months_of_history: 12, gst_periods: 12, bank_transactions: 100, invoice_records: 50, employment_periods: 12,
          freshness_scores: { gst: 100, bank: 100, invoices: 100 },
          composite_freshness_index: 95
        },
        obligation_verification: { state: 'VERIFIED_MATCH', cibil_monthly_emi: 5000, observed_monthly_debt_service: 5000 },
        contradiction_analysis: { severity: 'LOW', reconciliation_ratio: 1.0, gst_declared_revenue: 100000, bank_buyer_receipts: 100000 },
        assessment_certainty: 'HIGH_CERTAINTY',
        authoritative_evidence_ids: ['e1'],
        generated_at: '2023-01-01'
      },
      allowed_actions: { run_assessment: { allowed: false } }
    };

    mockApiFetch.mockImplementation(async (url: string) => {
      if (url.includes('verify-audit')) {
        return { status: 200, data: { audit_chain_valid: true, bola_verification_status: 'VERIFIED' } };
      }
      return { status: 200, data: mockCase };
    });

    render(<CaseEvaluationPage />);

    await waitFor(() => {
      // 1. Executive Card / Header should show Stark Industries
      expect(screen.getByText('Stark Industries')).toBeInTheDocument();
    });

    // 2. Switch to Sensitivity Lab Tab (if it's rendered by default or click it)
    // Actually, CaseEvaluationPage usually renders tabs. We don't have click logic here easily without knowing exact text.
    // Assuming Sensitivity Lab is visible or we can click it:
    const dpTab = screen.getByText(/Sensitivity Lab/i);
    dpTab.click();

    await waitFor(() => {
      // Decision Package should show TERM LOAN and the same limit
      expect(screen.getByText('TERM LOAN')).toBeInTheDocument();
      expect(screen.getByText(/85\.00 lakh/i)).toBeInTheDocument(); 
    });
  });
});
