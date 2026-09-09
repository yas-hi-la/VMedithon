Design and build a polished, futuristic medical genomics web application called **VMedithon**.

The product is a **hereditary cancer variant decision-support interface**. The user enters a gene, an HGVS variant notation, and structured evidence. The application then presents a transparent, explainable variant classification and shows the evidence and ACMG/AMP-style rules considered.

The design should feel like a high-end medical/genomics research product: trustworthy, scientific, modern, precise, and visually impressive enough for a hackathon demo.

## Overall visual direction

Use a dark, sophisticated scientific interface rather than a generic healthcare dashboard.

Visual language:

* deep navy / near-black background
* subtle blue, cyan, and violet accents
* glassmorphism used sparingly
* thin luminous borders
* soft gradients
* subtle grid/noise texture
* clean typography
* generous spacing
* rounded but professional cards
* strong visual hierarchy
* avoid excessive neon or gaming aesthetics
* avoid cartoonish medical imagery
* avoid stock-photo healthcare visuals

The interface should look like a combination of:

* genomic research software
* clinical decision-support software
* modern AI/scientific tooling

## Signature DNA animation

Make a **stylized double-helix DNA animation** the signature visual element of the application.

Place a large, elegant DNA double helix subtly in the background of the main interface.

The DNA should:

* slowly rotate or travel vertically across the screen
* have thin luminous strands
* have small glowing nucleotide/base-pair nodes
* have a subtle cyan-to-violet glow
* move smoothly and continuously
* remain partially transparent so it never interferes with readability
* react subtly to user interaction when possible

Create a visual effect where the DNA helix appears to travel through the application from the landing/input area toward the analysis/result area.

During the **Analyze Variant** action:

1. the DNA animation becomes slightly brighter
2. a small pulse travels along the helix
3. the interface transitions into an analysis/loading state
4. the DNA continues moving while the analysis card is loading
5. once the result appears, the DNA settles back to its normal subtle animation

The animation should feel like **genomic data moving through an analysis pipeline**, not like a decorative screensaver.

Keep animations smooth and performant. Respect reduced-motion accessibility preferences.

## Main page

Create a single primary application page.

### Header

Top navigation/header:

* VMedithon logo/wordmark
* small DNA/genomics-inspired icon
* navigation items such as:

  * Variant Analysis
  * Evidence
  * About
* a small status indicator such as:

  * "Decision Support"
  * "System Ready"

Keep the header minimal.

## Hero / introduction

At the top of the main content:

Large heading:

**Variant Intelligence**

Supporting text:

**Transparent evidence-driven analysis for hereditary cancer variants.**

Add a small scientific visual accent around the heading, incorporating the animated DNA motif.

Do NOT claim that the system provides definitive clinical diagnosis or treatment recommendations.

## Variant input section

Create a prominent card titled:

**Analyze a Variant**

Include:

### Gene

Label: `Gene`

Input placeholder:
`e.g. BRCA1`

### HGVS notation

Label: `HGVS notation`

Input placeholder:
`e.g. c.5266dupC`

Add a subtle helper text:

`Enter the variant using HGVS notation.`

## Evidence section

Inside the same main workflow, create an evidence builder.

Heading:

**Evidence**

Supporting text:

`Add structured evidence used in the analysis.`

Each evidence item should be displayed as a clean card/row containing:

* Evidence ID
* Criterion
* Strength
* Direction
* Source name
* Source reference
* Summary

Use dropdown/select controls for:

* Criterion:

  * PS3
  * PM2
  * PP3
  * BS1
  * BP4

* Strength:

  * supporting
  * moderate
  * strong
  * very_strong
  * stand_alone

* Direction:

  * pathogenic
  * benign

Provide:

**+ Add Evidence**

and allow evidence items to be removed.

Make this interaction extremely easy to use during a live hackathon demo.

## Primary action

Add a large prominent button:

**Analyze Variant**

The button should have a subtle animated glow/hover effect.

When clicked:

* validate the required fields
* show a loading state
* animate the DNA analysis transition
* show an analysis progress indicator
* then display the result

Do not fabricate backend results in the final implementation. The UI should be structured so it can consume the existing backend API.

## Analysis result

Create a visually impressive result card.

Heading:

**Analysis Result**

Show a large classification badge/value such as:

**Likely Pathogenic**

The UI must also support these classifications:

* Pathogenic
* Likely Pathogenic
* Uncertain Significance
* Likely Benign
* Benign
* Conflicting
* Insufficient Evidence

Do not use color alone to communicate classification.

Show additional metadata such as:

* Analysis status
* Variant
* Gene
* Criteria considered

## Explainability / evidence trace

This is one of the most important parts of the UI.

Create an expandable section titled:

**Evidence & Decision Trace**

Display each evidence item in a visual timeline or structured list.

Each item should clearly show:

* criterion
* strength
* direction
* evidence summary
* source
* provenance/reference when available

Below that, create a section:

**Rule Evaluation**

Show:

* rules considered
* satisfied rules
* unsupported rules
* the relationship between evidence and rules

Use connecting lines, small nodes, or a timeline-like visualization to make the decision path visually understandable.

The user should be able to visually answer:

**"Why did the system reach this classification?"**

without needing to inspect raw JSON.

## Saved evidence / retrieval

Include a small secondary action near the variant inputs:

**Load Saved Evidence**

This should be designed to retrieve previously persisted evidence for the entered gene + HGVS combination.

If no saved variant exists, show a friendly empty state:

`No saved evidence found for this variant.`

This should remain secondary to the main Analyze workflow.

## Loading state

Create a polished analysis loading state.

Example text:

**Analyzing variant**

Subtext:

`Evaluating structured evidence and decision rules...`

Visual elements:

* animated DNA helix
* pulsing nodes
* subtle progress indicator
* moving scan line
* glowing analysis card

Do not imply that an external AI model or external database is being queried.

## Error state

Create a clean error state for:

* invalid input
* malformed request
* server error
* persistence conflict

Use clear human-readable messages and a:

**Try Again**

action.

Avoid alarming red-heavy medical styling.

## Empty state

Before analysis, the result area should show:

**Ready for analysis**

with subtle DNA/genomic visual treatment.

Supporting text:

`Enter a gene, HGVS notation, and optional structured evidence to begin.`

## Responsive design

The application must work well on:

* desktop
* laptop
* tablet
* mobile

On mobile:

* stack the input sections vertically
* keep the DNA animation subtle
* make evidence cards easy to edit
* keep the Analyze Variant button prominent
* maintain readable result and decision-trace sections

## Micro-interactions

Add tasteful animations:

* DNA helix continuous movement
* glowing nodes traveling along DNA
* card hover elevation
* button hover glow
* input focus glow
* smooth expand/collapse for evidence and rules
* animated result appearance
* subtle transition between input and result states
* small pulse when an evidence item is added
* smooth loading → result transition

Keep animations restrained and professional.

## Important product constraints

This is a **decision-support interface**, not a diagnostic or treatment application.

Do NOT add:

* patient management
* patient records
* treatment recommendations
* medication recommendations
* authentication
* billing
* chatbots
* generic AI assistant chat
* unrelated dashboards
* unnecessary pages
* fake clinical statistics
* fake external evidence sources

Do not invent scientific evidence.

Use realistic example values only as UI examples/placeholders.

## Backend integration readiness

The frontend should be structured around these existing endpoints:

POST:

`/analysis/variants`

Used to submit:

* gene
* HGVS notation
* structured evidence

GET:

`/analysis/variants?gene=...&hgvs_notation=...`

Used to retrieve:

* variant identity
* persisted evidence

The frontend should not require any additional backend endpoints.

Keep API interaction isolated in a small service/helper layer so it can easily connect to the existing backend.

## Final impression

The final result should feel like a **premium genomic decision-support workstation**.

The DNA animation should become the visual identity of VMedithon.

The most important demo moment should be:

User enters:

`BRCA1`
`c.5266dupC`

adds evidence,

clicks:

**Analyze Variant**

then sees:

**Analysis Result**

followed by a beautiful, transparent visualization of:

**Evidence → Criteria → Rules → Classification**

Make this feel polished, scientific, explainable, and hackathon-demo ready.
