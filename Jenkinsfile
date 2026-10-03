pipeline {
    agent any

    triggers {
        pollSCM('H/2 * * * *')
    }

    options {
        disableConcurrentBuilds()
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }

    environment {
        APP   = 'vehicle-rental-service'
        NS    = 'vehicle-rental-system'
        MON   = 'monitoring'
        IMAGE = 'vehicle-rental-service'
    }

    stages {

        // ──────────────────────────────────────────────────────────────────
        // Stage 1: Preflight — ensure Docker + Minikube are available
        // ──────────────────────────────────────────────────────────────────
        stage('Preflight: Docker & Minikube') {
            steps {
                bat '''
                    echo ======= Preflight Checks =======

                    echo [1/3] Checking Docker...
                    docker info >nul 2>&1
                    if errorlevel 1 (
                        echo [ERROR] Docker is not running. Please start Docker Desktop.
                        exit /b 1
                    )
                    echo [OK] Docker is running.

                    echo [2/3] Checking Minikube...
                    where minikube >nul 2>&1
                    if errorlevel 1 (
                        echo [ERROR] Minikube is not installed.
                        exit /b 1
                    )
                    echo [OK] Minikube is installed.

                    echo [3/3] Ensuring Minikube cluster is running...
                    minikube status >nul 2>&1
                    if errorlevel 1 (
                        echo [INFO] Minikube is not running. Starting it now...
                        minikube start --driver=docker --memory=4096 --cpus=2
                        if errorlevel 1 (
                            echo [ERROR] Failed to start Minikube.
                            exit /b 1
                        )
                    )
                    echo [OK] Minikube cluster is running.

                    kubectl cluster-info >nul 2>&1
                    if errorlevel 1 (
                        echo [ERROR] kubectl cannot connect to the cluster.
                        exit /b 1
                    )
                    echo [OK] kubectl is connected.
                    echo ======= Preflight Complete =======
                '''
            }
        }

        // ──────────────────────────────────────────────────────────────────
        // Stage 2: Version & Test — read VERSION, install deps, run pytest
        // ──────────────────────────────────────────────────────────────────
        stage('Version & Test') {
            steps {
                bat '''
                    powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 1000,1001,1002 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }; exit 0"
                    if not exist VERSION echo v1.0.0> VERSION
                    set /p VER=<VERSION
                    echo ===========================================
                    echo   Running tests for version: %VER%
                    echo ===========================================
                    python -m pip install -r vehicle-rental-service/requirements.txt
                    python -m pytest vehicle-rental-service/tests -v
                '''
            }
        }

        // ──────────────────────────────────────────────────────────────────
        // Stage 3: Build Docker image with version tag
        // ──────────────────────────────────────────────────────────────────
        stage('Build Docker Image') {
            steps {
                bat '''
                    set /p VER=<VERSION
                    echo [INFO] Building Docker image %IMAGE%:%VER%...
                    docker build -t %IMAGE%:%VER% -t %IMAGE%:latest vehicle-rental-service
                    if errorlevel 1 (
                        echo [ERROR] Docker build failed.
                        exit /b 1
                    )
                    echo [OK] Docker image %IMAGE%:%VER% built successfully.
                '''
            }
        }

        // ──────────────────────────────────────────────────────────────────
        // Stage 4: Trivy security scan (HIGH + CRITICAL CVEs)
        // ──────────────────────────────────────────────────────────────────
        stage('Security Scan (Trivy)') {
            steps {
                bat '''
                    set /p VER=<VERSION
                    where trivy >nul 2>&1
                    if not errorlevel 1 (
                        echo [INFO] Running Trivy security scan on %IMAGE%:%VER%...
                        trivy image --severity HIGH,CRITICAL --exit-code 0 --format table %IMAGE%:%VER%
                        echo [OK] Security scan complete.
                    ) else (
                        echo [WARN] Trivy not installed — skipping security scan.
                        echo [WARN] Install with: choco install trivy
                    )
                    exit /b 0
                '''
            }
        }

        // ──────────────────────────────────────────────────────────────────
        // Stage 5: Stamp version into Kubernetes manifests
        // ──────────────────────────────────────────────────────────────────
        stage('Artifact Versioning') {
            steps {
                bat '''
                    set /p VER=<VERSION
                    echo [INFO] Stamping version %VER% into Kubernetes manifests...

                    powershell -NoProfile -Command ^
                        "$v = (Get-Content VERSION).Trim(); ^
                         $dep = 'kubernetes/vehicle-rental-service-deployment.yaml'; ^
                         (Get-Content $dep) -replace 'version: \"v[0-9]+\\.[0-9]+\\.[0-9]+\"', ('version: \"' + $v + '\"') ^
                                            -replace 'image: vehicle-rental-service:v[0-9]+\\.[0-9]+\\.[0-9]+', ('image: vehicle-rental-service:' + $v) ^
                                            -replace 'Deploy version v[0-9]+\\.[0-9]+\\.[0-9]+', ('Deploy version ' + $v) ^
                                            -replace 'value: \"v[0-9]+\\.[0-9]+\\.[0-9]+\"', ('value: \"' + $v + '\"') ^
                         | Set-Content $dep; ^
                         $svc = 'kubernetes/vehicle-rental-service.yaml'; ^
                         (Get-Content $svc) -replace 'version: \"v[0-9]+\\.[0-9]+\\.[0-9]+\"', ('version: \"' + $v + '\"') ^
                         | Set-Content $svc; ^
                         Write-Host '[OK] Manifests stamped with version' $v"
                '''
            }
        }

        // ──────────────────────────────────────────────────────────────────
        // Stage 6: Load Docker image into Minikube's container runtime
        // ──────────────────────────────────────────────────────────────────
        stage('Load Image into Minikube') {
            steps {
                bat '''
                    set /p VER=<VERSION
                    echo [INFO] Loading %IMAGE%:%VER% into Minikube...

                    docker save -o k8s.tar %IMAGE%:%VER%
                    if errorlevel 1 (
                        echo [ERROR] docker save failed.
                        exit /b 1
                    )

                    docker inspect minikube >nul 2>&1 && (
                        echo [INFO] Loading via docker cp into minikube container...
                        docker cp k8s.tar minikube:/k8s.tar
                        docker exec minikube ctr -n k8s.io images import /k8s.tar
                        docker exec minikube rm -f /k8s.tar
                    )

                    where minikube >nul 2>&1 && (
                        echo [INFO] Also loading via minikube image load...
                        minikube image load %IMAGE%:%VER% 2>nul
                    )

                    del /f /q k8s.tar 2>nul
                    echo [OK] Image loaded into Minikube.
                    exit /b 0
                '''
            }
        }

        // ──────────────────────────────────────────────────────────────────
        // Stage 7: Deploy ALL Kubernetes resources
        // ──────────────────────────────────────────────────────────────────
        stage('Deploy to Kubernetes') {
            steps {
                bat '''
                    echo ======= Deploying to Kubernetes =======

                    echo [1/5] Creating namespaces...
                    kubectl apply -f kubernetes/namespace.yaml
                    kubectl apply -f kubernetes/monitoring/namespace.yaml

                    echo [2/5] Deploying application...
                    kubectl apply -f kubernetes/vehicle-rental-service-deployment.yaml
                    kubectl apply -f kubernetes/vehicle-rental-service.yaml

                    echo [3/5] Deploying monitoring stack (Prometheus + Grafana + Fluentd)...
                    kubectl apply -f kubernetes/monitoring/prometheus.yaml
                    kubectl apply -f kubernetes/monitoring/grafana.yaml
                    kubectl apply -f kubernetes/monitoring/fluentd.yaml

                    echo [4/5] Applying security and scaling policies...
                    kubectl apply -f kubernetes/network-policy.yaml
                    kubectl apply -f kubernetes/resource-quota.yaml
                    kubectl apply -f kubernetes/hpa.yaml

                    echo [5/5] Restarting deployments...
                    kubectl rollout restart deployment/%APP% -n %NS%
                    kubectl rollout restart deployment/prometheus -n %MON%

                    echo ======= Waiting for rollouts =======
                    kubectl rollout status deployment/%APP% -n %NS% --timeout=180s
                    if errorlevel 1 (
                        echo [ERROR] %APP% rollout failed.
                        exit /b 1
                    )
                    kubectl rollout status deployment/prometheus -n %MON% --timeout=180s
                    if errorlevel 1 (
                        echo [ERROR] Prometheus rollout failed.
                        exit /b 1
                    )
                    echo [OK] All deployments are healthy.
                '''
            }
        }

        // ──────────────────────────────────────────────────────────────────
        // Stage 8: Verify deployment & rollout history
        // ──────────────────────────────────────────────────────────────────
        stage('Verify & Rollout History') {
            steps {
                bat '''
                    echo ======= Deployment Verification =======

                    echo [INFO] Pods in %NS%:
                    kubectl get pods -n %NS% -o wide

                    echo.
                    echo [INFO] Services in %NS%:
                    kubectl get svc -n %NS%

                    echo.
                    echo [INFO] Pods in %MON%:
                    kubectl get pods -n %MON% -o wide

                    echo.
                    echo [INFO] Rollout history:
                    kubectl rollout history deployment/%APP% -n %NS%

                    echo.
                    echo [INFO] HPA status:
                    kubectl get hpa -n %NS%

                    echo [OK] Verification complete.
                '''
            }
        }

        // ──────────────────────────────────────────────────────────────────
        // Stage 9: Port-forward services for local access
        // ──────────────────────────────────────────────────────────────────
        stage('Start Services') {
            steps {
                bat '''
                    set JENKINS_NODE_COOKIE=dontKillMe
                    powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 1000,1001,1002 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }; exit 0"

                    echo [INFO] Starting port-forward tunnels...
                    start /B kubectl port-forward service/prometheus 1000:1000 -n %MON%
                    start /B kubectl port-forward service/vehicle-rental-service 1001:1001 -n %NS%
                    start /B kubectl port-forward service/grafana 1002:1002 -n %MON%

                    powershell -NoProfile -Command "Start-Sleep -Seconds 5"

                    echo [INFO] Verifying services are reachable...
                    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri http://localhost:1001/health -UseBasicParsing -TimeoutSec 10; Write-Host '[OK] API is reachable — status:' $r.StatusCode } catch { Write-Host '[WARN] API health check pending — port-forward may need a moment.' }"
                    exit /b 0
                '''
            }
        }
    }

    post {
        success {
            echo "======================================================="
            echo "  PIPELINE SUCCEEDED — ALL SERVICES RUNNING!"
            echo "======================================================="
            echo "  Prometheus : http://localhost:1000"
            echo "  API Docs   : http://localhost:1001/docs"
            echo "  Grafana    : http://localhost:1002  (admin/admin)"
            echo "======================================================="
            echo ""
            echo "  Rollback:  kubectl rollout undo deployment/${APP} -n ${NS}"
            echo "  History:   kubectl rollout history deployment/${APP} -n ${NS}"
            echo "======================================================="
        }
        failure {
            echo "Pipeline failed! Attempting automatic rollback..."
            bat '''
                kubectl cluster-info >nul 2>&1
                if errorlevel 1 (
                    echo [WARN] Kubernetes not reachable, skipping rollback.
                ) else (
                    kubectl rollout undo deployment/%APP% -n %NS% 2>nul
                    if not errorlevel 1 (
                        echo [OK] Rollback completed.
                    ) else (
                        echo [WARN] Rollback skipped — no previous revision found.
                    )
                )
                exit /b 0
            '''
        }
        always {
            bat '''
                del /f /q k8s.tar 2>nul
                exit /b 0
            '''
        }
    }
}
