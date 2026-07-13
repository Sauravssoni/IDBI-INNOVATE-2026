export interface CaseListItem {
  id: string;
  business_id: string;
  business_name?: string; // Keep optional if needed, but remove if strict
  status: string;
  requested_amount: number;
  currency: string;
  created_at: string;
  requested_product?: string | null;
  recommendation?: string | null;
  analyst_recommendation?: string | null;
  human_decision?: string | null;
}

export interface CaseBusinessResponse {
  id: string;
  business_id: string;
  legal_name: string;
  sector: string;
}

export interface AssessmentActionContext {
  allowed: boolean;
  blocked_reason_code: string | null;
  message: string | null;
}

export interface AnalystActionContext {
  allowed: boolean;
  suggested_analyst_action: string | null;
  blocked_reason_code: string | null;
  message: string | null;
}

export interface HumanActionContext {
  allowed: boolean;
  suggested_human_action: string | null;
  allowed_human_actions: string[] | null;
  blocked_reason_code: string | null;
  message: string | null;
}

export interface AllowedActionsResponse {
  run_assessment: AssessmentActionContext;
  submit_analyst_recommendation: AnalystActionContext;
  record_human_decision: HumanActionContext;
  view_audit: boolean;
}

export interface CaseDetailResponse {
  id: string;
  business_id_fk: string;
  business: CaseBusinessResponse;
  requested_amount: number;
  requested_product?: string | null;
  currency: string;
  status: string;
  recommendation?: string | null;
  analyst_recommendation?: string | null;
  human_decision?: string | null;
  evaluation_result?: EvaluationResultResponse | null;
  allowed_actions: AllowedActionsResponse;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface EvaluateResponseDecision {
  decision?: string | null;
  recommendation?: string | null;
  binding_limit?: number | null;
  reason_codes?: string[] | null;
}

export interface EvaluateResponseFeatures {
  total_revenue?: number | null;
  total_obligations?: number | null;
  dscr?: number | null;
  reconciliation_metrics?: Record<string, unknown> | null;
  gst_metrics?: Record<string, unknown> | null;
  bank_metrics?: Record<string, unknown> | null;
}

export interface EvaluateResponseScores {
  evidence_confidence?: number | null;
  reconciliation_quality?: number | null;
}

export interface EvaluationResultResponse {
  decision?: EvaluateResponseDecision | null;
  features?: EvaluateResponseFeatures | null;
  scores?: EvaluateResponseScores | null;
}

export interface AssessmentHistoryItem {
  id: string;
  sequence: number;
  event_type: string;
  actor: string;
  actor_role: string;
  reason: string;
  created_at: string;
  recommendation: string;
  binding_limit: number | null;
  dscr: number | null;
  policy_version: string;
  calculation_version: string;
}

export interface PortfolioAuditItem {
  id: string;
  case_id: string;
  event_type: string;
  actor: string;
  created_at: string;
  event_hash: string;
}

export interface CreditTwinResponse {
  case_id: string;
  business_id: string;
  dscr: number | null;
  calculation_version: string;
  total_annual_revenue: number;
  binding_limit: number | null;
  recommendation: string | null;
  source_coverage: number | null;
  evidence_confidence: number | null;
  reconciliation_quality: number | null;
  evaluated_at: string | null;
  policy_version?: string;
}

export interface EvidenceMetadata {
  ingestion_mode: string | null;
  source_environment: string | null;
  source_system: string | null;
  consent_id: string | null;
  data_connection_id: string | null;
  evidence_as_of: string | null;
  received_at: string | null;
  data_quality_status: string | null;
}

export interface GSTEvidence {
  period: string;
  declared_revenue: number;
  tax_paid: number;
  status: string;
  metadata: EvidenceMetadata;
}

export interface BankEvidence {
  date: string;
  amount: number;
  type: string;
  category: string;
  metadata: EvidenceMetadata;
}

export interface InvoiceEvidence {
  id: string;
  date: string;
  amount: number;
  status: string;
  counterparty: string;
  metadata: EvidenceMetadata;
}

export interface EmploymentEvidence {
  period: string;
  employee_count: number;
  pf_remittance: number;
  metadata: EvidenceMetadata;
}

export interface ObligationEvidence {
  id: string;
  lender: string;
  facility_type: string | null;
  monthly_emi: number;
  outstanding_balance: number;
  metadata: EvidenceMetadata;
}

export interface ReconciliationCheck {
  check_id: string;
  name: string;
  status: string;
  observed_value?: number;
  reference_value?: number;
  variance_amount?: number;
  variance_percentage?: number;
  evidence_references?: string[];
  explanation?: string;
  rule_version?: string;
}

export interface EvaluateResponse {
  case_id: string;
  business_name: string;
  features: {
    total_revenue?: number;
    total_obligations?: number;
    dscr?: number;
  };
  scores: {
    evidence_confidence?: number;
    reconciliation_quality?: number;
  };
  decision: {
    recommendation?: string;
    binding_limit?: number;
    reason_codes?: string[];
  };
}

export interface HumanDecisionResponse {
  status: string;
  decision: string;
}

export interface AnalystRecommendationResponse {
  status: string;
  recommendation: string;
}

export interface ReconciliationResponse {
  total_bank_credits: number;
  total_gst_sales: number;
  reconciliation_match_percent: number;
  status: string;
  checks: ReconciliationCheck[];
}

export interface DashboardSummaryResponse {
  active_cases: number;
  total_requested_amount: number;
  awaiting_analyst: number;
  awaiting_human_decision: number;
  approved_cases: number;
  approved_amount: number;
  declined_cases: number;
  deferred_cases: number;
  completed_human_reviews: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
}

export interface DecisionPackageResponse {
  case_id: string;
  business_name: string;
  requested_amount: number;
  requested_product: string | null;
  reconciliation: {
    reconciliation_quality: number | null;
    evidence_confidence: number | null;
    source_coverage: number | null;
  };
  dscr: number | null;
  binding_limit: number | null;
  recommendation: string | null;
  reason_codes: string[];
  conditions: string[];
  policy_version: string;
  calculation_version: string;
  analyst_action: string | null;
  human_action: string | null;
  case_version: number;
  audit_chain: {
    event_type: string;
    actor: string;
    event_hash: string;
    created_at: string;
  }[];
  [key: string]: unknown; // Removed 'any' bypass
}

export interface VerificationResult {
  valid: boolean;
  expected_hash: string;
  actual_hash: string;
  package_id: string;
}

export interface ReplayResult {
  status: string;
  differences: string[];
  replayed_decision: string;
  package_hash_verified: boolean;
  mismatch_fields: string[];
}

export interface StressResponse {
  baseline_limit: number;
  overall_stress_status?: string;
  scenarios: {
    scenario_id: string;
    scenario_name?: string;
    name?: string;
    stressed_limit: number;
    description: string;
    impact?: string;
    status?: string;
    recomputed_dscr?: number;
    reverse_stress_details?: Record<string, string>;
  }[];
}

export interface HumanContext {
  [key: string]: unknown; // Replaced 'any'
}
