pipeline {
    agent any

    environment {
        APP_NAME = 'vehicle-rental-backend'
        NAMESPACE = 'vehicle-rental'
        MONITORING_NAMESPACE = 'vehicle-monitoring'
        IMAGE = 'vehicle-rental-backend:1.0.0'
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Install Dependencies') {
            steps { bat 'python -m pip install -r backend/requirements.txt' }
        }

        stage('Run Tests') {
            steps {
                bat '''
                    cd backend
                    python -m pytest tests -v
                '''
            }
        }

        stage('Dependency Validation') {
            steps { bat 'python -m pip check' }
        }

        stage('Security Scan - Dependencies') {
            steps {
                bat '''
                    python -m pip install pip-audit
                    python -m pip_audit -r backend/requirements.txt
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                bat '''
                    docker build --no-cache -t %IMAGE% backend
                    docker image inspect %IMAGE% >nul
                    if errorlevel 1 exit /b 1
                '''
            }
        }

        stage('Security Scan - Container') {
            steps {
                bat 'trivy image --severity HIGH,CRITICAL --exit-code 1 %IMAGE%'
            }
        }

        stage('Verify Docker Image') {
            steps {
                bat '''
                    docker run --rm %IMAGE% python --version
                    docker run --rm %IMAGE% python -c "from app.main import app; assert any(r.path == '/health' for r in app.routes); assert any(r.path == '/metrics' for r in app.routes); print('APPLICATION ROUTES OK')"
                '''
            }
        }

        stage('Prepare Kubernetes') {
            steps {
                bat '''
                    kubectl apply -f kubernetes/namespace.yaml
                    kubectl apply -f kubernetes/monitoring/namespace.yaml
                '''
            }
        }

        stage('Load Image Into Kubernetes') {
            steps {
                bat '''
                    for /f "delims=" %%C in ('kubectl config current-context') do (
                        echo Kubernetes context: %%C
                        if /I "%%C"=="minikube" minikube image load %IMAGE%
                        if /I "%%C"=="kind-kind" kind load docker-image %IMAGE%
                    )
                    docker inspect desktop-control-plane >nul 2>&1
                    if not errorlevel 1 (
                        echo Loading %IMAGE% into desktop-control-plane...
                        docker save -o k8s_image.tar %IMAGE%
                        docker cp k8s_image.tar desktop-control-plane:/k8s_image.tar
                        docker exec desktop-control-plane ctr -n k8s.io images import /k8s_image.tar
                        docker exec desktop-control-plane rm -f /k8s_image.tar
                        del /f /q k8s_image.tar
                    )
                    docker image inspect %IMAGE% >nul
                    if errorlevel 1 exit /b 1
                '''
            }
        }

        stage('Deploy Application') {
            steps {
                bat '''
                    kubectl apply -f kubernetes/backend-deployment.yaml
                    kubectl apply -f kubernetes/backend-service.yaml
                    kubectl rollout status deployment/%APP_NAME% -n %NAMESPACE% --timeout=180s
                '''
            }
        }

        stage('Health Check') {
            steps {
                bat '''
                    kubectl exec deployment/%APP_NAME% -n %NAMESPACE% -- python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health'); assert r.status == 200; print(r.read().decode())"
                '''
            }
        }

        stage('API Validation') {
            steps {
                bat '''
                    kubectl exec deployment/%APP_NAME% -n %NAMESPACE% -- python -c "from app.main import app; assert any(r.path == '/vehicles' for r in app.routes); assert any(r.path == '/customers' for r in app.routes); assert any(r.path == '/bookings' for r in app.routes); print('VEHICLE CUSTOMER BOOKING ROUTES OK')"
                '''
            }
        }

        stage('Metrics Check') {
            steps {
                bat '''
                    kubectl exec deployment/%APP_NAME% -n %NAMESPACE% -- python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/metrics'); assert r.status == 200; print('METRICS OK')"
                '''
            }
        }

        stage('Deploy Prometheus') {
            steps {
                bat '''
                    kubectl apply -f kubernetes/monitoring/prometheus.yaml
                    kubectl rollout status deployment/prometheus -n %MONITORING_NAMESPACE% --timeout=180s
                '''
            }
        }

        stage('Deploy Grafana') {
            steps {
                bat '''
                    kubectl apply -f kubernetes/monitoring/grafana.yaml
                    kubectl rollout status deployment/grafana -n %MONITORING_NAMESPACE% --timeout=180s
                '''
            }
        }

        stage('Monitoring Validation') {
            steps {
                bat '''
                    kubectl get pods -n %NAMESPACE%
                    kubectl get pods -n %MONITORING_NAMESPACE%
                    kubectl get services -n %NAMESPACE%
                    kubectl get services -n %MONITORING_NAMESPACE%
                    kubectl exec deployment/prometheus -n %MONITORING_NAMESPACE% -- wget -qO- http://127.0.0.1:9090/-/ready
                    kubectl exec deployment/grafana -n %MONITORING_NAMESPACE% -- wget -qO- http://127.0.0.1:3000/api/health
                '''
            }
        }

        stage('Start Services') {
            steps {
                bat '''
                    set JENKINS_NODE_COOKIE=dontKillMe
                    start "" /B cmd /c "set JENKINS_NODE_COOKIE=dontKillMe&& kubectl port-forward service/vehicle-rental-backend 1001:8000 -n vehicle-rental > vehicle-rental-port-forward.log 2>&1"
                    start "" /B cmd /c "set JENKINS_NODE_COOKIE=dontKillMe&& kubectl port-forward service/grafana 1002:3000 -n vehicle-monitoring > grafana-port-forward.log 2>&1"
                    powershell -NoProfile -Command "Start-Sleep -Seconds 5"
                '''
            }
        }

        stage('Rollback Validation') {
            steps {
                bat '''
                    kubectl rollout history deployment/%APP_NAME% -n %NAMESPACE%
                    kubectl rollout undo deployment/%APP_NAME% -n %NAMESPACE%
                    kubectl rollout status deployment/%APP_NAME% -n %NAMESPACE% --timeout=180s
                '''
            }
        }
    }

    post {
        success {
            echo 'VEHICLE RENTAL CI/CD PIPELINE SUCCESS'
            echo 'Swagger: http://localhost:1001/docs'
            echo 'Health: http://localhost:1001/health'
            echo 'Metrics: http://localhost:1001/metrics'
            echo 'Grafana: http://localhost:1002'
        }
        failure { echo 'VEHICLE RENTAL CI/CD PIPELINE FAILED' }
    }
}