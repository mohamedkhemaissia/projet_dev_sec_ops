# Threat model STRIDE - TrainingHub

## Perimetre

Le modele couvre les trois API Flask (`user-service`, `course-service` et
`certificate-service`), le frontend, la base MySQL partagee, les JWT, les images
Docker, Kubernetes, la pipeline GitHub Actions et la chaine d'observabilite.
Les clients de demonstration sont le portail web et Postman.

## Actifs a proteger

- mots de passe et profils des utilisateurs ;
- cles de signature JWT et jetons actifs ;
- roles `admin` et `learner` ;
- formations, inscriptions et statuts de completion ;
- certificats, codes de verification et fichiers PDF ;
- identifiants MySQL et secrets de la pipeline ;
- integrite des images publiees dans GHCR.

## Frontieres de confiance

1. Postman vers les API HTTP ;
2. API vers MySQL ;
3. `user-service` vers les autres services par l'intermediaire du JWT ;
4. depot GitHub vers les runners Actions et GHCR ;
5. hote local vers les conteneurs Docker ;
6. Prometheus vers les endpoints `/metrics` des services ;
7. Grafana et Alertmanager vers Prometheus ;
8. OWASP ZAP vers l'environnement de staging deploye.

## Analyse STRIDE

| Menace | Scenario principal | Mesures existantes | Risque residuel / action |
|---|---|---|---|
| Spoofing | Usurpation d'un utilisateur ou d'un admin | JWT signe, expiration, issuer, audience et claims obligatoires | Rotation des cles et revocation des jetons non implementees |
| Tampering | Modification d'un role, d'une inscription ou d'un certificat | Autorisations par role, validation des champs, requetes SQL parametrees | Ajouter des journaux d'audit pour les actions admin |
| Repudiation | Un admin nie une modification sensible | Identite presente dans le JWT | Ajouter un audit horodate des operations critiques |
| Information disclosure | Fuite de mots de passe, JWT ou certificats | Hash des mots de passe, erreurs generiques, controle de propriete, Gitleaks | Secrets de demonstration a remplacer hors environnement local |
| Denial of service | Requetes nombreuses ou corps volumineux | Limites de ressources, HPA, limite Ingress, `MAX_CONTENT_LENGTH` frontend et rate limiting NGINX | Ajouter un rate limiting specialise sur l'authentification |
| Elevation of privilege | Un learner appelle une route admin | Decorateurs `admin_required` et `learner_required`, roles controles | Ajouter davantage de tests negatifs sur toutes les routes CRUD |

## Menaces sur la chaine logicielle

| Risque | Controle |
|---|---|
| Secret commite | Gitleaks local et CI |
| Code Python vulnerable | Bandit |
| Dependance vulnerable | pip-audit |
| Regression fonctionnelle | Pytest et seuil de couverture |
| Image vulnerable | Docker Scout |
| Execution privilegiee | Utilisateur non-root, filesystem en lecture seule, capabilities supprimees |
| Publication non autorisee | Permissions minimales du workflow et authentification GHCR |
| Mauvaise configuration IaC | Rendu Kustomize et scan Trivy avant build |
| Mouvement lateral dans le cluster | NetworkPolicy en refus par defaut |
| Regression dynamique | OWASP ZAP Baseline apres deploiement |
| Incident non detecte | Metriques, alertes, request ID et logs structures |

## Hypotheses et risques acceptes pour le MVP

- HTTP est accepte uniquement sur la machine locale de demonstration.
- MySQL est partage entre les microservices afin de limiter la complexite du MVP.
- Les secrets Kubernetes presents dans le depot sont reserves a la demonstration
  locale et sont interdits en production.
- La disponibilite multi-region et la revocation JWT ne sont pas traitees comme
  des fonctions completes de production.
- Alertmanager utilise un receiver local ; un canal externe necessite des secrets.

## Revue du modele

Ce document doit etre revu lors de l'ajout d'un service, d'une nouvelle frontiere
reseau, d'une nouvelle categorie de donnees ou d'un mecanisme d'authentification.
