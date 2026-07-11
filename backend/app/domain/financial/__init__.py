"""
Financial domain engines for Vyapar Pulse.
Consolidates canonical capacity calculations, reducing-balance amortization,
and institutional debt-service coverage ratio (DSCR) definitions.
"""

from app.domain.financial.engine import FinancialCapacityEngine

__all__ = ["FinancialCapacityEngine"]
