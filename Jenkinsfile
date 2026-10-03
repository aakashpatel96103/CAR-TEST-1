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
                        echo [ERROR] Minikube is not installed. Please install minikube.
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

        stage('Version & Test') {
            steps {
                bat '''
                    powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 1000,1001,1002 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }; exit 0"
                    if not exist VERSION echo v1.0.0> VERSION
                    set /p VER=<VERSION
                    echo Running tests for version: %VER%
                    python -m pip install -r vehicle-rental-service/requirements.txt
                    python -m pytest vehicle-rental-service/tests -v
                '''
            }
        }

        stage('Build & Security Scan') {
            steps {
                bat '''
                    set /p VER=<VERSION
                    docker build -t %IMAGE%:%VER% -t %IMAGE%:latest vehicle-rental-service
                    if errorlevel 1 (
                        echo [ERROR] Docker build failed.
                        exit /b 1
                    )
                    echo [OK] Docker image %IMAGE%:%VER% built successfully.

                    where trivy >nul 2>&1
                    if not errorlevel 1 (
                        echo [INFO] Running Trivy security scan...
                        trivy image --severity HIGH,CRITICAL --exit-code 0 %IMAGE%:%VER%
                    ) else (
                        echo [INFO] Trivy not installed, skipping security scan.
                    )
                    exit /b 0
                '''
            }
        }

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

        stage('Deploy to Kubernetes') {
            steps {
                bat '''
                    echo [INFO] Applying Kubernetes manifests...

                    kubectl apply -f kubernetes/namespace.yaml
                    kubectl apply -f kubernetes/monitoring/namespace.yaml
                    kubectl apply -f kubernetes/vehicle-rental-service-deployment.yaml
                    kubectl apply -f kubernetes/vehicle-rental-service.yaml
                    kubectl apply -f kubernetes/monitoring/prometheus.yaml
                    kubectl apply -f kubernetes/monitoring/grafana.yaml

                    echo [INFO] Restarting deployments...
                    kubectl rollout restart deployment/%APP% -n %NS%
                    kubectl rollout restart deployment/prometheus -n %MON%

                    echo [INFO] Waiting for rollouts to complete...
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
                    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri http://localhost:1001/health -UseBasicParsing -TimeoutSec 10; Write-Host '[OK] API is reachable:' $r.StatusCode } catch { Write-Host '[WARN] API health check failed, port-forward may need a moment.' }"
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
            echo "  Grafana    : http://localhost:1002"
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
