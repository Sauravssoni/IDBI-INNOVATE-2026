from datetime import datetime, timezone
from hashlib import sha256
from json import dumps
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .engine import CreditEngine
from .models import (
    Assessment,
    AuditEvent,
    BusinessProfile,
    ConsentGrant,
    HumanDecisionRequest,
    ScenarioRequest,
    ScenarioResult,
)
from .sample_data import DEMO_CASES

app = FastAPI(
    title="VYAPAR PULSE AI API",
    version="0.1.0",
    description="Explainable financial-health, resilience and credit-structure engine for New-to-Bank MSMEs.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
engine = CreditEngine()
CONSENTS: dict[str, ConsentGrant] = {}
AUDIT_LOG: dict[str, list[AuditEvent]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def payload_hash(payload: dict) -> str:
    canonical = dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode()).hexdigest()


def append_audit(event: AuditEvent) -> None:
    AUDIT_LOG.setdefault(event.assessment_id, []).append(event)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "vyapar-pulse-api", "model_version": "vp-core-0.1.0"}


@app.get("/api/v1/demo-cases", response_model=list[BusinessProfile])
def demo_cases() -> list[BusinessProfile]:
    return DEMO_CASES


@app.post("/api/v1/consents", response_model=ConsentGrant)
def create_consent(grant: ConsentGrant) -> ConsentGrant:
    CONSENTS[grant.consent_id] = grant
    return grant


@app.get("/api/v1/consents/{consent_id}", response_model=ConsentGrant)
def get_consent(consent_id: str) -> ConsentGrant:
    if consent_id not in CONSENTS:
        raise HTTPException(status_code=404, detail="Consent not found")
    return CONSENTS[consent_id]


@app.post("/api/v1/assess", response_model=Assessment)
def assess(profile: BusinessProfile) -> Assessment:
    result = engine.assess(profile)
    append_audit(
        AuditEvent(
            event_id="evt_" + uuid4().hex[:16],
            assessment_id=result.assessment_id,
            business_id=result.business_id,
            event_type="assessment_created",
            actor="system:vp-core",
            occurred_at=now_iso(),
            model_version=result.model_version,
            payload_hash=payload_hash(result.model_dump()),
        )
    )
    return result


@app.post("/api/v1/simulate", response_model=ScenarioResult)
def simulate(request: ScenarioRequest) -> ScenarioResult:
    return engine.simulate(request)


@app.post("/api/v1/human-decisions", response_model=AuditEvent)
def record_human_decision(request: HumanDecisionRequest) -> AuditEvent:
    event = AuditEvent(
        event_id="evt_" + uuid4().hex[:16],
        assessment_id=request.assessment_id,
        business_id=request.business_id,
        event_type="human_decision_recorded",
        actor=request.actor,
        occurred_at=now_iso(),
        model_version="human-review",
        payload_hash=payload_hash(request.model_dump()),
        reason=f"{request.decision}: {request.reason}",
    )
    append_audit(event)
    return event


@app.get("/api/v1/audit/{assessment_id}", response_model=list[AuditEvent])
def audit_trail(assessment_id: str) -> list[AuditEvent]:
    if assessment_id not in AUDIT_LOG:
        raise HTTPException(status_code=404, detail="Assessment audit trail not found")
    return AUDIT_LOG[assessment_id]
