# Security Architecture

## Overview
Vyapar Pulse AI implements a Zero-Trust architecture, separating core banking logic from the web frontend and enforcing strictly bounded, deterministic evaluation constraints.

## Authentication & Authorization
- **Role-Based Access Control (RBAC):** Personas (Credit Analyst, Sanctioning Authority, RM) are isolated at the API level.
- **Data Boundaries:** Users can only access Cases explicitly assigned or within their branch hierarchy.

## Network & Transport
- All inter-service communication over TLS 1.3.
- Database access restricted via strict network policies, using authenticated internal VPC connections.

## Auditability
- **Immutable Log:** Every state change in a Case, every manual override, and every model execution is logged in the `AuditEvent` table.
- **Cryptographic Hashing:** Assessment payloads are hashed (SHA-256) at generation to prevent tampering.
