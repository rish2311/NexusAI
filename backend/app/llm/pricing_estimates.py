"""Optional commercial cost estimates for portfolio literacy — NOT billing."""

from __future__ import annotations

from decimal import Decimal

# Versioned estimate table (USD per 1M tokens). Informational only.
ESTIMATE_TABLE_VERSION = "2025-01-v1"

ESTIMATES_USD_PER_1M: dict[str, dict[str, Decimal]] = {
    "gemini-2.5-flash": {
        "input": Decimal("0.10"),
        "output": Decimal("0.40"),
    },
    "gemini-2.0-flash": {
        "input": Decimal("0.10"),
        "output": Decimal("0.40"),
    },
    "gemini-1.5-flash": {
        "input": Decimal("0.075"),
        "output": Decimal("0.30"),
    },
    "mock-1": {
        "input": Decimal("0.00"),
        "output": Decimal("0.00"),
    },
}


def estimate_commercial_cost_usd(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> Decimal:
    rates = ESTIMATES_USD_PER_1M.get(model) or ESTIMATES_USD_PER_1M["gemini-2.5-flash"]
    cost = (Decimal(input_tokens) / Decimal(1_000_000)) * rates["input"] + (
        Decimal(output_tokens) / Decimal(1_000_000)
    ) * rates["output"]
    return cost.quantize(Decimal("0.000001"))
