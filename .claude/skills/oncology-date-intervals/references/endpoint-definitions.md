# Endpoint definitions & edge cases (oncology date intervals)

## DxDate nuances

### Pathology dates
Prefer the date that best represents when malignancy was *established*:

- If note includes **specimen collection/biopsy date**, use it.
- Else if only **pathology report date** is available, use report date and note the assumption.

### Clinical dx vs problem list
Problem list entries ("Breast cancer (HCC)") often carry import dates and are unreliable without narrative support. Treat as weak evidence.

### Imaging
Imaging can be used for DxDate only when clinician explicitly states diagnosis based on imaging (common in advanced disease) and no tissue date exists.

## TxStart nuances

### Systemic therapy
- Infusion: use administration date (C1D1).
- Oral: use documented first dose date; if only "started on" is present, treat that as start.
- If only a plan exists ("will start next week"), do not set TxStart.

### Radiation
Use first fraction date; simulation/CT sim is not treatment start.

### Surgery
Use date of oncologic resection; exclude:
- diagnostic biopsies
- port placement
- exploratory/laparoscopy without definitive resection

## Multiple cancers / episodes
If the patient has multiple primaries, require the user or note context to identify the index cancer (site/histology).

If recurrence is present, clarify whether interval is:
- initial Dx  first treatment ever, or
- recurrence Dx  treatment for recurrence

## Date precision handling
When endpoints are partial, prefer reporting bounds (min/max). Only impute an exact day if the downstream consumer explicitly requires it.
