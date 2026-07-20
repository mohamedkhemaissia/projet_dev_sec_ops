# Kubernetes local avec Minikube - TrainingHub

Ce dossier contient les manifests Kubernetes pour executer le projet avec Minikube.
Le deploiement inclut les trois microservices, MySQL, un Ingress NGINX et
l'autoscaling HPA.

## Prerequis

- Docker Desktop
- Minikube
- `kubectl`

## 1. Demarrer Minikube

```powershell
minikube start --cpus=4 --memory=6144
minikube addons enable metrics-server
minikube addons enable ingress
```

Verifier les addons :

```powershell
minikube addons list
```

## 2. Construire les images dans Minikube

Construire les images directement dans l'environnement de Minikube :

```powershell
minikube image build -f infra/docker/user-service.Dockerfile -t user-service:latest .
minikube image build -f infra/docker/course-service.Dockerfile -t course-service:latest .
minikube image build -f infra/docker/certificate-service.Dockerfile -t certificate-service:latest .
```

## 3. Deployer

```powershell
kubectl apply -k k8s
kubectl get pods -n traininghub
kubectl get services -n traininghub
kubectl get ingress -n traininghub
kubectl get hpa -n traininghub
```

Attendre que tous les deploiements soient disponibles :

```powershell
kubectl wait --for=condition=available deployment/user-service -n traininghub --timeout=180s
kubectl wait --for=condition=available deployment/course-service -n traininghub --timeout=180s
kubectl wait --for=condition=available deployment/certificate-service -n traininghub --timeout=180s
```

## 4. Configurer et tester l'Ingress

Recuperer l'adresse IP :

```powershell
minikube ip
```

Ajouter ensuite cette ligne au fichier
`C:\Windows\System32\drivers\etc\hosts` avec les droits administrateur :

```text
MINIKUBE_IP traininghub.local
```

Remplacer `MINIKUBE_IP` par la valeur retournee, puis tester :

```powershell
curl.exe http://traininghub.local/api/v1/users/health
curl.exe http://traininghub.local/api/v1/courses/health
curl.exe http://traininghub.local/api/v1/certificates/health
```

Si l'Ingress n'est pas accessible avec le pilote Docker sous Windows, lancer
`minikube tunnel` dans un terminal administrateur et refaire les tests.

## 5. Verifier l'autoscaling

```powershell
kubectl top pods -n traininghub
kubectl get hpa -n traininghub
```

Le nombre de replicas evolue lorsque la consommation CPU ou memoire depasse les
seuils declares dans les manifests HPA.

## Acces alternatif avec port-forward

Le port-forward reste disponible pour tester les services sans Ingress :

```powershell
kubectl port-forward -n traininghub service/user-service 5001:5001
kubectl port-forward -n traininghub service/course-service 5002:5002
kubectl port-forward -n traininghub service/certificate-service 5004:5004
```

## Commandes utiles

```powershell
kubectl get all -n traininghub
kubectl logs -n traininghub deployment/user-service
kubectl logs -n traininghub deployment/course-service
kubectl logs -n traininghub deployment/certificate-service
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
- `Secret` pour les mots de passe et cles JWT de la demonstration locale
- `readinessProbe` et `livenessProbe` pour verifier la disponibilite des services
- `HorizontalPodAutoscaler` pour adapter le nombre de replicas
- `Ingress` NGINX pour exposer les trois APIs sous `traininghub.local`

Les secrets presents ici sont uniquement destines a un environnement local de
demonstration et ne doivent jamais etre utilises en production.
