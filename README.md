# TrainingHub - Plateforme microservices de formation

Projet PFE DevSecOps base sur une plateforme de training professionnelle.

Le monorepo contient deux microservices Python/Flask et une base MySQL unique:

- `user-service`: inscription, connexion JWT, profils et roles.
- `course-service`: catalogue de formations, CRUD des cours et inscriptions.
- `mysql`: base unique `training_platform_db`.

## Architecture

Tables principales du MVP:

- `users`
- `courses`
- `enrollments`

Roles applicatifs:

- `admin`
- `trainer`
- `learner`

Flux principal:

1. Un utilisateur cree un compte ou se connecte via `user-service`.
2. `user-service` retourne un JWT.
3. Le client envoie le JWT dans `Authorization: Bearer JWT_TOKEN`.
4. `course-service` verifie le JWT pour proteger les cours et les inscriptions.
5. Les deux microservices utilisent la meme base MySQL `training_platform_db`.

## Lancement avec Docker Compose

```bash
docker compose up --build
```

Services exposes:

- User Service: `http://localhost:5001`
- Course Service: `http://localhost:5002`
- MySQL: `localhost:3306`

Si un ancien volume MySQL existe avec les anciennes bases, reinitialiser le volume:

```bash
docker compose down -v
docker compose up --build
```

## Tests rapides

### Health checks

```bash
curl http://localhost:5001/api/v1/users/health
curl http://localhost:5002/courses/health
```

### Creer un utilisateur learner

```bash
curl -X POST http://localhost:5001/api/v1/users/register ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Alice Demo\",\"email\":\"alice@example.com\",\"password\":\"Password123!\",\"role\":\"learner\"}"
```

### Se connecter

```bash
curl -X POST http://localhost:5001/api/v1/users/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"alice@example.com\",\"password\":\"Password123!\"}"
```

### Creer une formation

Cette route demande un token avec le role `admin` ou `trainer`.

```bash
curl -X POST http://localhost:5002/courses ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer JWT_TOKEN_ICI" ^
  -d "{\"title\":\"DevSecOps Fundamentals\",\"description\":\"Introduction to secure delivery pipelines\",\"duration\":24,\"level\":\"beginner\",\"category\":\"DevSecOps\"}"
```

### Lister les formations

```bash
curl -X GET http://localhost:5002/courses ^
  -H "Authorization: Bearer JWT_TOKEN_ICI"
```

### S'inscrire a une formation

```bash
curl -X POST http://localhost:5002/courses/1/enroll ^
  -H "Authorization: Bearer JWT_TOKEN_ICI"
```

### Voir mes inscriptions

```bash
curl -X GET http://localhost:5002/courses/enrollments/me ^
  -H "Authorization: Bearer JWT_TOKEN_ICI"
```

### Changer le statut d'une inscription

Cette route demande un token avec le role `admin` ou `trainer`.

```bash
curl -X PUT http://localhost:5002/courses/enrollments/1/status ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer JWT_TOKEN_ICI" ^
  -d "{\"status\":\"completed\"}"
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

- `GET /courses/health`
- `GET /courses`
- `GET /courses/<id>`
- `POST /courses`
- `PUT /courses/<id>`
- `DELETE /courses/<id>`
- `POST /courses/<id>/enroll`
- `GET /courses/enrollments/me`
- `GET /courses/<id>/enrollments`
- `PUT /courses/enrollments/<id>/status`
