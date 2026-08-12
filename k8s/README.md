# Kubernetes local avec Minikube - TrainingHub

Ce dossier contient les manifests Kubernetes pour executer le projet avec Minikube.
Le deploiement inclut les trois microservices, le portail frontend, MySQL, les
Ingress NGINX, les NetworkPolicy et l'autoscaling HPA des quatre services.

## Prerequis

- Docker Desktop
- Minikube
- `kubectl`

## 1. Demarrer Minikube

```powershell
minikube start --cpus=2 --memory=3072
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
minikube image build -f infra/docker/user-service.Dockerfile -t user-service:pfe-local .
minikube image build -f infra/docker/course-service.Dockerfile -t course-service:pfe-local .
minikube image build -f infra/docker/certificate-service.Dockerfile -t certificate-service:pfe-local .
minikube image build -f infra/docker/frontend-service.Dockerfile -t frontend-service:pfe-local .
```

## 3. Deployer

```powershell
kubectl apply -k k8s
kubectl get pods -n traininghub
kubectl get services -n traininghub
kubectl get ingress -n traininghub
kubectl get hpa -n traininghub
```

Les tags locaux explicites `pfe-local` evitent qu'une ancienne image
`latest` reste dans le cache Minikube. Le workflow CD remplace ces references
par des tags GHCR immuables en production.

Attendre que tous les deploiements soient disponibles :

```powershell
kubectl wait --for=condition=available deployment/user-service -n traininghub --timeout=180s
kubectl wait --for=condition=available deployment/course-service -n traininghub --timeout=180s
kubectl wait --for=condition=available deployment/certificate-service -n traininghub --timeout=180s
kubectl wait --for=condition=available deployment/frontend-service -n traininghub --timeout=180s
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
curl.exe http://traininghub.local/health
```

Si l'Ingress n'est pas accessible avec le pilote Docker sous Windows, lancer
`minikube tunnel` dans un terminal administrateur, conserver ce terminal
ouvert et utiliser l'association suivante :

```text
127.0.0.1 traininghub.local
```

Le tunnel doit rester ouvert pendant les tests. Une alternative sans Ingress
est de suivre la section `Acces alternatif avec port-forward` ci-dessous.

## 5. Verifier l'autoscaling

```powershell
kubectl top pods -n traininghub
kubectl get hpa -n traininghub
```

Le nombre de replicas evolue lorsque la consommation CPU ou memoire depasse les
seuils declares dans les manifests HPA.

## 6. Deployer le monitoring Kubernetes

Prometheus, Grafana et Alertmanager disposent d'un Kustomize separe :

```powershell
kubectl apply -k k8s/monitoring
kubectl get pods -n monitoring
```

La procedure, l'architecture et les port-forward de demonstration sont
documentes dans `monitoring/README.md`.

## Validation effectuee

Le deploiement a ete valide sur Minikube v1.38.1 avec Kubernetes v1.35.1 :

- MySQL et tous les Pods applicatifs en etat `Running` ;
- trois replicas initiaux par microservice, puis reduction automatique a deux
  replicas par les HPA en l'absence de charge ;
- Ingress NGINX disponible sur `traininghub.local` ;
- HPA alimentes par les metriques CPU et memoire ;
- health checks des quatre Services reussis via Ingress ;
- scenario metier complet valide via `traininghub.local` ;
- Prometheus Kubernetes : huit replicas applicatifs decouverts et `UP` ;
- Grafana et Alertmanager deployes dans le namespace `monitoring`.

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
kubectl get all -n monitoring
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
- `Ingress` NGINX avec limite de debit et de taille de requete
- `NetworkPolicy` avec refus entrant par defaut et flux explicitement autorises
- utilisateur non-root fixe, seccomp, filesystem en lecture seule et capabilities supprimees
- annotations Prometheus pour la collecte des quatre endpoints `/metrics`
- stack Prometheus, Grafana et Alertmanager dans un namespace separe

Les secrets presents ici sont uniquement destines a un environnement local de
demonstration et ne doivent jamais etre utilises en production.

## Deploiement continu

L'overlay `overlays/production` exclut volontairement `secret.yaml`. Le workflow
GitHub Actions cree les secrets depuis l'environnement protege `production`,
injecte les tags GHCR immuables, controle les rollouts et execute les smoke
tests. La procedure complete se trouve dans
`../docs/deployment/cd-kubernetes.md`.
