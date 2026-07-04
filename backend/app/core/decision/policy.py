from typing import Dict, Any, List
from decimal import Decimal, ROUND_HALF_UP
from app.core.decision.limits import SafeLimitEngine
from app.db.orm.cases import SystemRecommendation

class DecisionPolicy:
    """
    Applies banking policy rules to computed scores and features
    to generate deterministic decisions and safe limits.
    """
    
    def __init__(self, features: Dict[str, Any], scores: Dict[str, Any], requested_amount: Decimal, requested_product: str):
        self.features = features
        self.scores = scores
        self.requested_amount = requested_amount
        self.requested_product = requested_product
        
    def evaluate(self) -> Dict[str, Any]:
        # 1. Base Checks (Precedence)
        consent_status = self.features.get("consent_status", "VALID")
        if consent_status != "VALID":
            return {
                "decision": "BLOCK_PROCESSING",
                "reasons": ["Invalid, revoked or expired consent"],
                "offers": [],
                "binding_limit": Decimal("0")
            }
            
        integrity_flag = self.features.get("integrity_flag", False)
        if integrity_flag:
            return {
                "decision": SystemRecommendation.ENHANCED_DUE_DILIGENCE.value,
                "reasons": ["Material integrity/fraud flag detected"],
                "offers": [],
                "binding_limit": Decimal("0")
            }
            
        evidence_confidence = Decimal(str(self.scores.get("evidence_confidence_score", 0)))
        decision_threshold = Decimal("40.0")
        if evidence_confidence < decision_threshold:
            return {
                "decision": SystemRecommendation.ADDITIONAL_EVIDENCE_REQUIRED.value,
                "reasons": ["Evidence confidence below configured decision threshold"],
                "offers": [],
                "binding_limit": Decimal("0")
            }
            
        # 2. Capacity & Limits Calculation
        applicable_limits = SafeLimitEngine.calculate_all_limits(self.features)
        
        if not applicable_limits:
            return {
                "decision": SystemRecommendation.DECLINE_RECOMMENDED.value,
                "reasons": ["Financial capacity inadequate and no currently viable alternative"],
                "offers": [],
                "binding_limit": Decimal("0")
            }
            
        # The binding limit for the case is the minimum of all applicable limits to be safe
        binding_limit = min(limit["calculated_limit"] for limit in applicable_limits)
        
        # Determine the product-specific limit if applicable, otherwise use binding limit
        product_limit = binding_limit
        for limit in applicable_limits:
            # Map requested_product to method if possible, here simplified
            if "WORKING_CAPITAL" in self.requested_product.upper() and limit["method"] == "WORKING_CAPITAL_LINE":
                product_limit = limit["calculated_limit"]
        
        # 3. Offer Generation
        offers = self._generate_offers(product_limit, self.requested_product)
        
        # 4. Final Recommendation Precedence
        # Rule 5: Requested structure unsupported but viable alternatives exist
        if self.requested_amount > product_limit:
            decision = SystemRecommendation.CONDITIONAL_OFFER.value
            reasons = [f"Requested amount ({self.requested_amount}) exceeds supportable limit ({product_limit}). Offering alternatives."]
        # Rule 6: Requested structure supportable with sufficient evidence
        else:
            decision = SystemRecommendation.READY_FOR_REVIEW.value
            reasons = [f"Requested structure supportable."]
            
        return {
            "decision": decision,
            "reasons": reasons,
            "offers": offers,
            "binding_limit": product_limit,
            "limit_details": applicable_limits
        }

    def _generate_offers(self, binding_limit: Decimal, product_type: str) -> List[Dict[str, Any]]:
        offers = []
        
        # CONSERVATIVE
        conservative_amount = (binding_limit * Decimal("0.6")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        offers.append({
            "tier": "CONSERVATIVE",
            "currency": "INR",
            "amount": str(conservative_amount),
            "product_type": product_type,
            "tenure_months": 12,
            "repayment_frequency": "MONTHLY",
            "estimated_repayment": str((conservative_amount / Decimal("12")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "base_dscr": "1.8",
            "stressed_dscr": "1.4",
            "liquidity_impact": "LOW",
            "applicable_capacity_ceilings": [str(binding_limit)],
            "binding_ceiling": str(binding_limit),
            "conditions": ["Quarterly GST submission"],
            "evidence_references": [],
            "policy_version": "1.0",
            "calculation_version": "1.0",
            "human_review_required": True
        })
        
        # BALANCED
        balanced_amount = (binding_limit * Decimal("0.8")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        offers.append({
            "tier": "BALANCED",
            "currency": "INR",
            "amount": str(balanced_amount),
            "product_type": product_type,
            "tenure_months": 24,
            "repayment_frequency": "MONTHLY",
            "estimated_repayment": str((balanced_amount / Decimal("24")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "base_dscr": "1.5",
            "stressed_dscr": "1.2",
            "liquidity_impact": "MEDIUM",
            "applicable_capacity_ceilings": [str(binding_limit)],
            "binding_ceiling": str(binding_limit),
            "conditions": ["Monthly AA sync", "Quarterly GST submission"],
            "evidence_references": [],
            "policy_version": "1.0",
            "calculation_version": "1.0",
            "human_review_required": True
        })
        
        # GROWTH
        growth_amount = binding_limit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        offers.append({
            "tier": "GROWTH",
            "currency": "INR",
            "amount": str(growth_amount),
            "product_type": product_type,
            "tenure_months": 36,
            "repayment_frequency": "MONTHLY",
            "estimated_repayment": str((growth_amount / Decimal("36")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "base_dscr": "1.2",
            "stressed_dscr": "1.0",
            "liquidity_impact": "HIGH",
            "applicable_capacity_ceilings": [str(binding_limit)],
            "binding_ceiling": str(binding_limit),
            "conditions": ["Monthly AA sync", "Monthly GST submission", "Escrow routing required"],
            "evidence_references": [],
            "policy_version": "1.0",
            "calculation_version": "1.0",
            "human_review_required": True
        })
        
        return offers
