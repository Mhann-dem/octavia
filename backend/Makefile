SHELL := /bin/bash

.PHONY: help dev api worker build up down test-api test-worker logs-api logs-worker

dev:
	@mkdir -p storage/uploads storage/results
	@docker compose -f database/docker-compose.yml up -d

api:
	@cd api-gateway && go run cmd/main.go

worker:
	@cd ai-worker && python app/main.py

build:
	@docker compose build

up:
	@mkdir -p storage/uploads storage/results
	@docker compose up -d

down:
	@docker compose down

test-api:
	@cd api-gateway && go test -v ./...

test-worker:
	@cd ai-worker && pytest -v

logs-api:
	@docker compose logs -f api-gateway

logs-worker:
	@docker compose logs -f ai-worker

help:
	@echo "Available targets:"
	@echo "  dev          - Start database services"
	@echo "  api          - Run API gateway locally"
	@echo "  worker       - Run AI worker locally"
	@echo "  build        - Build Docker images"
	@echo "  up           - Start all services"
	@echo "  down         - Stop all services"
	@echo "  test-api     - Test API gateway"
	@echo "  test-worker  - Test AI worker"
	@echo "  logs-api     - View API logs"
	@echo "  logs-worker  - View worker logs"
