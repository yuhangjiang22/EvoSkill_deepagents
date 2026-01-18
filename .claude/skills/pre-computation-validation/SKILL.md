---
name: pre-computation-validation
description: >
  Active enforcement of validation checkpoints before multi-step financial calculations.
  MUST be triggered BEFORE: (1) currency conversion of financial data, (2) multi-step
  forecasting calculations, (3) risk metric computations requiring data transformation.
  This skill ENFORCES explicit validation output—not just documentation of rules.
  Use when combining data from different sources, converting currencies, or performing
  any calculation where date alignment, data transformation, or source verification
  could introduce systematic errors. The skill requires explicit PASS/FAIL output
  before computation proceeds, creating an auditable trail that prevents error propagation.
---

# Pre-Computation Validation Protocol

**This skill enforces validation—rules exist in other skills; this skill makes you PROVE compliance.**

## Core Principle

Before ANY multi-step financial calculation, output explicit validation checks with PASS/FAIL status. Do not proceed if validation fails.

## Mandatory Validation Output Format

**ALWAYS output this block before computing:**

```
═══════════════════════════════════════════════════════
VALIDATION CHECKPOINT
═══════════════════════════════════════════════════════
Task: [task type]
───────────────────────────────────────────────────────
Check 1: [description]
  - Expected: [value]
  - Found: [value]
  - Status: [PASS/FAIL]

Check 2: [description]
  - Expected: [value]
  - Found: [value]
  - Status: [PASS/FAIL]
───────────────────────────────────────────────────────
OVERALL: [PASS - proceed / FAIL - halt and resolve]
═══════════════════════════════════════════════════════
```

## Task-Specific Validation Protocols

### Currency Conversion Validation

**Before EACH conversion, validate:**

```
═══════════════════════════════════════════════════════
VALIDATION CHECKPOINT - Currency Conversion
═══════════════════════════════════════════════════════
Check 1: Date Alignment
  - Price observation date: [exact date from source]
  - Exchange rate date: [exact date from rate source]
  - Status: [PASS if identical / FAIL if different]

Check 2: Rate Direction
  - Quote convention: [e.g., "DEM per USD" or "USD per DEM"]
  - Operation to apply: [multiply/divide]
  - Status: [PASS if verified / FAIL if uncertain]

Check 3: Source Documentation
  - Price source: [document/table/cell reference]
  - Rate source: [document/API/reference]
  - Status: [PASS if documented / FAIL if assumed]
───────────────────────────────────────────────────────
OVERALL: [PASS/FAIL]
═══════════════════════════════════════════════════════
```

**CRITICAL Date Alignment Rules:**
- "End of March" prices require "end of March" exchange rates
- "March 1" ≠ "end of March" → FAIL
- "April 1" ≠ "end of March" → FAIL
- Treasury Bulletin April edition contains END OF MARCH data

**If FAIL:** Output "VALIDATION FAILED: [reason]. Must obtain [correct data] before proceeding." Then STOP and resolve.

### Risk Calculation Validation

**Before ES, VaR, or volatility calculations:**

```
═══════════════════════════════════════════════════════
VALIDATION CHECKPOINT - Risk Calculation
═══════════════════════════════════════════════════════
Check 1: Data Form
  - Required form: returns
  - Current form: [levels/returns]
  - Status: [PASS if returns / FAIL if levels]

Check 2: Return Calculation (if transformed)
  - Formula used: [e.g., (V_t - V_{t-1}) / V_{t-1}]
  - Sample calculation: [show one example]
  - Status: [PASS if verified / FAIL if not shown]

Check 3: Output Sign Convention
  - Loss representation: negative returns
  - Status: [PASS if convention documented]
───────────────────────────────────────────────────────
OVERALL: [PASS/FAIL]
═══════════════════════════════════════════════════════
```

### Forecasting Validation

**Before exponential smoothing or time-series forecasts:**

```
═══════════════════════════════════════════════════════
VALIDATION CHECKPOINT - Forecasting
═══════════════════════════════════════════════════════
Check 1: Notation Parsing
  - Raw value: [as appears in source]
  - Parsed value: [decimal equivalent]
  - Parsing method: [e.g., "32nds: 76 + 18/32 = 76.5625"]
  - Status: [PASS if shown / FAIL if assumed]

Check 2: Initialization Method
  - Method: [e.g., "F_1 = Y_1 (first observation)"]
  - Initial value: [numeric]
  - Status: [PASS if explicit]

Check 3: Error Convention
  - Formula: Error = Actual - Forecast
  - Status: [PASS if using standard convention]
───────────────────────────────────────────────────────
OVERALL: [PASS/FAIL]
═══════════════════════════════════════════════════════
```

### Multi-Source Data Combination

**Before combining time series from different sources:**

```
═══════════════════════════════════════════════════════
VALIDATION CHECKPOINT - Data Combination
═══════════════════════════════════════════════════════
Check 1: Frequency Match
  - Source A frequency: [monthly/quarterly/etc.]
  - Source B frequency: [monthly/quarterly/etc.]
  - Status: [PASS if identical / FAIL if different]

Check 2: Date Convention Match
  - Source A dates: [e.g., "end of month"]
  - Source B dates: [e.g., "end of month"]
  - Status: [PASS if identical / FAIL if different]

Check 3: Period Alignment
  - Sample period: [e.g., "March 1972"]
  - Source A date: [exact date]
  - Source B date: [exact date]
  - Status: [PASS if aligned / FAIL if misaligned]
───────────────────────────────────────────────────────
OVERALL: [PASS/FAIL]
═══════════════════════════════════════════════════════
```

## Blocking Behavior

**When validation FAILS:**

1. Output: `VALIDATION FAILED: [specific reason]`
2. Output: `REQUIRED ACTION: [what must be obtained/corrected]`
3. **STOP** - Do not proceed with calculation
4. Attempt to resolve (find correct data, correct transformation)
5. Re-run validation checkpoint
6. Only proceed when all checks PASS

**Example failure response:**
```
VALIDATION FAILED: Date alignment check failed
  - Price date: end of March 1972
  - Exchange rate date: March 1, 1972
  - These are NOT the same date

REQUIRED ACTION: Obtain exchange rate for end of March 1972
(last business day of March, typically March 31 or prior)

Searching for correct exchange rate...
```

## Workflow Integration

```
Start multi-step calculation
        │
        ▼
┌───────────────────┐
│ Output validation │
│ checkpoint        │
└─────────┬─────────┘
          │
    ┌─────┴─────┐
    │ All PASS? │
    └─────┬─────┘
          │
    ┌─────┴─────┐
   YES         NO
    │           │
    ▼           ▼
Proceed    Output FAILED
with       Resolve issue
calc       Re-validate
    │           │
    │      ┌────┘
    │      │
    ▼      ▼
┌───────────────────┐
│ Next calculation  │
│ step              │
└─────────┬─────────┘
          │
          ▼
   (repeat validation
    for each step)
```

## Auditable Trail

Each validation checkpoint creates documentation that:
- Shows exactly what was checked
- Records the values found
- Proves alignment before computation
- Enables post-hoc verification of methodology

This transforms "I followed the rules" into "Here is proof I checked before computing."
