# FP&A Copilot (Streamlit)
## Author : Srividya Srinivasula
A mini finance assistant that answers CFO-style questions with numbers and charts.

Two-page, black-and-white FP&A app:
- **Home**: project overview
- **Agent**: ask finance questions against `fixtures/data.xlsx`

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data
Place your Excel at `fixtures/data.xlsx` with sheets: `actuals`, `budget`, `fx`, `cash`.
Columns:
- **actuals/budget**: Month, Entity, Account_category, Amount, Currency (case-insensitive)
- **fx**: month, currency, rate_to_usd
- **cash**: month, entity, cash_usd

## Skills/Stack
Python, Pandas, Streamlit, Plotly/Matplotlib, simple intent routing, Git/GitHub

## How to use (In-app)
- Open **Agent** page.
- Ask a question in plain English, e.g.:
  - `Revenue vs budget for 2025-06`
  - `Gross-margin trend last 6 months`
  - `OpEx by category for 2025-06`
  - `Cash runway in months`
- Get:
  - a concise numeric answer
  - a chart you can read at a glance

## How it works (brief)
- **Intent detection** parses the question (e.g., “revenue vs budget”).
- **Router** maps intent → the right metric function with month/entity.
- **Metric function** reads `fixtures/data.xlsx`, aggregates, and returns:
  - numbers for the answer
  - a figure object for the chart
- **UI** renders results and shows helpful notes if data/sheets are missing.
- **Metric function** reads `fixtures/data.xlsx`, aggregates, and returns:
  - numbers for the answer
  - a figure object for the chart
- **UI** renders results and shows helpful notes if data/sheets are missing.

## Demo
![image_alt](https://github.com/Srividya023/Financial-Planning-and-Analysis-FP-and-A-Copilot---A-mini-Financial-Assistant/blob/9f3eb40a7543dbc01be4706e756cda5566705747/Home%20Page.jpg)

