# Shift Right et observabilite de TrainingHub

## Objectif

Le Shift Left detecte les defauts avant le deploiement. Le Shift Right observe
le comportement reel de l'application apres son deploiement et renvoie un
feedback exploitable vers l'equipe.

TrainingHub couvre maintenant les deux directions :

- Shift Left : Gitleaks, Flake8, Pytest, Bandit, pip-audit, Trivy IaC et Docker
  Scout ;
- Shift Right : metriques applicatives, dashboard, alertes, logs structures,
  health checks, smoke tests, rollback et DAST OWASP ZAP.

## Architecture

```mermaid
flowchart LR
    Users[Utilisateurs] --> App[TrainingHub]
    App --> Metrics[/Endpoint metrics/]
    App --> Logs[Logs JSON avec request_id]
    Prom[Prometheus] -->|scrape 15 s| Metrics
    Prom --> Grafana[Dashboard Grafana]
    Prom --> Rules[Regles d'alerte]
    Rules --> Alertmanager[Alertmanager]
    Alertmanager --> Feedback[Feedback et remediation]
    CD[CD Kubernetes] --> App
    CD --> ZAP[OWASP ZAP Baseline]
    ZAP --> Report[Rapport DAST]
```

## Demarrage local

```powershell
docker compose up --build -d
docker compose ps
```

Interfaces :

| Composant | URL | Utilite |
| --- | --- | --- |
| TrainingHub | `http://localhost:3000` | Application |
| Prometheus | `http://localhost:9090` | Cibles, requetes et alertes |
| Grafana | `http://localhost:3001` | Dashboard `TrainingHub - Shift Right` |
| Alertmanager | `http://localhost:9093` | Alertes actives et resolues |

Grafana autorise la consultation anonyme en lecture seule. Le compte
d'administration local par defaut est `admin` / `admin`; il doit etre remplace
avec `GRAFANA_ADMIN_USER` et `GRAFANA_ADMIN_PASSWORD` hors demonstration locale.

## Monitoring dans Kubernetes

Une stack legere est egalement deployee dans le namespace `monitoring`.
Prometheus utilise la decouverte Kubernetes pour collecter chaque replica
`Running` annote dans `traininghub`. Grafana et Alertmanager communiquent avec
Prometheus par les Services internes du cluster.

```powershell
kubectl apply -k k8s/monitoring
kubectl get pods -n monitoring
kubectl port-forward -n monitoring service/grafana 3001:3000
```

La documentation complete se trouve dans `../k8s/monitoring/README.md`.

## Metriques exposees

Chaque service fournit `GET /metrics` :

- `traininghub_http_requests_total` : volume par service, methode, route et
  statut ;
- `traininghub_http_request_duration_seconds` : histogramme de latence ;
- `traininghub_http_requests_in_progress` : requetes en cours ;
- metriques standard du processus Python.

Exemples PromQL :

```promql
sum by (service) (rate(traininghub_http_requests_total[5m]))
```

```promql
sum by (service) (rate(traininghub_http_requests_total{status=~"5.."}[5m]))
```

```promql
histogram_quantile(
  0.95,
  sum by (le, service) (
    rate(traininghub_http_request_duration_seconds_bucket[5m])
  )
)
```

## Alertes implementees

- service indisponible pendant plus d'une minute ;
- taux de reponses 5xx superieur a 5 % pendant deux minutes ;
- latence p95 superieure a une seconde pendant cinq minutes.

Pour demontrer une alerte, arreter temporairement un service :

```powershell
docker compose stop course-service
```

Attendre environ une minute, puis ouvrir Prometheus ou Alertmanager. Relancer
ensuite immediatement le service :

```powershell
docker compose start course-service
```

## Logs et correlation

Chaque reponse contient `X-Request-ID`. Chaque service produit un log JSON avec
le meme identifiant, la route normalisee, le statut et la duree. Les mots de
passe, JWT, corps de requete et parametres sensibles ne sont jamais journalises.

Les logs restent consultables avec :

```powershell
docker compose logs -f user-service course-service certificate-service frontend-service
```

Loki ou Elasticsearch peut etre ajoute ulterieurement pour leur centralisation,
mais ce n'est pas necessaire pour demontrer la boucle Shift Right du MVP.

## DAST OWASP ZAP

Le workflow `.github/workflows/dast.yml` execute un scan passif OWASP ZAP :

- manuellement avec l'URL de staging ;
- apres un CD reussi si la variable GitHub `DAST_TARGET_URL` est definie ;
- chaque lundi si cette variable est disponible.

Le rapport est conserve comme artefact GitHub Actions. Le scan est initialement
non bloquant afin de permettre le triage de la baseline. Apres classification
des alertes legitimes, passer `fail_action` a `true` pour en faire un quality
gate.

Un scan actif agressif ne doit pas etre lance sur un environnement de production
sans autorisation et fenetre de maintenance.

## Limites et extensions

- Alertmanager affiche les alertes localement. Un receiver e-mail, Slack ou
  Teams necessite un secret externe.
- Les annotations Kubernetes permettent a une instance Prometheus du namespace
  `monitoring` de decouvrir les quatre services.
- Falco, OpenTelemetry, Jaeger et Loki sont des extensions possibles, non
  obligatoires pour le perimetre PFE.
