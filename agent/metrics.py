from __future__ import annotations
from typing import Optional, Tuple, Iterable
import pandas as pd


def _ensure_cols(df: pd.DataFrame | None) -> pd.DataFrame:
    """Normalize common column names and types across sheets."""
    if df is None or df.empty:
        return pd.DataFrame()

    d = df.copy()

    # Standardize headers
    d.columns = [c.strip().lower().replace(" ", "_") for c in d.columns]

    # Map common variants
    if "date" not in d.columns and "month" in d.columns:
        d = d.rename(columns={"month": "date"})
    if "account" not in d.columns and "account_category" in d.columns:
        d = d.rename(columns={"account_category": "account"})
    if "amount" not in d.columns and "cash_usd" in d.columns:
        d = d.rename(columns={"cash_usd": "amount"})

    # Ensure columns exist
    if "currency" not in d.columns:
        d["currency"] = "USD"

    # Coerce types
    if "date" in d.columns:
        # Accept both YYYY-MM strings and true Excel dates; normalize to month-start Timestamp
        d["date"] = pd.to_datetime(d["date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    if "amount" in d.columns:
        d["amount"] = pd.to_numeric(d["amount"], errors="coerce").fillna(0.0)
    if "entity" in d.columns:
        d["entity"] = d["entity"].astype(str)
    if "account" in d.columns:
        d["account"] = d["account"].astype(str)

    return d


def latest_year_month(df: pd.DataFrame, date_col: str = "date") -> Tuple[Optional[int], Optional[int]]:
    """Return (year, month) for the latest available row in df[date_col]."""
    if df is None or df.empty or date_col not in df.columns:
        return None, None
    s = pd.to_datetime(df[date_col], errors="coerce")
    if s.isna().all():
        return None, None
    latest = s.max()
    return int(latest.year), int(latest.month)


def _apply_entity(df: pd.DataFrame, entity: Optional[str]) -> pd.DataFrame:
    """Filter by entity substring (case-insensitive)."""
    if df.empty or not entity or "entity" not in df.columns:
        return df.copy()
    mask = df["entity"].astype(str).str.lower().str.contains(str(entity).lower(), na=False)
    return df.loc[mask].copy()


def _merge_fx(df: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    """
    Left-join FX by (date, currency). Output always has 'amount_usd'.
    Missing FX rate -> 1.0 (assume already USD).
    """
    d = _ensure_cols(df)
    f = _ensure_cols(fx)

    if d.empty:
        out = d.copy()
        out["amount_usd"] = 0.0
        return out

    keep = ["date", "currency", "rate_to_usd"]
    if not f.empty:
        f = f[[c for c in keep if c in f.columns]].copy()
    else:
        f = pd.DataFrame(columns=keep)

    if "rate_to_usd" not in f.columns:
        f["rate_to_usd"] = 1.0

    m = d.merge(f, on=["date", "currency"], how="left")
    m["rate_to_usd"] = pd.to_numeric(m.get("rate_to_usd", 1.0), errors="coerce").fillna(1.0)
    m["amount_usd"] = pd.to_numeric(m.get("amount", 0.0), errors="coerce").fillna(0.0) * m["rate_to_usd"]
    return m


def _filter_month(df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    """Filter df to a given year and month, handling both string and datetime values."""
    d = _ensure_cols(df)
    if d.empty:
        return d.iloc[0:0]

    if "date" not in d.columns:
        return d.iloc[0:0]

    # Normalize all to string form like "2025-06"
    d["_date_str"] = d["date"].astype(str)
    target_str = f"{year:04d}-{month:02d}"

    mask = (
        (d["_date_str"].str.startswith(target_str))
        | ((d["date"].dt.year == year) & (d["date"].dt.month == month))
    )

    return d.loc[mask].copy()


def _sum_account_prefix(df: pd.DataFrame, prefixes: Iterable[str] | str) -> float:
    """
    Sum 'amount_usd' for rows whose 'account' starts with any of the given prefixes,
    case/space tolerant (e.g., 'Revenue', ' revenue', 'COGS :', etc.).
    """
    if df is None or df.empty:
        return 0.0
    d = df.copy()
    if "amount_usd" not in d.columns:
        d["amount_usd"] = pd.to_numeric(d.get("amount", 0.0), errors="coerce").fillna(0.0)
    if "account" not in d.columns:
        return 0.0

    if isinstance(prefixes, str):
        prefixes = [prefixes]

    s = d["account"].astype(str).str.strip().str.lower()
    mask = False
    for p in prefixes:
        mask = mask | s.str.startswith(str(p).strip().lower())
    return float(pd.to_numeric(d.loc[mask, "amount_usd"], errors="coerce").fillna(0.0).sum())


# =========================
# Core Metrics
# =========================

def revenue_only(actuals: pd.DataFrame, fx: pd.DataFrame, year: int, month: int, entity: Optional[str] = None):
    a = _merge_fx(_filter_month(actuals, year, month), fx)
    a = _apply_entity(a, entity)
    rev = _sum_account_prefix(a, ("revenue", "sales", "income"))
    return {"year": year, "month": month, "entity": entity, "revenue_usd": float(rev)}


def revenue_vs_budget(
    actuals: pd.DataFrame, budget: pd.DataFrame, fx: pd.DataFrame, year: int, month: int, entity: Optional[str] = None
):
    a = _merge_fx(_filter_month(actuals, year, month), fx)
    b = _merge_fx(_filter_month(budget,  year, month), fx)
    a = _apply_entity(a, entity)
    b = _apply_entity(b, entity)

    rev_actual = _sum_account_prefix(a, ("revenue", "sales", "income"))
    rev_budget = _sum_account_prefix(b, ("revenue", "sales", "income"))
    delta = rev_actual - rev_budget
    pct = (delta / rev_budget * 100.0) if rev_budget else None

    return {
        "year": year,
        "month": month,
        "entity": entity,
        "revenue_actual_usd": float(rev_actual),
        "revenue_budget_usd": float(rev_budget),
        "delta_usd": float(delta),
        "pct_vs_budget": float(pct) if pct is not None else None,
    }


def gross_margin_pct_trend(
    actuals: pd.DataFrame, fx: pd.DataFrame,
    start_year: int, start_month: int, end_year: int, end_month: int,
    entity: Optional[str] = None
) -> pd.DataFrame:
    a_all = _merge_fx(_ensure_cols(actuals), _ensure_cols(fx))
    a_all = _apply_entity(a_all, entity)

    rng = pd.period_range(
        start=f"{start_year:04d}-{start_month:02d}",
        end=f"{end_year:04d}-{end_month:02d}",
        freq="M",
    )

    rows = []
    for per in rng:
        ts = per.to_timestamp()
        dm = a_all[a_all["date"] == ts]
        rev = _sum_account_prefix(dm, ("revenue", "sales", "income"))
        cogs = _sum_account_prefix(dm, ("cogs", "cost of goods sold"))
        gm = rev - cogs
        gm_pct = (gm / rev * 100.0) if rev else None
        rows.append({
            "date": ts,
            "revenue_usd": float(rev),
            "cogs_usd": float(cogs),
            "gm_pct": round(float(gm_pct), 2) if gm_pct is not None else None,
        })

    return pd.DataFrame(rows)


def opex_by_category(actuals: pd.DataFrame, fx: pd.DataFrame, year: int, month: int, entity: Optional[str] = None) -> pd.DataFrame:
    a = _merge_fx(_filter_month(actuals, year, month), fx)
    a = _apply_entity(a, entity)
    if a.empty or "account" not in a.columns:
        return pd.DataFrame(columns=["category", "amount_usd"])

    # Case-insensitive match for "Opex:*"
    opex = a[a["account"].astype(str).str.strip().str.lower().str.startswith("opex:")].copy()
    if opex.empty:
        return pd.DataFrame(columns=["category", "amount_usd"])

    # Derive category after "Opex:"
    opex["category"] = (
        opex["account"].astype(str)
        .str.strip()
        .str.replace("Opex:", "", n=1, regex=False)
        .str.replace("opex:", "", n=1, regex=False)
        .str.strip()
    )

    out = (
        opex.groupby("category", as_index=False)["amount_usd"]
        .sum()
        .sort_values("amount_usd", ascending=False)
    )
    out["amount_usd"] = out["amount_usd"].astype(float)
    return out


def ebitda(actuals: pd.DataFrame, fx: pd.DataFrame, year: int, month: int, entity: Optional[str] = None):
    a = _merge_fx(_filter_month(actuals, year, month), fx)
    a = _apply_entity(a, entity)
    rev = _sum_account_prefix(a, ("revenue", "sales", "income"))
    cogs = _sum_account_prefix(a, ("cogs", "cost of goods sold"))
    opex = float(a[a["account"].astype(str).str.strip().str.lower().str.startswith("opex:")]["amount_usd"].sum())
    return {
        "year": year,
        "month": month,
        "entity": entity,
        "revenue_usd": float(rev),
        "cogs_usd": float(cogs),
        "opex_usd": float(opex),
        "ebitda_usd": float(rev - cogs - opex),
    }


def cash_runway_months(
    cash: pd.DataFrame, actuals: pd.DataFrame, fx: pd.DataFrame,
    end_year: int, end_month: int, lookback: int = 3, entity: Optional[str] = None
):
    ym_end = pd.Timestamp(year=end_year, month=end_month, day=1)

    # Current cash (convert via FX)
    c = _ensure_cols(cash)
    c = c[c["date"] == ym_end]
    c = _apply_entity(c, entity)
    f = _ensure_cols(fx)
    if not f.empty:
        f = f[["date", "currency", "rate_to_usd"]]
    c = c.merge(f, on=["date", "currency"], how="left")
    c["rate_to_usd"] = pd.to_numeric(c.get("rate_to_usd", 1.0), errors="coerce").fillna(1.0)
    c["amount_usd"] = pd.to_numeric(c.get("amount", 0.0), errors="coerce").fillna(0.0) * c["rate_to_usd"]
    current_cash = float(c["amount_usd"].sum()) if not c.empty else 0.0

    # Compute net burn for last N months
    a = _merge_fx(_ensure_cols(actuals), _ensure_cols(fx))
    a = _apply_entity(a, entity)
    a = a[a["date"] <= ym_end]

    months_sorted = sorted(a["date"].dropna().unique())
    if not months_sorted:
        return {"end": ym_end.strftime("%Y-%m"), "entity": entity, "current_cash_usd": current_cash, "avg_burn_usd": None, "runway_months": None}

    last = months_sorted[-lookback:] if len(months_sorted) >= lookback else months_sorted
    burns = []
    for ts in last:
        dm = a[a["date"] == ts]
        rev = _sum_account_prefix(dm, ("revenue", "sales", "income"))
        cogs = _sum_account_prefix(dm, ("cogs", "cost of goods sold"))
        opex = float(dm[dm["account"].astype(str).str.strip().str.lower().str.startswith("opex:")]["amount_usd"].sum())
        burns.append(opex + cogs - rev)  # positive = cash out

    avg_burn = (sum(burns) / len(burns)) if burns else None
    runway = (current_cash / avg_burn) if (avg_burn and avg_burn > 0) else None

    return {
        "end": ym_end.strftime("%Y-%m"),
        "entity": entity,
        "current_cash_usd": current_cash,
        "avg_burn_usd": float(avg_burn) if avg_burn is not None else None,
        "runway_months": float(runway) if runway is not None else None,
    }


# =========================
# Additional getters
# =========================

def cogs_only(actuals: pd.DataFrame, fx: pd.DataFrame, year: int, month: int, entity: Optional[str] = None):
    a = _merge_fx(_filter_month(actuals, year, month), fx)
    a = _apply_entity(a, entity)
    return {"year": year, "month": month, "entity": entity, "cogs_usd": float(_sum_account_prefix(a, ("cogs", "cost of goods sold")))}


def opex_total(actuals: pd.DataFrame, fx: pd.DataFrame, year: int, month: int, entity: Optional[str] = None):
    a = _merge_fx(_filter_month(actuals, year, month), fx)
    a = _apply_entity(a, entity)
    val = float(a[a["account"].astype(str).str.strip().str.lower().str.startswith("opex:")]["amount_usd"].sum())
    return {"year": year, "month": month, "entity": entity, "opex_usd": val}


def budget_revenue(budget: pd.DataFrame, fx: pd.DataFrame, year: int, month: int, entity: Optional[str] = None):
    b = _merge_fx(_filter_month(budget, year, month), fx)
    b = _apply_entity(b, entity)
    val = float(_sum_account_prefix(b, ("revenue", "sales", "income")))
    return {"year": year, "month": month, "entity": entity, "budget_revenue_usd": val}


def cash_balance(cash: pd.DataFrame, year: int, month: int, entity: Optional[str] = None):
    ym = pd.Timestamp(year=year, month=month, day=1)
    c = _ensure_cols(cash)
    c = c[c["date"] == ym]
    c = _apply_entity(c, entity)
    total = float(pd.to_numeric(c.get("amount", 0.0), errors="coerce").fillna(0.0).sum()) if not c.empty else 0.0
    return {"year": year, "month": month, "entity": entity, "cash_usd": total}


def fx_rate(fx: pd.DataFrame, year: int, month: int, currency: Optional[str]):
    if not currency:
        return {"year": year, "month": month, "currency": None, "rate_to_usd": None}
    ym = pd.Timestamp(year=year, month=month, day=1)
    f = _ensure_cols(fx)
    if f.empty:
        return {"year": year, "month": month, "currency": currency.upper(), "rate_to_usd": None}
    row = f[(f["date"] == ym) & (f["currency"].str.upper() == currency.upper())]
    rate = float(pd.to_numeric(row["rate_to_usd"], errors="coerce").iloc[0]) if not row.empty else None
    return {"year": year, "month": month, "currency": currency.upper(), "rate_to_usd": rate}


def metric_value(actuals, budget, fx, cash, metric: str, year: int, month: int, entity: Optional[str]):
    """Return a single-month value for a named metric (lowercase)."""
    metric = (metric or "").lower()
    if metric in ("revenue", "rev"):
        return revenue_only(actuals, fx, year, month, entity)["revenue_usd"]
    if metric == "cogs":
        return cogs_only(actuals, fx, year, month, entity)["cogs_usd"]
    if metric in ("opex", "opex_total"):
        return opex_total(actuals, fx, year, month, entity)["opex_usd"]
    if metric == "ebitda":
        return ebitda(actuals, fx, year, month, entity)["ebitda_usd"]
    if metric in ("cash", "cash_balance"):
        return cash_balance(cash, year, month, entity)["cash_usd"]
    if metric in ("budget_revenue", "revenue_budget", "budget_rev"):
        return budget_revenue(budget, fx, year, month, entity)["budget_revenue_usd"]
    return None


def metric_series(
    actuals, budget, fx, cash,
    metric: str, start_year: int, start_month: int, end_year: int, end_month: int, entity: Optional[str]
) -> pd.DataFrame:
    """Return month-by-month series for a metric across a period."""
    rng = pd.period_range(
        start=f"{start_year:04d}-{start_month:02d}",
        end=f"{end_year:04d}-{end_month:02d}",
        freq="M",
    )
    rows = []
    for per in rng:
        y, m = per.year, per.month
        rows.append({"date": per.to_timestamp(), "value": metric_value(actuals, budget, fx, cash, metric, y, m, entity)})
    return pd.DataFrame(rows)
