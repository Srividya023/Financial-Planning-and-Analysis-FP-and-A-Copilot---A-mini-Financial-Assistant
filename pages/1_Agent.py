from __future__ import annotations
import streamlit as st
import pandas as pd
from pathlib import Path

from agent.intent import detect_intent
from agent.metrics import (
    latest_year_month,
    revenue_vs_budget, revenue_only, gross_margin_pct_trend,
    opex_by_category, ebitda as ebitda_fn, cash_runway_months,
    cogs_only, opex_total, cash_balance, fx_rate, metric_series
)
from agent.charts import fig_revenue_vs_budget, fig_gm_trend, fig_opex_pie

st.set_page_config(page_title="FP&A Agent", layout="wide")

# --- Theme ---
st.markdown("""
<style>
html, body, .stApp { background:#0b0b0b !important; color:#f5f5f5 !important; }
[data-testid="stSidebarNav"]{ display:none; }
section[data-testid="stSidebar"] { background:#0b0b0b !important; }
section[data-testid="stSidebar"] * { color:#f5f5f5 !important; }
section[data-testid="stSidebar"] .stRadio label { font-weight:700 !important; }
section[data-testid="stSidebar"] .stButton > button {
  width:100%; text-align:left; background:#1b1b1b !important; color:#ffffff !important;
  border:1px solid #3a3a3a !important; border-radius:12px; font-weight:700; padding:.60rem .85rem;
  box-shadow:none !important; opacity:1 !important; filter:none !important; pointer-events:auto !important;
}
section[data-testid="stSidebar"] .stButton > button:hover { background:#242424 !important; border-color:#5a5a5a !important; }
section[data-testid="stSidebar"] .stButton > button:focus { outline:1px solid #8a8a8a !important; }
.stButton > button { background:#ffffff !important; color:#111111 !important; border:1px solid #ffffff !important; border-radius:10px; font-weight:800; padding:.55rem 1.0rem; }
.stButton > button:hover { background:#f2f2f2 !important; }
.stTextInput input, textarea { background:#0f0f0f !important; color:#f5f5f5 !important; border:1px solid #ffffff33 !important; }
h1,h2,h3,h4,h5 { color:#ffffff !important; }
[data-testid="stMetric"] { background:#111; border:1px solid #ffffff22; border-radius:12px; padding:.75rem 1rem; }
[data-testid="stMetric"] * { color:#f5f5f5 !important; }
iframe[title="dataframe"] { filter: invert(1) hue-rotate(180deg) contrast(1.05); }
.stAlert { background:#101010 !important; border:1px solid #ffffff22 !important; color:#ddd !important; }
.stAlert [data-testid="stMarkdownContainer"] * { color:#ddd !important; }
.block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ---------------- Helpers ----------------
def money(x):
    try: return f"${x:,.0f}"
    except Exception: return "n/a"

def _who(entity): return f" for {entity}" if entity else ""

def _explain_no_data(what, year, month, entity=None):
    msg = f"No {what} found for {year}-{month:02d}{_who(entity)}."
    msg += " This usually means there are no matching rows in the source sheets."
    st.warning(msg)

def _use_preset(q: str):
    st.session_state["q"] = q
    st.session_state["do_answer"] = True
    st.rerun()

# ---------------- Load Data ----------------
@st.cache_data
def load_data():
    xls_path = Path(__file__).parents[1]/"fixtures"/"data.xlsx"
    if not xls_path.exists():
        raise FileNotFoundError(f"Missing Excel file at {xls_path}")
    xls = pd.ExcelFile(xls_path)
    def norm(s): return pd.to_datetime(pd.Series(s), errors="coerce")
    def load_sheet(name, cols):
        df = pd.read_excel(xls, name)
        df.columns = [c.lower() for c in df.columns]
        df.rename(columns={"month": "date", "account_category": "account_category"}, inplace=True)
        df["date"] = norm(df["date"])
        return df[cols]
    actuals = load_sheet("actuals", ["date","entity","account_category","currency","amount"])
    budget  = load_sheet("budget",  ["date","entity","account_category","currency","amount"])
    fx      = load_sheet("fx",      ["date","currency","rate_to_usd"])
    cash    = load_sheet("cash",    ["date","entity","cash_usd"])
    cash["currency"] = "USD"; cash["amount"] = cash["cash_usd"]
    return actuals, budget, fx, cash

try:
    actuals, budget, fx, cash = load_data()
except Exception as e:
    st.error(f"Data load error: {e}")
    st.stop()

# ---------------- Sidebar ----------------
latest_a = latest_year_month(actuals, "date")
st.sidebar.title("Sections")
nav_choice = st.sidebar.radio("Navigate", options=("🏠 Home", "🤖 Agent"), index=1)
if nav_choice == "🏠 Home":
    for target in ("Home.py", "pages/0_Home.py", "0_Home.py", "pages/Home.py"):
        try: st.switch_page(target)
        except Exception: continue
    st.sidebar.warning("Home page not found.")

st.sidebar.markdown(f"**Latest month in actuals:** {latest_a[0]}-{latest_a[1]:02d}")
st.sidebar.write("Try:")
PRESETS = [
 "What was 2025-12 revenue vs budget in USD for EMEA?",
 "What was 2025-12 revenue vs budget in USD for ParentCo?",
 "What is our cash runway right now?",
 "Show Gross Margin % trend for the last 3 months.",
 "What was June 2025 revenue vs budget in USD?",
 "Show Opex by subcategory for ParentCo in 2025-12",
]
for i, q in enumerate(PRESETS):
    st.sidebar.button(q, key=f"preset_{i}", use_container_width=True, on_click=_use_preset, args=(q,))

# ---------------- Main ----------------
st.title("FP&A Agent")
st.info(
  "Heads up: this is an MVP, not a full-fledged product. If a question returns no result, "
  "it's likely because the current version isn't fully trained or the data slice doesn't exist for that period/entity.\n\n"
  "This app is trained for finance/FP&A questions only. Please ask about revenue, budget, COGS, Opex, GM%, EBITDA, cash balance/runway, or FX."
)

question = st.text_input("Ask a question:", key="q", value="", placeholder="Type a finance/FP&A question…")
go = st.button("Answer", key="answer_btn")
trigger = go or st.session_state.pop("do_answer", False)

# ---------------- Router ----------------
if trigger:
    q = st.session_state.get("q", "").strip()
    if not q:
        st.info("Please type a finance question or click one of the preset questions on the left.")
        st.stop()

    from agent.intent import detect_intent
    intent, params, err = detect_intent(q)
    if err: st.error(err); st.stop()
    if not intent: st.error("Unsupported question. Please ask finance/FP&A questions."); st.stop()

    y = params.get("year"); m = params.get("month")
    entity = params.get("entity"); currency = params.get("currency")
    last_n = params.get("last_n") or 3
    if not y or not m: y, m = latest_a

    if intent == "revenue_vs_budget":
        res = revenue_vs_budget(actuals, budget, fx, y, m, entity=entity)
        st.caption("Shows actual revenue, budgeted revenue, and the variance for the selected month.")
        st.subheader(f"Revenue vs Budget — {entity or 'Total'} — {y}-{m:02d}")
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Actual (USD)", money(res["revenue_actual_usd"]))
        with c2: st.metric("Budget (USD)", money(res["revenue_budget_usd"]))
        with c3:
            pct = res["pct_vs_budget"]
            st.metric("Variance", money(res["delta_usd"]), f"{pct:.1f}%" if pct is not None else "n/a")
        st.pyplot(fig_revenue_vs_budget(res))

    elif intent == "gm_trend":
        import datetime
        from dateutil.relativedelta import relativedelta
        end = datetime.datetime(y, m, 1)
        start = end - relativedelta(months=last_n - 1)
        df = gross_margin_pct_trend(actuals, fx, start.year, start.month, end.year, end.month, entity=entity)
        st.caption("Gross Margin % = (Revenue − COGS) / Revenue, shown by month.")
        st.subheader(f"Gross Margin % — Last {last_n} Months{_who(entity)}")
        if df.empty or df["gm_pct"].notna().sum() == 0:
            _explain_no_data("GM% values", y, m, entity)
            st.dataframe(df, use_container_width=True)
        else:
            st.pyplot(fig_gm_trend(df.dropna(subset=["gm_pct"])))

    elif intent == "opex_breakdown":
        df = opex_by_category(actuals, fx, y, m, entity=entity)
        st.caption("Opex by subcategory (e.g., Marketing, Sales, R&D, Admin) for the selected month.")
        st.subheader(f"Opex by Subcategory — {entity or 'Total'} — {y}-{m:02d}")
        if df.empty: _explain_no_data("Opex", y, m, entity)
        else:
            st.dataframe(df, use_container_width=True)
            st.pyplot(fig_opex_pie(df))

    elif intent == "ebitda":
        res = ebitda_fn(actuals, fx, y, m, entity=entity)
        st.caption("EBITDA = Revenue − COGS − Opex (proxy).")
        st.subheader(f"EBITDA — {y}-{m:02d}{_who(entity)}")
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Revenue", money(res["revenue_usd"]))
        with c2: st.metric("COGS", money(res["cogs_usd"]))
        with c3: st.metric("Opex", money(res["opex_usd"]))
        with c4: st.metric("EBITDA", money(res["ebitda_usd"]))

    elif intent == "cash_runway":
        res = cash_runway_months(cash, actuals, fx, y, m, 3, entity)
        st.caption("Runway = Cash ÷ average monthly net burn across the last 3 months.")
        st.subheader("Cash & Runway")
        c1, c2 = st.columns(2)
        with c1: st.metric("Cash (USD)", money(res["current_cash_usd"]))
        with c2: st.metric("Avg burn (3m)", money(res["avg_burn_usd"] or 0))
        st.metric("Runway (months)", f"{res['runway_months']:.1f}" if res["runway_months"] else "n/a")

    elif intent == "fx_rate":
        cur = (currency or st.session_state.get("fx_currency") or "USD").strip().upper()
        cur = st.text_input("Currency (3-letter, e.g., EUR, USD, GBP):", value=cur, key="fx_currency").strip().upper()
        if len(cur) != 3:
            st.error("Please enter a valid 3-letter currency code (e.g., EUR, USD, GBP).")
            st.stop()
        res = fx_rate(fx, y, m, cur)
        st.caption("Monthly conversion rate to USD from the FX sheet.")
        st.subheader(f"FX Rate to USD — {cur} — {y}-{m:02d}")
        rate = res.get("rate_to_usd")
        st.metric("Rate", f"1 {cur} = {rate:.4f} USD" if rate is not None else "n/a")
