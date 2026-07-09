export interface CaseListItem {
  id: string;
  business_id: string;
  business_name: string;
  status: string;
  requested_amount: number;
  currency: string;
  created_at: string;
  assigned_analyst: string;
  assigned_rm: string;
  requested_product?: string | null;
  recommendation?: string | null;
  analyst_recommendation?: string | null;
  human_decision?: string | null;
  evaluation_result?: any | null;
}

export interface CaseDetailResponse {
  id: string;
  business_id: string;
  business_name: string;
  status: string;
  requested_amount: number;
  currency: string;
  created_at: string;
  assigned_analyst: string;
  assigned_rm: string;
  industry: string;
  region: string;
  branch: string;
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
  features: Record<string, any>;
  scores: Record<string, any>;
  decision: Record<string, any>;
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
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
}
