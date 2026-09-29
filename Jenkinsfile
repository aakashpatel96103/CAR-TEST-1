pipeline {
    agent any

    parameters {
        string(name: 'GIT_URL', defaultValue: 'https://github.com/aakashpatel96103/CAR-TEST-1.git', description: 'GitHub repository URL')
        string(name: 'GIT_BRANCH', defaultValue: 'main', description: 'Branch to build')
    }

    environment {
        APP_NAME = 'vehicle-service'
        NAMESPACE = 'vehicle-system'
        MONITORING_NAMESPACE = 'monitoring'
        DEPLOY_STARTED = 'false'
    }

    stages {
        stage('Checkout from GitHub') {
            steps {
                script {
                    if (params.GIT_URL && !params.GIT_URL.contains('<your-username>')) {
                        try {
                            git url: params.GIT_URL, branch: params.GIT_BRANCH
                        } catch (Exception e) {
                            echo "Direct git checkout using ${params.GIT_URL} failed (${e.getMessage()}). Falling back to configured SCM repository."
                            checkout scm
                        }
                    } else {
                        checkout scm
                    }
                }
            }
        }

        stage('Generate Artifact Version') {
            steps {
                script {
                    def version = readFile('VERSION').trim()
                    def commit = bat(returnStdout: true, script: '@git rev-parse --short HEAD').trim()
                    // example: v1.0.0-12-a1b2c3d  (version - build number - git commit)
                    env.IMAGE_TAG = "v${version}-${env.BUILD_NUMBER}-${commit}"
                    env.IMAGE = "${env.APP_NAME}:${env.IMAGE_TAG}"
                    currentBuild.displayName = "#${env.BUILD_NUMBER} ${env.IMAGE_TAG}"
                    echo "=================================================="
                    echo "Target Image: ${env.IMAGE}"
                    echo "=================================================="
                }
            }
        }

        stage('Install Dependencies') {
            steps { bat 'python -m pip install -r vehicle-service/requirements-dev.txt' }
        }

        stage('Run Tests') {
            steps {
                bat '''
                    cd vehicle-service
                    python -m pytest tests -v --junitxml=..\\test-results.xml
                '''
            }
            post { always { junit allowEmptyResults: true, testResults: 'test-results.xml' } }
        }

        stage('Security Scan - Code and Dependencies') {
            steps {
                // build is marked UNSTABLE (not failed) if issues are found
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    bat '''
                        cd vehicle-service
                        python -m bandit -r app -ll
                        python -m pip_audit -r requirements.txt
                    '''
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                bat '''
                    docker build --build-arg APP_VERSION=%IMAGE_TAG% -t %IMAGE% vehicle-service
                    docker tag %IMAGE% %APP_NAME%:latest
                    docker image inspect %IMAGE% >nul
                    if errorlevel 1 exit /b 1
                '''
            }
        }

        stage('Security Scan - Docker Image (Trivy)') {
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    bat '''
                        where trivy >nul 2>&1
                        if not errorlevel 1 (
                            trivy image --severity HIGH,CRITICAL --exit-code 1 --no-progress %IMAGE% > trivy-report.txt 2>&1
                        ) else (
                            docker run --rm -v //var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --severity HIGH,CRITICAL --exit-code 1 --no-progress %IMAGE% > trivy-report.txt 2>&1
                        )
                        set RC=%ERRORLEVEL%
                        type trivy-report.txt
                        exit /b %RC%
                    '''
                }
                archiveArtifacts artifacts: 'trivy-report.txt', allowEmptyArchive: true
            }
        }

        stage('Save Versioned Artifact') {
            steps {
                bat 'docker save -o vehicle-service-%IMAGE_TAG%.tar %IMAGE%'
                archiveArtifacts artifacts: 'vehicle-service-*.tar', fingerprint: true
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
                    for /f "delims=" %%C in ('kubectl config current-context') do set K8S_CONTEXT=%%C
                    echo Kubernetes context: %K8S_CONTEXT%
                    if /I "%K8S_CONTEXT%"=="minikube" minikube image load %IMAGE%
                    if /I "%K8S_CONTEXT%"=="kind-kind" kind load docker-image %IMAGE%
                    docker inspect desktop-control-plane >nul 2>&1
                    if not errorlevel 1 (
                        echo Loading %IMAGE% into desktop-control-plane...
                        docker save -o k8s_image.tar %IMAGE%
                        docker cp k8s_image.tar desktop-control-plane:/k8s_image.tar
                        docker exec desktop-control-plane ctr -n k8s.io images import /k8s_image.tar
                        docker exec desktop-control-plane rm -f /k8s_image.tar
                        del /f /q k8s_image.tar
                    )
                    exit /b 0
                '''
            }
        }

        stage('Deploy Vehicle Service') {
            steps {
                script { env.DEPLOY_STARTED = 'true' }
                bat '''
                    kubectl apply -f kubernetes/vehicle-service-deployment.yaml
                    kubectl apply -f kubernetes/vehicle-service.yaml
                    kubectl set image deployment/%APP_NAME% %APP_NAME%=%IMAGE% -n %NAMESPACE%
                    kubectl annotate deployment/%APP_NAME% -n %NAMESPACE% kubernetes.io/change-cause="deploy %IMAGE%" --overwrite
                    kubectl rollout status deployment/%APP_NAME% -n %NAMESPACE% --timeout=180s
                '''
            }
        }

        stage('Verify Vehicle Service') {
            steps {
                bat '''
                    kubectl get deployment %APP_NAME% -n %NAMESPACE% -o wide
                    kubectl get pods -n %NAMESPACE% -o wide
                    kubectl get service %APP_NAME% -n %NAMESPACE%
                    kubectl rollout history deployment/%APP_NAME% -n %NAMESPACE%
                '''
            }
        }

        stage('Health Check') {
            steps {
                bat '''
                    kubectl exec deployment/%APP_NAME% -n %NAMESPACE% -- python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health'); assert r.status == 200; print(r.read().decode())"
                    kubectl exec deployment/%APP_NAME% -n %NAMESPACE% -- python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/ready'); assert r.status == 200; print(r.read().decode())"
                '''
            }
        }

        stage('Metrics Check') {
            steps {
                bat '''
                    kubectl exec deployment/%APP_NAME% -n %NAMESPACE% -- python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/metrics'); assert r.status == 200; print('METRICS OK'); print(r.read().decode()[:500])"
                '''
            }
        }

        stage('Show Application Logs') {
            steps { bat 'kubectl logs deployment/%APP_NAME% -n %NAMESPACE% --tail=20' }
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
                    kubectl rollout restart deployment/grafana -n %MONITORING_NAMESPACE%
                    kubectl rollout status deployment/grafana -n %MONITORING_NAMESPACE% --timeout=180s
                '''
            }
        }

        stage('Monitoring Validation') {
            steps {
                bat '''
                    kubectl get pods -n %MONITORING_NAMESPACE%
                    kubectl exec deployment/prometheus -n %MONITORING_NAMESPACE% -- wget -qO- http://127.0.0.1:9090/-/ready
                    kubectl exec deployment/grafana -n %MONITORING_NAMESPACE% -- wget -qO- http://127.0.0.1:3000/api/health
                '''
            }
        }

        stage('Start Services') {
            steps {
                bat '''
                    taskkill /F /IM kubectl.exe 2>nul || exit /b 0
                    set JENKINS_NODE_COOKIE=dontKillMe
                    start "" /B cmd /c "set JENKINS_NODE_COOKIE=dontKillMe&& kubectl port-forward service/vehicle-service 8001:8000 -n vehicle-system > vehicle-service-port-forward.log 2>&1"
                    start "" /B cmd /c "set JENKINS_NODE_COOKIE=dontKillMe&& kubectl port-forward service/grafana 8002:3000 -n monitoring > grafana-port-forward.log 2>&1"
                    powershell -NoProfile -Command "Start-Sleep -Seconds 5"
                '''
            }
        }
    }

    post {
        success { echo "PIPELINE SUCCESSFUL - released ${env.IMAGE}" }
        failure {
            script {
                // automatic rollback, only if this run already touched the deployment
                if (env.DEPLOY_STARTED == 'true') {
                    echo 'Deployment failed - rolling back to the previous version'
                    bat '''
                        kubectl rollout undo deployment/%APP_NAME% -n %NAMESPACE%
                        kubectl rollout status deployment/%APP_NAME% -n %NAMESPACE% --timeout=180s
                        exit /b 0
                    '''
                }
            }
            echo 'PIPELINE FAILED'
        }
    }
}
