# Add to types.ts
cat << 'TYPE_EOF' >> frontend/lib/types.ts

export interface ApplicantViewResponse {
  id: string;
  business_name: string;
  requested_amount?: number;
  requested_product: string;
  status: string;
  vyapar_credit_health_score?: number;
  binding_limit?: number;
  recommendation?: string;
  hindi_summary?: {
    decision_label: string;
    reason_explanation: string;
    bankability_path_actions: string[];
  };
  offers?: {
    product_type: string;
    amount: number;
    interest_rate_pct: number;
    tenure_months: number;
  }[];
}
TYPE_EOF

# Update page.tsx
sed -i '' 's/DecisionPackageResponse/ApplicantViewResponse/g' frontend/app/applicant/\[caseId\]/page.tsx

