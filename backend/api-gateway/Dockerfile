FROM golang:1.25.4-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o api-gateway ./cmd

FROM alpine:3.18
WORKDIR /app
COPY --from=builder /app/api-gateway .
RUN mkdir -p storage/uploads storage/results
EXPOSE 8080
CMD ["./api-gateway"]
