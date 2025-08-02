# Claude Code Configuration

## Security Preferences
- **NEVER** read or access .env files
- Always ask for configuration information instead of reading sensitive files

## Project Structure
This is a Financial Analyzer application with:
- Frontend: React/TypeScript with Vite
- Backend: Python service with FastAPI
- Additional: Go API service

## Development Guidelines
- Follow existing code conventions in each service
- Use existing libraries and frameworks already present in the codebase
- Always check package.json, pyproject.toml, or go.mod before assuming library availability

## Environment Configuration
- Most frameworks and tools look for .env files by default in the project root
- To provide environment variables:
  * Create a .env file in the project root directory
  * Use specific environment-specific .env files (e.g., .env.development, .env.production)
  * Can also set environment variables directly through the system or deployment platform