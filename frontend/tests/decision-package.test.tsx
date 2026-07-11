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
      case_id: 'CASE-001',
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
        multi_rail_coverage: 100,
        composite_freshness_index: 95,
        obligation_verification: true,
        contradiction_severity: 'LOW',
        assessment_certainty: 'HIGH'
      }
    } as any;

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
      expect(screen.getByText(/50\.00 lakh/i)).toBeInTheDocument(); 
      expect(screen.getByText('12.5% p.a. / 36M')).toBeInTheDocument();
      expect(screen.getByText('1.45')).toBeInTheDocument();
    });
  });

  it('renders zero offer as Not Applicable', async () => {
    const mockData: DecisionPackageResponse = {
      case_id: 'CASE-001',
      offers: [
        {
          product_type: 'OVERDRAFT',
          amount: 0,
          interest_rate_pct: 14.0,
          tenure_months: 12,
        }
      ],
      evidence_passport: {
        case_id: 'CASE-001'
      }
    } as any;

    mockApiFetch.mockImplementation(async (url: string) => {
      if (url.includes('decision-package')) return { status: 200, data: mockData };
      if (url.includes('stress-lab')) return { status: 200, data: { single_factor_results: {} } };
      return { status: 404, data: null };
    });

    render(<DecisionPackageTab caseId="CASE-001" />);

    await waitFor(() => {
      expect(screen.getByText('OVERDRAFT')).toBeInTheDocument();
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
