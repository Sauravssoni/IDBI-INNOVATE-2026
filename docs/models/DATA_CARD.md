# Data Card: MSME Synthetic Datasets

## Dataset Overview
- **Purpose:** Prototype evaluation for IDBI Innovate 2026 Track 03.
- **Nature:** 100% Synthetic and Deterministic. No real customer PII is used.

## Data Sources Emulated
1. **GSTN:** Monthly declared revenue and tax paid.
2. **Account Aggregator (Bank):** Transaction level credits/debits.
3. **EPFO:** Employee counts and PF remittances.
4. **ERP/Invoices:** Counterparty, amount, status, and settlement dates.

## Bias & Limitations
Synthetic data assumes logical economic behavior (e.g., higher revenue implies higher bank credits). It does not perfectly capture real-world noise, off-book transactions, or black-swan economic shocks.
