# Vehicle Rental System – DevOps Pipeline

Version: **v1.0.0**

A FastAPI-based Vehicle Rental System with vehicles, customers and bookings, automated CI/CD through Jenkins, Docker containerization, Kubernetes deployment, rollback support, monitoring, logging and Trivy security scanning.

## Features

- Vehicle CRUD APIs (Create, Read, Update, Delete)
- Customer CRUD APIs (Create, Read, Update, Delete)
- Booking APIs with vehicle/customer validation & availability checks
- FastAPI Swagger documentation (`/docs`)
- Health endpoint with system stats (`/health`)
- Version endpoint (`/version`)
- Application log viewer (`/logs`)
- Prometheus metrics endpoint (`/metrics`)
- Structured JSON logging with request-ID tracing
- Pytest automated test suite (18 tests)
- Multi-stage Docker build with non-root user
- Docker image versioning via `VERSION` file
- Jenkins CI/CD pipeline (9 stages)
- Trivy HIGH/CRITICAL security scanning
- Kubernetes deployment with readiness/liveness/startup probes
- Rolling update strategy with zero-downtime deploys
- Kubernetes rollout history and automatic rollback on failure
- Network policies for pod-level security
- Resource quotas and limits
- Horizontal Pod Autoscaler (HPA)
- Prometheus monitoring with alerting rules
- Grafana observability dashboard (pre-configured)
- Fluentd centralized log aggregation
- CORS support

## Ports

- Prometheus UI: **1000**
- Vehicle Rental API / Swagger: **1001**
- Grafana: **1002**
- Internal container ports: 8000 (app), 9090 (prometheus), 3000 (grafana)

## URLs

```text
http://localhost:1000         (Prometheus UI & Metrics)
http://localhost:1001/        (Vehicle Rental API)
http://localhost:1001/docs    (Swagger UI)
http://localhost:1001/health  (Health Check)
http://localhost:1001/version (Version Info)
http://localhost:1001/logs    (Application Log Viewer)
http://localhost:1001/metrics (Application Prometheus Metrics)
http://localhost:1002         (Grafana Observability Dashboard)
```

## API Endpoints

```text
GET/POST           /vehicles
GET/PUT/DELETE     /vehicles/{vehicle_id}

GET/POST           /customers
GET/PUT/DELETE     /customers/{customer_id}

GET/POST           /bookings
GET/PUT/DELETE     /bookings/{booking_id}

GET  /health       (Health check with counts)
GET  /version      (Application version)
GET  /logs         (Recent application logs)
GET  /metrics      (Prometheus metrics)
```

## CI/CD Pipeline (9 Stages)

```text
1. Preflight: Docker & Minikube  → Verify Docker, auto-start Minikube if stopped
2. Version & Test                → Read VERSION, install deps, run 18 pytest tests
3. Build Docker Image            → Multi-stage build with version tag + latest tag
4. Security Scan (Trivy)         → Scan image for HIGH/CRITICAL CVEs
5. Artifact Versioning           → Stamp version into K8s deployment manifests
6. Load Image into Minikube      → docker save → docker cp → ctr import
7. Deploy to Kubernetes          → Apply all manifests (app + monitoring + policies)
8. Verify & Rollout History      → Show pods, services, HPA, rollout history
9. Start Services                → Port-forward Prometheus(1000), API(1001), Grafana(1002)
```

On a failed pipeline after deployment, Jenkins automatically performs `kubectl rollout undo` for the Vehicle Rental deployment.

### Automation

Jenkins is configured with `pollSCM('H/2 * * * *')` — it automatically polls GitHub every ~2 minutes and triggers a new build whenever changes are detected. Simply push to `main` and the full pipeline runs automatically.

## Rollback

```bash
# Rollback to previous revision
kubectl rollout undo deployment/vehicle-rental-service -n vehicle-rental-system

# Rollback to specific revision
kubectl rollout undo deployment/vehicle-rental-service -n vehicle-rental-system --to-revision=2

# View rollout history
kubectl rollout history deployment/vehicle-rental-service -n vehicle-rental-system
```

## Artifact Versioning

The application version is managed via the `VERSION` file at the project root. The version is:
- Read by the Jenkinsfile to tag Docker images (`vehicle-rental-service:v1.0.0`)
- Dynamically injected into Kubernetes deployment labels, annotations and image tags
- Exposed via the `/version` API endpoint
- Embedded in Kubernetes `change-cause` annotations for rollback tracking
- Passed as `APP_VERSION` environment variable to the container

To release a new version:
1. Update `VERSION` (e.g., `v1.1.0`)
2. Commit and push – Jenkins handles the rest automatically

## Docker

Multi-stage Dockerfile with security hardening:
- **Builder stage** – installs Python dependencies into isolated prefix
- **Runtime stage** – copies only installed packages (no pip/setuptools in final image)
- **Non-root user** (`appuser`) – principle of least privilege
- **HEALTHCHECK** – container-level health monitoring via `/health`
- **Minimal image** – `python:3.12-alpine` base (~50MB)

```bash
# Build manually
docker build -t vehicle-rental-service:v1.0.0 vehicle-rental-service

# Run manually
docker run -p 8000:8000 vehicle-rental-service:v1.0.0
```

## Kubernetes Architecture

| Resource | Namespace | Description |
|---|---|---|
| Deployment (`vehicle-rental-service`) | `vehicle-rental-system` | 2 replicas, rolling updates, resource limits |
| Service (`vehicle-rental-service`) | `vehicle-rental-system` | ClusterIP, ports 1001/8000 |
| NetworkPolicy | `vehicle-rental-system` | Pod-level ingress restriction |
| ResourceQuota | `vehicle-rental-system` | Namespace CPU/memory limits |
| HPA | `vehicle-rental-system` | Auto-scale 2→5 replicas (CPU 70%, Memory 80%) |
| Deployment (`prometheus`) | `monitoring` | Metrics collection + alerting rules |
| Deployment (`grafana`) | `monitoring` | Pre-configured dashboards |
| DaemonSet (`fluentd`) | `monitoring` | Centralized log aggregation |

## Monitoring

### Prometheus
- Scrapes `/metrics` every 15 seconds
- Evaluates alerting rules every 15 seconds
- Alerting rules for: service down, high error rate (>5% 5xx), high latency (>500ms), high memory (>80%)

### Grafana
- Pre-configured datasource (Prometheus)
- Pre-built 13-panel dashboard:
  - **Application Overview** — Service status, total requests, avg latency, memory usage
  - **Traffic & Throughput** — Request rate (QPS), per-endpoint traffic
  - **HTTP Status & Resources** — Status code distribution, latency by endpoint, CPU utilization
  - **API Endpoint Metrics** — Activity summary table, live endpoint traffic
  - **System Probes** — Health check count, Prometheus scrape count
- Default credentials: `admin` / `admin`

### Logging
- Application emits structured JSON logs to stdout
- Fluentd DaemonSet collects container logs from `/var/log/containers/`
- Request-ID tracing via `X-Request-ID` header (auto-generated UUID)
- Response time tracking via `X-Response-Time-ms` header
- In-app log buffer (last 200 entries) accessible via `/logs` endpoint

## Security

- **Trivy scanning** – scans Docker images for HIGH/CRITICAL CVEs in CI pipeline
- **Non-root container** – application runs as `appuser` (not root)
- **Multi-stage build** – no build tools (pip/setuptools) in production image
- **Network policies** – restrict pod ingress to same namespace + monitoring only
- **Resource quotas** – namespace-level CPU/memory caps prevent resource exhaustion
- **Resource limits** – per-container CPU (500m) / memory (256Mi) bounds
- **CORS configuration** – configurable origin restrictions
- **HEALTHCHECK** – Docker-level container health monitoring

## Jenkins

The Jenkinsfile is written for a Windows Jenkins agent and uses `bat` commands. Docker Desktop and Minikube are required (Minikube is auto-started by the pipeline if not running).

### Prerequisites

- Python 3.12+
- Docker Desktop
- Minikube (`choco install minikube`)
- Jenkins with Pipeline plugin
- kubectl configured with cluster access
- Trivy CLI (optional: `choco install trivy`)

## Running Tests Locally

```bash
cd vehicle-rental-service
pip install -r requirements.txt
python -m pytest tests -v
```

## Running Locally (without Docker/K8s)

```bash
cd vehicle-rental-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
