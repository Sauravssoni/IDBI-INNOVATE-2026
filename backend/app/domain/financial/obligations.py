from decimal import Decimal
from typing import Any, Iterable, Tuple


VERIFIED_OBLIGATIONS = "VERIFIED_OBLIGATIONS"
VERIFIED_ZERO_DEBT = "VERIFIED_ZERO_DEBT"
UNKNOWN_OBLIGATIONS = "UNKNOWN_OBLIGATIONS"

ASSESSABLE_OBLIGATION_STATES = {VERIFIED_OBLIGATIONS, VERIFIED_ZERO_DEBT}


def decimal_or_none(value: Any) -> Decimal | None:
    if value is None or str(value).strip().upper() in {"", "NONE", "UNKNOWN"}:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def normalize_obligation_state(
    explicit_state: Any,
    explicit_existing_ds: Any = None,
    obligations: Iterable[dict[str, Any]] | None = None,
    existing_emi: Any = None,
    debt_service_verified: bool = False,
    verified_zero_debt: bool = False,
) -> Tuple[str, Decimal, list[str]]:
    state = str(explicit_state or "").upper()
    existing_ds = decimal_or_none(explicit_existing_ds)
    obligation_list = list(obligations or [])

    if state in {VERIFIED_OBLIGATIONS, "VERIFIED_MATCH", "VERIFIED_CIBIL_ONLY"}:
        if existing_ds is not None and existing_ds > 0:
            return VERIFIED_OBLIGATIONS, existing_ds, []
        if obligation_list:
            total = sum(
                (
                    decimal_or_none(o.get("monthly_emi")) or Decimal("0.00")
                    for o in obligation_list
                ),
                Decimal("0.00"),
            )
            if total > 0:
                return VERIFIED_OBLIGATIONS, total, []
        emi = decimal_or_none(existing_emi)
        if emi is not None and emi > 0:
            return VERIFIED_OBLIGATIONS, emi, []
        return (
            UNKNOWN_OBLIGATIONS,
            Decimal("0.00"),
            [
                "VERIFIED_OBLIGATIONS requires positive authoritative debt-service amount."
            ],
        )

    if state in {VERIFIED_ZERO_DEBT, "VERIFIED_NO_DEBT"}:
        if verified_zero_debt or existing_ds == Decimal("0.00") or not obligation_list:
            return VERIFIED_ZERO_DEBT, Decimal("0.00"), []
        return (
            UNKNOWN_OBLIGATIONS,
            Decimal("0.00"),
            ["VERIFIED_ZERO_DEBT requires explicit zero-debt evidence."],
        )

    if state == "VERIFIED":
        if existing_ds is not None and existing_ds > 0:
            return VERIFIED_OBLIGATIONS, existing_ds, []
        if verified_zero_debt:
            return VERIFIED_ZERO_DEBT, Decimal("0.00"), []
        return (
            UNKNOWN_OBLIGATIONS,
            Decimal("0.00"),
            [
                "Generic VERIFIED without debt amount or explicit zero-debt evidence is not assessable."
            ],
        )

    if obligation_list:
        total = sum(
            (
                decimal_or_none(o.get("monthly_emi")) or Decimal("0.00")
                for o in obligation_list
            ),
            Decimal("0.00"),
        )
        if total > 0:
            return VERIFIED_OBLIGATIONS, total, []

    emi = decimal_or_none(existing_emi)
    if emi is not None and emi > 0:
        return VERIFIED_OBLIGATIONS, emi, []

    if debt_service_verified:
        bank_ds = decimal_or_none(explicit_existing_ds)
        if bank_ds is not None and bank_ds > 0:
            return VERIFIED_OBLIGATIONS, bank_ds, []

    if verified_zero_debt:
        return VERIFIED_ZERO_DEBT, Decimal("0.00"), []

    return (
        UNKNOWN_OBLIGATIONS,
        Decimal("0.00"),
        [
            "Existing obligations are not verified by bureau, obligation records, observed debt service, or explicit zero-debt evidence."
        ],
    )
