# Kubernetes local - TrainingHub NativeOps

Ce dossier contient les manifests Kubernetes pour executer le projet en local.

## Prerequis

- Docker Desktop avec Kubernetes active, ou Minikube
- `kubectl`

## Option 1 - Docker Desktop Kubernetes

Construire les images locales :

```powershell
docker build -f infra/docker/user-service.Dockerfile -t user-service:latest .
docker build -f infra/docker/course-service.Dockerfile -t course-service:latest .
```

Deployer :

```powershell
kubectl apply -k k8s
kubectl get pods -n traininghub
```

Exposer les APIs en local :

```powershell
kubectl port-forward -n traininghub service/user-service 5001:5001
kubectl port-forward -n traininghub service/course-service 5002:5002
```

Tester :

```powershell
curl http://localhost:5001/api/v1/users/health
curl http://localhost:5002/api/v1/courses/health
```

## Option 2 - Minikube

Demarrer Minikube :

```powershell
minikube start
```

Construire les images directement dans l'environnement Docker de Minikube :

```powershell
minikube image build -f infra/docker/user-service.Dockerfile -t user-service:latest .
minikube image build -f infra/docker/course-service.Dockerfile -t course-service:latest .
```

Deployer :

```powershell
kubectl apply -k k8s
kubectl get pods -n traininghub
```

## Commandes utiles

```powershell
kubectl get all -n traininghub
kubectl logs -n traininghub deployment/user-service
kubectl logs -n traininghub deployment/course-service
kubectl describe pod -n traininghub -l app=mysql
```

Nettoyer l'environnement :

```powershell
kubectl delete namespace traininghub
```

## Note rapport PFE

Cette configuration represente un deploiement Kubernetes local du MVP :

- `Namespace` dedie : `traininghub`
- `Deployment` et `Service` pour chaque microservice
- `Deployment`, `Service` et `PersistentVolumeClaim` pour MySQL
- `ConfigMap` pour la configuration non sensible
- `Secret` pour les mots de passe et cles JWT
- `readinessProbe` et `livenessProbe` pour verifier la disponibilite des services

Les secrets presents ici sont uniquement destines a un environnement local de demonstration.
