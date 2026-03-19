---
name: oncology-date-intervals
description: Extract and compute oncology clinical date intervals (e.g., days from diagnosis to first definitive treatment start) from unstructured clinical notes; use when normalizing messy/partial dates, reconciling multiple candidate dates, and reporting interval values with provenance.
---

# Oncology date intervals (diagnosis → treatment start)

## Workflow (high reliability)

### 1) Define endpoints (before extracting)

**A. Diagnosis date (DxDate)**
Choose the earliest date that supports *clinical diagnosis* of the malignancy of interest.
Use this priority order (stop at the first available, unambiguous option):

1. **Pathologic diagnosis date**: biopsy / surgical pathology confirming malignancy ("path confirmed", "biopsy showed...").
2. **Clinical diagnosis date**: oncologist explicitly documents diagnosis ("diagnosed with", "new dx", "cancer diagnosed on").
3. **Imaging highly suspicious + documented as diagnosis**: only if note treats imaging as diagnosis (avoid if merely "concern for").

**Do not use** symptom onset, referral date, first abnormal imaging (unless explicitly documented as diagnosis), or historical/problem-list dates without supporting context.

**B. Treatment start date (TxStart)**
Choose the earliest date of the **first definitive anti-cancer therapy** for the indexed diagnosis:

- **Systemic therapy**: first administration date (infusion/injection) or first dose date for oral agents.
- **Radiation**: first fraction date / "RT start".
- **Surgery**: date of curative-intent resection (not diagnostic biopsy).

If multiple modalities exist, use the earliest definitive modality as TxStart (unless user specifies a modality).

### 2) Extract candidate dates with evidence
From notes, collect all candidate dates for Dx and Tx with:

- **raw snippet** (1–2 sentences)
- **doc date** (note authored/signed date, if known)
- **date string** as written (e.g., "3/4/21", "March 2021", "last Friday")
- **event type** (DxPath, DxClinical, TxChemo, TxRT, TxSurgery, etc.)

If dates are relative ("yesterday", "two weeks ago"), resolve them using the note's authored date; otherwise mark as unresolved.

### 3) Normalize dates (handle partial/ambiguous)
Normalize to ISO (`YYYY-MM-DD`) and attach a **precision** label:

- `day` — full date
- `month` — `YYYY-MM` only
- `year` — `YYYY` only
- `unknown`

Rules:

- If **MM/DD/YY** ambiguity exists (US vs non-US), assume **US** unless the dataset is known otherwise; if ambiguous, keep as ambiguous and ask.
- For partial dates:
  - Prefer not to impute. If an interval must be computed, compute **bounds** (min/max):
    - `YYYY-MM` — earliest = first day of month, latest = last day of month
    - `YYYY` — earliest = Jan 1, latest = Dec 31
- If multiple notes disagree, prefer:
  1) direct contemporaneous documentation closest to event,
  2) pathology report dates,
  3) later summaries.

### 4) Select final endpoints
Pick one DxDate and one TxStart with:

- **selection rationale** (why this candidate wins)
- **provenance** (source note + snippet)
- **precision** and any assumptions

If endpoints remain ambiguous, output top candidates and ask a targeted clarification question.

### 5) Compute interval
Compute:

- `days_to_treatment = (TxStart - DxDate).days`

If either endpoint is partial, compute:

- `days_to_treatment_min`
- `days_to_treatment_max`

Also return whether interval is negative; if negative, flag likely mis-anchoring (e.g., prior cancer, adjuvant therapy for recurrence).

## Output template (copy/paste)

```yaml
interval_name: days_from_diagnosis_to_treatment_start
index_cancer: <free text>
DxDate:
  value: YYYY-MM-DD|YYYY-MM|YYYY|unknown
  precision: day|month|year|unknown
  event_type: DxPath|DxClinical|DxImaging
  evidence:
    note_date: YYYY-MM-DD|unknown
    snippet: "..."
TxStart:
  value: YYYY-MM-DD|YYYY-MM|YYYY|unknown
  precision: day|month|year|unknown
  modality: systemic|radiation|surgery|unknown
  evidence:
    note_date: YYYY-MM-DD|unknown
    snippet: "..."
interval:
  days: <int|null>
  days_min: <int|null>
  days_max: <int|null>
  negative_flag: true|false
assumptions:
  - <bullets>
open_questions:
  - <only if needed>
```

## Common note patterns (mapping)

- "Dx: <cancer> on <date>" — DxClinical
- "Biopsy (<site>) <date>: invasive carcinoma" — DxPath (use pathology specimen/collection date if explicit; otherwise report date)
- "Started FOLFOX <date>" / "Cycle 1 Day 1 <date>" — TxStart systemic
- "RT start <date>" / "First fraction <date>" — TxStart radiation
- "Underwent <procedure> on <date>" — TxStart surgery (ensure not biopsy/port placement)

## Guardrails / exclusions

- Separate **initial diagnosis** vs **recurrence/metastatic diagnosis**. If note says "recurrent", anchor DxDate to recurrence diagnosis unless user asks for initial.
- Port placement, staging scans, oncology consult, and referral dates are not TxStart.
- If therapy started as neoadjuvant vs adjuvant, still TxStart is first definitive therapy for the indexed episode.
