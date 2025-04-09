## 1. Project Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                  Single Server                   │
│                                                  │
│  ┌─────────────┐        ┌─────────────────────┐  │
│  │             │        │                     │  │
│  │  Go API     │◄──────►│  Python Analysis    │  │
│  │  (8080)     │        │  Service (5000)     │  │
│  │             │        │                     │  │
│  └─────┬───────┘        └─────────────────────┘  │
│        │                                         │
└────────┼─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│                 │
│ React/TypeScript│
│ Frontend        │
│                 │
└─────────────────┘
```

## 2. Root Directory Structure

```
financial-analyzer/
├── backend/
│   ├── go-api/            # Go service
│   └── python-service/    # Python service
├── frontend/              # TypeScript/React frontend
├── docker-compose.yml     # Development environment setup
├── .github/               # GitHub Actions workflows
├── .gitignore
├── README.md
└── docs/                  # Project documentation
```

## 3. Backend Structure

### Go API Service

```
backend/go-api/
├── cmd/
│   └── api/
│       └── main.go        # Entry point
├── internal/
│   ├── config/            # Configuration
│   ├── handlers/          # HTTP handlers
│   ├── middleware/        # HTTP middleware
│   ├── models/            # Data models
│   └── services/          # Business logic
├── pkg/                   # Shared packages
│   ├── database/          # Database connection
│   └── utils/             # Utility functions
├── Dockerfile
├── go.mod
├── go.sum
└── Makefile               # Build commands
```

### Python Analysis Service

```
backend/python-service/
├── app/
│   ├── __init__.py
│   ├── main.py            # Entry point
│   ├── config.py          # Configuration
│   ├── api/               # API routes
│   │   ├── __init__.py
│   │   └── endpoints/
│   ├── core/              # Core business logic
│   │   ├── __init__.py
│   │   ├── analysis/      # Financial analysis logic
│   │   └── data/          # Data processing
│   ├── models/            # Data models
│   └── utils/             # Utility functions
├── tests/                 # Test cases
├── Dockerfile
├── requirements.txt
└── pyproject.toml         # Python project config
```

## 4. Frontend Structure (TypeScript/React)

```
frontend/
├── public/                # Static files
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── common/        # Shared components
│   │   ├── charts/        # Financial charts
│   │   └── layout/        # Layout components
│   ├── pages/             # Page components
│   ├── hooks/             # Custom React hooks
│   ├── services/          # API service calls
│   ├── store/             # State management
│   ├── types/             # TypeScript type definitions
│   ├── utils/             # Utility functions
│   ├── App.tsx            # Main application
│   ├── index.tsx          # Entry point
│   └── routes.tsx         # Routing configuration
├── .eslintrc.js           # Linting configuration
├── Dockerfile
├── package.json
├── tsconfig.json
└── vite.config.ts         # Using Vite for faster builds
```