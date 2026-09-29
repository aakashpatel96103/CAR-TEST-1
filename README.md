# Vehicle Rental System – DevOps Pipeline

Backend-only FastAPI application for managing vehicles, customers and bookings.

## Features
- Vehicle, customer and booking CRUD
- Jenkins CI/CD
- Artifact versioning
- Docker containerization
- Kubernetes deployment
- Automated deployment and rollback validation
- Prometheus and Grafana monitoring
- Application logging
- pip-audit dependency security scanning
- Trivy container security scanning

## Ports
- Swagger/API: http://localhost:1001/docs
- Health: http://localhost:1001/health
- Metrics: http://localhost:1001/metrics
- Grafana: http://localhost:1002
- Grafana credentials: admin / admin

## Pipeline
GitHub → Jenkins → Tests → Dependency Scan → Docker Build → Trivy → Kubernetes → Health → Metrics → Prometheus → Grafana → Rollback

## Logs
kubectl logs -n vehicle-rental -l app=vehicle-rental-backend
