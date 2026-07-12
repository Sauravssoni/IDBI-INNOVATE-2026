export interface DecisionPackageReconciliation {
  reconciliation_quality?: number | null;
  evidence_confidence?: number | null;
  source_coverage?: number | null;
}

export interface DecisionPackageAuditItem {
  event_type: string;
  actor: string;
  event_hash: string;
  created_at: string;
}

export interface ProductOffer {
  amount: number;
  product_type: string;
  interest_rate_pct: number;
  tenure_months: number;
  estimated_repayment: number;
  post_loan_dscr: number;
  covenants: string[];
  collateral_structure: string;
}

export interface LimitDetail {
  product: string;
  requested: number;
  max_capacity: number;
  binding_limit: number;
  is_applicable: boolean;
  reason_codes: string[];
}

export interface EvidencePassportRailCoverage {
  gst: boolean;
  account_aggregator: boolean;
  invoices: boolean;
  epfo: boolean;
  cibil: boolean;
}

export interface EvidencePassportFreshnessScores {
  gst: number;
  bank: number;
  invoices: number;
}

export interface EvidencePassportFreshnessDepth {
  months_of_history: number;
  gst_periods: number;
  bank_transactions: number;
  invoice_records: number;
  employment_periods: number;
  freshness_scores: EvidencePassportFreshnessScores;
  composite_freshness_index: number;
}

export interface EvidencePassportObligationVerification {
  state: string;
  cibil_monthly_emi: number;
  observed_monthly_debt_service: number;
}

export interface EvidencePassportContradictionAnalysis {
  severity: string;
  reconciliation_ratio: number;
  gst_declared_revenue: number;
  bank_buyer_receipts: number;
}

export interface EvidencePassport {
  case_id: string;
  business_id: string;
  consent_status: string;
  consent_scope: string;
  rail_coverage: EvidencePassportRailCoverage;
  freshness_depth: EvidencePassportFreshnessDepth;
  obligation_verification: EvidencePassportObligationVerification;
  contradiction_analysis: EvidencePassportContradictionAnalysis;
  assessment_certainty: string;
  authoritative_evidence_ids: string[];
  generated_at: string;
  evidence_tier?: string;
  tier_description?: string;
}

export interface PeerContext {
  peer_sample_size?: number;
  median_dscr?: number;
  median_margin?: number;
}

export interface FinancialHealthBreakdown {
  score: number;
  max_score: number;
  status: string;
  observed_inputs: string[];
  missing_inputs: string[];
  positive_reason_codes: string[];
  adverse_reason_codes: string[];
  evidence_ids: string[];
}

export interface AuditVerification {
  audit_chain_valid: boolean;
  analyst_event_status: string;
  human_decision_event_status: string;
  package_hash_valid: boolean;
  authorization_scope_valid: boolean;
  package_hash: string;
  audit_tip_hash: string;
  verified_at: string;
  verification_version: string;
  reason?: string;
}

export interface BankabilityIntervention {
  changed_input: string;
  observed_baseline: number;
  simulated_target: number;
  assumption: string;
  before_fhi?: number | null;
  after_fhi?: number | null;
  before_credit_score?: number | null;
  after_credit_score?: number | null;
  before_certainty?: string | null;
  after_certainty?: string | null;
  before_post_loan_dscr?: number | null;
  after_post_loan_dscr?: number | null;
  before_supportable_amount?: number | null;
  after_supportable_amount?: number | null;
  before_policy_result?: string | null;
  after_policy_result?: string | null;
  impact_status?: string | null;
}

export interface BankabilityPath {
  target_amount?: number;
  target_dscr?: number;
  interventions: BankabilityIntervention[];
  feasibility: string;
}

export interface DecisionPackageResponse {
  case_id: string;
  business_name: string;
  requested_amount: number;
  requested_product?: string | null;
  reconciliation: DecisionPackageReconciliation;
  dscr?: number | null;
  post_loan_dscr?: number | null;
  binding_limit?: number | null;
  recommendation?: string | null;
  reason_codes: string[];
  conditions: string[];
  offers?: ProductOffer[] | null;
  limit_details?: LimitDetail[] | null;
  evidence_passport?: EvidencePassport | null;
  assessment_certainty?: string | null;
  certainty_reasons?: string[] | null;
  peer_context?: PeerContext | null;
  hindi_summary?: Record<string, any> | null;
  policy_version: string;
  calculation_version: string;
  scoring_version?: string | null;
  financial_health_index?: number | string | null;
  vyapar_credit_health_score?: number | null;
    fhi_breakdown?: Record<string, FinancialHealthBreakdown> | null;
  credit_score_disclaimer?: string | null;
  calculation_evidence_ids?: Record<string, string[]> | null;
  analyst_action?: string | null;
  human_action?: string | null;
  case_version: number;
  audit_chain: DecisionPackageAuditItem[];
  bankability_path?: BankabilityPath | null;
  assessment?: AssessmentResultResponse | null;
}

export interface ScenarioResult {
  scenario_id: string;
  name: string;
  description: string;
  recomputed_dscr: number;
  recomputed_limit: number;
  status: string;
  policy_rule_id: string;
  transition_explanation: string;
}

export interface StressResult {
  overall_stress_status: string;
  base_dscr: number;
  base_binding_limit: number;
  scenarios: ScenarioResult[];
  stressed: {
    dscr: number;
    max_loan_amount: number;
    status: string;
  };
}

export interface FinancialHealthPillarResponse {
  name: string;
  score: number;
  health_status: string;
}

export interface BindingConstraintResponse {
  constraint_type: string;
  reason: string;
}

export interface AssessmentResultResponse {
  current_dscr?: number | null;
  proposed_debt_service?: number | null;
  post_loan_dscr?: number | null;
  stressed_dscr?: number | null;
  supportable_amount?: number | null;
  binding_constraint?: BindingConstraintResponse | null;
  six_pillars?: FinancialHealthPillarResponse[] | null;
  stress_results?: any[] | null;
}
