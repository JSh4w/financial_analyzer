# LucrumStack

A real-time financial analysis platform demonstrating modern async Python patterns, WebSocket streaming, and full-stack development.

## Technical Highlights

- **Async-first FastAPI backend** with WebSocket subscription management
- **Real-time data streaming** via Server-Sent Events (SSE) and WebSocket aggregation
- **DuckDB** for high-performance columnar market data storage
- **Hidden Markov Model** regime detection (C++ implementation, 9-state volatility/trend matrix)
- **FinBERT sentiment analysis** on financial news
- **Modal** for serverless batch compute (model training)
- **JWT authentication** with RS256/JWKS validation via Supabase

## Architecture

```
Frontend (React/TypeScript)
    |
    v
FastAPI Backend
    |
    +-- WebSocket Manager (subscription lifecycle)
    +-- Data Aggregator (tick-to-candle streaming)
    +-- DuckDB (market data persistence)
    +-- Supabase (auth, user data)
    |
    +-- Alpaca Markets WebSocket (live market data)
    +-- GoCardless API (Open Banking)
    |
    v
Modal (serverless)
    +-- HMM batch training (rolling window)
    +-- Historical regime computation
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, TypeScript, Vite, Lightweight Charts |
| Backend | FastAPI, Uvicorn, Python 3.11+ |
| Data | DuckDB, Pandas, NumPy |
| Auth | Supabase, PyJWT (RS256) |
| Streaming | WebSockets, SSE, asyncio |
| ML/Compute | Modal, FinBERT, HMM (C++) |
| Monitoring | Sentry |
| Infrastructure | Docker, Azure Container Apps |

## Project Structure

```
frontend/                   React SPA
backend/
  stock-service/           Primary FastAPI service
    routes/                API endpoints
    services/              Business logic
    core/                  Config, auth, logging
    models/                Pydantic schemas
  portfolio-service/       Portfolio tracking (WIP)
  go-api/                  Auxiliary Go service
```

## Key Implementation Details

### WebSocket Subscription Management
Custom subscription manager handles per-user WebSocket lifecycle, including graceful cleanup and reconnection handling.

### Tick-to-Candle Aggregation
Real-time aggregation of market ticks into OHLCV candles with configurable timeframes, streamed to frontend via SSE.

### HMM Regime Detection
9-state Hidden Markov Model classifying market conditions:
- 3 volatility levels (low, medium, high)
- 3 trend directions (bearish, neutral, bullish)

Rolling retrain on Modal, live inference on server.

### JWT Authentication
RS256 token validation using JWKS endpoint, with HS256 fallback. Middleware extracts and validates tokens on protected routes.

## Running Locally

### Backend
```bash
cd backend/stock-service
poetry install
poetry run uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Docker
```bash
docker-compose up
```

## Configuration

Requires environment variables for:
- Alpaca Markets API credentials
- Supabase project URL and keys
- GoCardless credentials (optional)

## License

MIT
