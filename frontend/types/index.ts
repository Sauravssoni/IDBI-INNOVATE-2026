export interface CaseResponse {
  id: string;
  business_id_fk: string;
  product_type: string;
  requested_amount: number;
  status: string;
  version: number;
  recommendation?: string;
  analyst_recommendation?: string;
  human_decision?: string;
  dscr?: number;
  created_at: string;
  updated_at: string;
}

export interface CreditTwinResponse {
  dscr: number;
  recommendation: string;
  binding_limit: number | null;
  policy_version?: string;
  confidence_score?: number;
}

export interface RecommendationResponse {
  decision: string;
  reason: string;
  expected_version: number;
}

export interface HumanDecisionResponse {
  decision: string;
  reason: string;
  approved_amount: number;
  expected_version: number;
}
