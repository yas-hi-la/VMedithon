# Variant-to-Verdict

**An explainable decision-support system that classifies uncertain cancer gene variants and uses a machine learning model to rank candidate drugs.**

> From an unreadable genetic test result → to a transparent, evidence-backed treatment lead.

---

## The Problem

Genetic testing for hereditary cancer risk (BRCA1, BRCA2, ATM, Lynch syndrome genes, etc.) often returns a result no one can act on: a **Variant of Uncertain Significance (VUS)**. Clinical guidelines explicitly state a VUS should not be used in clinical decision-making — so the patient and their doctor are left waiting, sometimes for years, exactly when they need an answer most.

- **Over 2 million** variants sit in ClinVar today, and **41%** are Uncertain Significance or Conflicting.
- Re-reviewing just BRCA1/2 VUS reclassified **11%** of variants — directly changing care for **6.8%** of families.
- Even the best existing classification tools (InterVar, Franklin, VarSome) only match expert-panel classification **65–94%** of the time, and they disagree most on exactly the borderline cases that matter.
- **The real gap:** none of the existing tools go beyond a label. Even a confirmed pathogenic result requires a separate, manual step to connect it to an actual treatment. Nothing carries a patient from *uncertainty* to *action*.

## Target Users

- Genetic counselors & clinical geneticists
- Oncologists & treating physicians
- Diagnostic lab technicians / molecular pathology labs
- Precision oncology researchers
- Ultimately: patients and families carrying hereditary cancer risk

## Our Solution

Variant-to-Verdict ingests a patient's variant (a raw FASTA sequence or an HGVS/rsID call) and pulls structured evidence via the **ClinVar E-utilities API**, **gnomAD's GraphQL API**, and **Ensembl VEP** (for REVEL, CADD, and BayesDel scores in one batched call). This evidence is passed into a **deterministic rule engine** that encodes the ACMG/AMP evidence codes (BA1, BS1, PM2, PP3, BP4) as explicit threshold logic — not a learned model — so every classification is a traceable if/then decision, not an inferred probability. A **PubMed E-utilities** query in parallel flags any variant with existing published functional data.

For variants still Uncertain after the rule engine, we query **GDSC (Genomics of Drug Sensitivity in Cancer)** for cell lines carrying the same or a structurally similar variant, and compare their drug-response profile (IC50/AUC) against the profile of cell lines with ClinGen-confirmed pathogenic mutations in the same gene, using a simple distance/similarity metric. This output is stored and displayed as a separate, sample-size-labeled field — architecturally isolated from the classification output so it structurally cannot overwrite a verdict.

Once a variant clears the rule engine as Pathogenic or Likely Pathogenic, its mutation profile is fed into a **supervised ML model (gradient-boosted trees, e.g. XGBoost/LightGBM)** trained on GDSC's mutation-profile-to-drug-response dataset, which outputs a ranked list of candidate drugs by predicted sensitivity. Feature importance for each prediction is computed with **SHAP**, so the ranking ships with a breakdown of which mutation features drove it — not just a ranked list.

## Why This, Not Something Else Already Out There

Automated ACMG classification already exists (InterVar, Franklin, AutoGVP, AAVC) — we're not claiming to have invented that. What's missing from all of them is: (1) a transparent, single-gene triage view instead of an opaque final label, (2) an explicit, sample-size-aware exploratory signal for the hardest cases, held clearly separate from real evidence, and (3) a treatment-ranking step that actually closes the loop to an existing drug. We built the parts that were missing, on top of a category the field already trusts.

## System Architecture

```
Patient Gene Sequence / Variant
            │
            ▼
┌───────────────────────┐
│ 1. Input               │  FASTA sequence or HGVS/rsID variant
└───────────────────────┘
            │
            ▼
┌───────────────────────┐
│ 2. Mutation Detection  │  Align to reference, call base + amino-acid change
└───────────────────────┘
            │
            ▼
┌───────────────────────┐
│ 3. Classification      │  ClinVar + gnomAD + REVEL/CADD/BayesDel
│    (ACMG rule engine)  │  → Benign · Likely Benign · VUS · Likely Path. · Pathogenic
└───────────────────────┘
            │
      ┌─────┴─────┐
      │ Uncertain? │
      └─────┬─────┘
            ▼
┌───────────────────────┐
│ 4. Exploratory Signal  │  GDSC drug-response similarity check
│    (NOT diagnostic)    │  Flag only — never changes classification
└───────────────────────┘
            │
      Pathogenic / Likely Pathogenic
            ▼
┌───────────────────────┐
│ 5. ML Drug Ranking     │  Model trained on GDSC drug-response data
│                        │  ranks candidate drugs by predicted sensitivity
└───────────────────────┘
            │
            ▼
   Clinician-Facing Report
   (verdict + full evidence trail + ranked drugs)
```

## Core Features

| Feature | Description |
|---|---|
| **Automated Variant Classification** | Pulls ClinVar, gnomAD, and REVEL/CADD/BayesDel scores automatically; applies rule-based ACMG evidence codes (BA1, BS1, PM2, PP3, BP4); outputs a standard 5-tier label with full supporting evidence shown. |
| **Exploratory Functional Signal** | Cross-checks GDSC cell-line drug-response patterns for still-uncertain variants, clearly labeled as a hypothesis-generating flag, never a diagnostic input. |
| **ML-Based Drug Ranking** | A model trained on cancer cell-line drug-response data ranks candidate drugs by predicted sensitivity for a confirmed pathogenic mutation. |
| **Evidence-Transparent Report** | One clinician-facing output — variant, classification with evidence, and ranked drugs — designed to be reviewed, not blindly trusted. |
| **Built-In Validation Check** | Any exploratory signal is benchmarked against known-answer variants (ClinGen expert panel calls) before being trusted on real uncertain cases. |

## Explainability, By Design

Explainability isn't a report bolted on after the fact — it constrains which methods we allow into the pipeline at all:

- **Classification** is rule-based ACMG scoring: every evidence code fired is shown with the exact number that triggered it.
- **Third-party predictors** (REVEL, CADD, BayesDel) are shown alongside the evidence categories they weigh, not just a bare score.
- **The exploratory signal** ships with its own audit trail — which cell lines, how many, and the raw values — and if a trained model is used here, it's restricted to interpretable methods (e.g., logistic regression or SHAP-explained gradient boosting), never an opaque black box.
- **The final report** always pairs a verdict with its evidence trail, so a reviewer can reconstruct our reasoning rather than trust it blindly.

## Scope & Honest Limitations

| In scope | Explicitly out of scope / disclosed |
|---|---|
| One well-studied hereditary cancer gene (BRCA1, BRCA2, or ATM), missense VUS | Multi-gene, genome-wide classification |
| Rule-based ACMG codes computable from public data (BA1, BS1, PM2, PP3, BP4) | Codes requiring clinical/family data we don't have |
| Exploratory GDSC signal, sanity-checked against known-answer variants first | Treating the exploratory signal as diagnostic evidence |
| Two demonstrable gene→drug links with real regulatory backing (BRCA→PARP inhibitors, MMR genes→pembrolizumab), plus ML-ranked candidates | A general-purpose drug engine with no evidentiary backing |
| Decision support for a clinician / genetic counselor to review | Autonomous diagnosis or treatment decisions |

This is a **decision-support tool**, not a diagnostic replacement — final calls remain with a clinician or genetic counselor.

## Tech Stack

| Layer | Tools / Libraries |
|---|---|
| **Backend / API** | Python, FastAPI |
| **Sequence handling** | Biopython (reference alignment, variant calling from FASTA input) |
| **External data retrieval** | ClinVar E-utilities API, gnomAD GraphQL API, Ensembl VEP REST API, PubMed E-utilities API |
| **Rule engine** | Custom Python threshold-based ACMG evidence-code scorer (deterministic, no ML) |
| **ML model (drug ranking)** | XGBoost / LightGBM (gradient-boosted trees), trained on GDSC mutation-profile → drug-response data |
| **Explainability** | SHAP (feature-importance breakdown for every drug ranking) |
| **Data processing** | pandas, NumPy |
| **Caching / storage** | SQLite (cached API pulls, to avoid re-querying on repeat runs) |
| **Frontend / report UI** | Streamlit (interactive dashboard) *or* React + Tailwind (if a custom UI is preferred) |
| **Validation notebooks** | Jupyter, scikit-learn (concordance benchmarking against ClinGen labels) |

## Data Sources

- [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar) — NIH/NCBI variant classification archive
- [gnomAD](https://gnomad.broadinstitute.org) — population allele frequency (Broad Institute)
- [ClinGen](https://clinicalgenome.org) — expert-panel curated gold-standard classifications, used for validation
- REVEL, CADD, BayesDel (via [Ensembl VEP](https://ensembl.org/Tools/VEP) / dbNSFP) — computational pathogenicity predictors
- [GDSC](https://www.cancerrxgene.org) (Genomics of Drug Sensitivity in Cancer) — cell-line mutation and drug-response data
- [PubMed](https://pubmed.ncbi.nlm.nih.gov) — published functional studies and case reports

## Roadmap (Beyond the Hackathon)

- Expand from one gene to the broader hereditary-cancer gene panel
- Formal wet-lab collaboration to validate the exploratory GDSC signal at scale
- Clinician usability testing on the report format

---

*Built as a decision-support tool for clinicians and researchers — every output is designed to be checked, not just trusted.*
