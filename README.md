# FP&A Copilot (Streamlit)
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
