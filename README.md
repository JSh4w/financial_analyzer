# LucrumStack

A net worth tracking and stock analysis platform with real-time market data, brokerage integration, and Open Banking support.

> **Status:** Actively developed. Core market data streaming, charting, and bank linking are functional. Portfolio service and ML prediction pipeline are in progress.

---

## What It Does

- **Live stock charts** — real-time tick data from Alpaca, aggregated into OHLCV candles and streamed to the browser via SSE
- **Persistent watchlists** — subscribe to symbols and they persist across sessions (backed by Supabase)
- **News feed** — real-time financial news streamed from Alpaca's news WebSocket
- **Bank account linking** — connect bank accounts through GoCardless (Open Banking) and view balances in one place
- **Brokerage integration** — pull holdings from brokerages via SnapTrade (Questrade, BMO, etc.)
- **Sentiment analysis** — FinBERT-based sentiment scoring on financial news, run on Modal GPUs
- **Market regime detection** — Hidden Markov Model classifying volatility and trend conditions (C++ core, Python bindings)

---

## Architecture

```
┌──────────────────────────────┐
│  Frontend (React/TypeScript) │
│  Lightweight Charts · SSE    │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│  FastAPI Backend              │
│                               │
│  ├─ WebSocket Manager         │  Alpaca market data stream
│  ├─ Trade Data Aggregator     │  Tick → 1-min OHLCV candles
│  ├─ Subscription Manager      │  Per-user watchlist lifecycle
│  ├─ News Manager              │  Real-time news processing
│  ├─ TradingView Datafeed API  │  UDF-compatible chart data
│  │                            │
│  ├─ GoCardless Client         │  Open Banking integration
│  ├─ SnapTrade Client          │  Multi-broker aggregation
│  │                            │
│  ├─ DuckDB                    │  Columnar market data store
│  └─ Supabase                  │  Auth, user data, watchlists
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│  Modal (Serverless GPU)       │
│  ├─ FinBERT sentiment         │
│  └─ HMM batch training        │
└──────────────────────────────┘
```

### Data Flow

1. Alpaca WebSocket pushes trade ticks to the backend
2. `TradeDataAggregator` buffers ticks and builds 1-minute OHLCV candles per symbol
3. Candles are persisted to DuckDB and broadcast to connected clients via Server-Sent Events
4. The frontend renders candles using TradingView's Lightweight Charts library
5. On first subscription, historical data is backfilled from Alpaca's REST API

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite, Lightweight Charts, ECharts |
| Backend | FastAPI, Uvicorn, Python 3.11+ |
| Market Data | Alpaca WebSocket (IEX / paper trading) |
| Banking | GoCardless (Open Banking API) |
| Brokerage | SnapTrade SDK, Trading212 |
| Database | DuckDB (market data), Supabase (auth + user data) |
| Auth | Supabase Auth, JWT (RS256 via JWKS, HS256 fallback) |
| Streaming | WebSockets (upstream), SSE (downstream to browser) |
| ML | Modal (serverless GPU), FinBERT, HMM (C++/PyBind11) |
| Monitoring | Sentry |
| Deployment | Docker, Azure Container Apps |

---

## Project Structure

```
frontend/
  src/
    components/          UI — Dashboard, Charts, NewsFeed, SearchBar, Login
    services/            API client, TradingView datafeed, Supabase client
    theme/               Design tokens (colours, typography)

backend/
  stock-service/         Primary FastAPI service
    app/
      main.py            Entry point, lifespan events, SSE endpoints
      auth.py            JWT validation (RS256/HS256)
      config.py          Environment configuration
      routes/
        banking.py       GoCardless endpoints
        snaptrade.py     Brokerage endpoints
        t212.py          Trading212 endpoints
      stocks/
        websocket_manager.py      Alpaca WebSocket connection
        subscription_manager.py   Per-user subscription orchestration
        data_aggregator.py        Tick-to-candle aggregation
        stockHandler.py           Per-symbol candle state
        historical_data.py        Backfill from Alpaca REST
        news_websocket.py         News stream
      database/
        connection.py             DuckDB setup
        stock_data_manager.py     OHLCV read/write
        news_data_manager.py      News storage
        external_database_manager.py  Supabase operations
      modal/
        finbert_analysis.py       GPU sentiment analysis
      cpp/hmm/
        src/hmm.cpp               9-state HMM implementation
        setup.py                  PyBind11 build
    models/              Pydantic schemas (trades, quotes, bars)
    tests/               pytest suite (116 tests)

  portfolio-service/     Portfolio tracking (WIP)
  go-api/                Auxiliary Go service (WIP)
```

---

## Key Implementation Details

### WebSocket Subscription Management

The backend maintains a single upstream connection to Alpaca's WebSocket and multiplexes it across users. `SubscriptionManager` maps user-level subscriptions to WebSocket-level subscriptions, tracking subscriber counts so symbols are only unsubscribed from Alpaca when no users are watching. Subscriptions are persisted in Supabase and rehydrated on startup.

### Tick-to-Candle Aggregation

`TradeDataAggregator` receives raw trade ticks and builds 1-minute OHLCV candles in memory. It buffers up to 500 symbols concurrently. Completed candles are written to DuckDB and pushed to all subscribed clients via per-user SSE queues.

### TradingView Datafeed API

The backend exposes a UDF-compatible API (`/api/tradingview/*`) that the frontend's Lightweight Charts consume directly. Historical bars are served from DuckDB, with real-time updates layered on top via SSE.

### Authentication

JWT tokens are validated against Supabase's JWKS endpoint (RS256). For SSE connections where `Authorization` headers aren't available, the token is passed as a query parameter. An HS256 fallback exists for local development.

### HMM Regime Detection

A 9-state Hidden Markov Model classifies market conditions into a 3x3 matrix:
- **Volatility:** low, medium, high
- **Trend:** bearish, neutral, bullish

The core is written in C++ for performance and exposed to Python via PyBind11. Training runs on Modal with rolling windows; inference runs on the server.

### FinBERT Sentiment Analysis

Financial news is scored using [FinBERT](https://huggingface.co/ProsusAI/finbert) (a BERT model fine-tuned on financial text). Inference runs on Modal's T4 GPUs in batches of 8, returning positive/negative/neutral labels with confidence scores.

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Poetry](https://python-poetry.org/) (Python dependency management)
- API keys for: Alpaca Markets, Supabase

Optional: GoCardless credentials (bank linking), SnapTrade credentials (brokerage), Modal account (ML features)

### Environment Variables

Create a `.env` file in `backend/stock-service/` with the required credentials. The backend expects variables for Alpaca, Supabase, and optionally GoCardless, SnapTrade, and Modal. See `app/config.py` for the full list of settings.

### Running Locally

**Backend:**
```bash
cd backend/stock-service
poetry install
poetry run uvicorn app.main:app --reload --port 8001
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Docker (both services):**
```bash
docker-compose up
```

The frontend will be available at `http://localhost:3000` and the backend at `http://localhost:8001`.

### Running Tests

```bash
cd backend/stock-service
poetry run pytest
```

116 tests covering the data aggregator, DuckDB manager, subscription lifecycle, WebSocket handling, and API routes.

---

## API Overview

| Endpoint | Description |
|---|---|
| `GET /api/subscribe/{symbol}` | Subscribe to a symbol (persisted) |
| `DELETE /api/subscribe/{symbol}` | Unsubscribe from a symbol |
| `GET /api/subscriptions` | List current watchlist |
| `GET /stream/{symbol}` | SSE stream of real-time candles |
| `GET /api/snapshot/{symbol}` | Current candle data snapshot |
| `GET /api/tradingview/history` | Historical bars (UDF format) |
| `GET /news/stream` | SSE stream of financial news |
| `GET /banking/institutions` | List available banks |
| `POST /banking/requisition` | Start bank linking flow |
| `GET /banking/all_balances` | All linked bank balances |
| `GET /brokerages/holdings` | Brokerage holdings via SnapTrade |
| `GET /aggregator/status` | Aggregator health and stats |
| `GET /health` | Service health check |

All authenticated endpoints require a `Bearer` token in the `Authorization` header.

---

## Roadmap

- [ ] Portfolio service — unified view of brokerage holdings and performance tracking
- [ ] ML prediction pipeline — sentiment-driven stock movement prediction (FinBERT + technical indicators → XGBoost)
- [ ] Prediction overlays on charts with sentiment gauges
- [ ] Backtesting framework
- [ ] Go API service for auxiliary endpoints

---

## License

MIT
