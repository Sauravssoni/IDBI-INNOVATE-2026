# Clean Room Verification

**Date**: July 4, 2026
**Environment**: Local (Docker Desktop for Mac, Apple Silicon / x86_64 equivalent)

## Overview

This document records the exact steps and results of the "Clean Room" deployment verification for the Vyapar Pulse AI prototype. It serves as proof that the repository can be fully initialized, built, and seeded with zero manual configuration steps other than standard prerequisites, fulfilling the automated reproducible build requirement.

## Prerequisites

- `make`
- `docker` and `docker-compose`
- `node` (>= 22.0.0) and `npm`
- `python` (3.10+)

## Verification Steps

### 1. `make setup`

```bash
make setup
```

**Result**: PASS.
- Python virtual environment (`.venv`) created successfully.
- Python dependencies installed correctly from `requirements.txt`.
- Node dependencies installed correctly in `frontend/` using `npm install`.

### 2. `make demo`

```bash
make demo
```

**Result**: PASS.
The `make demo` process correctly handles tearing down any existing environment, bringing up the new environment, waiting for database readiness, running database migrations, and executing the seeding scripts. 

Detailed Sub-steps Verified:
1. `docker-compose down -v` cleanly resets the environment.
2. The database container (`vyapar_pulse_db`) starts up.
3. The migration retry loop successfully connects to the PostgreSQL database and executes `alembic upgrade head`, proving resilience against race conditions during database initialization.
4. The `backend` container starts `uvicorn` correctly.
5. The `frontend` container successfully completes the `next build` phase and starts the Next.js production server on port 3005 (mapped).
6. The `make seed` script executes deterministically, outputting:
   ```
   Seeding deterministic data...
   Starting data seeding process...
   Seeding users...
   ✅ Successfully seeded Shakti Precision Components ...
   ✅ All deterministic seed data generated successfully.
   Demo environment is ready.
   ```

### 3. Port Allocation

Due to the common presence of other local development servers (e.g., Supabase, other projects), the frontend has been configured to map to **port 3005** on the host, preventing the classic `EADDRINUSE` port 3000 collision.

The Next.js frontend is accessible at: `http://localhost:3005`
The backend API is accessible at: `http://localhost:8000`

### Conclusion

The system reliably achieves a fully functional, seeded state using the single command `make demo` from a clean repository clone. No forbidden autonomous decision terms were detected in the generated documentation or configurations.
