# TrainingHub

Projet PFE DevSecOps basé sur une plateforme web de gestion des formations,
des inscriptions et des certificats.

Le monorepo contient trois microservices métier Python/Flask, un service de
présentation web et une base MySQL unique:

- `user-service`: inscription, connexion JWT, profils et roles.
- `course-service`: catalogue de formations et inscriptions.
- `certificate-service`: emission et verification des certificats.
- `frontend-service`: portail Jinja2/Bootstrap pour les espaces public, learner
  et admin.
- `mysql`: base unique `training_platform_db`.

La démonstration fonctionnelle principale se fait avec le portail web. La
collection Postman reste disponible pour démontrer et vérifier directement les
contrats des API.

## Securite applicative

- JWT avec expiration, emetteur, audience et claims obligatoires.
- Autorisations explicites pour les roles `admin` et `learner`.
- Validation et normalisation des entrees JSON.
- Mots de passe de 12 a 128 caracteres avec lettres, chiffre et caractere special.
- CORS configurable et en-tetes HTTP de securite.
- Protection contre l'acces aux certificats d'un autre learner.

## Architecture

Tables principales:

- `users`
- `courses`
- `enrollments`
- `certificates`

Roles applicatifs:

- `admin`
- `learner`

Flux principal:

1. Un utilisateur cree un compte ou se connecte via `user-service`.
2. `user-service` retourne un JWT.
3. Le client Postman envoie le JWT dans `Authorization: Bearer JWT_TOKEN`.
4. `course-service` protege les cours et les inscriptions avec le JWT.
5. Un admin marque une inscription comme `completed`.
6. Le learner demande son certificat via `certificate-service`.
7. Le certificat peut etre verifie publiquement avec son code.

## Lancement Docker Compose

```bash
docker compose up --build
```

Services exposes:

- Frontend TrainingHub: `http://localhost:3000`
- User Service: `http://localhost:5001`
- Course Service: `http://localhost:5002`
- Certificate Service: `http://localhost:5004`
- MySQL: `localhost:3306`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001`
- Alertmanager: `http://localhost:9093`

Le dashboard `TrainingHub - Observability` est provisionne automatiquement dans
Grafana. Les services applicatifs et AIOps exposent leurs metriques sur
`/metrics`.

Si un ancien volume MySQL contient les anciennes tables, reinitialiser le volume:

```bash
docker compose down -v
docker compose up --build
```

## Tests automatises

```powershell
pip install -r services/user-service/requirements.txt
pip install -r services/course-service/requirements.txt
pip install -r services/certificate-service/requirements.txt
pip install -r services/frontend-service/requirements.txt
pip install -r requirements-test.txt
.\.venv\Scripts\python.exe -m pytest tests/ services/frontend-service/tests/ -v
```

Ou:

```powershell
.\scripts\run-tests.ps1
```

## Controles Shift Left locaux

Installer les dependances de test et les hooks Git une seule fois :

```powershell
winget install --id Gitleaks.Gitleaks --exact
pip install -r requirements-test.txt
pre-commit install
```

Ouvrir un nouveau terminal apres l'installation de Gitleaks afin que la commande
soit disponible dans le `PATH`.

Les controles de format, YAML, Flake8, Bandit et Gitleaks sont executes avant
chaque commit. La suite Pytest avec son seuil de couverture est executee avant
chaque push.

Pour verifier tout le depot manuellement :

```powershell
pre-commit run --all-files
pre-commit run --all-files --hook-stage pre-push
```

La politique de securite se trouve dans `SECURITY.md` et le threat model STRIDE
dans `docs/security/threat-model.md`.

## Scenario Postman

Une collection directement importable et auto-verifiee est disponible dans
`postman/TrainingHub.postman_collection.json`. Son guide d'utilisation se trouve
dans `postman/README.md`.

### 1. Health checks

```bash
curl http://localhost:5001/api/v1/users/health
curl http://localhost:5002/api/v1/courses/health
curl http://localhost:5004/api/v1/certificates/health
```

### 2. Creer un learner

```bash
curl -X POST http://localhost:5001/api/v1/users/register ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Alice Demo\",\"email\":\"alice@example.com\",\"password\":\"Password123!\"}"
```

### 3. Se connecter

```bash
curl -X POST http://localhost:5001/api/v1/users/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"alice@example.com\",\"password\":\"Password123!\"}"
```

### 4. Se connecter admin

Compte admin cree automatiquement au demarrage:

```txt
email: admin@training.com
password: <DEFAULT_ADMIN_PASSWORD>
```

Ou les valeurs definies dans `.env`.

### 5. Creer une formation

Cette route demande un token `admin`.

```bash
curl -X POST http://localhost:5002/api/v1/courses ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer ADMIN_JWT_TOKEN" ^
  -d "{\"title\":\"DevSecOps Fundamentals\",\"description\":\"Introduction to secure delivery pipelines\",\"duration\":24,\"level\":\"beginner\",\"category\":\"DevSecOps\"}"
```

### 6. Lister les formations

```bash
curl -X GET http://localhost:5002/api/v1/courses ^
  -H "Authorization: Bearer LEARNER_JWT_TOKEN"
```

### 7. S'inscrire a une formation

```bash
curl -X POST http://localhost:5002/api/v1/courses/1/enroll ^
  -H "Authorization: Bearer LEARNER_JWT_TOKEN"
```

### 8. Voir les inscriptions du cours

Cette route demande un token `admin`.

```bash
curl -X GET http://localhost:5002/api/v1/courses/1/enrollments ^
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

Recuperer l'`id` de l'inscription dans la reponse.

### 9. Marquer l'inscription comme terminee

Cette route demande un token `admin`.

```bash
curl -X PUT http://localhost:5002/api/v1/courses/enrollments/1/status ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer ADMIN_JWT_TOKEN" ^
  -d "{\"status\":\"completed\"}"
```

### 10. Generer un certificat

Cette route demande un token `learner`.

```bash
curl -X POST http://localhost:5004/api/v1/certificates/courses/1/issue ^
  -H "Authorization: Bearer LEARNER_JWT_TOKEN"
```

### 11. Lister mes certificats

```bash
curl -X GET http://localhost:5004/api/v1/certificates/me ^
  -H "Authorization: Bearer LEARNER_JWT_TOKEN"
```

### 12. Verifier un certificat publiquement

```bash
curl -X GET http://localhost:5004/api/v1/certificates/verify/TH-CODE_ICI
```

### 13. Telecharger un certificat PDF

Cette route demande le token du learner proprietaire du certificat ou un token admin.

```bash
curl -X GET http://localhost:5004/api/v1/certificates/1/download ^
  -H "Authorization: Bearer LEARNER_JWT_TOKEN" ^
  -o certificat.pdf
```

## Endpoints principaux

User Service:

- `GET /api/v1/users/health`
- `POST /api/v1/users/register`
- `POST /api/v1/users/login`
- `GET /api/v1/users/me`
- `PUT /api/v1/users/me`
- `GET /api/v1/users/`
- `GET /api/v1/users/<id>`
- `PUT /api/v1/users/<id>`
- `DELETE /api/v1/users/<id>`

Course Service:

- `GET /api/v1/courses/health`
- `GET /api/v1/courses`
- `GET /api/v1/courses/<id>`
- `POST /api/v1/courses`
- `PUT /api/v1/courses/<id>`
- `DELETE /api/v1/courses/<id>`
- `POST /api/v1/courses/<id>/enroll`
- `DELETE /api/v1/courses/<id>/enroll`
- `GET /api/v1/courses/enrollments/me`
- `GET /api/v1/courses/<id>/enrollments`
- `PUT /api/v1/courses/enrollments/<id>/status`

Certificate Service:

- `GET /api/v1/certificates/health`
- `POST /api/v1/certificates/courses/<course_id>/issue`
- `GET /api/v1/certificates/me`
- `GET /api/v1/certificates/<id>`
- `GET /api/v1/certificates/<id>/download`
- `GET /api/v1/certificates/verify/<code>`

## Pipeline CI/CD

A chaque push sur `main` ou `develop`, GitHub Actions execute:

1. Gitleaks + Flake8 + Pytest (couverture minimale de 55 %) + Bandit + pip-audit
2. Tests du service frontend, de ses pages et de ses contrôles d'accès
3. Rendu Kustomize et scan de securite IaC avec Trivy
4. Build Docker + scan Docker Scout des vulnerabilites critiques et hautes corrigibles
5. Push des images vers ghcr.io sur `main`
6. Deploiement Kubernetes apres validation de l'environnement `production`
7. Verification des rollouts et smoke tests des services deployes

Images construites:

- `user-service`
- `course-service`
- `certificate-service`
- `frontend-service`
- `ai-ops-service`

La configuration du CD, des secrets GitHub et du rollback est documentee dans
`docs/deployment/cd-kubernetes.md`.

## Monitoring et observabilite

Le projet observe les services apres leur deploiement avec :

- metriques Prometheus sur les services applicatifs et AIOps ;
- dashboard Grafana provisionne automatiquement dans Docker Compose et Kubernetes ;
- alertes de disponibilite, taux d'erreur et latence ;
- logs JSON correles par `X-Request-ID` ;
- health checks Kubernetes, smoke tests et rollback.

Voir `docs/observability.md` pour le lancement, les requetes PromQL et la
demonstration d'une alerte.
Le deploiement Kubernetes du monitoring est documente dans
`k8s/monitoring/README.md`.

### Assistance AIOps basee sur l'observabilite

TrainingHub inclut un assistant d'analyse d'incidents en lecture seule. Il recoit
les alertes d'Alertmanager, enrichit le contexte depuis Prometheus et genere un
diagnostic structure. Le mode `rules` est reproductible sans modele ; le mode
`ollama` active une analyse LLM locale avec repli automatique.
L'assistant reste en lecture seule, ne declenche aucune remediation automatique
et soumet ses recommandations a un operateur humain.

Apres le demarrage Docker Compose, lancer un scenario controle avec :

```powershell
.\scripts\run-aiops-scenario.ps1
```

Le contrat, les limites de securite et le protocole d'evaluation sont detailles
dans [`docs/aiops-architecture.md`](docs/aiops-architecture.md).
Les premiers resultats comparatifs sont presentes dans
[`docs/aiops-evaluation.md`](docs/aiops-evaluation.md).

## Documentation PFE

- Etat final et actions de soutenance : `docs/project-status.md`
- Deroule de demonstration : `docs/demo-soutenance.md`
- Architecture technique : `docs/diagrams/architecture.md`
- Architecture du portail web : `docs/frontend-architecture.md`
- Parcours metier : `docs/diagrams/business-flow.md`
- Pipeline DevSecOps : `docs/diagrams/ci-cd-pipeline.md`
- Modele de menaces STRIDE : `docs/security/threat-model.md`
- Monitoring et observabilite : `docs/observability.md`
- Matrice de couverture DevSecOps : `docs/devsecops-coverage.md`
- Assistant AIOps : `docs/aiops-architecture.md`
- Evaluation AIOps : `docs/aiops-evaluation.md`
