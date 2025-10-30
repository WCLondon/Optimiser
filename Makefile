# Makefile for BNG Optimiser deployment

# Configuration
PROJECT_ID ?= your-gcp-project
REGION ?= europe-west2
REGISTRY ?= gcr.io

# Image names
BACKEND_IMAGE = $(REGISTRY)/$(PROJECT_ID)/bng-backend:latest
FRONTEND_IMAGE = $(REGISTRY)/$(PROJECT_ID)/bng-frontend:latest
WORKER_IMAGE = $(REGISTRY)/$(PROJECT_ID)/bng-worker:latest

.PHONY: help
help:
	@echo "BNG Optimiser - Deployment Commands"
	@echo ""
	@echo "Local Development:"
	@echo "  make dev            - Start all services with docker-compose"
	@echo "  make dev-down       - Stop all services"
	@echo "  make dev-logs       - View logs from all services"
	@echo ""
	@echo "Build:"
	@echo "  make build-all      - Build all Docker images"
	@echo "  make build-backend  - Build backend image"
	@echo "  make build-frontend - Build frontend image"
	@echo "  make build-worker   - Build worker image"
	@echo ""
	@echo "Cloud Run Deployment:"
	@echo "  make deploy-cloudrun-backend  - Deploy backend to Cloud Run"
	@echo "  make deploy-cloudrun-frontend - Deploy frontend to Cloud Run"
	@echo ""
	@echo "Fly.io Deployment:"
	@echo "  make deploy-fly-backend  - Deploy backend to Fly.io"
	@echo "  make deploy-fly-frontend - Deploy frontend to Fly.io"

# Local Development
.PHONY: dev
dev:
	docker-compose up -d

.PHONY: dev-down
dev-down:
	docker-compose down

.PHONY: dev-logs
dev-logs:
	docker-compose logs -f

.PHONY: dev-rebuild
dev-rebuild:
	docker-compose up -d --build

# Build Images
.PHONY: build-all
build-all: build-backend build-frontend build-worker

.PHONY: build-backend
build-backend:
	docker build -f docker/Dockerfile.backend -t bng-backend:latest .

.PHONY: build-frontend
build-frontend:
	docker build -f docker/Dockerfile.frontend -t bng-frontend:latest .

.PHONY: build-worker
build-worker:
	docker build -f docker/Dockerfile.worker -t bng-worker:latest .

# Push to GCR
.PHONY: push-backend
push-backend: build-backend
	docker tag bng-backend:latest $(BACKEND_IMAGE)
	docker push $(BACKEND_IMAGE)

.PHONY: push-frontend
push-frontend: build-frontend
	docker tag bng-frontend:latest $(FRONTEND_IMAGE)
	docker push $(FRONTEND_IMAGE)

.PHONY: push-worker
push-worker: build-worker
	docker tag bng-worker:latest $(WORKER_IMAGE)
	docker push $(WORKER_IMAGE)

# Cloud Run Deployment
.PHONY: deploy-cloudrun-backend
deploy-cloudrun-backend: push-backend
	gcloud run deploy bng-backend \
		--image $(BACKEND_IMAGE) \
		--platform managed \
		--region $(REGION) \
		--allow-unauthenticated \
		--min-instances 1 \
		--max-instances 10 \
		--memory 2Gi \
		--cpu 2 \
		--set-env-vars REDIS_HOST=$$REDIS_HOST,REDIS_PORT=6379

.PHONY: deploy-cloudrun-frontend
deploy-cloudrun-frontend: push-frontend
	gcloud run deploy bng-frontend \
		--image $(FRONTEND_IMAGE) \
		--platform managed \
		--region $(REGION) \
		--allow-unauthenticated \
		--min-instances 1 \
		--max-instances 5 \
		--memory 4Gi \
		--cpu 2 \
		--port 8501 \
		--set-env-vars BACKEND_URL=$$BACKEND_URL

# Fly.io Deployment
.PHONY: deploy-fly-backend
deploy-fly-backend:
	fly deploy -c fly.backend.toml

.PHONY: deploy-fly-frontend
deploy-fly-frontend:
	fly deploy -c fly.frontend.toml

# Clean
.PHONY: clean
clean:
	docker-compose down -v
	docker system prune -f
