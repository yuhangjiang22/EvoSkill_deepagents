#!/usr/bin/env python3
"""
Economic Time-Series Analysis Script

Performs inflation adjustment and linear regression on economic data.

Usage:
    python analyze_timeseries.py <data_file> [--output <output_file>]

Input JSON format:
{
    "nominal_values": [
        {"period": "1970-03", "value": 100.0},
        {"period": "1970-06", "value": 110.0}
    ],
    "cpi_values": [
        {"period": "1970-03", "value": 38.8},
        {"period": "1970-06", "value": 39.0}
    ],
    "base_period": "1970-03",
    "analysis_type": "linear_regression"
}

Output JSON format:
{
    "real_values": [
        {"period": "1970-03", "nominal": 100.0, "real": 100.0},
        {"period": "1970-06", "nominal": 110.0, "real": 109.44}
    ],
    "regression": {
        "slope": 44.00,
        "intercept": 231.52
    },
    "formatted_result": "[44.00, 231.52]"
}
"""

import json
import sys
from typing import Optional


def load_data(filepath: str) -> dict:
    """Load JSON data from file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def validate_data(data: dict) -> tuple[bool, str]:
    """Validate input data structure."""
    required = ['nominal_values', 'cpi_values', 'base_period']
    for field in required:
        if field not in data:
            return False, f"Missing required field: {field}"

    if not data['nominal_values']:
        return False, "nominal_values cannot be empty"
    if not data['cpi_values']:
        return False, "cpi_values cannot be empty"

    return True, ""


def get_cpi_for_period(cpi_values: list, period: str) -> Optional[float]:
    """Get CPI value for a specific period."""
    for item in cpi_values:
        if item['period'] == period:
            return float(item['value'])
    return None


def adjust_for_inflation(nominal_values: list, cpi_values: list, base_period: str) -> list:
    """
    Adjust nominal values for inflation.

    Formula: Real Value = Nominal × (CPI_base / CPI_current)
    """
    cpi_base = get_cpi_for_period(cpi_values, base_period)
    if cpi_base is None:
        raise ValueError(f"Base period CPI not found: {base_period}")

    real_values = []
    for item in nominal_values:
        period = item['period']
        nominal = float(item['value'])

        cpi_current = get_cpi_for_period(cpi_values, period)
        if cpi_current is None:
            raise ValueError(f"CPI not found for period: {period}")

        real = nominal * (cpi_base / cpi_current)
        real_values.append({
            'period': period,
            'nominal': nominal,
            'real': round(real, 2)
        })

    return real_values


def linear_regression(values: list) -> tuple[float, float]:
    """
    Perform simple linear regression.

    Uses period index (0, 1, 2, ...) as x-values.
    Returns (slope, intercept) rounded to 2 decimal places.
    """
    n = len(values)
    if n < 2:
        raise ValueError("Need at least 2 data points for regression")

    # x values are indices 0, 1, 2, ...
    # y values are the real (inflation-adjusted) values
    y_values = [v['real'] for v in values]

    # Calculate means
    x_mean = (n - 1) / 2  # mean of 0, 1, ..., n-1
    y_mean = sum(y_values) / n

    # Calculate slope: sum((x-x_mean)(y-y_mean)) / sum((x-x_mean)^2)
    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(y_values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        slope = 0.0
    else:
        slope = numerator / denominator

    # Calculate intercept
    intercept = y_mean - slope * x_mean

    return round(slope, 2), round(intercept, 2)


def analyze(data: dict) -> dict:
    """Main analysis function."""
    # Validate
    valid, error = validate_data(data)
    if not valid:
        raise ValueError(error)

    # Adjust for inflation
    real_values = adjust_for_inflation(
        data['nominal_values'],
        data['cpi_values'],
        data['base_period']
    )

    # Perform analysis
    analysis_type = data.get('analysis_type', 'linear_regression')

    result = {
        'real_values': real_values
    }

    if analysis_type == 'linear_regression':
        slope, intercept = linear_regression(real_values)
        result['regression'] = {
            'slope': slope,
            'intercept': intercept
        }
        result['formatted_result'] = f"[{slope:.2f}, {intercept:.2f}]"

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_timeseries.py <data_file> [--output <output_file>]")
        print("\nExample:")
        print("  python analyze_timeseries.py input.json")
        print("  python analyze_timeseries.py input.json --output results.json")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = None

    if '--output' in sys.argv:
        idx = sys.argv.index('--output')
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]

    try:
        data = load_data(input_file)
        result = analyze(data)

        output = json.dumps(result, indent=2)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            print(f"Results written to: {output_file}")
        else:
            print(output)

        # Print formatted result for easy extraction
        if 'formatted_result' in result:
            print(f"\nFormatted Answer: {result['formatted_result']}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
