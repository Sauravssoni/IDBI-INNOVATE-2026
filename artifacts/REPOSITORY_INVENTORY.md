# Repository Inventory

## Executable Scripts
- `scripts/all_tests.sh` (retain): The canonical test runner.
- `backend/scripts/run_decision_assurance.py` (rewrite): Proof test script for data and domain logic assurance.
- `backend/scripts/run_demo_walkthrough.py` (rewrite/retain): End-to-end executable walkthrough.
- `generate_docs.py` (delete): Unused auto-generator not tied to Makefile.

## Seeders
- `backend/app/seed/run_demo_reset.py` (retain): Main reset script.
- `backend/app/seed/run_evaluations.py` (retain): Pre-evaluates advanced states.
- `backend/app/seed/seed_shakti.py` (retain): Personas seeder.
- `backend/app/seed/seed_navprerna.py` (retain): Personas seeder.
- `backend/app/seed/seed_rangrez.py` (retain): Personas seeder.
- `backend/app/seed/seed_aarohan.py` (retain): Personas seeder.

## Generated Artifacts
- `artifacts/FINAL_EVIDENCE_REPORT.md` (retain): Current summary report.
- `artifacts/decision_assurance.json` (rewrite): Required output of assurance test.
- `artifacts/demo_walkthrough.json` (rewrite): Required output of walkthrough.
- `artifacts/walkthrough.json` (delete): Deprecated output of previous walkthrough.

## Documentation Files
- `README.md` (rewrite): Needs full rewrite for evaluator guidelines.
- `docs/DECISION_ASSURANCE.md` (rewrite): Will be populated dynamically by the assurance script.
- `docs/THREAT_MODEL.md` (retain): Requested in repo professionalism guidelines.
- `docs/ARCHITECTURE.md` (retain): Requested in repo professionalism guidelines (Note: currently in `docs/architecture/SYSTEM_ARCHITECTURE.md`, need to rename/move).
- `docs/EVALUATOR_GUIDE.md` (retain/create): Need to check if exists, otherwise create.
- Various files in `docs/` (delete): Most boilerplates will be deleted to ensure professionalism as per user's "Review and retain only useful documentation".

## Root-Level Files
- `Makefile` (rewrite): Requires rewrite for demo-up, demo-down, etc.
- `docker-compose.yml` (retain): Core infrastructure.
- `test.db` (delete): Extraneous DB.

