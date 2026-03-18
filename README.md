# 💰 ExpenseIQ

> **Smart Personal Finance Tracker** built with Streamlit, Plotly & SQLite

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B?logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-5.x-3F4F75?logo=plotly&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📊 **Dashboard** | 4 KPI cards, monthly bar chart, category donut, heatmap, budget gauges |
| 💸 **Expense Management** | Add/edit/delete with emoji categories, color-coded amounts, CSV import/export |
| 📈 **Analytics** | Category trends, deep-dive, auto-generated insights, yearly heatmap matrix |
| 🎯 **Budget Manager** | Set limits per category, gauge charts, smart 3-month-avg recommendations |
| 🌙 **Dark Mode** | Premium dark theme with accent glows, grid overlay, custom scrollbar |
| ⚡ **Quick Add** | Add expenses from the dashboard without navigating away |
| 📤 **CSV Import/Export** | Bulk import with validation + one-click export |
| 💡 **Smart Insights** | Auto-generated spending analysis with month-over-month comparisons |

---

## 🚀 Quick Start

```bash
# 1. Clone / navigate to the project
cd expense_tracker

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

The app opens at **http://localhost:8501** and seeds 5 demo expenses on first run.

---

## 📁 Project Structure

```
expense_tracker/
├── app.py                  # Streamlit entry point + routing
├── requirements.txt        # Python dependencies
├── README.md
├── db/
│   ├── database.py         # SQLite connection, schema, category seeds
│   └── queries.py          # CRUD + aggregation functions
├── components/
│   ├── sidebar.py          # Navigation, filters, theme toggle
│   ├── dashboard.py        # KPIs, charts, quick-add
│   ├── expenses.py         # Full expense CRUD + CSV import/export
│   ├── analytics.py        # Trends, deep-dive, insights, yearly
│   └── budget.py           # Budget setup, gauges, recommendations
├── utils/
│   ├── charts.py           # 6 Plotly chart factory functions
│   └── helpers.py          # CSS injection, formatting, date utils
├── assets/
│   └── style.css           # Premium dark-mode design system
└── data/
    └── expenses.db         # SQLite database (auto-created)
```

---

## 🛠️ Tech Stack

- **Frontend:** [Streamlit](https://streamlit.io) — rapid Python web apps
- **Charts:** [Plotly](https://plotly.com/python/) — interactive, dark-themed visualisations
- **Database:** SQLite (via Python stdlib `sqlite3`) — zero-config, file-based
- **Data:** [Pandas](https://pandas.pydata.org) — dataframes for queries & transformations
- **Styling:** Custom CSS injected via `st.markdown` — no Tailwind required

---

## 📸 Screenshots

*Coming soon — run the app to see the UI in action!*

---

## 📄 License

MIT — free for personal and educational use.
