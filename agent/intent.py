from __future__ import annotations
import re
from typing import Optional, Tuple

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

def _parse_year_month(q: str) -> Tuple[Optional[int], Optional[int]]:
    """Find YYYY-MM (or YYYY/MM, YYYY.MM) or 'Month YYYY' anywhere in the string."""
    q_sp = q.strip()

    m = re.search(r"\b(20\d{2})[-/\.](0?[1-9]|1[0-2])\b", q_sp)
    if m:
        return int(m.group(1)), int(m.group(2))

    m2 = re.search(r"\b(" + "|".join(MONTHS.keys()) + r")\s+(20\d{2})\b", q_sp, flags=re.I)
    if m2:
        return int(m2.group(2)), MONTHS[m2.group(1).lower()]

    return None, None

def _parse_last_n(q: str) -> Optional[int]:
    m = re.search(r"last\s+(\d+)\s+months?", q, flags=re.I)
    return int(m.group(1)) if m else None

def _parse_entity(q: str) -> Optional[str]:
    m = re.search(r"\bfor\s+([A-Za-z0-9 &/_\-]+)", q, flags=re.I)
    if not m:
        return None
    ent = m.group(1).strip()
    ent = re.sub(r"\bin\s+(20\d{2})([-/\.](0?[1-9]|1[0-2]))?$", "", ent, flags=re.I).strip()
    ent = re.sub(r"(20\d{2})([-/\.](0?[1-9]|1[0-2]))?$", "", ent).strip()
    return ent or None

def _parse_currency(q: str) -> Optional[str]:
    """Prefer 'for <CCY>' as source; else if 'to USD' pick non-USD token; else fall back to 'in/to <CCY>'."""
    q_up = q.upper()
    CURRENCIES = {"USD","EUR","GBP","INR","CAD","AUD","JPY","CHF","CNY"}

    m_for = re.search(r"\bFOR\s+([A-Z]{3})\b", q_up)
    if m_for and m_for.group(1) in CURRENCIES:
        return m_for.group(1)

    if re.search(r"\bTO\s+USD\b", q_up):
        toks = [t for t in re.findall(r"\b([A-Z]{3})\b", q_up) if t in CURRENCIES]
        for t in toks:
            if t != "USD":
                return t

    m = re.search(r"\b(IN|TO)\s+([A-Z]{3})\b", q_up)
    if m and m.group(2) in CURRENCIES:
        return m.group(2)

    return None

def detect_intent(question: str):
    if not question or not question.strip():
        return None, {}, "Please type a finance question or click one of the preset buttons."

    q = question.strip()
    q_low = q.lower()

    year, month = _parse_year_month(q)
    last_n = _parse_last_n(q) or 3
    entity = _parse_entity(q)
    currency = _parse_currency(q)

    if "cash runway" in q_low or "runway" in q_low:
        return "cash_runway", {"year": year, "month": month, "entity": entity}, None

    if (
        "opex" in q_low
        and (
            "breakdown" in q_low or "break down" in q_low
            or "by category" in q_low or "by subcategory" in q_low
            or re.search(r"\bcategory\b", q_low) or re.search(r"\bsubcategory\b", q_low)
        )
    ):
        return "opex_breakdown", {"year": year, "month": month, "entity": entity}, None

    if "opex" in q_low and ("total" in q_low or "overall" in q_low) and "category" not in q_low and "subcategory" not in q_low:
        return "opex_total", {"year": year, "month": month, "entity": entity}, None

    if (("cogs" in q_low and "actual" in q_low) or re.search(r"\bcogs\b", q_low)) and "budget" not in q_low:
        return "cogs_only", {"year": year, "month": month, "entity": entity}, None

    if ("revenue vs budget" in q_low) or ("revenue versus budget" in q_low) or ("variance" in q_low and "revenue" in q_low):
        return "revenue_vs_budget", {"year": year, "month": month, "entity": entity}, None

    if "revenue" in q_low and "budget" not in q_low and "vs" not in q_low and "versus" not in q_low:
        return "revenue_only", {"year": year, "month": month, "entity": entity}, None

    if ("gross margin" in q_low or "gm%" in q_low or "gm %" in q_low) and "trend" in q_low:
        return "gm_trend", {"year": year, "month": month, "last_n": last_n, "entity": entity}, None

    if "ebitda" in q_low:
        return "ebitda", {"year": year, "month": month, "entity": entity}, None

    if "cash balance" in q_low or (q_low.startswith("cash") and "runway" not in q_low):
        return "cash_balance", {"year": year, "month": month, "entity": entity}, None

    if "fx" in q_low or "exchange rate" in q_low or re.search(r"\brate\b.*\bto\b.*\busd\b", q_low):
        return "fx_rate", {"year": year, "month": month, "currency": currency or "USD"}, None

    m_agg = re.search(
        r"\b(sum|avg|average|min|max|diff|pct\s*change)\s+of\s+(revenue|cogs|opex|ebitda|cash|budget(_|\s*)revenue)\b",
        q_low
    )
    if m_agg:
        op = m_agg.group(1).replace("average", "avg").replace("pct ", "pct_")
        metric = m_agg.group(2).replace(" ", "_")
        ln = _parse_last_n(q)
        return "metric_aggregate", {
            "metric": metric,
            "op": op,
            "last_n": ln,
            "year": year,
            "month": month,
            "entity": entity
        }, None

    return None, {}, "I didn’t recognize that. Please ask a finance question (revenue/budget, COGS, Opex, GM%, EBITDA, cash, FX)."
