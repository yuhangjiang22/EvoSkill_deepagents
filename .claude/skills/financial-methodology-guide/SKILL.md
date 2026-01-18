---
name: financial-methodology-guide
description: >
  Domain-specific methodology guidance for quantitative financial analysis tasks. MUST be triggered
  BEFORE performing risk metric calculations (Expected Shortfall, VaR, volatility), government
  accounting classifications, or financial data transformations. Use when: (1) calculating ES/CVaR
  or VaR on yield/price data, (2) classifying federal budget obligations by category, (3) computing
  returns from levels, (4) interpreting OMB or Treasury accounting terminology. Prevents systematic
  methodology errors by enforcing correct data transformations and domain definitions.
---

# Financial & Economic Analysis Methodology Guide

**CRITICAL: Verify methodology BEFORE computation. Wrong methodology = wrong answer regardless of correct data extraction.**

## Pre-Flight Checklist

Before ANY quantitative financial analysis:

1. **Identify the metric type** → Determines required data form
2. **Check data form** → Is it levels or returns? Prices or yields?
3. **Apply required transformation** → Convert if needed
4. **Validate output sign/magnitude** → Sanity check results

## Risk Metric Methodology

### Expected Shortfall (ES / CVaR)

**CRITICAL: ES is calculated on RETURNS, not raw values.**

| Data Form | Required Action | Example |
|-----------|-----------------|---------|
| Yield levels (9.56%, 8.36%, ...) | Compute returns FIRST | r_t = (Y_t - Y_{t-1}) / Y_{t-1} |
| Price levels ($100, $98, ...) | Compute returns FIRST | r_t = (P_t - P_{t-1}) / P_{t-1} |
| Return series (-2.5%, 1.2%, ...) | Use directly | No transformation |

**Formula:**
```
ES_α = E[Loss | Loss > VaR_α]
```

At α = 5%, ES is the average of the worst 5% of returns.

**Correct workflow for yield data:**
1. Extract yield levels: [9.56%, 9.60%, 8.36%, 7.37%, 7.68%, 6.69%, 5.87%, 6.04%, 5.65%, 6.14%]
2. Compute period-over-period returns: [(9.60-9.56)/9.56, (8.36-9.60)/9.60, ...]
3. Sort returns, take worst α percentile
4. Average those worst returns → ES

**Common error:** Taking min/max of raw levels. This is NOT ES.

**Output validation:**
- ES representing losses should be negative (e.g., -18.51%)
- Magnitude should reflect plausible return movements
- If ES equals min(raw_values), methodology was wrong

### Value at Risk (VaR)

Same transformation rules as ES. VaR is the threshold loss at confidence level α.

```
VaR_α = quantile(returns, α)
```

At 95% confidence, VaR is the 5th percentile of returns.

## Data Transformation Rules

### When to Compute Returns

| Analysis Type | Requires Returns? | Why |
|---------------|-------------------|-----|
| ES / CVaR | YES | Risk metrics measure change, not level |
| VaR | YES | Same as ES |
| Volatility / Std Dev | Usually YES | Volatility of returns, not levels |
| Performance analysis | YES | Compare % gains/losses |
| Trend analysis | NO | Levels show trend direction |
| Point-in-time snapshot | NO | Current state, not change |

### Return Calculation Methods

**Simple returns** (default for most financial analysis):
```
r_t = (V_t - V_{t-1}) / V_{t-1}
```

**Log returns** (for compounding analysis):
```
r_t = ln(V_t / V_{t-1})
```

Use simple returns unless log returns are specifically required.

## Government Accounting Classifications

**CRITICAL: Use OMB/Treasury definitions, not intuitive interpretation.**

For federal obligation classifications, see `references/federal-accounting.md`.

Key principle: "Service-related" in federal accounting has specific regulatory meaning per OMB Circular A-11 that differs from casual interpretation.

## Validation Checks

Before reporting any result, verify:

| Metric | Expected Characteristics | Red Flag |
|--------|-------------------------|----------|
| ES on returns | Negative value (for loss measurement) | Positive or equals raw data min |
| VaR on returns | Negative value at α < 50% | Positive or equals raw percentile of levels |
| Percentage of total | Between 0% and 100% | Outside range or sum ≠ 100% |
| Classification ratio | Matches expected category scope | Drastically different from reasonable range |

## Quick Decision Tree

```
Calculating ES, VaR, or volatility?
├── YES → Is data already in return form?
│   ├── YES → Proceed with calculation
│   └── NO → Compute returns first, then calculate
└── NO → Is it a classification task?
    ├── YES → Check references/federal-accounting.md for definitions
    └── NO → Proceed with standard analysis
```
