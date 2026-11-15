# LucrumStack

A net worth tracker and stock analysis platform: live market data, brokerage holdings and Open Banking balances in one place.

**Live:** [lucrum-stack.vercel.app](https://lucrum-stack.vercel.app) · **Status:** actively developed. Market data, charting, bank and brokerage linking work; the portfolio service and ML pipeline are in progress.

## Features

- **Live stock charts:** Alpaca ticks aggregated into 1-minute OHLCV candles and streamed to the browser over SSE
- **Watchlists:** per-user subscriptions, persisted in Supabase and restored on restart
- **News feed:** real-time financial news, with FinBERT sentiment scoring on Modal GPUs
- **Bank balances:** account linking via GoCardless (Open Banking)
- **Brokerage holdings:** via SnapTrade (Trading212, Vanguard, Interactive Brokers and more)
- **Market regimes:** a 9-state Hidden Markov Model (C++ core, PyBind11 bindings) classifying volatility and trend

## Architecture

```
React + TypeScript (Vercel)
        │  REST + SSE
FastAPI backend (Azure Container Apps)
  ├─ Alpaca WebSocket ──► tick aggregator ──► DuckDB + SSE to clients
  ├─ GoCardless · SnapTrade clients
  └─ Supabase (auth, user data)
        │
Modal (serverless GPU): FinBERT sentiment, HMM training
```

A single upstream Alpaca connection is shared across all users. The subscription manager reference-counts symbols, so a symbol is only dropped upstream when nobody is watching it.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite, Lightweight Charts, ECharts |
| Backend | FastAPI, Python 3.11, DuckDB |
| Data & integrations | Alpaca, GoCardless, SnapTrade, Supabase (auth + Postgres) |
| ML | Modal, FinBERT, HMM (C++/PyBind11) |
| Infra | Docker, Terraform, Azure Container Apps, Vercel, Sentry, GitHub Actions |

## Running Locally

Needs Python 3.11, Node 22, Poetry, and Alpaca + Supabase API keys (GoCardless, SnapTrade and Modal are optional). Put credentials in `backend/stock-service/.env`; see `app/config.py` for the full list.

```bash
# Backend: http://localhost:8001
cd backend/stock-service && poetry install && poetry run uvicorn app.main:app --reload --port 8001

# Frontend: http://localhost:3000
cd frontend && npm install && npm run dev

# Or both together
docker-compose up
```

**Tests:** `cd backend/stock-service && poetry run pytest` (130 tests covering aggregation, storage, subscriptions, auth and API routes).

**Deploy:** the frontend auto-deploys to Vercel. The backend deploys with `terraform/apply.sh`, which runs the tests and then `terraform plan` + `apply`.

## Roadmap

- [ ] Portfolio service: unified holdings and performance tracking
- [ ] Sentiment-driven price prediction (FinBERT + technical indicators → XGBoost) with chart overlays
- [ ] Backtesting framework

## License

MIT
