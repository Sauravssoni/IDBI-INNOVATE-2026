import uuid
from decimal import Decimal


def run_evaluations(db_session=None):
    if db_session is None:
        from app.db.session import SessionLocal

        db = SessionLocal()
    else:
        db = db_session

    from app.db.orm.cases import Case, Business, CaseStatus, AuditEvent
    from app.db.orm.users import User
    from app.core.features.engine import FeatureEngine
    from app.core.scoring.scorer import ScoringEngine
    from app.core.decision.policy import DecisionPolicy
    from app.core.audit import calculate_audit_hash
    from app.db.orm.cases import utc_now
    from fastapi.encoders import jsonable_encoder

    # Find the credit analyst user for the analyst recommendation
    ca_user = db.query(User).filter(User.email == "credit@bank.example").first()
    if not ca_user:
        print("Error: credit@bank.example user not found. Run seeders first.")
        return

    cases = db.query(Case).join(Business).all()
    for case in cases:
        b = case.business

        if b.business_id == "SHAKTI_PRECISION_001":
            print(f"Skipping {b.legal_name} (will be evaluated in demo)")
            continue

        print(f"Evaluating {b.legal_name}...")

        try:
            # 1. Derive Features
            feature_engine = FeatureEngine(db, str(case.business_id_fk))
            features = feature_engine.derive_all_features()

            # 2. Score
            scorer = ScoringEngine(features)
            scores = scorer.compute_all_scores()

            # 3. Decision
            policy = DecisionPolicy(
                features,
                scores,
                Decimal(str(case.requested_amount)),
                case.requested_product.value,
            )
            decision = policy.evaluate()

            result_payload = {
                "case_id": str(case.id),
                "business_name": case.business.legal_name,
                "features": features,
                "scores": scores,
                "decision": decision,
            }

            dscr_val = None
            if (
                "bank_metrics" in features
                and "dscr" in features["bank_metrics"]
                and features["bank_metrics"]["dscr"] is not None
            ):
                dscr_val = Decimal(str(features["bank_metrics"]["dscr"]))

            # Update case
            case.recommendation = decision["decision"]
            case.status = CaseStatus.ASSESSMENT_COMPLETED
            case.dscr = dscr_val
            prior_version = case.version
            case.version += 1
            resulting_version = case.version

            db.flush()

            # Audit event for evaluate
            prev_event = (
                db.query(AuditEvent)
                .filter(AuditEvent.case_id == case.id)
                .order_by(AuditEvent.event_sequence.desc())
                .first()
            )
            prior_hash = (
                prev_event.event_hash
                if prev_event and prev_event.event_hash
                else "GENESIS"
            )
            event_sequence = (
                (prev_event.event_sequence + 1)
                if prev_event and prev_event.event_sequence
                else 1
            )

            metadata_enc = jsonable_encoder(result_payload)
            correlation_id = str(uuid.uuid4())
            now_utc = utc_now()

            hash_payload = {
                "sequence": event_sequence,
                "actor": str(ca_user.id),
                "actor_role": ca_user.role.value,
                "action": "evaluate",
                "rationale": "System Evaluation",
                "correlation_id": correlation_id,
                "prior_version": prior_version,
                "resulting_version": resulting_version,
                "idempotency_record_id": None,
                "model_version": "1.0",
                "policy_version": "1.0",
                "timestamp": now_utc.isoformat(),
                "metadata": metadata_enc,
            }

            event_hash = calculate_audit_hash(prior_hash, hash_payload)

            audit_eval = AuditEvent(
                case_id=case.id,
                event_sequence=event_sequence,
                event_type="evaluate",
                actor=str(ca_user.id),
                actor_role=ca_user.role.value,
                idempotency_record_id=None,
                prior_case_version=prior_version,
                resulting_case_version=resulting_version,
                reason="System Evaluation",
                correlation_id=correlation_id,
                model_version="1.0",
                policy_version="1.0",
                metadata_json=metadata_enc,
                prior_event_hash=prior_hash,
                event_hash=event_hash,
                created_at=now_utc,
            )
            db.add(audit_eval)
            db.flush()

            if b.business_id == "RANGREZ_TEXTILES_001":
                print(f"Submitting analyst recommendation for {b.legal_name}...")

                # Update case
                case.analyst_recommendation = "RECOMMEND_ALTERNATIVE_STRUCTURE"
                case.status = CaseStatus.DECISION_PENDING
                prior_version = case.version
                case.version += 1
                resulting_version = case.version

                db.flush()

                rec_payload = {
                    "status": "success",
                    "recommendation": "RECOMMEND_ALTERNATIVE_STRUCTURE",
                }

                prev_event = (
                    db.query(AuditEvent)
                    .filter(AuditEvent.case_id == case.id)
                    .order_by(AuditEvent.event_sequence.desc())
                    .first()
                )
                prior_hash = (
                    prev_event.event_hash
                    if prev_event and prev_event.event_hash
                    else "GENESIS"
                )
                event_sequence = (
                    (prev_event.event_sequence + 1)
                    if prev_event and prev_event.event_sequence
                    else 1
                )

                metadata_enc = jsonable_encoder(rec_payload)
                correlation_id = str(uuid.uuid4())
                now_utc = utc_now()

                hash_payload = {
                    "sequence": event_sequence,
                    "actor": str(ca_user.id),
                    "actor_role": ca_user.role.value,
                    "action": "analyst_recommendation",
                    "rationale": "Seasonal cash flow requires structured approach.",
                    "correlation_id": correlation_id,
                    "prior_version": prior_version,
                    "resulting_version": resulting_version,
                    "idempotency_record_id": None,
                    "model_version": "1.0",
                    "policy_version": "1.0",
                    "timestamp": now_utc.isoformat(),
                    "metadata": metadata_enc,
                }

                event_hash = calculate_audit_hash(prior_hash, hash_payload)

                audit_rec = AuditEvent(
                    case_id=case.id,
                    event_sequence=event_sequence,
                    event_type="analyst_recommendation",
                    actor=str(ca_user.id),
                    actor_role=ca_user.role.value,
                    idempotency_record_id=None,
                    prior_case_version=prior_version,
                    resulting_case_version=resulting_version,
                    reason="Seasonal cash flow requires structured approach.",
                    correlation_id=correlation_id,
                    model_version="1.0",
                    policy_version="1.0",
                    metadata_json=metadata_enc,
                    prior_event_hash=prior_hash,
                    event_hash=event_hash,
                    created_at=now_utc,
                )
                db.add(audit_rec)
                db.flush()

        except Exception as e:
            print(f"Evaluation failed for {b.legal_name}: {e}")
            raise e

    print("Evaluations complete.")
    if db_session is None:
        db.commit()


if __name__ == "__main__":
    run_evaluations()
