---
name: forecasting-methodology-guide
description: >
  Domain-specific methodology guidance for time series forecasting and currency conversion tasks.
  MUST be triggered BEFORE performing: (1) exponential smoothing forecasts on price/yield data,
  (2) moving average forecasts, (3) currency conversion of historical financial data, (4) forecast
  error calculations, (5) parsing bond prices in 32nds notation. Use when tasks involve forecasting
  Treasury prices, converting USD values to foreign currencies using historical exchange rates,
  or computing forecast errors. Prevents systematic methodology errors from incorrect initialization,
  wrong error sign conventions, date misalignment, or notation parsing mistakes.
---

# Time Series Forecasting & Currency Conversion Methodology Guide

**CRITICAL: Verify methodology BEFORE computation. Wrong conventions cascade through all calculations.**

## Pre-Flight Checklist

Before ANY forecasting or currency conversion task:

1. **Identify notation format** → Is it 32nds? Decimal? Parse correctly first
2. **Choose initialization method** → First observation for short series
3. **Align dates** → Match exchange rates to price observation dates
4. **Verify error convention** → Error = Actual - Forecast (standard)

## Bond Price Notation Parsing

### 32nds Notation (Treasury Securities)

**CRITICAL: Treasury bond prices are quoted in 32nds, not decimals.**

| Notation | Meaning | Decimal Value |
|----------|---------|---------------|
| 76.18 | 76 + 18/32 | 76.5625 |
| 99.16 | 99 + 16/32 | 99.5000 |
| 100.08 | 100 + 8/32 | 100.2500 |
| 98.24+ | 98 + 24.5/32 | 98.765625 |

**Conversion formula:**
```
Decimal Price = Integer Part + (Fractional Part / 32)
```

**The "+" suffix:**
- 98.24+ means 98 + 24.5/32 (adds 0.5 to the numerator)
- Equivalent to adding 1/64 to the base price

**Validation checks:**
- Fractional part must be 00-31 (values ≥32 are invalid)
- Treasury note prices typically range 90-110
- Treasury bond prices can range more widely

**Common error:** Treating 76.18 as 76.18 decimal instead of 76 + 18/32 = 76.5625.

## Exponential Smoothing Methodology

### Simple Exponential Smoothing Formula

```
F_{t+1} = α × Y_t + (1-α) × F_t
```

Where:
- F_{t+1} = Forecast for period t+1 (made at end of period t)
- Y_t = Actual value observed in period t
- F_t = Forecast that was made for period t
- α = Smoothing parameter (0 < α ≤ 1)

### Initialization Methods

| Method | When to Use | Formula |
|--------|-------------|---------|
| First observation | Short series (<20 obs), simple | F_1 = Y_1 |
| Average of first k | Longer series, more stable | F_1 = mean(Y_1...Y_k) |
| Backcast | Optimal but complex | Requires iterative fitting |

**Default:** Use first observation method (F_1 = Y_1) unless otherwise specified.

### Forecast Timing Convention

**CRITICAL: A forecast for period t is made at the END of period t-1.**

| Time | Action | Available Information |
|------|--------|----------------------|
| End of Period 1 | Make forecast F_2 | Know Y_1, F_1 |
| End of Period 2 | Make forecast F_3 | Know Y_1, Y_2, F_1, F_2 |
| End of Period t-1 | Make forecast F_t | Know Y_1...Y_{t-1}, F_1...F_{t-1} |

### Step-by-Step Calculation

Given: α = 0.3, observations Y = [100, 105, 102, 108]

1. **Initialize:** F_1 = Y_1 = 100
2. **Period 2 forecast:** F_2 = 0.3(100) + 0.7(100) = 100.00
3. **Period 3 forecast:** F_3 = 0.3(105) + 0.7(100) = 101.50
4. **Period 4 forecast:** F_4 = 0.3(102) + 0.7(101.50) = 101.55
5. **Period 5 forecast:** F_5 = 0.3(108) + 0.7(101.55) = 103.49

## Forecast Error Conventions

### Standard Convention

**CRITICAL: Error = Actual - Forecast (NOT Forecast - Actual)**

```
e_t = Y_t - F_t
```

| Error Sign | Interpretation |
|------------|----------------|
| Positive (+) | Under-forecast (actual exceeded forecast) |
| Negative (-) | Over-forecast (actual was below forecast) |

**Example:**
- Actual (Y_t) = 190.73
- Forecast (F_t) = 210.02
- Error = 190.73 - 210.02 = **-19.29** (over-forecast)

### Common Error

**WRONG:** e_t = F_t - Y_t (reverses sign interpretation)

If you calculate 210.02 - 190.73 = +19.29, the SIGN IS WRONG.

### Error Metrics

| Metric | Formula | Notes |
|--------|---------|-------|
| Error | Y_t - F_t | Signed, for single period |
| Absolute Error | \|Y_t - F_t\| | Always positive |
| Squared Error | (Y_t - F_t)² | For MSE calculation |
| MAE | mean(\|errors\|) | Mean Absolute Error |
| RMSE | sqrt(mean(errors²)) | Root Mean Squared Error |

## Currency Conversion Date Alignment

### Matching Dates Rule

**CRITICAL: Use the exchange rate from the SAME DATE as the price observation.**

| Price Date | Exchange Rate Date | Correct? |
|------------|-------------------|----------|
| End of March | End of March | ✓ Yes |
| End of March | March 1 | ✗ No |
| End of March | Beginning of April | ✗ No |

### End-of-Month Convention

For end-of-month price data:
- Use end-of-month exchange rates
- "End of month" typically means last business day
- Not "first of next month" or "average for month"

### Exchange Rate Direction

**Verify quote convention before applying:**

| Convention | Example | To convert USD → DEM |
|------------|---------|---------------------|
| DEM per USD | 1.85 DEM/USD | Multiply: USD × 1.85 |
| USD per DEM | 0.54 USD/DEM | Divide: USD ÷ 0.54 |

**Common sources:**
- Federal Reserve: Usually foreign currency per USD
- ECB: Usually EUR per foreign currency
- OANDA: Configurable, check carefully

### Multi-Step Conversion Workflow

1. **Extract price** in source currency (parse notation if needed)
2. **Identify observation date** exactly
3. **Find exchange rate** for that exact date
4. **Verify quote direction** (per USD or per foreign)
5. **Apply conversion** with correct operation
6. **Validate magnitude** (sanity check result)

## Data Period Alignment Validation

### Pre-Computation Checklist

Before combining multiple time series:

- [ ] All series have same observation frequency
- [ ] Dates align exactly (not "approximately")
- [ ] End-of-month means end-of-month for ALL series
- [ ] No calendar vs. business day mismatches

### Common Misalignments

| Source A | Source B | Problem |
|----------|----------|---------|
| End of month | First of next month | 1 day off, compounds |
| Business day close | Calendar month end | Weekend drift |
| New York close | London close | Time zone shift |

### Validation Step

After alignment, verify:
```
For each date d in combined dataset:
  - Price observation is for date d
  - Exchange rate is for date d
  - No interpolation was used unless documented
```

## Quick Decision Tree

```
Starting a forecasting task?
├── Is price data in 32nds notation?
│   ├── YES → Parse: Integer + Fractional/32
│   └── NO → Use as-is (verify it's decimal)
│
├── Using exponential smoothing?
│   ├── How to initialize?
│   │   └── Use F_1 = Y_1 (first observation)
│   └── Computing error?
│       └── Error = Actual - Forecast (signed)
│
└── Converting currencies?
    ├── Match exchange rate date to price date exactly
    ├── Verify rate direction (per USD or per foreign)
    └── Validate converted magnitude is reasonable
```

## Validation Checks

| Calculation | Expected | Red Flag |
|-------------|----------|----------|
| Parsed 32nds price | Close to quoted integer | >1 point difference |
| Exponential smooth | Between min and max of data | Outside data range |
| Forecast error sign | Negative if over-forecast | Sign seems reversed |
| Currency conversion | Same order of magnitude | 10x or 0.1x original |
| Date alignment | Exact date match | Off by days |
