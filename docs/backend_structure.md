## GO service structure 
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

## Python analysis Service 
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
