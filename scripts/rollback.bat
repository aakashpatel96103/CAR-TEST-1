@echo off
REM Manual rollback. Usage: scripts\rollback.bat        (previous version)
REM                        scripts\rollback.bat 3      (specific revision)
kubectl rollout history deployment/vehicle-service -n vehicle-system
if "%1"=="" (
    kubectl rollout undo deployment/vehicle-service -n vehicle-system
) else (
    kubectl rollout undo deployment/vehicle-service -n vehicle-system --to-revision=%1
)
kubectl rollout status deployment/vehicle-service -n vehicle-system --timeout=180s
kubectl exec deployment/vehicle-service -n vehicle-system -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"
