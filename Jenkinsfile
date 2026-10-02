pipeline {
    agent any

    environment {
        APP   = 'vehicle-rental-service'
        NS    = 'vehicle-rental-system'
        MON   = 'monitoring'
        IMAGE = 'vehicle-rental-service'
    }

    stages {
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
                    where trivy >nul 2>&1 && (
                        trivy image --severity HIGH,CRITICAL --exit-code 0 %IMAGE%:%VER%
                    ) || (
                        echo [INFO] Trivy not installed, skipping security scan.
                    )
                '''
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                bat '''
                    set /p VER=<VERSION
                    docker save -o k8s.tar %IMAGE%:%VER%
                    docker inspect minikube >nul 2>&1 && (
                        echo Loading %IMAGE%:%VER% into minikube...
                        docker cp k8s.tar minikube:/k8s.tar
                        docker exec minikube ctr -n k8s.io images import /k8s.tar
                        docker exec minikube rm -f /k8s.tar
                    )
                    docker inspect desktop-control-plane >nul 2>&1 && (
                        echo Loading %IMAGE%:%VER% into desktop-control-plane...
                        docker cp k8s.tar desktop-control-plane:/k8s.tar
                        docker exec desktop-control-plane ctr -n k8s.io images import /k8s.tar
                        docker exec desktop-control-plane rm -f /k8s.tar
                    )
                    del /f /q k8s.tar 2>nul

                    kubectl apply -f kubernetes/namespace.yaml
                    kubectl apply -f kubernetes/monitoring/namespace.yaml
                    kubectl apply -f kubernetes/vehicle-rental-service-deployment.yaml
                    kubectl apply -f kubernetes/vehicle-rental-service.yaml
                    kubectl apply -f kubernetes/monitoring/prometheus.yaml
                    kubectl apply -f kubernetes/monitoring/grafana.yaml
                    kubectl apply -f kubernetes/monitoring/fluentd.yaml 2>nul || exit /b 0

                    kubectl rollout restart deployment/%APP% -n %NS%
                    kubectl rollout restart deployment/prometheus -n %MON%
                    kubectl rollout status deployment/%APP% -n %NS% --timeout=120s
                    kubectl rollout status deployment/prometheus -n %MON% --timeout=60s
                '''
            }
        }

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
            echo "SERVICES ARE RUNNING SUCCESSFULLY!"
            echo "Prometheus: http://localhost:1000"
            echo "API Docs:   http://localhost:1001/docs"
            echo "Grafana:    http://localhost:1002"
            echo "======================================================="
        }
        failure {
            echo "Pipeline failed! Performing automatic rollback..."
            bat 'kubectl rollout undo deployment/%APP% -n %NS%'
        }
    }
}
