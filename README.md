# Explainable Hereditary Cancer Variant Decision-Support Prototype

## Purpose

This hackathon MVP will accept a genetic variant described by a gene and HGVS notation, gather supporting evidence, evaluate a defined subset of ACMG criteria, and produce an explainable classification with an evidence-backed treatment association.

This is a prototype and decision-support tool. It is not a clinical diagnostic system and must not be used to prescribe or select treatment.

## High-Level Architecture

- `frontend/`: Future user interface.
- `backend/api/`: HTTP entry points and API route handlers.
- `backend/services/`: Independently developed integrations and application services.
- `backend/acmg_engine/`: Future ACMG rules and classification components.
- `backend/models/`: Shared data models.
- `backend/utils/`: Shared utilities.
- `backend/config/`: Configuration and environment handling.
- `tests/`: Automated tests.
- `data/`: Local development data and fixtures.

## Current Implementation Status

Step 1 scaffolding is complete. The backend currently exposes only a minimal health check:

```text
GET /health
{"status": "ok"}
```

No variant validation, normalization, external API retrieval, predictor retrieval, ACMG rules, classification, treatment logic, or frontend screens have been implemented.

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

## Disclaimer

This project is an early prototype for research and hackathon development. It is not a clinical diagnostic or treatment-prescribing system. Outputs require review by appropriately qualified professionals and should not replace clinical judgment.
