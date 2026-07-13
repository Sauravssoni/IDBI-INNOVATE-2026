import re

# Patch responses.py
with open("backend/app/schemas/responses.py", "r") as f:
    content = f.read()

new_schemas = """
class ApplicantViewOffer(BaseModel):
    product_type: str
    amount: Decimal
    interest_rate_pct: float
    tenure_months: int

class ApplicantViewHindiSummary(BaseModel):
    decision_label: str
    reason_explanation: str
    bankability_path_actions: List[str]

class ApplicantViewResponse(BaseModel):
    id: str
    business_name: str
    requested_amount: Optional[float] = None
    requested_product: str
    status: str
    vyapar_credit_health_score: Optional[int] = None
    binding_limit: Optional[Decimal] = None
    recommendation: Optional[str] = None
    hindi_summary: Optional[ApplicantViewHindiSummary] = None
    offers: Optional[List[ApplicantViewOffer]] = None

"""

if "class ApplicantViewResponse" not in content:
    with open("backend/app/schemas/responses.py", "w") as f:
        f.write(content + "\n" + new_schemas)

# Patch cases.py
with open("backend/app/api/routers/cases.py", "r") as f:
    cases_content = f.read()

if "ApplicantViewResponse" not in cases_content:
    cases_content = cases_content.replace(
        "from app.schemas.responses import (",
        "from app.schemas.responses import (\n    ApplicantViewResponse,"
    )

new_applicant_view = """@router.get("/{case_id}/applicant-view", response_model=ApplicantViewResponse)
def get_applicant_view(
    case_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = can_view_case(db, user, case_id)
    
    from app.services.assessment_service import AssessmentService
    service = AssessmentService(db)
    snapshot = service.get_latest_assessment(str(case_id))
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="No assessment snapshot found for applicant view")
        
    assessment = snapshot.canonical_assessment_json
    
    hindi_rec_map = {
        "CONDITIONAL_OFFER": "सशर्त प्रस्ताव (Conditional Offer)",
        "DECLINE_RECOMMENDED": "अस्वीकृति अनुशंसित (Decline Recommended)",
        "APPROVE": "स्वीकृत (Approved)",
        "ADDITIONAL_EVIDENCE_REQUIRED": "अतिरिक्त साक्ष्य की आवश्यकता (Additional Evidence Required)",
    }
    
    rec_str = case.recommendation or assessment.get("policy_recommendation", "")
    
    hindi_summary = {
        "decision_label": hindi_rec_map.get(str(rec_str), "समीक्षा के लिए तैयार (Ready for Review)"),
        "reason_explanation": "आवेदक का ऋण सेवा अनुपात (DSCR) और वित्तीय साक्ष्य अनुशंसित कार्यशील पूंजी सीमा की पुष्टि करते हैं।"
        if str(rec_str) in ["CONDITIONAL_OFFER", "APPROVE"]
        else "वित्तीय साक्ष्य और नकदी प्रवाह वर्तमान ऋण आवेदन का समर्थन करने में असमर्थ हैं।",
        "bankability_path_actions": [
            f"{m.get('intervention_type', '')}: {m.get('description', '')}"
            for m in assessment.get("bankability_interventions", [])
        ]
    }
    
    offers = []
    for cap in assessment.get("product_capacities", []):
        offers.append({
            "product_type": cap.get("product_name", ""),
            "amount": cap.get("capacity", 0),
            "interest_rate_pct": 11.5,
            "tenure_months": 36,
        })
        
    return {
        "id": str(case.id),
        "business_name": case.business.legal_name if case.business else "Applicant",
        "requested_amount": float(case.requested_amount) if case.requested_amount else None,
        "requested_product": case.requested_product.value if hasattr(case.requested_product, 'value') else str(case.requested_product),
        "status": case.status.value if hasattr(case.status, 'value') else str(case.status),
        "vyapar_credit_health_score": assessment.get("vyapar_credit_health_score"),
        "binding_limit": assessment.get("supportable_amount"),
        "recommendation": str(rec_str) if rec_str else None,
        "hindi_summary": hindi_summary,
        "offers": offers,
    }"""

cases_content = re.sub(
    r'@router\.get\("/{case_id}/applicant-view"\).*?def get_applicant_view.*?return {.*?}',
    new_applicant_view,
    cases_content,
    flags=re.DOTALL
)

with open("backend/app/api/routers/cases.py", "w") as f:
    f.write(cases_content)

