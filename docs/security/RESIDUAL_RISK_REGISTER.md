# Residual Risk Register

## Overview
This document tracks identified security risks that remain after the implementation of Phase 1.1 controls, acknowledging the current prototype constraints and roadmap for remediation in subsequent phases.

## 1. Prototype Infrastructure Limitations

| Risk ID | Description | Severity | Mitigation in Prototype | Target Phase for Full Remediation |
|---------|-------------|----------|-------------------------|-----------------------------------|
| RSK-001 | No TLS termination on localhost Docker Compose setup. | Low (Dev Only) | Bound strictly to loopback interface. Not deployed to public IP. | Pre-Production / Phase 7 |
| RSK-002 | Mock JWT secrets and default local configuration (`.env` fallbacks). | Medium | Environment templates strictly enforce `.env.example`. Test keys are deterministic and well-known, not used in any actual banking network. | Pre-Production / Phase 7 |
| RSK-003 | Hardcoded mock passwords in seeding script (`seed_shakti.py`). | Low | Suppressed in Bandit (`# nosec B105`). Database is transient and local-only. | N/A (By Design for prototype eval) |

## 2. Business Logic / Application Level

| Risk ID | Description | Severity | Mitigation in Prototype | Target Phase for Full Remediation |
|---------|-------------|----------|-------------------------|-----------------------------------|
| RSK-004 | Lack of 2FA/MFA for Banker Console logins. | Medium | Current authentication relies on strong passwords and simulated SSO headers. RBAC strictly enforced post-login. | Phase 3 (Auth Extension) |
| RSK-005 | No automated DAST pipeline implemented yet. | Medium | Heavy SAST, strict linting, and manual validation. | Phase 8 (Final Hardening) |
| RSK-006 | AI context length vulnerability (Denial of Wallet). | Low | Maximum token limits hardcoded in prompt definitions. No untrusted user strings fed directly to agent evaluation block. | Ongoing monitoring |

## 3. GitHub & CI/CD Security

| Risk ID | Description | Severity | Mitigation in Prototype | Target Phase for Full Remediation |
|---------|-------------|----------|-------------------------|-----------------------------------|
| RSK-007 | Missing GitHub Actions execution permissions (startup failure). | High | SAST/Linting runs manually via `make check`. CI configurations are committed but blocked by org/repo policy. | Immediate Admin Review |
| RSK-008 | Repository is PRIVATE, obstructing Hack2Skill evaluation. | Critical | Evaluators must be manually invited, or repo visibility updated to PUBLIC. | Immediate Admin Review |

## Review Cycle
To be reviewed at the conclusion of Phase 3 and Phase 8.
