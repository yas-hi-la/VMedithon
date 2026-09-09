# Explainable Hereditary Cancer Variant Decision-Support Prototype

## Purpose

This hackathon MVP will accept a genetic variant described by a gene and HGVS notation, gather supporting evidence, evaluate a defined subset of ACMG criteria, and produce an explainable classification with an evidence-backed treatment association.

This is a prototype and decision-support tool. It is not a clinical diagnostic system and must not be used to prescribe or select treatment.

## High-Level Architecture

- `frontend/`: Future user interface.
- `backend/api/`: HTTP entry points and API route handlers.
- `backend/services/`: Independently developed integrations and application services.
- `backend/database/`: SQLite configuration, connections, initialization, schema, and health checks.
- `backend/acmg_engine/`: Future ACMG rules and classification components.
- `backend/models/`: Shared data models.
- `backend/utils/`: Shared utilities.
- `backend/config/`: Configuration and environment handling.
- `tests/`: Automated tests.
- `data/`: Local development data and fixtures.

## Current Implementation Status

Step 2 foundation work is complete. The backend currently exposes only a minimal health check:

```text
GET /health
{"status": "ok"}
```

No variant validation, normalization, external API retrieval, predictor retrieval, ACMG rules, classification, treatment logic, or frontend screens have been implemented.

The backend is organized into configuration (`backend/config/`), HTTP server setup (`backend/api/server.py`), route definitions (`backend/api/routes.py`), request handling (`backend/api/handler.py`), controllers (`backend/api/controllers.py`), services (`backend/services/`), and an HTTP-independent SQLite database layer (`backend/database/`).

Step 4 adds the initial `Variant` domain model. It stores only the required gene and HGVS notation fields; HGVS validation and normalization remain future work. The current SQLite schema version is 2.

## Planned Modules

- Variant input, HGVS validation, and normalization.
- ClinVar and gnomAD evidence services.
- REVEL, CADD, and BayesDel predictor services.
- ACMG rule evaluation and classification.
- Treatment association and explainable report generation.
- Frontend workflow for submitting variants and reviewing evidence.

## Start the Backend

The current backend uses only the Python standard library, so no dependency installation is required.

From the project root:

```bash
python3 -m backend.api.main
```

Then check the endpoint in another terminal:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status": "ok"}
```

To configure the listening address or port, export `BACKEND_HOST` and `BACKEND_PORT`. `.env.example` lists placeholders for future integrations; it contains no real credentials or secrets.

### Database Setup

The database layer uses Python's built-in `sqlite3` module, so no dependency installation is required. `DB_PATH` controls the SQLite file location and defaults to `data/app.db`.

Initialize the local database explicitly:

```bash
python3 -m backend.database.initialize
```

The initialization command is safe to run repeatedly. Check database connectivity and query execution with:

```bash
python3 -m backend.database.health
```

Initialization upgrades a Step 3 database from schema version 1 to version 2 without deleting existing data. Fresh databases are initialized directly to version 2. No HTTP endpoint depends on database initialization or domain data.

The database tests use isolated temporary SQLite files:

```bash
python3 -m unittest tests.test_database
```

Model and repository tests use isolated temporary SQLite files as well:

```bash
python3 -m unittest tests.test_variant_repository
```

Run the backend checks with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

The tests cover the health response and the basic not-found error response. The application does not load `.env` files automatically; configuration is read from the process environment.

## Disclaimer

This project is an early prototype for research and hackathon development. It is not a clinical diagnostic or treatment-prescribing system. Outputs require review by appropriately qualified professionals and should not replace clinical judgment.
