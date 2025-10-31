# Makefile for BNG Optimiser deployment

# Configuration
PROJECT_ID ?= your-gcp-project-id
REGION ?= europe-west2
REGISTRY ?= gcr.io
IMAGE_TAG ?= latest

# Image names
BACKEND_IMAGE = $(REGISTRY)/$(PROJECT_ID)/bng-backend:$(IMAGE_TAG)
FRONTEND_IMAGE = $(REGISTRY)/$(PROJECT_ID)/bng-frontend:$(IMAGE_TAG)
WORKER_IMAGE = $(REGISTRY)/$(PROJECT_ID)/bng-worker:$(IMAGE_TAG)

.PHONY: help
help:
	@echo "BNG Optimiser Deployment"
	@echo ""
	@echo "Local Development:"
	@echo "  make run               - Run Shiny app with auto-reload"
	@echo "  make local-up          - Start all services locally with docker-compose"
	@echo "  make local-down        - Stop all services"
	@echo "  make local-logs        - View logs from all services"
	@echo ""
	@echo "Build & Push:"
	@echo "  make build-backend     - Build backend Docker image"
	@echo "  make build-frontend    - Build frontend Docker image"
	@echo "  make build-worker      - Build worker Docker image"
	@echo "  make build-all         - Build all Docker images"
	@echo "  make push-all          - Push all images to registry"
	@echo ""
	@echo "Cloud Run Deployment:"
	@echo "  make deploy-backend    - Deploy backend to Cloud Run"
	@echo "  make deploy-frontend   - Deploy frontend to Cloud Run"
	@echo "  make deploy-all        - Deploy all services to Cloud Run"
	@echo ""
	@echo "Fly.io Deployment:"
	@echo "  make fly-deploy        - Deploy to Fly.io"
	@echo ""
	@echo "Configuration:"
	@echo "  PROJECT_ID=$(PROJECT_ID)"
	@echo "  REGION=$(REGION)"

# Shiny Development
.PHONY: run
run:
	shiny run --reload app.py

# Local Development
.PHONY: local-up
local-up:
	docker-compose up -d
	@echo "Services starting..."
	@echo "Frontend: http://localhost:8501"
	@echo "Backend: http://localhost:8000"
	@echo "Backend docs: http://localhost:8000/docs"

.PHONY: local-down
local-down:
	docker-compose down

.PHONY: local-logs
local-logs:
	docker-compose logs -f

.PHONY: local-restart
local-restart: local-down local-up

# Build Images
.PHONY: build-backend
build-backend:
	docker build -t $(BACKEND_IMAGE) -f docker/Dockerfile.backend .
	@echo "Built backend image: $(BACKEND_IMAGE)"

.PHONY: build-frontend
build-frontend:
	docker build -t $(FRONTEND_IMAGE) -f docker/Dockerfile.frontend .
	@echo "Built frontend image: $(FRONTEND_IMAGE)"

.PHONY: build-worker
build-worker:
	docker build -t $(WORKER_IMAGE) -f docker/Dockerfile.worker .
	@echo "Built worker image: $(WORKER_IMAGE)"

.PHONY: build-all
build-all: build-backend build-frontend build-worker

# Push Images
.PHONY: push-backend
push-backend: build-backend
	docker push $(BACKEND_IMAGE)

.PHONY: push-frontend
push-frontend: build-frontend
	docker push $(FRONTEND_IMAGE)

.PHONY: push-worker
push-worker: build-worker
	docker push $(WORKER_IMAGE)

.PHONY: push-all
push-all: push-backend push-frontend push-worker

# Cloud Run Deployment
.PHONY: deploy-backend
deploy-backend: push-backend
	gcloud run deploy bng-backend \
		--image=$(BACKEND_IMAGE) \
		--platform=managed \
		--region=$(REGION) \
		--allow-unauthenticated \
		--min-instances=1 \
		--max-instances=10 \
		--cpu=2 \
		--memory=4Gi \
		--port=8000 \
		--set-env-vars="REDIS_HOST=$$REDIS_HOST,REDIS_PORT=6379" \
		--project=$(PROJECT_ID)
	@echo "Backend deployed to Cloud Run"

.PHONY: deploy-frontend
deploy-frontend: push-frontend
	@echo "Getting backend URL..."
	$(eval BACKEND_URL := $(shell gcloud run services describe bng-backend --region=$(REGION) --format='value(status.url)' --project=$(PROJECT_ID)))
	gcloud run deploy bng-frontend \
		--image=$(FRONTEND_IMAGE) \
		--platform=managed \
		--region=$(REGION) \
		--allow-unauthenticated \
		--min-instances=1 \
		--max-instances=10 \
		--cpu=2 \
		--memory=4Gi \
		--port=8501 \
		--set-env-vars="BACKEND_URL=$(BACKEND_URL)" \
		--project=$(PROJECT_ID)
	@echo "Frontend deployed to Cloud Run"

.PHONY: deploy-all
deploy-all: deploy-backend deploy-frontend
	@echo ""
	@echo "Deployment complete!"
	@echo "Backend: https://bng-backend-<hash>.a.run.app"
	@echo "Frontend: https://bng-frontend-<hash>.a.run.app"

# Fly.io Deployment
.PHONY: fly-deploy
fly-deploy:
	@echo "Deploying to Fly.io..."
	@echo "Make sure you have configured fly.toml for each service"
	cd backend && fly deploy -c fly.backend.toml
	cd frontend && fly deploy -c fly.frontend.toml
	@echo "Deployed to Fly.io"

# Cleanup
.PHONY: clean
clean:
	docker-compose down -v
	docker system prune -f

# Development helpers
.PHONY: test-backend
test-backend:
	@echo "Testing backend API..."
	curl http://localhost:8000/health || echo "Backend not running"

.PHONY: test-frontend
test-frontend:
	@echo "Testing frontend..."
	curl http://localhost:8501/_stcore/health || echo "Frontend not running"

.PHONY: redis-cli
redis-cli:
	docker-compose exec redis redis-cli

.PHONY: worker-logs
worker-logs:
	docker-compose logs -f worker
