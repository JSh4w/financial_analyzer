# Portfolio & Net Worth Service

Portfolio management, banking data, and net worth tracking service for the Financial Analyzer application.

## Features

- Portfolio management and tracking
- Bank account integration (Monzo and others)
- Net worth calculations
- Trading data and position tracking
- User management

## API Endpoints

- `GET /` - Service health check
- `GET /health` - Detailed health status
- `GET /portfolio` - Get portfolio data
- `GET /networth` - Get net worth calculation

## Environment Variables

```env
DATABASE_URL=postgresql://user:password@localhost:5432/financial_analyzer
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## Development

```bash
# Install dependencies
poetry install

# Run development server
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

## Docker

```bash
# Build image
docker build -t portfolio-service .

# Run container with database
docker-compose up portfolio-service
```