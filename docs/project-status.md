# Etat final du projet TrainingHub

## Livrables termines

| Domaine | Etat | Preuve dans le depot |
| --- | --- | --- |
| API metier | Termine | Trois microservices Flask couverts par 40 tests |
| Portail web | Termine | Frontend Flask/Jinja2, espaces public, learner et admin |
| Authentification et RBAC | Termine | JWT signe, roles admin/learner et tests negatifs |
| Certificats | Termine | Emission, verification publique et PDF |
| Conteneurisation | Termine | Dockerfiles durcis et Docker Compose valide |
| Kubernetes | Termine | Deployments, Services, Ingress, HPA, ConfigMap, Secret local et PVC |
| Shift Left | Termine | Hooks pre-commit et pre-push |
| CI DevSecOps | Termine | Gitleaks, Flake8, Pytest, Bandit, pip-audit et Docker Scout |
| Securite IaC | Termine | Rendu Kustomize de production et scan Trivy bloquant |
| Publication | Termine | Images versionnees dans GHCR sur `main` |
| CD Kubernetes | Implemente | Workflow, environnement production, smoke tests et rollback |
| Shift Right | Termine pour le MVP | Prometheus, Grafana et Alertmanager dans Docker Compose et Kubernetes, logs JSON et OWASP ZAP |
| Securite runtime | Termine pour le MVP | NetworkPolicy, non-root, seccomp, limites et rate limiting Ingress |
| Demonstration | Termine | Portail web et collection Postman testée de bout en bout |
| Documentation securite | Termine | Politique de securite et threat model STRIDE |
| Diagrammes | Termine | Architecture, parcours metier et pipeline CI/CD |

## Validations locales du 27 juillet 2026

- 53 tests Pytest reussis, y compris les quatre endpoints Prometheus ;
- couverture totale de 59,59 % pour un seuil CI de 55 % ;
- Flake8 et Bandit reussis ;
- Docker Compose, JSON Grafana et manifests Kubernetes rendus sans erreur ;
- deploiement Minikube valide lors de
  la validation precedente ;
- historique de 60 commits analyse sans secret par Gitleaks ;
- aucune vulnerabilite connue detectee par pip-audit ;
- scenario reel Docker valide de l'inscription au certificat PDF.

## Validation Kubernetes du 29 juillet 2026

- Minikube v1.38.1 et Kubernetes v1.35.1 ;
- quatre Deployments applicatifs avec deux replicas sains chacun ;
- Ingress `traininghub.local`, HPA, metrics-server et NetworkPolicies valides ;
- scenario metier complet reussi via l'Ingress, jusqu'au certificat PDF ;
- Prometheus, Grafana et Alertmanager deployes dans `monitoring` ;
- huit replicas applicatifs decouverts automatiquement et `UP` ;
- dashboard provisionne, datasource saine et trois regles Prometheus valides ;
- quatre services disponibles, trafic metier collecte et taux 5xx egal a zero.

## Actions externes restantes

Ces actions ne demandent plus de developpement :

1. creer l'environnement GitHub `production` et ses secrets si un cluster distant
   doit recevoir le CD ;
2. executer la collection Postman et conserver une capture des resultats pour la
   soutenance ;
3. exporter les diagrammes Mermaid en PNG ou SVG pour le rapport ;
4. inserer les captures GitHub Actions, Docker, Kubernetes et Postman dans le
   memoire ;
5. capturer le dashboard Grafana, les cibles Prometheus et une alerte ;
6. executer OWASP ZAP contre une URL de staging accessible ;
7. preparer une courte demonstration orale fondee sur le portail, le pipeline
   et la boucle Shift Right.

Le cluster de production et le rapport academique sont des livrables externes au
code. Le MVP du depot est fonctionnel et demonstrable sans eux avec Docker
Compose.
