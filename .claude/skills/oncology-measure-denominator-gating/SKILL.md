---
name: oncology-measure-denominator-gating
description: Produce a denominator-eligibility gate (ELIGIBLE/EXCLUDED/INSUFFICIENT_INFO) with evidence mapping before scoring oncology quality measures that include EXCLUDED or stage/setting qualifiers (advanced/metastatic, unresectable, recurrent, first-line systemic therapy).
---

# Oncology Measure Denominator Gating (EXCLUDED-first)

## Workflow

### 1) Inputs

- **measure_question**: full measure prompt, including any C1/C2 requirements and output labels
- **case_evidence**: chart snippets/structured fields (dx/histology, staging, intent, setting, treatments, dates)
- **draft_answer** (optional): if provided, ignore any concordance conclusion until denominator is gated

### 2) Denominator extraction (from measure text only)

Extract *explicit* denominator qualifiers. Do **not** assume guideline intent.

Capture:
- **Disease context**: cancer type + relevant subtype (e.g., non-squamous NSCLC)
- **Stage/extent**: advanced/metastatic; stage group; M0/M1; unresectable; recurrent
- **Treatment setting**: first-line systemic therapy, metastatic systemic therapy, palliative intent, perioperative/adjuvant/neoadjuvant
- **Episode/timing**: diagnosis window, start-of-therapy window, “prior to X”, etc.

Write these as a checklist of **denominator_requirements**.

### 3) Evidence check (explicit stage/setting verification)

For each denominator requirement, search **case_evidence** and record:
- **supporting quote(s)** with source/date if available, or
- **not found**

Prefer the most definitive sources:
- TNM + stage group (e.g., *T1cN2M0, stage IIIA*)
- Explicit metastatic language (e.g., *metastatic*, *M1b*, *distant mets to liver*)
- Explicit intent/setting (e.g., *palliative*, *first-line systemic therapy*, *unresectable*)

### 4) Hard rules (guardrails)

- **Hard rule A (early-stage contradiction → EXCLUDED):**
  If the denominator implies **advanced/metastatic/systemic-therapy** context, and evidence explicitly indicates **non-advanced disease** (e.g., stage I–III with **M0** and curative/surgical/adjuvant/neoadjuvant context) → **EXCLUDED**.

- **Hard rule B (missing denominator facts → INSUFFICIENT_INFO):**
  If the denominator requires advanced/metastatic/systemic-therapy context and the record does **not** establish stage/setting → **INSUFFICIENT_INFO**.
  *Do not* default to CONCORDANT because testing exists.

Only after **ELIGIBLE**, proceed to concordance scoring (biomarker adequacy/timing, etc.).

## Required output (must be produced before concordance)

Return this object:

```yaml
denominator_status: ELIGIBLE | EXCLUDED | INSUFFICIENT_INFO

denominator_requirements:
  - <requirement inferred from measure text>
  - ...

evidence_map:
  - requirement: <same text as above>
    evidence:
      - "<supporting quote>"  # or [] if not found
    status: MET | NOT_FOUND | CONTRADICTS

decision: <1-2 sentences explaining the denominator determination>

next_step:
  if_EXCLUDED: "Return EXCLUDED and stop. Do not score concordance."
  if_INSUFFICIENT_INFO: "Ask for the missing denominator facts and stop."
  if_ELIGIBLE: "Proceed to concordance evaluation."
```

## Examples

### Example 1 — Stage IIIA with testing present → EXCLUDED

- **Measure text** (implied): advanced/metastatic systemic-therapy setting.
- **Evidence**: “clinical stage IIIA (T1cN2M0) adenocarcinoma”; PD-L1 and NGS ordered.
- **Gate**: **EXCLUDED** (early-stage contradiction), *even though* testing was done.

### Example 2 — Testing present but stage/setting absent → INSUFFICIENT_INFO

- **Evidence**: biomarker panel resulted; no stage group, no metastatic status, no systemic-therapy context.
- **Gate**: **INSUFFICIENT_INFO**; request: stage group/TNM, M status, recurrence/unresectable status, and whether first-line systemic therapy is planned/started.

### Example 3 — Stage IV metastatic → ELIGIBLE then score

- **Evidence**: “Stage IV metastatic non-squamous NSCLC”; first-line systemic therapy planned/started; required testing documented.
- **Gate**: **ELIGIBLE** → proceed to CONCORDANT/NONCONCORDANT based on measure specifics.
