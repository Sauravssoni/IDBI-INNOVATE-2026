import hashlib
import json
from typing import Any, Dict


def calculate_audit_hash(prior_hash: str, payload: Dict[str, Any]) -> str:
    payload_str = json.dumps(payload, sort_keys=True)
    return hashlib.sha256((prior_hash + payload_str).encode("utf-8")).hexdigest()
