from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
import hashlib
import secrets
from alembic.config import Config
from alembic.script import ScriptDirectory
from app.api.routers import cases, audit, evidence, demo, stress, bankability
from app.api import auth
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.core.versions import (
    API_SERVICE_NAME,
    API_VERSION,
    SCHEMA_VERSION,
    POLICY_VERSION,
    CALCULATION_VERSION,
    SCORING_VERSION,
    PASSPORT_ENGINE_VERSION,
    FEATURE_SCHEMA_VERSION,
    PACKAGE_SCHEMA_VERSION,
    AUDIT_HASH_VERSION,
)


app = FastAPI(
    title="VYAPAR PULSE AI API",
    version=API_VERSION,
    description="Evidence-First Financial Health Card and Credit-Twin for MSMEs.",
    redirect_slashes=False,
)


try:
    settings = get_settings()
except Exception as e:
    raise RuntimeError(f"Startup configuration error: {e}") from e

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        if request.url.path.startswith(
            "/api/auth/login"
        ) or request.url.path.startswith("/api/auth/demo/session"):
            return await call_next(request)

        csrf_header = request.headers.get("x-csrf-token")
        session_cookie = request.cookies.get("vyapar_session_token")

        if not csrf_header or not session_cookie:
            return JSONResponse(
                status_code=403, content={"detail": "CSRF token missing"}
            )

        from app.db.session import SessionLocal
        from app.db.orm.users import SessionStore

        db = SessionLocal()
        try:
            session_hash = hashlib.sha256(session_cookie.encode("utf-8")).hexdigest()
            db_session = (
                db.query(SessionStore)
                .filter(SessionStore.session_token == session_hash)
                .first()
            )
            if not db_session:
                return JSONResponse(
                    status_code=403, content={"detail": "Invalid session"}
                )

            expected_csrf_hash = db_session.csrf_token_hash
            if not expected_csrf_hash:
                return JSONResponse(
                    status_code=403, content={"detail": "CSRF token missing on session"}
                )

            actual_csrf_hash = hashlib.sha256(csrf_header.encode("utf-8")).hexdigest()

            if not secrets.compare_digest(expected_csrf_hash, actual_csrf_hash):
                return JSONResponse(
                    status_code=403, content={"detail": "CSRF token invalid"}
                )

        finally:
            db.close()

    return await call_next(request)


app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(audit.router)
app.include_router(evidence.router)
app.include_router(demo.router)
app.include_router(stress.router)
app.include_router(bankability.router)
app.include_router(bankability.simulation_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": API_SERVICE_NAME, "version": API_VERSION}


@app.get("/ready")
def ready() -> dict:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        current_revision = db.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
        alembic_cfg = Config("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)
        heads = script.get_heads()
        if len(heads) != 1:
            raise RuntimeError(f"Expected one Alembic head, found {heads}")
        if current_revision != heads[0]:
            raise RuntimeError(
                f"Database migration head mismatch: current={current_revision}, expected={heads[0]}"
            )
        required_versions = {
            "schema_version": SCHEMA_VERSION,
            "policy_version": POLICY_VERSION,
            "calculation_version": CALCULATION_VERSION,
            "scoring_version": SCORING_VERSION,
            "evidence_passport_version": PASSPORT_ENGINE_VERSION,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "audit_hash_version": AUDIT_HASH_VERSION,
        }
        missing_versions = [
            key for key, value in required_versions.items() if not value
        ]
        if missing_versions:
            raise RuntimeError(f"Version registry incomplete: {missing_versions}")
        seed_count = db.execute(
            text(
                "SELECT count(*) FROM businesss WHERE business_id IN "
                "('SHAKTI_PRECISION_001', 'NAVPRERNA_TRADERS_001', 'RANGREZ_TEXTILES_001', 'NIRMAAN_WORKS_001')"
            )
        ).scalar()
        demo_seed_ready = int(seed_count or 0) >= 1
        if settings.DEMO_ACCESS_ENABLED and not demo_seed_ready:
            raise RuntimeError("Demo access is enabled but demo seed is incomplete")
        return {
            "status": "ready",
            "database": "connected",
            "migration_head": current_revision,
            "demo_seed_ready": demo_seed_ready,
            "service": API_SERVICE_NAME,
            "version": API_VERSION,
            "schema_version": SCHEMA_VERSION,
        }
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "reason": "Database connection or schema failed",
            },
        )
    finally:
        db.close()
