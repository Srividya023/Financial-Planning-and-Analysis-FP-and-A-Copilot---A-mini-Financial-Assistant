import pandas as pd
import pytest
from fpna_copilot.agent.metrics import revenue_vs_budget


def test_revenue_vs_budget_basic():
    # --- Mock actuals data ---
    actuals = pd.DataFrame({
        "date": ["2025-12-01", "2025-12-01"],
        "entity": ["ParentCo", "EMEA"],
        "account_category": ["Revenue", "Revenue"],
        "currency": ["USD", "USD"],
        "amount": [100000, 50000]
    })

    # --- Mock budget data ---
    budget = pd.DataFrame({
        "date": ["2025-12-01", "2025-12-01"],
        "entity": ["ParentCo", "EMEA"],
        "account_category": ["Revenue", "Revenue"],
        "currency": ["USD", "USD"],
        "amount": [90000, 60000]
    })

    # --- Mock FX rates (for USD = 1) ---
    fx = pd.DataFrame({
        "date": ["2025-12-01"],
        "currency": ["USD"],
        "rate_to_usd": [1.0]
    })

    # --- Run the function for ParentCo ---
    result = revenue_vs_budget(actuals, budget, fx, 2025, 12, entity="ParentCo")

    # --- Assert expected results ---
    assert result["revenue_actual_usd"] == 100000
    assert result["revenue_budget_usd"] == 90000
    assert result["delta_usd"] == 10000
    assert result["pct_vs_budget"] == pytest.approx(11.11, rel=1e-2)
