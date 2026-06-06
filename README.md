# Projet DevSecOps - Microservices Demo

Monorepo de démonstration pour un PFE DevSecOps contenant deux microservices Python/Flask (User Service et Course Service), un frontend minimal, et l'infrastructure CI/CD et monitoring.

Structure et instructions de démarrage sont dans les dossiers `services/`, `frontend/`, `infra/` et `pipelines/`.

## Architecture du projet

Le projet est organisé en monorepo avec une architecture microservices.

### Vue d'ensemble

- `user-service` gère l'inscription, la connexion, les jetons JWT et la gestion des comptes utilisateurs.
- `course-service` gère le catalogue de formations et les opérations CRUD protégées par JWT.
- `docker-compose.yml` orchestre le lancement local des services, du monitoring et de la supervision.
- `infra/docker/` contient les Dockerfiles de chaque service.
- `pipelines/` contient l'exemple de pipeline historique; l'automatisation active doit maintenant se faire avec GitHub Actions.

### Logique d'exécution

1. Le client appelle `user-service` pour créer un compte ou se connecter.
2. `user-service` renvoie un JWT signé.
3. Le client envoie ce JWT dans l'en-tête `Authorization: Bearer ...`.
4. `course-service` vérifie le jeton avant d'autoriser les opérations protégées.
5. Chaque microservice reste indépendant sur son domaine métier, ce qui facilite la maintenance et le déploiement.

## Lancer les microservices Flask

Les deux applications sont des microservices RESTful. Dans un projet comme celui-ci, le terme le plus correct est donc microservices, même si on peut aussi dire web services.

### Option 1 - Lancement avec Docker Compose

```bash
docker compose up --build
```

Services exposés:

- User Service: `http://localhost:5001`
- Course Service: `http://localhost:5002`

### Option 2 - Lancement local en Python

Terminal 1:

```bash
cd services/user-service
python app.py
```

Terminal 2:

```bash
cd services/course-service
python app.py
```

## Tester rapidement

### 1. Créer un utilisateur

```bash
curl -X POST http://localhost:5001/users ^
	-H "Content-Type: application/json" ^
	-d "{\"name\":\"Alice Demo\",\"email\":\"alice@example.com\",\"password\":\"Password123!\"}"
```

### 2. Se connecter et récupérer le JWT

```bash
curl -X POST http://localhost:5001/users/login ^
	-H "Content-Type: application/json" ^
	-d "{\"email\":\"alice@example.com\",\"password\":\"Password123!\"}"
```

### 3. Créer une formation avec le token JWT

```bash
curl -X POST http://localhost:5002/courses ^
	-H "Content-Type: application/json" ^
	-H "Authorization: Bearer JWT_TOKEN_ICI" ^
	-d "{\"title\":\"DevSecOps Fundamentals\",\"description\":\"Introduction to secure delivery pipelines\",\"duration\":24,\"instructor\":\"Dr. Martin\"}"
```

### Endpoints principaux

- User Service: `GET /users/health`, `POST /users`, `POST /users/login`, `GET /users/me`, `GET /users/<id>`, `PUT /users/<id>`, `DELETE /users/<id>`
- Course Service: `GET /courses/health`, `GET /courses`, `GET /courses/<id>`, `POST /courses`, `PUT /courses/<id>`, `DELETE /courses/<id>`
