# TrainingHub Frontend Service

Service de présentation web de TrainingHub construit avec Flask, Jinja2,
Bootstrap 5, HTMX, Chart.js et une identité graphique personnalisée.

## Responsabilités

- afficher les parcours publics, learner et admin ;
- appeler les trois API métier sans accéder directement à MySQL ;
- conserver le JWT dans une session serveur ;
- appliquer la protection CSRF et les en-têtes HTTP de sécurité ;
- transmettre les téléchargements de certificats PDF.

Le service ne possède aucune table métier et ne duplique pas la logique des API.

## Lancement local

Depuis la racine du dépôt :

```powershell
.\.venv\Scripts\python.exe -m pip install -r services\frontend-service\requirements.txt
cd services\frontend-service
..\..\.venv\Scripts\python.exe app.py
```

Interface : `http://127.0.0.1:3000`

## Variables d'environnement

- `FRONTEND_SECRET_KEY` : signature des sessions et jetons CSRF ;
- `USER_SERVICE_URL` : adresse interne du user-service ;
- `COURSE_SERVICE_URL` : adresse interne du course-service ;
- `CERTIFICATE_SERVICE_URL` : adresse interne du certificate-service ;
- `SESSION_COOKIE_SECURE` : doit valoir `true` derrière HTTPS ;
- `SESSION_FILE_DIR` : stockage temporaire des sessions serveur.

En production, les sessions sont stockées dans un répertoire temporaire du
conteneur. Une évolution vers Redis permettra de partager les sessions entre
plusieurs réplicas du frontend.
