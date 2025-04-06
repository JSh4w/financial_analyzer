# Development stage
FROM golang:1.21-alpine AS dev

WORKDIR /app

# Install development tools
RUN go install github.com/cosmtrek/air@latest && \
    apk add --no-cache make gcc libc-dev

# Copy Go module files
COPY go.mod go.sum ./
RUN go mod download

# Copy the rest of the source code
COPY . .

# Use air for hot reloading in development
CMD ["air", "-c", ".air.toml"]

# Build stage
FROM golang:1.21-alpine AS build

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /go-api ./cmd/api

# Production stage
FROM alpine:3.18 AS prod

WORKDIR /app

COPY --from=build /go-api /app/go-api

EXPOSE 8080

CMD ["/app/go-api"]