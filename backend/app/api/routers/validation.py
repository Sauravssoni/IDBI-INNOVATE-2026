from fastapi import APIRouter
from typing import Dict, Any
from app.validation.invariant_checker import run_validation_suite

router = APIRouter(prefix="/api/validation", tags=["validation"])


@router.get("/run")
def run_invariants() -> Dict[str, Any]:
    """
    Executes a 1,000-case deterministic synthetic run (seed 20260713).
    Evaluates exact canonical invariants via independent challenger logic.
    """
    return run_validation_suite()
