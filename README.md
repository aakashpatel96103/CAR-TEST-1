# Vehicle Rental System – DevOps Pipeline

A containerized FastAPI application to manage **vehicles, customers and bookings**, deployed to Kubernetes through a Jenkins CI/CD pipeline that pulls code from GitHub, with Prometheus + Grafana monitoring, JSON logging, security scanning, versioned artifacts and rollback.

---

## Architecture Overview

- **Vehicle Service**: FastAPI REST API (SQLite database inside the pod) with `/health`, `/ready` and `/metrics`.
- **Containerization**: Docker image tagged `vehicle-service:v<VERSION>-<build>-<git-commit>` (example `v1.0.0-12-a1b2c3d`).
- **Orchestration**: Kubernetes namespace `vehicle-system` with liveness/readiness probes and resource limits.
- **Monitoring**: Prometheus + Grafana in namespace `monitoring`; the dashboard is auto-provisioned.
- **Logging**: JSON logs on stdout (`kubectl logs`).
- **CI/CD**: Jenkins Declarative Pipeline (GitHub -> test -> scan -> build -> deploy -> verify -> rollback on failure).

## Project File Structure

```text
vehicle-rental-devops/
├── vehicle-service/
│   ├── app/                      # FastAPI code (main, models, schemas, database)
│   ├── tests/test_main.py        # pytest tests
│   ├── Dockerfile
│   ├── requirements.txt          # runtime dependencies
│   └── requirements-dev.txt      # + pytest, bandit, pip-audit
├── kubernetes/
│   ├── namespace.yaml
│   ├── vehicle-service-deployment.yaml
│   ├── vehicle-service.yaml
│   └── monitoring/               # namespace, prometheus, grafana (with dashboard)
├── scripts/rollback.bat          # manual rollback
├── Jenkinsfile
├── VERSION                       # 1.0.0
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/`, `/health`, `/ready`, `/metrics` | Status, probes, Prometheus metrics |
| POST / GET | `/vehicles` | Add vehicle / list (`?available=true`) |
| GET / PUT / DELETE | `/vehicles/{id}` | Read, update, delete vehicle |
| POST / GET | `/customers` | Add / list customers |
| GET / PUT / DELETE | `/customers/{id}` | Read, update, delete customer |
| POST / GET | `/bookings` | Create booking (cost = days x daily rate) / list |
| GET | `/bookings/{id}` | Read booking |
| POST | `/bookings/{id}/return` | Return vehicle (booking COMPLETED) |
| POST | `/bookings/{id}/cancel` | Cancel booking |

Swagger UI: `/docs`.

---

## Setup

### 1. Put the project on GitHub
```
git init
git add .
git commit -m "Vehicle rental DevOps pipeline"
git branch -M main
git remote add origin https://github.com/<your-username>/vehicle-rental-devops.git
git push -u origin main
```

### 2. Create the Jenkins job
1. New Item -> **Pipeline** -> OK.
2. Pipeline -> Definition: **Pipeline script from SCM** -> SCM: Git -> Repository URL: your GitHub URL -> Branch `*/main` -> Script Path `Jenkinsfile`.
3. Save -> **Build Now** once (registers the parameters) -> then **Build with Parameters** and check `GIT_URL`.
4. Optional automatic build: GitHub -> Settings -> Webhooks -> `http://<jenkins-host>:8080/github-webhook/`, and tick "GitHub hook trigger for GITScm polling" in the job.

### Prerequisites (same as the earlier build)
Windows Jenkins with Git and Pipeline plugins, **Docker Desktop with Kubernetes enabled**, `kubectl`, Python 3.12+. Trivy runs as a Docker container, nothing extra to install.

---

## CI/CD Pipeline Stages

1. **Checkout from GitHub** – pulls `GIT_URL` / `GIT_BRANCH`.
2. **Generate Artifact Version** – `v<VERSION>-<build>-<commit>`.
3. **Install Dependencies** and **Run Tests** – pytest with a JUnit report.
4. **Security Scan (code + dependencies)** – bandit and pip-audit (build turns UNSTABLE if issues are found).
5. **Build Docker Image** – tagged with the version and `latest`.
6. **Security Scan (image)** – Trivy HIGH/CRITICAL report, archived in Jenkins.
7. **Save Versioned Artifact** – `vehicle-service-<tag>.tar` archived in Jenkins.
8. **Prepare Kubernetes** and **Load Image** into the local cluster.
9. **Deploy Vehicle Service** – `kubectl set image` to the new tag (old versions are kept in the rollout history).
10. **Verify, Health, Metrics** checks and application logs.
11. **Deploy Prometheus and Grafana**, then validate them.
12. **Start Services** – port-forwards for the API and Grafana.
13. **Automatic rollback** – if any stage fails after the deploy started, `kubectl rollout undo` restores the previous version.

## Access after a successful build

| Service | URL | Credentials |
|---|---|---|
| Swagger UI | http://localhost:8001/docs | None |
| Health | http://localhost:8001/health | None |
| Metrics | http://localhost:8001/metrics | None |
| Grafana (dashboard "Vehicle Rental Monitoring") | http://localhost:8002 | `admin` / `admin` |

Create a vehicle, a customer and a booking in Swagger, and the Grafana panels (requests/sec, latency, status codes, 5xx, active bookings, bookings created, running version) start moving.

## Rollback (manual)
```
kubectl rollout history deployment/vehicle-service -n vehicle-system
scripts\rollback.bat          # previous version
scripts\rollback.bat 3        # a specific revision
```
The running version is shown by `http://localhost:8001/health`.

To demo a rollback: run the pipeline twice (two versions), then run `scripts\rollback.bat` and check `/health`.

## Logs
```
kubectl logs -f deployment/vehicle-service -n vehicle-system
```

## Notes
- SQLite lives inside the pod, so data resets when a new version is deployed (fine for a demo). Use PostgreSQL for real data.
- Change the Grafana password (`GF_SECURITY_ADMIN_PASSWORD` in `kubernetes/monitoring/grafana.yaml`) outside a lab.
- The pipeline does not push to Docker Hub; the image is loaded straight into the local Kubernetes cluster like the earlier build.
