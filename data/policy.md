# LowTrans AML/KYT Triage Policy v1.0

**Jurisdiction:** default  
**Version:** v1.0  
**Scope:** Combined retail + crypto demo policy (fallback when no tenant selected)

## Auto-Clear Criteria (LOW risk)
- KYT risk score < 35
- Travel Rule payload complete and beneficiary matches
- Wallet age > 90 days with no prior flags
- Amount < $10,000 USD equivalent
- No sanctions, PEP, or mixer exposure
- Counterparty not on internal blocklist

## Review Criteria (MEDIUM risk)
- KYT score 35–65
- Travel Rule incomplete but amount < $5,000
- New wallet (< 30 days) with moderate transaction history
- Single weak signal (e.g., high-risk jurisdiction IP only)

## Escalate Criteria (HIGH risk)
- KYT score > 65
- Sanctions or PEP match (any confidence)
- Mixer, tumbler, or darknet market exposure
- Travel Rule missing for transfers > $3,000
- Structuring pattern: multiple sub-threshold transfers within 24h
- Counterparty linked to known fraud cluster

## Crypto-Specific Rules
- BTC/ETH transfers to flagged CEX withdrawal clusters → REVIEW minimum
- DeFi bridge hops > 3 in 1 hour → ESCALATE
- Stablecoin off-ramp > $25,000 without enhanced DD → ESCALATE

## Disposition Actions
- **auto_clear**: Document rationale, close alert, no SAR
- **analyst_review**: Queue for L1 within 4h SLA
- **escalate_edd**: Enhanced due diligence + SAR consideration
- **block_transaction**: Freeze pending compliance sign-off
