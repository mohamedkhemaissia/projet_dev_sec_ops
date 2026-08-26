# TrainingHub - Technical Evidence

Ce dossier contient les preuves techniques collectées durant la validation du projet TrainingHub.

## Kubernetes
- `kubernetes-pods.txt` : état des Pods du cluster.
- `kubernetes-workloads.txt` : Deployments et Services Kubernetes.
- `kubernetes-network-policies.txt` : règles de sécurité réseau et isolation des namespaces.

## Monitoring
- `prometheus-targets.json` : état des targets surveillées par Prometheus.
- `prometheus-rules.json` : règles d'alerting Prometheus.

## AIOps
- `aiops-incidents.txt` : preuve de réception des alertes `firing` et `resolved` par le service AIOps.

## CI/CD
- `github-actions-ci.json` : derniers runs CI sur la branche main.
- `github-actions-ci-jobs.json` : détails des jobs et contrôles DevSecOps exécutés.
- `github-actions-workflows.txt` : déclencheurs CI et CD Kubernetes.

## État validé
La chaîne suivante a été validée :

Prometheus -> Alertmanager -> Webhook authentifié -> AIOps -> Incident

La CI GitHub Actions exécute également les tests, contrôles qualité, scans de sécurité, builds Docker et publication des images.
