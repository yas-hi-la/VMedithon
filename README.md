# Explainable Hereditary Cancer Variant Decision-Support Prototype

## Purpose

This hackathon MVP will accept a genetic variant described by a gene and HGVS notation, gather supporting evidence, evaluate a defined subset of ACMG criteria, and produce an explainable classification with an evidence-backed treatment association.

This is a prototype and decision-support tool. It is not a clinical diagnostic system and must not be used to prescribe or select treatment.

## High-Level Architecture

- `frontend/`: Future user interface.
- `backend/api/`: HTTP entry points and API route handlers.
- `backend/services/`: Independently developed integrations and application services.
- `backend/services/variant_service/analysis_service.py`: Application use case that orchestrates local deterministic variant analysis.
- `backend/database/`: SQLite configuration, connections, initialization, schema, and health checks.
- `backend/analysis/`: In-memory deterministic analysis types and engine.
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

No variant validation, normalization, external API retrieval, predictor retrieval, treatment logic, or frontend screens have been implemented.

The backend is organized into configuration (`backend/config/`), HTTP server setup (`backend/api/server.py`), route definitions (`backend/api/routes.py`), request handling (`backend/api/handler.py`), controllers (`backend/api/controllers.py`), services (`backend/services/`), and an HTTP-independent SQLite database layer (`backend/database/`).

Step 4 adds the initial `Variant` domain model. It stores only the required gene and HGVS notation fields; HGVS validation and normalization remain future work. The current SQLite schema version is 3.

Step 5 adds an HTTP- and database-independent analysis layer. It accepts an existing `Variant` plus explicitly supplied evidence, preserves evidence provenance and ACMG/AMP criterion traceability, and returns a machine-readable result. The current deterministic behavior reports `insufficient_evidence` when evidence is absent or no combination rule is implemented, and reports `conflicting` when pathogenic and benign evidence are both present. It does not call external sources, infer evidence from gene/HGVS strings, or provide treatment recommendations.

Step 6 adds a deterministic ACMG/AMP-style rule layer inside `backend/analysis/`. It evaluates only explicitly supplied criteria and strengths, preserves criterion-level evaluations, and records satisfied rules and evidence IDs in the decision trace. The supported benign subset includes one stand-alone benign criterion, two strong benign criteria, and one strong plus one supporting benign criterion. Empty, conflicting, and unsupported combinations remain conservative. This is an engineering foundation, not a clinically validated classifier.

Step 7 adds a thin application service at `backend/services/variant_service/analysis_service.py`. Its `run_variant_analysis` entry point accepts an existing `Variant` and explicitly supplied evidence, delegates to the deterministic analysis engine, and returns its `AnalysisResult` unchanged. It does not retrieve evidence, implement scientific rules, access SQLite, or generate clinical recommendations. No HTTP endpoint uses it yet.

Step 8 adds `POST /analysis/variants`, a thin JSON HTTP boundary around the Step 7 application service. Requests supply the variant and evidence explicitly; evidence is not retrieved automatically. Responses include the controlled classification, status, criterion and rule evaluations, evidence IDs, and decision trace. This remains a limited deterministic ACMG/AMP-style engineering foundation, not a clinically validated classifier or medical recommendation system.

Step 9 separates request parsing and domain mapping into `backend/api/analysis_requests.py`. The parser validates request structure and existing enum vocabularies before the controller calls the Step 7 service; it does not perform scientific interpretation or ACMG/AMP rule evaluation.

Step 10 adds SQLite persistence for explicitly submitted evidence in `variant_evidence`, linked to `variants` by foreign key. Evidence rows preserve source provenance, reject duplicate `(variant_id, evidence_id)` pairs, and are inserted through transaction-aware repository/service functions. The analysis engine remains in-memory and database-independent; `POST /analysis/variants` does not persist evidence yet.

## Planned Modules

- Variant input, HGVS validation, and normalization.
- ClinVar and gnomAD evidence services.
- REVEL, CADD, and BayesDel predictor services.
- Expanded ACMG/AMP rule evaluation and classification.
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

Submit an explicitly structured analysis request:

```bash
curl -X POST http://127.0.0.1:8000/analysis/variants \
	-H 'Content-Type: application/json' \
	-d '{"variant":{"gene":"BRCA1","hgvs_notation":"c.5266dupC"},"evidence":[]}'
```

Valid analysis requests return HTTP 200, including when the result is `insufficient_evidence` or `conflicting`. Malformed JSON or structurally invalid input returns HTTP 400. The endpoint does not access the database.

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

Initialization upgrades earlier databases from schema version 1 or 2 to the current version 3 without deleting existing data. Fresh databases are initialized directly to version 3. No HTTP endpoint depends on database initialization or domain data.

The current schema version is 3. Initialization adds the `variant_evidence` table without rewriting existing variants, enables SQLite foreign-key enforcement on each connection, and remains repeatable.

The database tests use isolated temporary SQLite files:

```bash
python3 -m unittest tests.test_database
```

Model and repository tests use isolated temporary SQLite files as well:

```bash
python3 -m unittest tests.test_variant_repository
```

Analysis tests use in-memory domain objects and no external services:

```bash
python3 -m unittest tests.test_analysis
```

Application-service orchestration tests:

```bash
python3 -m unittest tests.test_variant_analysis_service
```

The analysis engine does not retrieve evidence or infer criterion values. Additional ACMG/AMP combinations that are not represented in `backend/analysis/rules.py` are reported as unsupported rather than guessed.

Run the backend checks with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

The tests cover the health response and the basic not-found error response. The application does not load `.env` files automatically; configuration is read from the process environment.

## Disclaimer

This project is an early prototype for research and hackathon development. It is not a clinical diagnostic or treatment-prescribing system. Outputs require review by appropriately qualified professionals and should not replace clinical judgment.
