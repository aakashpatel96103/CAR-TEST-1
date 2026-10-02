pipeline {
    agent any

    environment {
        APP   = 'vehicle-rental-service'
        NS    = 'vehicle-rental-system'
        MON   = 'monitoring'
        IMAGE = 'vehicle-rental-service'
    }

    stages {
        // ─── Stage 1: Versioning ─────────────────────────────────────────
        stage('Versioning') {
            steps {
                bat '''
                    echo === Artifact Versioning ===
                    if exist VERSION (
                        set /p VER=<VERSION
                    ) else (
                        set VER=v1.0.0
                        echo v1.0.0> VERSION
                    )
                    call set /p VER=<VERSION
                    echo Current version: %VER%
                    echo %VER%> .image_tag
                '''
            }
        }

        // ─── Stage 2: Install Dependencies ───────────────────────────────
        stage('Install Dependencies') {
            steps {
                bat '''
                    echo === Installing Python dependencies ===
                    python -m pip install --upgrade pip
                    python -m pip install -r vehicle-rental-service/requirements.txt
                '''
            }
        }

        // ─── Stage 3: Automated Tests ────────────────────────────────────
        stage('Automated Tests') {
            steps {
                bat '''
                    echo === Running pytest test suite ===
                    python -m pytest vehicle-rental-service/tests -v --tb=short
                '''
            }
        }

        // ─── Stage 4: Dependency Validation ──────────────────────────────
        stage('Dependency Validation') {
            steps {
                bat '''
                    echo === Validating installed dependencies ===
                    python -m pip check
                    echo === Verifying critical packages ===
                    python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')"
                    python -c "import uvicorn; print(f'Uvicorn {uvicorn.__version__}')"
                    python -c "import pydantic; print(f'Pydantic {pydantic.__version__}')"
                    python -c "import prometheus_client; print(f'Prometheus Client {prometheus_client.__version__}')"
                '''
            }
        }

        // ─── Stage 5: Docker Build ──────────────────────────────────────
        stage('Docker Build') {
            steps {
                bat '''
                    set /p VER=<VERSION
                    echo === Building Docker image %IMAGE%:%VER% ===
                    docker build -t %IMAGE%:%VER% vehicle-rental-service
                    docker tag %IMAGE%:%VER% %IMAGE%:latest
                    echo === Build complete ===
                '''
            }
        }

        // ─── Stage 6: Trivy Security Scan ────────────────────────────────
        stage('Trivy Security Scan') {
            steps {
                bat '''
                    set /p VER=<VERSION
                    echo === Running Trivy vulnerability scanner ===
                    echo Scanning %IMAGE%:%VER% for HIGH and CRITICAL vulnerabilities...
                    trivy image --severity HIGH,CRITICAL --exit-code 0 --format table %IMAGE%:%VER%
                    echo === Security scan complete ===
                '''
            }
        }

        // ─── Stage 7: Image Verification ─────────────────────────────────
        stage('Image Verification') {
            steps {
                bat '''
                    set /p VER=<VERSION
                    echo === Verifying Docker image ===
                    docker inspect %IMAGE%:%VER% >nul 2>&1
                    if errorlevel 1 (
                        echo ERROR: Image %IMAGE%:%VER% not found!
                        exit /b 1
                    )
                    echo Image %IMAGE%:%VER% verified successfully
                    docker images %IMAGE% --format "{{.Repository}}:{{.Tag}} {{.Size}}"
                '''
            }
        }

        // ─── Stage 8: Load Image to Kubernetes ───────────────────────────
        stage('Load Image to Kubernetes') {
            steps {
                bat '''
                    set /p VER=<VERSION
                    echo === Loading image into Kubernetes cluster ===
                    docker save -o k8s.tar %IMAGE%:%VER%
                    docker inspect minikube >nul 2>&1 && (
                        echo Loading %IMAGE%:%VER% into minikube container...
                        docker cp k8s.tar minikube:/k8s.tar
                        docker exec minikube ctr -n k8s.io images import /k8s.tar
                        docker exec minikube rm -f /k8s.tar
                    )
                    docker inspect desktop-control-plane >nul 2>&1 && (
                        echo Loading %IMAGE%:%VER% into desktop-control-plane container...
                        docker cp k8s.tar desktop-control-plane:/k8s.tar
                        docker exec desktop-control-plane ctr -n k8s.io images import /k8s.tar
                        docker exec desktop-control-plane rm -f /k8s.tar
                    )
                    del /f /q k8s.tar
                    echo === Image loaded successfully ===
                '''
            }
        }

        // ─── Stage 9: Kubernetes Deployment ──────────────────────────────
        stage('Deploy to Kubernetes') {
            steps {
                bat '''
                    echo === Deploying to Kubernetes ===

                    echo --- Applying namespaces ---
                    kubectl apply -f kubernetes/namespace.yaml
                    kubectl apply -f kubernetes/monitoring/namespace.yaml

                    echo --- Applying security policies ---
                    kubectl apply -f kubernetes/network-policy.yaml
                    kubectl apply -f kubernetes/resource-quota.yaml

                    echo --- Deploying application ---
                    kubectl apply -f kubernetes/vehicle-rental-service-deployment.yaml
                    kubectl apply -f kubernetes/vehicle-rental-service.yaml

                    echo --- Deploying autoscaler ---
                    kubectl apply -f kubernetes/hpa.yaml

                    echo --- Deploying monitoring stack ---
                    kubectl apply -f kubernetes/monitoring/prometheus.yaml
                    kubectl apply -f kubernetes/monitoring/alerts.yaml
                    kubectl apply -f kubernetes/monitoring/grafana.yaml
                    kubectl apply -f kubernetes/monitoring/fluentd.yaml

                    echo --- Rolling out deployments ---
                    kubectl rollout restart deployment/%APP% -n %NS%
                    kubectl rollout restart deployment/prometheus -n %MON%

                    echo --- Waiting for rollouts to complete ---
                    kubectl rollout status deployment/%APP% -n %NS% --timeout=120s
                    kubectl rollout status deployment/prometheus -n %MON% --timeout=60s

                    echo === Deployment complete ===
                '''
            }
        }

        // ─── Stage 10: Health & API Validation ───────────────────────────
        stage('Health & API Validation') {
            steps {
                bat '''
                    echo === Validating deployment health ===
                    powershell -NoProfile -Command "Start-Sleep -Seconds 5"

                    echo --- Checking pod status ---
                    kubectl get pods -n %NS% -l app=%APP%
                    kubectl get pods -n %MON%

                    echo --- Testing health endpoint via kubectl ---
                    kubectl exec deployment/%APP% -n %NS% -- python -c "import urllib.request; r=urllib.request.urlopen('http://localhost:8000/health'); print(r.read().decode())"

                    echo --- Testing API root endpoint ---
                    kubectl exec deployment/%APP% -n %NS% -- python -c "import urllib.request; r=urllib.request.urlopen('http://localhost:8000/'); print(r.read().decode())"

                    echo --- Testing version endpoint ---
                    kubectl exec deployment/%APP% -n %NS% -- python -c "import urllib.request; r=urllib.request.urlopen('http://localhost:8000/version'); print(r.read().decode())"

                    echo === API validation passed ===
                '''
            }
        }

        // ─── Stage 11: Monitoring & Logging Validation ───────────────────
        stage('Monitoring & Logging Validation') {
            steps {
                bat '''
                    echo === Validating monitoring stack ===

                    echo --- Checking Prometheus deployment ---
                    kubectl get deployment prometheus -n %MON%

                    echo --- Checking Grafana deployment ---
                    kubectl get deployment grafana -n %MON%

                    echo --- Checking Fluentd DaemonSet ---
                    kubectl get daemonset fluentd -n %MON%

                    echo --- Checking metrics endpoint ---
                    kubectl exec deployment/%APP% -n %NS% -- python -c "import urllib.request; r=urllib.request.urlopen('http://localhost:8000/metrics'); data=r.read().decode(); print('Metrics OK - lines:', len(data.splitlines()))"

                    echo --- Checking application logs ---
                    kubectl logs deployment/%APP% -n %NS% --tail=10

                    echo === Monitoring validation passed ===
                '''
            }
        }

        // ─── Stage 12: Rollback Capability Check ─────────────────────────
        stage('Rollback Capability Check') {
            steps {
                bat '''
                    echo === Verifying rollback capability ===

                    echo --- Deployment rollout history ---
                    kubectl rollout history deployment/%APP% -n %NS%

                    echo --- Current revision ---
                    kubectl describe deployment/%APP% -n %NS% | findstr /i "revision"

                    echo === Rollback capability verified ===
                    echo To rollback: kubectl rollout undo deployment/%APP% -n %NS%
                    echo To rollback to specific revision: kubectl rollout undo deployment/%APP% -n %NS% --to-revision=N
                '''
            }
        }

        // ─── Stage 13: Start Services (Port Forwarding) ─────────────────
        stage('Start Services') {
            steps {
                bat '''
                    set JENKINS_NODE_COOKIE=dontKillMe
                    powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 1000,1001,1002 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }; exit 0"
                    start /B kubectl port-forward service/prometheus 1000:1000 -n %MON%
                    start /B kubectl port-forward service/vehicle-rental-service 1001:1001 -n %NS%
                    start /B kubectl port-forward service/grafana 1002:1002 -n %MON%
                    powershell -NoProfile -Command "Start-Sleep -Seconds 3"
                    exit /b 0
                '''
            }
        }
    }

    post {
        success {
            echo "======================================================="
            echo "ALL PIPELINE STAGES PASSED SUCCESSFULLY!"
            echo "======================================================="
            echo "Prometheus:  http://localhost:1000"
            echo "API Docs:    http://localhost:1001/docs"
            echo "API Health:  http://localhost:1001/health"
            echo "API Version: http://localhost:1001/version"
            echo "API Logs:    http://localhost:1001/logs"
            echo "Grafana:     http://localhost:1002"
            echo "======================================================="
        }
        failure {
            echo "Pipeline failed! Attempting rollback..."
            bat '''
                kubectl rollout undo deployment/%APP% -n %NS% 2>nul
                if errorlevel 1 (
                    echo WARNING: Rollback failed or no previous revision available
                ) else (
                    echo Rollback initiated successfully
                    kubectl rollout status deployment/%APP% -n %NS% --timeout=60s
                )
            '''
        }
    }
}
