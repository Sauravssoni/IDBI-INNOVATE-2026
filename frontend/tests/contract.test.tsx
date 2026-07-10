import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import CaseEvaluationPage from '../app/cases/[caseId]/page';
import { BankerShell } from '../components/BankerShell';

// Mock Next.js Link and navigation
vi.mock('next/link', () => ({
  default: ({ children, href }: any) => <a href={href}>{children}</a>,
}));
const mockUseParams = vi.fn().mockReturnValue({ caseId: 'CASE-001' });
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

describe('Frontend Contract Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('backend allowed_actions=false overrides role', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'usr-1', full_name: 'Analyst', role: 'CREDIT_ANALYST' },
    });
    mockApiFetch.mockResolvedValue({
      status: 200,
      data: {
        id: 'CASE-001',
        business_name: 'Test Business',
        allowed_actions: { run_assessment: { allowed: false, blocked_reason_code: "ACTION_NOT_ALLOWED", message: "Not allowed" }, submit_analyst_recommendation: { allowed: false, blocked_reason_code: "ACTION_NOT_ALLOWED", message: "Not allowed" } }
      },
    });

    render(<CaseEvaluationPage />);

    await waitFor(() => {
      expect(screen.getByText(/Not allowed|Read-Only Workspace Access/i)).toBeInTheDocument();
      expect(screen.queryByText('Run Assessment Engine')).not.toBeInTheDocument();
    });
  });

  it('unassigned Analyst sees no mutations', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'usr-1', full_name: 'Analyst', role: 'CREDIT_ANALYST' },
    });
    mockApiFetch.mockResolvedValue({
      status: 200,
      data: {
        id: 'CASE-001',
        business_name: 'Test Business',
        allowed_actions: { run_assessment: { allowed: false, blocked_reason_code: "ACTION_NOT_ALLOWED", message: "Not allowed" }, submit_analyst_recommendation: { allowed: false, blocked_reason_code: "ACTION_NOT_ALLOWED", message: "Not allowed" }, record_human_decision: { allowed: false, blocked_reason_code: "ACTION_NOT_ALLOWED", message: "Not allowed" } }
      },
    });

    render(<CaseEvaluationPage />);

    await waitFor(() => {
      expect(screen.getByText(/Not allowed|Read-Only Workspace Access/i)).toBeInTheDocument();
      expect(screen.queryByText('Run Assessment Engine')).not.toBeInTheDocument();
    });
  });

  it('SA sees only human decision controls', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'usr-1', full_name: 'SA', role: 'SANCTIONING_AUTHORITY' },
    });
    mockApiFetch.mockResolvedValue({
      status: 200,
      data: {
        id: 'CASE-001',
        business_name: 'Test Business',
        allowed_actions: { record_human_decision: { allowed: true, allowed_human_actions: ["APPROVE_AS_REQUESTED","APPROVE_ALTERNATIVE_STRUCTURE","DEFER_FOR_EVIDENCE","ESCALATE_FOR_DUE_DILIGENCE","DECLINE_AFTER_HUMAN_REVIEW"] } }
      },
    });

    render(<CaseEvaluationPage />);

    await waitFor(() => {
      expect(screen.getByText('Sanctioning Authority Gate')).toBeInTheDocument();
      expect(screen.queryByText('Credit Analyst Workflows')).not.toBeInTheDocument();
      expect(screen.queryByText('Run Assessment Engine')).not.toBeInTheDocument();
    });
  });

  it('Auditor/Risk Admin see no mutations', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'usr-1', full_name: 'Auditor', role: 'AUDITOR' },
    });
    mockApiFetch.mockResolvedValue({
      status: 200,
      data: {
        id: 'CASE-001',
        business_name: 'Test Business',
        allowed_actions: { run_assessment: { allowed: false, blocked_reason_code: "ACTION_NOT_ALLOWED", message: "Not allowed" }, submit_analyst_recommendation: { allowed: false, blocked_reason_code: "ACTION_NOT_ALLOWED", message: "Not allowed" }, record_human_decision: { allowed: false, blocked_reason_code: "ACTION_NOT_ALLOWED", message: "Not allowed" } }
      },
    });

    const { unmount } = render(<CaseEvaluationPage />);

    await waitFor(() => {
      expect(screen.getByText(/Not allowed|Read-Only Workspace Access/i)).toBeInTheDocument();
      expect(screen.queryByText('Run Assessment Engine')).not.toBeInTheDocument();
    });
    unmount();

    mockUseAuth.mockReturnValue({
      user: { id: 'usr-1', full_name: 'Risk', role: 'RISK_ADMIN' },
    });
    render(<CaseEvaluationPage />);

    await waitFor(() => {
      expect(screen.getByText(/Not allowed|Read-Only Workspace Access/i)).toBeInTheDocument();
    });
  });

  it('System Admin sees no case nav or borrower content', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'usr-1', full_name: 'Admin', role: 'SYSTEM_ADMIN' },
    });
    
    render(<CaseEvaluationPage />);

    await waitFor(() => {
      expect(screen.getByText('Access Restricted')).toBeInTheDocument();
      expect(screen.getByText(/System Administrators do not have access to case workspace content/i)).toBeInTheDocument();
    });
  });

  it('/cases/random-value never resolves to Shakti', async () => {
    // If not found, the code tries to list and find shakti only if target is "shakti".
    // For random-value, it should not resolve.
    mockUseParams.mockReturnValue({ caseId: 'random-value' });
    
    mockUseAuth.mockReturnValue({
      user: { id: 'usr-1', full_name: 'Analyst', role: 'CREDIT_ANALYST' },
    });
    // First call returns 404
    mockApiFetch.mockImplementation(async (url: string) => {
      if (url === '/api/cases/random-value') return { status: 404, data: null };
      if (url === '/api/cases/') return { status: 200, data: [] }; // no cases
      return { status: 404, data: null };
    });

    render(<CaseEvaluationPage />);

    await waitFor(() => {
      expect(screen.getByText('Case Access Error')).toBeInTheDocument();
      expect(screen.getByText('Case not found in current scope.')).toBeInTheDocument();
    });
  });

  it('analyst JSON sends RECOMMEND_ALTERNATIVE_STRUCTURE for Shakti (CONDITIONAL_OFFER fallback)', async () => {
    mockUseParams.mockReturnValue({ caseId: 'CASE-001' });
    mockUseAuth.mockReturnValue({
      user: { id: 'usr-1', full_name: 'Analyst', role: 'CREDIT_ANALYST' },
    });
    
    mockApiFetch.mockImplementation(async (url: string, opts?: RequestInit) => {
      if (opts?.method === 'POST') {
        if (url.includes('evaluate')) {
          return { status: 200, data: { decision: { decision: 'CONDITIONAL_OFFER', binding_limit: 100000 } } };
        }
        if (url.includes('analyst-recommendation')) {
          return { status: 200, data: {} };
        }
      }
      return {
        status: 200,
        data: {
          id: 'CASE-001',
          business_name: 'Shakti',
          version: 1,
          allowed_actions: { run_assessment: { allowed: true }, submit_analyst_recommendation: { allowed: true, suggested_analyst_action: "RECOMMEND_ALTERNATIVE_STRUCTURE" } }
        }
      };
    });

    render(<CaseEvaluationPage />);

    await waitFor(() => {
      expect(screen.getByText('Run Assessment Engine')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Run Assessment Engine'));

    await waitFor(() => {
      expect(screen.getByText(/AI-assisted credit assessment completed successfully/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Submit:/i));

    await waitFor(() => {
      const calls = mockApiFetch.mock.calls;
      const recCall = calls.find(c => c[0].includes('analyst-recommendation') && c[1]?.method === 'POST');
      expect(recCall).toBeDefined();
      const body = JSON.parse(recCall![1].body);
      expect(body.recommendation).toBe('RECOMMEND_ALTERNATIVE_STRUCTURE');
    });
  });

  it('all 5 human decision option values canonical', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'usr-1', full_name: 'SA', role: 'SANCTIONING_AUTHORITY' },
    });
    mockApiFetch.mockResolvedValue({
      status: 200,
      data: {
        id: 'CASE-001',
        business_name: 'Test Business',
        requested_amount: 1000,
        allowed_actions: { record_human_decision: { allowed: true, allowed_human_actions: ["APPROVE_AS_REQUESTED","APPROVE_ALTERNATIVE_STRUCTURE","DEFER_FOR_EVIDENCE","ESCALATE_FOR_DUE_DILIGENCE","DECLINE_AFTER_HUMAN_REVIEW"] } }
      },
    });

    render(<CaseEvaluationPage />);

    await waitFor(() => {
      const select = screen.getByRole('combobox');
      expect(select).toBeInTheDocument();
      
      const options = Array.from(select.querySelectorAll('option')).map(o => o.value);
      expect(options).toEqual([
        'APPROVE_AS_REQUESTED',
        'APPROVE_ALTERNATIVE_STRUCTURE',
        'DEFER_FOR_EVIDENCE',
        'ESCALATE_FOR_DUE_DILIGENCE',
        'DECLINE_AFTER_HUMAN_REVIEW'
      ]);
    });
  });

  it('no composite score text rendered', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'usr-1', full_name: 'Analyst', role: 'CREDIT_ANALYST' },
    });
    mockApiFetch.mockResolvedValue({
      status: 200,
      data: {
        id: 'CASE-001',
        business_name: 'Test Business',
        allowed_actions: { run_assessment: { allowed: true } }
      },
    });

    render(<CaseEvaluationPage />);

    await waitFor(() => {
      expect(screen.queryByText(/total_score/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Band/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/\/ 900/)).not.toBeInTheDocument();
      expect(screen.queryByText(/out of 900/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Credit Score/)).not.toBeInTheDocument();
    });
  });

  it('RM nav excludes Audit/Policy', () => {
    mockUsePathname.mockReturnValue('/');
    mockUseAuth.mockReturnValue({ user: { id: 'usr-2', full_name: 'RM User', role: 'RELATIONSHIP_MANAGER' } });
    render(<BankerShell><div>child</div></BankerShell>);
    
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Case Inventory')).toBeInTheDocument();
    expect(screen.queryByText('Policy & Risk Engine')).not.toBeInTheDocument();
    expect(screen.queryByText('Audit Log & CAS Trail')).not.toBeInTheDocument();
  });

  it('Analyst/SA nav matches agreed matrix', () => {
    mockUsePathname.mockReturnValue('/');
    
    mockUseAuth.mockReturnValue({ user: { id: 'usr-1', full_name: 'Analyst', role: 'CREDIT_ANALYST' } });
    const { unmount } = render(<BankerShell><div>child</div></BankerShell>);
    expect(screen.getByText('Policy & Risk Engine')).toBeInTheDocument();
    expect(screen.queryByText('Audit Log & CAS Trail')).not.toBeInTheDocument();
    unmount();

    mockUseAuth.mockReturnValue({ user: { id: 'usr-3', full_name: 'SA', role: 'SANCTIONING_AUTHORITY' } });
    render(<BankerShell><div>child</div></BankerShell>);
    expect(screen.getByText('Policy & Risk Engine')).toBeInTheDocument();
    expect(screen.queryByText('Audit Log & CAS Trail')).not.toBeInTheDocument();
  });
});

