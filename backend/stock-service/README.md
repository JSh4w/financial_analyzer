# Stock Market Data Service

Real-time stock market data and websocket service for the Financial Analyzer application.

## Features

- Real-time WebSocket connection to Finnhub API
- Stock subscription management
- Market data processing and storage
- RESTful API for stock data access

## API Endpoints

- `GET /` - Service health check
- `GET /health` - Detailed health status
- `GET /apple` - Get Apple stock data (demo)
- `POST /subscriptions/subscribe` - Subscribe to stock symbol
- `DELETE /subscriptions/unsubscribe` - Unsubscribe from stock symbol
- `GET /subscriptions/list` - Get current subscriptions
- `GET /subscriptions/status` - WebSocket connection status

## Environment Variables

```env
FINNHUB_API_KEY=your_finnhub_api_key
```

## Development

```bash
# Install dependencies
poetry install

# Run development server
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Docker

```bash
# Build image
docker build -t stock-service .

# Run container
docker run -p 8001:8001 -e FINNHUB_API_KEY=your_key stock-service
```