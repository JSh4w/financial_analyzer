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

## Terminal Changes
- Always confirm specific changes before executing commands in the terminal
- Use clear and descriptive commit messages when making changes
- Verify command syntax and potential impacts before running



# Sentry Rules
These examples should be used as guidance when configuring Sentry functionality within a project.

## Error / Exception Tracking

Use `Sentry.captureException(error)` to capture an exception and log the error in Sentry.
Use this in try catch blocks or areas where exceptions are expected

## Tracing Examples

Spans should be created for meaningful actions within an applications like button clicks, API calls, and function calls
Ensure you are creating custom spans with meaningful names and operations
Use the `Sentry.startSpan` function to create a span
Child spans can exist within a parent span

### Custom Span instrumentation in component actions

```javascript
function TestComponent() {
  const handleTestButtonClick = () => {
    // Create a transaction/span to measure performance
    Sentry.startSpan(
      {
        op: "ui.click",
        name: "Test Button Click",
      },
      (span) => {
        const value = "some config";
        const metric = "some metric";

        // Metrics can be added to the span
        span.setAttribute("config", value);
        span.setAttribute("metric", metric);

        doSomething();
      },
    );
  };

  return (
    <button type="button" onClick={handleTestButtonClick}>
      Test Sentry
    </button>
  );
}
```

### Custom span instrumentation in API calls

```javascript
async function fetchUserData(userId) {
  return Sentry.startSpan(
    {
      op: "http.client",
      name: `GET /api/users/${userId}`,
    },
    async () => {
      const response = await fetch(`/api/users/${userId}`);
      const data = await response.json();
      return data;
    },
  );
}
```

## Logs

Where logs are used, ensure Sentry is imported using `import * as Sentry from "@sentry/react"`
Enable logging in Sentry using `Sentry.init({ enableLogs: true })`
Reference the logger using `const { logger } = Sentry`
Sentry offers a consoleLoggingIntegration that can be used to log specific console error types automatically without instrumenting the individual logger calls

### Configuration

#### Baseline

```javascript
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: "https://d13035c07cc79c2d04884d24f8df907d@o4510152998715392.ingest.de.sentry.io/4510153008414800",

  enableLogs: true,
});
```

#### Logger Integration

```javascript
Sentry.init({
  dsn: "https://d13035c07cc79c2d04884d24f8df907d@o4510152998715392.ingest.de.sentry.io/4510153008414800",
  integrations: [
    // send console.log, console.warn, and console.error calls as logs to Sentry
    Sentry.consoleLoggingIntegration({ levels: ["log", "warn", "error"] }),
  ],
});
```

### Logger Examples

`logger.fmt` is a template literal function that should be used to bring variables into the structured logs.

```javascript
logger.trace("Starting database connection", { database: "users" });
logger.debug(logger.fmt`Cache miss for user: ${userId}`);
logger.info("Updated profile", { profileId: 345 });
logger.warn("Rate limit reached for endpoint", {
  endpoint: "/api/results/",
  isEnterprise: false,
});
logger.error("Failed to process payment", {
  orderId: "order_123",
  amount: 99.99,
});
logger.fatal("Database connection pool exhausted", {
  database: "users",
  activeConnections: 100,
});
```