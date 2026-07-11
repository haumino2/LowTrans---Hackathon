# Clario AML/KYT Policy — Vietnam Retail v1.1

**Jurisdiction:** vn-retail  
**Version:** v1.1  
**Scope:** Payroll, e-wallet, remittance, and SME merchant rails (fiat)

## Auto-Clear Criteria (LOW risk)
- KYT / risk score < 30
- Amount below retail CTR band (< VND 300M / ~USD 12,000 equivalent) with clean history
- Product in payroll or e-wallet top-up with KYC tier ≥ basic
- No sanctions, PEP, or corridor-risk flags
- Account age > 90 days and prior alerts = 0 (or prior CLEAR only)

## Review Criteria (MEDIUM risk)
- Remittance corridor or incomplete SOF / KYC for amount ≥ USD 3,000
- Sub-threshold structuring pattern across e-wallet / remittance within 24h
- New account (< 30 days) with elevated velocity
- Travel-rule analogue incomplete on cross-border remittance

## Escalate Criteria (HIGH risk)
- Sanctions or PEP hit (any confidence)
- High-value remittance (≥ USD 7,000) with incomplete verification on higher-risk corridor
- Suspected mule / account takeover on e-wallet
- CTR/threshold evasion (smurfing) across related customers

## Retail-Specific Rules
- **Payroll:** Salary credits matching employer pattern → prefer FAST-TRACK CLEAR
- **E-wallet:** Top-ups < USD 500, aged account → auto-CLEAR lane
- **Remittance:** Cross-border corridors with incomplete docs → REVIEW minimum; ≥ USD 10,000 → ESCALATE
- **Merchant (SME):** Settlement payouts with full KYB → CLEAR unless adverse media / sanctions

## Disposition Actions
- **auto_clear**: Document rationale, close alert, no STR
- **analyst_review**: Queue for L1 within 4h SLA (HITL if confidence < 70%)
- **escalate_edd**: Enhanced DD + STR consideration
- **block_transaction**: Freeze pending compliance sign-off
