---
name: economic-timeseries-analysis
description: >
  Streamlined workflow for economic/financial time-series analysis tasks. Use this skill when
  performing multi-step economic data analysis involving inflation adjustment using CPI values,
  linear regression on time-series data, or analysis of nominal dollar values converted to real
  values. Triggers on tasks requiring Treasury data analysis, BLS CPI adjustments, economic trend
  analysis, or formatted regression output like [slope, intercept].
---

# Economic Time-Series Analysis

Standardized workflow for inflation adjustment and statistical analysis of economic data.

## Workflow Overview

1. **Gather & Structure Data** - Collect nominal values and CPI data with consistent period formatting
2. **Adjust for Inflation** - Apply CPI formula: `Real = Nominal × (CPI_base / CPI_current)`
3. **Perform Analysis** - Run linear regression on inflation-adjusted values
4. **Format Output** - Present results as `[slope, intercept]` rounded to 2 decimal places

## Step 1: Data Collection

Gather these inputs:
- **Nominal values**: Dollar amounts by period (e.g., monthly Treasury data)
- **CPI values**: Consumer Price Index for each period (BLS CPI-U series)
- **Base period**: Reference period for inflation adjustment (e.g., "1970-03")

Structure data with consistent period format (YYYY-MM):

```json
{
    "nominal_values": [
        {"period": "1970-03", "value": 275.52},
        {"period": "1970-04", "value": 318.44}
    ],
    "cpi_values": [
        {"period": "1970-03", "value": 38.8},
        {"period": "1970-04", "value": 39.0}
    ],
    "base_period": "1970-03"
}
```

## Step 2: Inflation Adjustment

Apply the standard inflation adjustment formula:

```
Real Value = Nominal Value × (CPI_base / CPI_current)
```

Example calculation:
- Nominal: $318.44 (April 1970)
- CPI_base (March 1970): 38.8
- CPI_current (April 1970): 39.0
- Real = 318.44 × (38.8 / 39.0) = $316.81

## Step 3: Linear Regression

Run regression with period index as x-values (0, 1, 2, ...) and real values as y-values.

Use `scripts/analyze_timeseries.py` for automated analysis:

```bash
python scripts/analyze_timeseries.py input.json
```

Input JSON format:
```json
{
    "nominal_values": [...],
    "cpi_values": [...],
    "base_period": "1970-03",
    "analysis_type": "linear_regression"
}
```

## Step 4: Format Output

Present regression results rounded to 2 decimal places:

```
[slope, intercept]
```

Example: `[44.00, 231.52]`

## Quick Reference

| Step | Action | Output |
|------|--------|--------|
| 1 | Structure data | JSON with periods, values |
| 2 | Apply CPI adjustment | Real values series |
| 3 | Linear regression | slope, intercept |
| 4 | Format | `[slope, intercept]` |

## Common Data Sources

- **Treasury Bulletin**: Monthly Statement of Public Debt
- **BLS CPI-U**: Bureau of Labor Statistics Consumer Price Index
