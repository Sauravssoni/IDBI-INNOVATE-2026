import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import DecisionPackageTab from '../app/cases/[caseId]/tabs/DecisionPackageTab';
import type { DecisionPackageResponse } from '../lib/types';

const mockApiFetch = vi.fn();
vi.mock('../lib/api', () => ({
  apiFetch: (...args: any[]) => mockApiFetch(...args),
}));

describe('DecisionPackageTab UI & Contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders non-zero offer amount correctly', async () => {
    const mockData: DecisionPackageResponse = {
      package_id: 'PKG-001',
      case_id: 'CASE-001',
      business_name: 'Test Business',
      requested_amount: 5000000,
      requested_product: 'TERM_LOAN',
      reconciliation: {
        reconciliation_quality: 95,
        evidence_confidence: 90,
        source_coverage: 80,
      },
      dscr: 1.8,
      post_loan_dscr: 1.45,
      binding_limit: 5000000,
      recommendation: 'CONDITIONAL_OFFER',
      reason_codes: [],
      conditions: [],
      offers: [
        {
          product_type: 'TERM_LOAN',
          amount: 5000000,
          interest_rate_pct: 12.5,
          tenure_months: 36,
          estimated_repayment: 167000,
          post_loan_dscr: 1.45,
          covenants: [],
          collateral_structure: 'Unsecured'
        }
      ],
      evidence_passport: {
        case_id: 'CASE-001',
        business_id: 'BUS-001',
        consent_status: 'VALID',
        consent_scope: 'ALL',
        rail_coverage: { gst: true, account_aggregator: true, invoices: false, epfo: false, cibil: true },
        freshness_depth: {
          months_of_history: 12, gst_periods: 12, bank_transactions: 100, invoice_records: 0, employment_periods: 0,
          freshness_scores: { gst: 100, bank: 90, invoices: 0 },
          composite_freshness_index: 95
        },
        obligation_verification: { state: 'VERIFIED_MATCH', cibil_monthly_emi: 5000, observed_monthly_debt_service: 5000 },
        contradiction_analysis: { severity: 'LOW', reconciliation_ratio: 1.0, gst_declared_revenue: 100000, bank_buyer_receipts: 100000 },
        assessment_certainty: 'HIGH_CERTAINTY',
        authoritative_evidence_ids: ['ev-001'],
        generated_at: '2023-01-01T00:00:00Z'
      },
      policy_version: '2.0-CANONICAL',
      calculation_version: '2.0-CANONICAL',
      scoring_version: '3.0-EVIDENCE-CONDITIONED-FHI',
      case_version: 1,
      audit_chain: []
    };

    mockApiFetch.mockImplementation(async (url: string) => {
      if (url.includes('decision-package')) {
        return { status: 200, data: mockData };
      }
      if (url.includes('stress-lab')) {
        return { status: 200, data: { single_factor_results: {} } };
      }
      return { status: 404, data: null };
    });

    render(<DecisionPackageTab caseId="CASE-001" />);

    await waitFor(() => {
      // 5000000 -> ₹50.00 lakh formatting typically
      expect(screen.getByText('TERM LOAN')).toBeInTheDocument();
      expect(screen.getAllByText(/50\.00 lakh/i).length).toBeGreaterThan(0);
      expect(screen.getByText('12.5% p.a. / 36M')).toBeInTheDocument();
      expect(screen.getAllByText('1.45').length).toBeGreaterThan(0);
    });
  });

  it('renders zero offer as Not Applicable', async () => {
    const mockData: DecisionPackageResponse = {
      package_id: 'PKG-002',
      case_id: 'CASE-001',
      business_name: 'Test Business',
      requested_amount: 5000000,
      requested_product: 'OVERDRAFT',
      reconciliation: {
        reconciliation_quality: 95,
        evidence_confidence: 90,
        source_coverage: 80,
      },
      dscr: 1.8,
      post_loan_dscr: 0,
      binding_limit: 0,
      recommendation: 'ADDITIONAL_EVIDENCE_REQUIRED',
      reason_codes: [],
      conditions: [],
      offers: [
        {
          product_type: 'OVERDRAFT',
          amount: 0,
          interest_rate_pct: 14.0,
          tenure_months: 12,
          estimated_repayment: 0,
          post_loan_dscr: 0,
          covenants: [],
          collateral_structure: 'None'
        }
      ],
      evidence_passport: {
        case_id: 'CASE-001',
        business_id: 'BUS-001',
        consent_status: 'VALID',
        consent_scope: 'ALL',
        rail_coverage: { gst: true, account_aggregator: true, invoices: false, epfo: false, cibil: true },
        freshness_depth: {
          months_of_history: 12, gst_periods: 12, bank_transactions: 100, invoice_records: 0, employment_periods: 0,
          freshness_scores: { gst: 100, bank: 90, invoices: 0 },
          composite_freshness_index: 95
        },
        obligation_verification: { state: 'VERIFIED_MATCH', cibil_monthly_emi: 5000, observed_monthly_debt_service: 5000 },
        contradiction_analysis: { severity: 'LOW', reconciliation_ratio: 1.0, gst_declared_revenue: 100000, bank_buyer_receipts: 100000 },
        assessment_certainty: 'HIGH_CERTAINTY',
        authoritative_evidence_ids: ['ev-001'],
        generated_at: '2023-01-01T00:00:00Z'
      },
      policy_version: '2.0-CANONICAL',
      calculation_version: '2.0-CANONICAL',
      scoring_version: '3.0-EVIDENCE-CONDITIONED-FHI',
      case_version: 1,
      audit_chain: []
    };

    mockApiFetch.mockImplementation(async (url: string) => {
      if (url.includes('decision-package')) return { status: 200, data: mockData };
      if (url.includes('stress-lab')) return { status: 200, data: { single_factor_results: {} } };
      return { status: 404, data: null };
    });

    render(<DecisionPackageTab caseId="CASE-001" />);

    await waitFor(() => {
      expect(screen.getAllByText('OVERDRAFT').length).toBeGreaterThan(0);
      expect(screen.getByText('Not Applicable')).toBeInTheDocument();
      expect(screen.getByText(/Product cap or cash-flow headroom constraints preclude non-zero limit assignment./i)).toBeInTheDocument();
    });
  });

  it('shows contract error when amount and product_type are missing', async () => {
    const mockData = {
      case_id: 'CASE-001',
      offers: [
        {
          // Missing product_type and amount
          interest_rate_pct: 10,
        }
      ]
    };

    mockApiFetch.mockImplementation(async (url: string) => {
      if (url.includes('decision-package')) return { status: 200, data: mockData };
      if (url.includes('stress-lab')) return { status: 200, data: { single_factor_results: {} } };
      return { status: 404, data: null };
    });

    render(<DecisionPackageTab caseId="CASE-001" />);

    await waitFor(() => {
      expect(screen.getByText('Invalid Offer Contract')).toBeInTheDocument();
    });
  });
});
