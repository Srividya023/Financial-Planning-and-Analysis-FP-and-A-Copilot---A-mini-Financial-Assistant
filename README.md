# FP&A Copilot (Streamlit)
A mini finance assistant that answers CFO-style questions with numbers and charts.
## Author : Srividya Srinivasula

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
Go to Agent page.
Ask a question in plain English, for example:
“Revenue vs budget for May 2025”
“Gross-margin trend last 6 months”
“OpEx by category for 2025-06”
“Cash runway in months if burn = last 3-mo average”
Read the answer + view the chart.
Adjust your question or month to drill down.

## How it works (brief)
Intent detection parses the question (e.g., “revenue vs budget”).
Router calls the right metric function with parsed month/entity.
Metric function reads from fixtures/data.xlsx, aggregates, and returns:
         1. a concise numeric answer and
         2. a figure object for the chart.
The UI renders both. If something’s missing, it shows a helpful note.
