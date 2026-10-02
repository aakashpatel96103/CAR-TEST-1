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
- Pytest automated test suite (17+ tests)
- Multi-stage Docker build with non-root user
- Docker image versioning via `VERSION` file
- Jenkins CI/CD pipeline (13 stages)
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

## CI/CD Pipeline

```text
1. Version & Test       → Read VERSION, install dependencies, run pytest
2. Build & Scan         → Docker build with version tag & Trivy security scan
3. Deploy to Kubernetes → Load image, deploy app & monitoring stack, verify rollout
4. Start Services       → Port forward Prometheus (1000), App (1001), Grafana (1002)
```

On a failed pipeline after deployment, Jenkins automatically performs `kubectl rollout undo` for the Vehicle Rental deployment.

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
- Read by the Jenkinsfile to tag Docker images
- Injected into Kubernetes deployment labels and annotations
- Exposed via the `/version` API endpoint
- Embedded in Kubernetes `change-cause` annotations for rollback tracking

To release a new version:
1. Update `VERSION` (e.g., `v1.1.0`)
2. Commit and push – Jenkins handles the rest

## Docker

Multi-stage Dockerfile with security hardening:
- **Builder stage** – installs Python dependencies
- **Runtime stage** – copies only what's needed
- **Non-root user** (`appuser`) – principle of least privilege
- **HEALTHCHECK** – container-level health monitoring
- **Minimal image** – `python:3.12-slim` base

## Kubernetes Architecture

| Resource | Namespace | Description |
|---|---|---|
| Deployment (`vehicle-rental-service`) | `vehicle-rental-system` | 2 replicas, rolling updates |
| Service (`vehicle-rental-service`) | `vehicle-rental-system` | ClusterIP, ports 1001/8000 |
| NetworkPolicy | `vehicle-rental-system` | Pod-level ingress restriction |
| ResourceQuota | `vehicle-rental-system` | Namespace resource limits |
| HPA | `vehicle-rental-system` | Auto-scale 2→5 replicas |
| Deployment (`prometheus`) | `monitoring` | Metrics collection |
| Deployment (`grafana`) | `monitoring` | Dashboards |
| DaemonSet (`fluentd`) | `monitoring` | Log aggregation |
| ConfigMap (`prometheus-alerts`) | `monitoring` | Alerting rules |

## Monitoring

### Prometheus
- Scrapes `/metrics` every 15 seconds
- Alerting rules for: service down, high error rate, high latency, high memory

### Grafana
- Pre-configured datasource (Prometheus)
- Pre-built dashboard: Application Overview, Traffic & Throughput, HTTP Status & Resources, API Endpoint Metrics
- Default credentials: `admin` / `admin`

### Logging
- Application emits structured JSON logs to stdout
- Fluentd DaemonSet collects container logs
- Request-ID tracing via `X-Request-ID` header
- In-app log buffer accessible via `/logs` endpoint

## Security

- **Trivy scanning** – scans Docker images for HIGH/CRITICAL CVEs
- **Non-root container** – application runs as `appuser`
- **Network policies** – restrict pod-to-pod traffic
- **Resource quotas** – prevent resource exhaustion
- **Resource limits** – per-container CPU/memory bounds
- **CORS configuration** – configurable origin restrictions

## Jenkins

The Jenkinsfile is written for a Windows Jenkins agent and uses `bat` commands. Docker Desktop and a working Kubernetes context (minikube or Docker Desktop Kubernetes) are required.

### Prerequisites

- Python 3.12+
- Docker Desktop (with Kubernetes enabled) or minikube
- Jenkins with Pipeline plugin
- Trivy CLI (`choco install trivy` or manual install)
- kubectl configured with cluster access

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
