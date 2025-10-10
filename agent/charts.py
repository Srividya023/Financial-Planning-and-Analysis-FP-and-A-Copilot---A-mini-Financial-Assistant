import matplotlib.pyplot as plt
import pandas as pd

def fig_revenue_vs_budget(res: dict):
    actual = res.get("revenue_actual_usd") or 0
    budget = res.get("revenue_budget_usd") or 0
    year, month = res.get("year"), res.get("month")

    fig, ax = plt.subplots()
    ax.bar(["Actual", "Budget"], [actual, budget])
    ax.set_title(f"Revenue vs Budget {year:04d}-{month:02d} (usd)")
    ax.set_ylabel("USD")
    return fig

def fig_gm_trend(df: pd.DataFrame):
    fig, ax = plt.subplots()
    if not df.empty:
        xs = pd.to_datetime(df["date"])
        ys = df["gm_pct"]
        ax.plot(xs, ys, marker="o")
    ax.set_title("Gross Margin % Trend")
    ax.set_ylabel("GM%")
    ax.set_xlabel("Month")
    return fig

def fig_opex_pie(df: pd.DataFrame):
    fig, ax = plt.subplots()
    if not df.empty:
        ax.pie(df["amount_usd"], labels=df["category"], autopct="%1.0f%%")
        ax.set_title("Opex by Category")
    else:
        ax.set_title("Opex by Category (no data)")
    return fig
