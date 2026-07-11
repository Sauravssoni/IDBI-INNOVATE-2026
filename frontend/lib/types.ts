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

export interface EvidencePassport {
  multi_rail_coverage?: number | null;
  composite_freshness_index?: number | null;
  obligation_verification?: boolean | null;
  contradiction_severity?: string | null;
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
  bola_verification_status: string;
  cas_verification_status: string;
  audit_chain_valid: boolean;
  package_hash: string;
  audit_tip_hash: string;
  verified_at: string;
  verification_version: string;
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

export interface DecisionPackage {
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
  hindi_summary?: any | null;
  policy_version: string;
  calculation_version: string;
  scoring_version?: string | null;
  financial_health_index?: number | null;
  vyapar_credit_health_score?: number | null;
  fhi_breakdown?: Record<string, FinancialHealthBreakdown> | null;
  credit_score_disclaimer?: string | null;
  calculation_evidence_ids?: Record<string, string[]> | null;
  analyst_action?: string | null;
  human_action?: string | null;
  case_version: number;
  audit_chain: DecisionPackageAuditItem[];
  bankability_path?: BankabilityPath | null;
}

export interface StressResult {
  shock_scenario: string;
  interest_rate_shock: number;
  stressed_dscr: number;
  stressed_repayment: number;
  viability: string;
  cushion_percentage: number;
  amortisation_approximation?: boolean;
}
