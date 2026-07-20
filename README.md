# TrainingHub Backend API

Projet PFE DevSecOps base sur une plateforme backend de gestion des formations,
des inscriptions et des certificats.

Le monorepo contient trois microservices Python/Flask et une base MySQL unique:

- `user-service`: inscription, connexion JWT, profils et roles.
- `course-service`: catalogue de formations et inscriptions.
- `certificate-service`: emission et verification des certificats.
- `mysql`: base unique `training_platform_db`.

La partie frontend, le chatbot et les avatars ne font plus partie du perimetre de livraison.
La demonstration fonctionnelle se fait avec Postman.

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

- User Service: `http://localhost:5001`
- Course Service: `http://localhost:5002`
- Certificate Service: `http://localhost:5004`
- MySQL: `localhost:3306`

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
pip install -r requirements-test.txt
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

Ou:

```powershell
.\scripts\run-tests.ps1
```

## Scenario Postman

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
password: Admin123!
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
2. Build Docker + scan Docker Scout des vulnerabilites critiques et hautes corrigibles
3. Push des images vers ghcr.io sur `main`

Images construites:

- `user-service`
- `course-service`
- `certificate-service`
