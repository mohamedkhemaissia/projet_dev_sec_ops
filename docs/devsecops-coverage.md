# Couverture DevSecOps du projet

Cette matrice relie les notions presentees dans les supports DevSecOps au code
et aux preuves de TrainingHub.

| Notion | Etat | Implementation / preuve |
| --- | --- | --- |
| CI/CD pipelines | Couvert | GitHub Actions CI, publication GHCR et CD Kubernetes |
| Infrastructure as Code | Couvert pour le deploiement | Manifests Kubernetes et overlays Kustomize |
| Provisioning cloud | Hors perimetre | Terraform/Ansible inutiles sans compte cloud cible |
| Security tools | Couvert | Gitleaks, Bandit, pip-audit, Docker Scout, Trivy et ZAP |
| Cloud-native | Couvert | Docker, GHCR, Kubernetes, Ingress, HPA et probes |
| Monitoring | Couvert | Prometheus en Docker Compose et Kubernetes, decouverte des pods et endpoints `/metrics` |
| Observability | Couvert au niveau MVP | Metriques RED, logs JSON, request ID et dashboard Grafana provisionne |
| Alerting | Couvert | Prometheus rules et Alertmanager dans le namespace `monitoring` |
| Collaboration | Partiel | GitHub, pull requests et documentation ; plateforme externe optionnelle |
| Code analysis / SAST | Couvert | Bandit et Flake8 |
| Software composition analysis | Couvert | pip-audit |
| Dynamic security testing | Couvert | OWASP ZAP Baseline sur l'environnement de staging |
| Interactive security testing | Non couvert, optionnel | IAST non necessaire pour ce MVP |
| Threat modeling | Couvert | Modele STRIDE versionne |
| Change management | Couvert au niveau MVP | Git, images immuables, rolling update et rollback |
| Compliance as Code | Partiel | Trivy IaC ; pas de referentiel reglementaire impose |
| Security training | Documentaire | Politique de securite et consignes de demonstration |
| Shift Left | Couvert | Hooks locaux et controles CI bloquants |
| Shift Right | Couvert au niveau MVP | Telemetrie, alertes, DAST post-deploiement et feedback |

## Ce qu'il ne faut pas sur-declarer dans le rapport

Les elements suivants sont des resultats attendus, pas des fonctions techniques :

- livraison plus rapide ;
- reduction des couts ;
- innovation accrue ;
- meilleure collaboration ;
- meilleure conformite.

Ils peuvent etre presentes comme benefices de la demarche. Pour les annoncer
comme resultats mesures, il faudrait comparer des indicateurs avant/apres :
lead time, frequence de deploiement, taux d'echec, temps moyen de restauration,
nombre de vulnerabilites et temps de remediation.

## Formulation recommandee pour le rapport

> TrainingHub met en oeuvre une chaine DevSecOps bidirectionnelle. Le Shift Left
> automatise les controles de qualite et de securite avant publication. Le Shift
> Right observe les services deployes, detecte les indisponibilites, erreurs et
> degradations de performance, puis produit un feedback exploitable. Cette
> boucle reduit le delai de detection et soutient une livraison continue plus
> fiable.

## Elements volontairement hors perimetre

- IAST commercial ;
- provisioning AWS, Azure ou GCP ;
- certification HIPAA, sans rapport avec le domaine metier ;
- service mesh, chaos engineering et canary deployment ;
- SIEM et SOC complets ;
- outils de collaboration payants.

Ces exclusions evitent d'accumuler des outils sans valeur demonstrable et
maintiennent un perimetre coherent avec un PFE.
