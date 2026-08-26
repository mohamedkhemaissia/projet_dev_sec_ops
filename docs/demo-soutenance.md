# Deroule de demonstration pour la soutenance

Ce scenario tient en environ douze minutes et montre la valeur metier, la
demarche DevSecOps, l'observabilite et l'assistance AIOps.

## Preparation avant l'arrivee du jury

Demarrer Minikube et conserver les terminaux du tunnel et des port-forward
ouverts :

```powershell
minikube start --driver=docker --cpus=2 --memory=3072
minikube tunnel
kubectl port-forward -n monitoring service/grafana 3001:3000
kubectl port-forward -n monitoring service/prometheus 9090:9090
kubectl port-forward -n monitoring service/alertmanager 9093:9093
```

Verifier que `127.0.0.1 traininghub.local` est present dans le fichier `hosts`.

## 1. Introduction - 1 minute

TrainingHub est une plateforme web de gestion de formations construite avec
trois microservices Flask et un service de presentation Jinja2/Bootstrap. Le
projet couvre le cycle complet, depuis le developpement securise jusqu'au
deploiement Kubernetes.

Afficher `docs/diagrams/architecture.md` et presenter :

- le portail web TrainingHub ;
- les trois API et MySQL ;
- Docker et Kubernetes ;
- GitHub Actions et GHCR ;
- Prometheus, Grafana et Alertmanager.

## 2. Controles DevSecOps - 2 minutes

Afficher `.github/workflows/ci.yml`, puis expliquer :

1. Gitleaks recherche les secrets ;
2. Flake8 controle la qualite Python ;
3. Pytest impose 55 % de couverture ;
4. Bandit effectue le SAST ;
5. pip-audit analyse les dependances ;
6. Docker Scout analyse les images ;
7. Trivy analyse le manifeste Kubernetes de production ;
8. les images validees sont publiees dans GHCR ;
9. le CD effectue le rolling update et les smoke tests.

Montrer ensuite un run GitHub Actions vert.

## 3. Kubernetes - 1 minute

```powershell
kubectl get pods -n traininghub
kubectl get hpa -n traininghub
kubectl get pods -n monitoring
```

Tous les pods doivent etre `Running`. Les HPA doivent afficher leurs valeurs
CPU et memoire.

Montrer rapidement :

- probes de disponibilite ;
- limites CPU et memoire ;
- execution non privilegiee ;
- HPA et metrics-server ;
- Ingress et NetworkPolicies ;
- secrets injectes par le CD ;
- rollback en cas d'echec.

## 4. Demonstration fonctionnelle - 4 minutes

Ouvrir `http://traininghub.local`, puis presenter :

1. creation ou connexion du learner ;
2. consultation du catalogue et inscription ;
3. connexion de l'admin et passage a `completed` ;
4. retour dans l'espace learner ;
5. emission et telechargement du certificat ;
6. verification publique avec le code du certificat.

Si le jury demande une preuve automatisee :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-business-scenario.ps1 `
  -UserBaseUrl http://traininghub.local `
  -CourseBaseUrl http://traininghub.local `
  -CertificateBaseUrl http://traininghub.local `
  -FrontendBaseUrl http://traininghub.local
```

## 5. Monitoring, observabilite et AIOps - 3 minutes

Ouvrir :

- Grafana sur `http://localhost:3001`, dashboard
  `TrainingHub - Observability` ;
- Prometheus sur `http://localhost:9090/targets`, avec les huit replicas
  applicatifs et `ai-ops-service` `UP` ;
- Alertmanager sur `http://localhost:9093`.

Expliquer que :

- Prometheus decouvre automatiquement les pods annotes ;
- le dashboard regroupe les cibles par service ;
- `/health` et `/metrics` sont exclus du debit metier ;
- les erreurs 5xx valent zero en absence d'erreur ;
- les alertes couvrent disponibilite, taux 5xx et latence p95.

Montrer enfin le dashboard AIOps : Alertmanager transmet une alerte au service,
qui enrichit le contexte depuis Prometheus, interroge Ollama/Gemma si ce mode est
active et restitue une recommandation a l'operateur humain. Preciser que le
service reste en lecture seule et ne declenche aucune remediation automatique.

## 6. Conclusion - 1 minute

Le MVP est fonctionnel, teste, conteneurise, securise par des controles Shift
Left, deployable automatiquement et supervise apres deploiement avec une
assistance AIOps en lecture seule.

## Solution de secours

Avant la soutenance, conserver des captures :

- pods `traininghub` et `monitoring` ;
- scenario metier entierement vert ;
- run GitHub Actions vert ;
- dashboard Grafana et cibles Prometheus ;
- dashboard AIOps et exemple d'incident analyse ;
- certificat PDF genere.

Si Kubernetes n'est pas disponible, lancer `docker compose up -d` et utiliser
`http://localhost:3000`. Docker Compose et le scenario automatise prouvent le
parcours fonctionnel ; les captures servent alors a expliquer Kubernetes.
