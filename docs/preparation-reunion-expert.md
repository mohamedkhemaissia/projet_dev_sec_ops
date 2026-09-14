# Préparation à la réunion avec l’expert — TrainingHub

Ce document est rédigé pour être appris progressivement et réutilisé directement
pendant une réunion, une soutenance ou dans un rapport. Les formulations à la
première personne peuvent être copiées telles quelles.

## 1. La présentation la plus courte à mémoriser

> Mon projet s’appelle TrainingHub. C’est une plateforme web de gestion de
> formations conçue comme un projet PFE DevSecOps. Un apprenant peut créer un
> compte, consulter les formations, s’inscrire, suivre son statut et obtenir un
> certificat PDF après validation par un administrateur. Le certificat possède
> un code unique qui peut être vérifié publiquement. L’application comprend
> trois microservices métier Flask, un frontend Flask avec Jinja2, une base
> MySQL, un déploiement Docker et Kubernetes, une chaîne CI/CD sécurisée, une
> stack d’observabilité avec Prometheus, Grafana et Alertmanager.

La phrase essentielle qui résume la valeur du projet est :

> TrainingHub couvre le cycle complet : développement d’une fonction métier,
> tests et contrôles de sécurité avant livraison, déploiement conteneurisé,
> supervision après déploiement et assistance humaine à l’analyse des incidents.

## 2. Le problème, les utilisateurs et la valeur métier

TrainingHub répond à un besoin simple : gérer tout le parcours d’une formation
dans une seule plateforme.

Il existe quatre types d’acteurs :

- le visiteur public, qui peut créer un compte et vérifier un certificat ;
- l’apprenant, appelé learner dans le code, qui consulte les cours, s’inscrit et
  récupère ses certificats ;
- l’administrateur, appelé admin, qui gère les utilisateurs, les formations et
  la progression des inscriptions ;
- l’opérateur technique, qui consulte Grafana et Alertmanager pour surveiller
  l’application.

Le parcours métier principal est :

1. un apprenant crée un compte ;
2. il se connecte et le user-service émet un JWT ; avec le portail, le frontend
   le reçoit et le garde côté serveur, tandis qu’avec Postman le client reçoit
   directement le token ;
3. un administrateur crée une formation ;
4. l’apprenant s’inscrit ;
5. l’administrateur fait évoluer l’inscription de enrolled vers in_progress puis
   completed ;
6. l’apprenant demande l’émission de son certificat ;
7. le service de certificats vérifie que la formation est terminée ;
8. un code de certificat unique est conservé en base ;
9. le PDF est généré à la demande ;
10. le code permet une vérification publique.

Le MVP ne diffuse pas encore de vidéos, de modules, de quiz ou d’examen. Le
statut de progression est modifié manuellement par un administrateur. La durée
du cours est une information descriptive, pas un chronomètre automatique.

## 3. Architecture générale

### 3.1 Vue simple

    Navigateur
        |
        v
    frontend-service (port 3000)
        |
        +------ HTTP REST + JWT ------> user-service (5001)
        +------ HTTP REST + JWT ------> course-service (5002)
        +------ HTTP REST + JWT ------> certificate-service (5004)

    Postman -------- HTTP REST + JWT --------> les trois API directement

    user-service -----------+
    course-service ---------+----> MySQL (3306)
    certificate-service ----+

    Services ---- /metrics ----> Prometheus ----> Grafana
                                      |
                                      v
                                Alertmanager

### 3.2 Les composants et leurs responsabilités

| Composant | Responsabilité | Port local |
| --- | --- | ---: |
| user-service | Comptes, mots de passe, connexion, profils, rôles et création du JWT | 5001 |
| course-service | Catalogue, création des cours, inscriptions et progression | 5002 |
| certificate-service | Émission, consultation, vérification et génération PDF | 5004 |
| frontend-service | Interface web publique, learner et admin | 3000 |
| MySQL | Persistance métier partagée | 3306 |
| Prometheus | Collecte des métriques et évaluation des règles d’alerte | 9090 |
| Grafana | Visualisation des métriques | 3001 |
| Alertmanager | Regroupement et suivi des alertes | 9093 |

### 3.3 Est-ce vraiment une architecture microservices ?

Réponse exacte à donner :

> Les responsabilités, les applications Flask, les API, les images Docker et
> les Deployments Kubernetes sont séparés. En revanche, les trois services
> métier partagent actuellement la même base MySQL. C’est donc une architecture
> de microservices au niveau applicatif, mais pas un découplage strict selon le
> principe database per service. C’est un compromis assumé pour le MVP.

Pourquoi ce choix est pratique :

- moins de complexité pour un projet académique ;
- jointures SQL simples ;
- clés étrangères et intégrité référentielle faciles à démontrer ;
- scénario métier complet plus rapide à réaliser.

Ses inconvénients :

- les services sont couplés au même schéma ;
- MySQL est un point unique de défaillance ;
- une modification de table peut affecter plusieurs services ;
- les services ne peuvent pas faire évoluer leurs données de manière totalement
  indépendante.

Une évolution plus stricte serait une base ou un schéma par service, avec des
API ou des événements via RabbitMQ ou Kafka. Aucun broker de messages n’est
utilisé actuellement.

## 4. Structure du monorepo et du code

Le projet est un monorepo : tous les composants se trouvent dans un seul dépôt
Git. Cela simplifie la CI, la documentation et les changements coordonnés.

Structure simplifiée :

    services/
      user-service/
      course-service/
      certificate-service/
      frontend-service/
    infra/
      docker/
      mysql/
      monitoring/
    k8s/
    tests/
    scripts/
    postman/
    docs/
    .github/workflows/
    docker-compose.yml

Les trois services métier suivent presque la même organisation :

    service/
      app.py
      config.py
      requirements.txt
      routes/
      db/connection.py
      observability.py

Rôle de chaque élément :

- app.py crée l’application Flask, enregistre les routes, les métriques, les
  headers de sécurité et les gestionnaires d’erreur ;
- config.py lit la configuration depuis les variables d’environnement ;
- routes contient les endpoints HTTP, les validations et les autorisations ;
- db/connection.py contient les requêtes SQL vers MySQL ;
- observability.py ajoute les métriques Prometheus et les logs JSON ;
- requirements.txt décrit les bibliothèques Python du service.

Chaque service utilise une fonction create_app. C’est le patron application
factory : une fonction construit l’application et rend les tests et la
configuration plus faciles.

Les routes sont regroupées dans des Blueprints Flask. Un Blueprint est un groupe
de routes que l’on branche ensuite sur l’application principale. Cela évite un
seul très grand fichier.

Fichiers particuliers :

- user-service/models/user.py construit une vue publique d’un utilisateur sans
  son hash de mot de passe ;
- certificate-service/certificate_pdf.py génère le document PDF ;
- frontend-service/api_client.py centralise les appels vers les trois API ;
- frontend-service/templates contient les vues Jinja2 ;
- frontend-service/static contient le CSS, le JavaScript et l’image SVG.

## 5. Partie développement

### 5.1 Technologies principales

Le backend est écrit en Python avec Flask. Les API utilisent HTTP et JSON. Le
frontend est également un service Flask, mais il rend des pages HTML avec
Jinja2. Ce n’est pas une application React, Angular ou Vue.

Le projet utilise des routes versionnées sous /api/v1. Cela permet, à l’avenir,
d’ajouter une version incompatible sous /api/v2 sans casser immédiatement les
anciens clients.

Les codes HTTP importants sont :

- 200 : opération réussie ;
- 201 : ressource créée ;
- 400 : requête ou donnée invalide ;
- 401 : utilisateur non authentifié ou token invalide ;
- 403 : utilisateur identifié mais non autorisé ;
- 404 : ressource inexistante ;
- 409 : conflit, par exemple inscription déjà existante ou certificat révoqué ;
- 503 : code interne utilisé par le client frontend pour représenter un service
  distant indisponible ; la page web peut ensuite afficher un message et une
  redirection au lieu de renvoyer elle-même ce statut.

### 5.2 Bibliothèques Python utilisées

| Bibliothèque | Services | Utilité |
| --- | --- | --- |
| Flask, version 2.3 ou supérieure | tous | Routes HTTP, réponses, application web |
| PyJWT, version 2.8 ou supérieure | user, course, certificate | Création et validation des JWT |
| Flask-Cors, version 4.0 ou supérieure | les trois API métier | Origines web autorisées |
| mysql-connector-python, version 9.0 ou supérieure | les trois API métier | Connexion et requêtes MySQL |
| prometheus-client, version 0.20 ou supérieure | tous | Exposition des métriques |
| ReportLab, version 4.0 ou supérieure | certificate-service | Création des PDF |
| Flask-Session, version 0.8 ou supérieure | frontend | Session conservée côté serveur |
| Flask-WTF, version 1.2 ou supérieure | frontend | Protection CSRF des formulaires |
| CacheLib, version 0.13 ou supérieure | frontend | Stockage fichier des sessions |
| Requests, version 2.32 ou supérieure | frontend | Appels HTTP vers les trois API métier |
| Gunicorn | frontend | Serveur WSGI dans le conteneur |

Jinja2 et Werkzeug sont apportés par Flask. Jinja2 produit le HTML. Werkzeug
fournit notamment generate_password_hash et check_password_hash.

Les dépendances du navigateur sont chargées depuis jsDelivr :

- Bootstrap 5.3.7 ;
- Bootstrap Icons 1.13.1 ;
- HTMX 2.0.6 ;
- Chart.js 4.5.0 ;
- la police Manrope via Fontsource 5.2.6.

À connaître comme limite :

> Les requirements utilisent actuellement des bornes minimales avec le symbole
> supérieur ou égal, et non un fichier de verrouillage avec des versions exactes
> et des hash. Pour une meilleure reproductibilité, je pourrais utiliser un lock
> file ou des versions entièrement figées.

Les ressources CDN ne possèdent pas non plus d’attribut Subresource Integrity.
Une évolution serait de les héberger localement ou d’ajouter SRI.

### 5.3 Base de données

La base s’appelle training_platform_db et contient quatre tables.

| Table | Contenu principal |
| --- | --- |
| users | nom, email unique, hash du mot de passe, rôle, date |
| courses | titre, description, durée, niveau, catégorie |
| enrollments | relation utilisateur-cours, statut et dates |
| certificates | relation utilisateur-cours, code unique, statut et date |

Les rôles possibles sont admin et learner.

Les niveaux sont beginner, intermediate et advanced.

Les statuts d’inscription sont enrolled, in_progress et completed.

Les statuts de certificat sont active et revoked.

Les contraintes importantes sont :

- email unique ;
- une seule inscription par couple utilisateur-cours ;
- un seul certificat par couple utilisateur-cours ;
- code de certificat unique ;
- clés étrangères avec suppression en cascade.

Le projet n’utilise pas d’ORM comme SQLAlchemy. Il utilise du SQL écrit à la
main avec mysql-connector-python. Les valeurs sont transmises séparément avec
des paramètres %s, ce qui réduit le risque d’injection SQL.

Chaque opération ouvre actuellement une connexion puis la ferme. Il existe une
attente avec plusieurs tentatives au démarrage, mais pas de pool de connexions.
Une évolution de production serait un pool et un outil de migration de schéma
comme Alembic ou Flyway.

Les trois services utilisent aussi le même compte tms_user, auquel le script
accorde tous les privilèges sur la base TrainingHub. C’est simple pour le MVP,
mais ce n’est pas le moindre privilège. Une évolution créerait un compte et des
droits limités pour chaque service.

Le schéma est initialisé par infra/mysql/init.sql. Le user-service crée ou remet
à jour le compte administrateur par défaut au démarrage. Dans une production
réelle, ce bootstrap serait mieux géré par une tâche d’initialisation séparée,
afin de ne pas réinitialiser un mot de passe administrateur à chaque redémarrage.

### 5.4 Communication entre services

Le navigateur utilise principalement le frontend. Le frontend appelle ensuite
les API avec Requests et ajoute le token dans le header :

    Authorization: Bearer <JWT>

Le timeout par défaut de ces appels est de cinq secondes. Une panne réseau est
convertie en ServiceError portant le code 503 et un message compréhensible. La
route web qui intercepte cette erreur peut afficher le message dans la page ou
rediriger ; elle ne renvoie donc pas systématiquement un statut HTTP 503 au
navigateur.

Dans Docker Compose, user-service, course-service et certificate-service sont
des noms DNS internes. Dans Kubernetes, les objets Service fournissent cette
résolution réseau.

Les trois API métier ne s’appellent pas directement entre elles. Course et
Certificate valident localement le JWT. Certificate vérifie la fin de formation
directement dans la base partagée.

Les appels sont synchrones et il n’existe actuellement ni file de messages, ni
circuit breaker, ni stratégie de retry avancée.

### 5.5 Frontend

Le frontend est un service de présentation rendu côté serveur :

- les formulaires et pages sont traités par Flask ;
- Jinja2 injecte les données dans les templates HTML ;
- Bootstrap et le CSS personnalisé gèrent la présentation ;
- Chart.js affiche les statistiques de l’espace admin ;
- JavaScript gère le thème, la barre latérale, les confirmations et certains
  composants visuels ;
- HTMX est chargé, mais l’essentiel du parcours fonctionne par formulaires et
  navigation Flask classiques.

Le frontend ne lit jamais directement MySQL. Il passe toujours par les API.
La logique métier et les vérifications importantes restent donc dans les
services backend.

### 5.6 Endpoints métier à connaître

User service, préfixe /api/v1/users :

| Méthode et chemin | Accès | Fonction |
| --- | --- | --- |
| GET /health | public | santé du processus |
| POST /register | public | créer un learner |
| POST /login | public | vérifier les identifiants et émettre le JWT |
| GET /me | connecté | voir son profil |
| PUT /me | connecté | modifier son profil |
| GET / | admin | lister les utilisateurs |
| GET /<id> | admin | voir un utilisateur |
| PUT /<id> | admin | modifier nom, rôle ou mot de passe |
| DELETE /<id> | admin | supprimer un utilisateur, sauf soi-même |

Course service, préfixe /api/v1/courses :

| Méthode et chemin | Accès | Fonction |
| --- | --- | --- |
| GET /health | public | santé du processus |
| GET / | connecté | catalogue |
| GET /<course_id> | connecté | détail d’un cours |
| POST / | admin | créer un cours |
| PUT /<course_id> | admin | modifier un cours |
| DELETE /<course_id> | admin | supprimer un cours |
| POST /<course_id>/enroll | learner | s’inscrire |
| DELETE /<course_id>/enroll | learner | annuler son inscription |
| GET /enrollments/me | learner | voir ses inscriptions |
| GET /<course_id>/enrollments | admin | voir les inscrits du cours |
| PUT /enrollments/<id>/status | admin | changer la progression |

Certificate service, préfixe /api/v1/certificates :

| Méthode et chemin | Accès | Fonction |
| --- | --- | --- |
| GET /health | public | santé du processus |
| POST /courses/<course_id>/issue | learner | émettre après completion |
| GET /me | learner | lister ses certificats |
| GET /<certificate_id> | connecté | consulter avec contrôle de propriété |
| GET /<certificate_id>/download | connecté | télécharger avec contrôle de propriété |
| GET /verify/<code> | public | vérifier le code et le statut |

## 6. Le certificat PDF en détail

### 6.1 Émission et téléchargement : deux opérations différentes

Quand le learner appelle l’endpoint d’émission, le service vérifie d’abord
l’existence d’une inscription completed. Il crée ensuite uniquement les
métadonnées du certificat en base, dont un code de la forme TH-XXXXXXXXXXXX.

L’émission est pratiquement idempotente : si un certificat existe déjà pour ce
learner et ce cours, l’API renvoie l’existant au lieu d’en créer un deuxième.

Le fichier PDF n’est produit que lors du téléchargement. Il n’est jamais stocké
sur disque ou dans MySQL.

### 6.2 Bibliothèque et fonctionnement

Réponse à apprendre :

> Le PDF est généré avec ReportLab, plus précisément son API canvas. Le code
> construit une page A4 en paysage, dessine le cadre et les textes avec des
> coordonnées, puis écrit le résultat dans un BytesIO en mémoire. Flask renvoie
> ensuite ce buffer avec le type MIME application/pdf.

Le document contient :

- le titre du certificat ;
- le nom de l’apprenant ;
- le nom de la formation ;
- la catégorie et le niveau ;
- la date d’émission ;
- le code unique ;
- l’URL de vérification.

Les polices utilisées sont Helvetica et Helvetica-Bold, fournies par ReportLab.
Le PDF est dessiné directement ; il n’est pas converti depuis un template HTML.

### 6.3 Sécurité du téléchargement

- un learner ne peut télécharger que son propre certificat ;
- un admin peut télécharger un certificat ;
- un certificat revoked ne peut pas être téléchargé ;
- le nom de fichier est nettoyé ;
- la réponse utilise application/pdf ;
- Cache-Control vaut private, no-store ;
- X-Content-Type-Options vaut nosniff.

Le frontend ne lit pas le PDF. Il reçoit les octets du certificate-service et
les retransmet au navigateur.

La vérification publique ne fait pas confiance au contenu visuel du fichier.
Elle recherche le code en base et considère le certificat valide uniquement si
son statut est active.

### 6.4 Limites PDF à dire honnêtement

- aucun QR code ;
- aucune signature numérique du fichier ;
- aucun lecteur ou parseur PDF ;
- aucun stockage historique des fichiers ;
- pas de gestion avancée des très longs textes ;
- pas de test visuel automatisé de la mise en page ;
- le statut revoked existe en base, mais il n’existe pas encore d’endpoint admin
  pour révoquer un certificat.

Réponse recommandée :

> Pour le MVP, l’authenticité repose sur le code unique et la vérification dans
> la base. Une évolution serait d’ajouter un QR code vers la page de vérification
> et une signature cryptographique du PDF.

## 7. Sécurité applicative

### 7.1 Authentification et autorisation

L’authentification répond à la question « qui êtes-vous ? ». L’autorisation
répond à la question « qu’avez-vous le droit de faire ? ».

Le user-service authentifie l’utilisateur avec son email et son mot de passe.
Les mots de passe ne sont pas stockés en clair : Werkzeug produit un hash lent
et salé, puis compare ce hash à la connexion.

Il faut distinguer stockage et transport :

> Le hash protège le mot de passe enregistré dans MySQL. Il ne chiffre pas la
> requête réseau. Seul HTTPS protège les identifiants pendant leur transport.
> Comme l’environnement local utilise encore HTTP, je ne dois pas affirmer que
> le transport est déjà sécurisé comme en production.

La politique applicative exige :

- entre 12 et 128 caractères ;
- une minuscule ;
- une majuscule ;
- un chiffre ;
- un caractère spécial.

L’inscription publique force toujours le rôle learner. Un utilisateur ne peut
pas envoyer role=admin pendant son inscription.

Les autorisations sont appliquées avec les décorateurs token_required,
admin_required et learner_required. Le contrôle du frontend améliore
l’expérience, mais la vraie barrière de sécurité reste le backend.

### 7.2 Fonctionnement du JWT

Le JWT contient :

- user_id ;
- email ;
- role ;
- iat, date d’émission ;
- exp, date d’expiration ;
- iss, service émetteur ;
- aud, API destinataire ;
- jti, identifiant unique du token.

Sa durée par défaut est de 60 minutes. Il est signé avec HS256 et un secret
partagé par les trois API.

Une phrase importante :

> Un JWT signé n’est pas chiffré. Sa signature garantit qu’il n’a pas été
> modifié, mais son contenu peut être décodé. Je n’y place donc ni mot de passe
> ni secret.

Course et Certificate vérifient la signature, l’algorithme autorisé, la date
d’expiration, l’émetteur, l’audience, les claims obligatoires et le rôle.

Le user-service recharge aussi l’utilisateur depuis MySQL lorsqu’il protège ses
propres routes. Course et Certificate font confiance au rôle contenu dans le
token jusqu’à son expiration. Ainsi, après un changement de rôle, un ancien
token peut garder ses anciens droits sur ces deux services pendant au maximum
la durée restante. Les améliorations possibles sont une liste de révocation,
des tokens plus courts, une introspection ou une signature asymétrique gérée par
un fournisseur d’identité.

Il n’existe actuellement ni refresh token, ni rotation automatique de clé, ni
révocation centralisée.

### 7.3 Session web et CSRF

Le JWT n’est pas enregistré dans localStorage. Le frontend le conserve dans une
session côté serveur avec Flask-Session et CacheLib. Le navigateur reçoit un
cookie de session :

- HttpOnly, donc non lisible par JavaScript ;
- SameSite=Lax ;
- durée de 60 minutes ;
- Secure activable et imposé par l’overlay Kubernetes de production.

Tous les formulaires sont protégés par un token CSRF via Flask-WTF. Le CSRF est
une attaque où un autre site pousse le navigateur connecté à envoyer une action
non voulue. Le token prouve que le formulaire vient bien de TrainingHub.

La session est stockée dans le système de fichiers temporaire du conteneur. Le
frontend est donc volontairement limité à un replica dans son HPA. Pour plusieurs
replicas, il faudrait Redis ou un stockage de session partagé.

### 7.4 Validation, SQL et headers

Les API vérifient :

- que le corps est un objet JSON ;
- les champs obligatoires ;
- les champs inconnus ;
- les longueurs et types ;
- le format de l’email ;
- les valeurs permises pour le rôle, le niveau et le statut ;
- une durée de cours strictement positive et bornée.

Les requêtes SQL sont paramétrées. Des contraintes MySQL complètent les contrôles
applicatifs.

Les réponses ajoutent notamment :

- X-Content-Type-Options: nosniff ;
- X-Frame-Options: DENY ;
- Referrer-Policy ;
- une Content-Security-Policy plus complète sur le frontend ;
- Permissions-Policy sur le frontend.

Le frontend vérifie aussi les redirections locales pour éviter une open redirect.

### 7.5 CORS n’est pas une authentification

CORS limite les origines auxquelles le navigateur autorise l’accès aux réponses
des API. La valeur locale par défaut autorise le frontend sur localhost:3000.
CORS ne remplace ni le JWT ni le RBAC et ne bloque pas un client comme curl ou
Postman.

Il n’existe pas encore de MFA, de vérification d’email, de récupération de mot
de passe, de verrouillage de compte ou de rate limiting spécialisé sur login.
Les erreurs de connexion restent volontairement génériques pour ne pas confirmer
si un compte existe.

La vérification publique d’un certificat renvoie le nom du learner et les
informations de la formation, mais pas son email. En production, il faudrait
valider ce choix avec une politique de confidentialité, le consentement de
l’utilisateur et éventuellement minimiser davantage le nom affiché.

### 7.6 Secrets

Les secrets sont fournis par variables d’environnement, fichier .env local,
Secrets Kubernetes ou secrets GitHub Actions. Le vrai .env est ignoré par Git.
Les fichiers example ne contiennent que des placeholders.

Les secrets concernés incluent :

- clé Flask ;
- clé de signature JWT ;
- mots de passe MySQL ;
- mot de passe admin initial ;
- identifiants GHCR et kubeconfig dans le CD.

Règle à dire :

> Je ne place jamais un secret, un mot de passe ou un JWT dans Git, dans une
> capture ou dans un log. Les valeurs de démonstration doivent être remplacées
> avant toute exposition réelle.

### 7.7 Threat modeling STRIDE

Le dépôt contient un modèle de menaces STRIDE :

- Spoofing : usurpation d’identité ;
- Tampering : modification de données ;
- Repudiation : nier une action ;
- Information disclosure : fuite d’informations ;
- Denial of service : indisponibilité ;
- Elevation of privilege : gain de droits non autorisé.

Exemples de mesures :

- JWT et hash de mot de passe contre l’usurpation ;
- RBAC, validations et SQL paramétré contre les modifications non autorisées ;
- logs corrélés contre une partie du risque de répudiation ;
- secrets externes et Gitleaks contre les fuites ;
- limites de ressources, HPA et limite Ingress contre une partie du déni de
  service ;
- décorateurs admin et learner contre l’élévation de privilèges.

Le risque résiduel important est l’absence d’un véritable journal d’audit métier
des opérations administrateur.

## 8. DevOps et DevSecOps

### 8.1 Définitions simples

DevOps rapproche le développement et l’exploitation afin d’automatiser la
construction, le test, la livraison et l’exploitation d’une application.

DevSecOps ajoute la sécurité dans tout ce cycle. La sécurité n’est pas seulement
un contrôle final ; elle commence dès le poste du développeur et continue dans
la CI, les images, l’infrastructure et le runtime.

Shift Left signifie déplacer les contrôles le plus tôt possible, vers la gauche
du cycle. Trouver un secret ou une vulnérabilité avant le déploiement coûte
moins cher que la découvrir en production.

### 8.2 Contrôles automatisés

Le projet ne dépend pas de hooks Git locaux. Les commits et les push restent
simples, tandis que GitHub Actions exécute automatiquement Gitleaks, Flake8,
Pytest avec couverture, Bandit, pip-audit, Trivy et Docker Scout.

La CI constitue ainsi une source de vérité identique pour tous les développeurs
et ne dépend pas de la configuration de leur poste.

### 8.3 Pipeline d’intégration continue

La CI GitHub Actions s’exécute sur :

- un push vers main ou develop ;
- une pull request vers main.

Elle contient trois étapes logiques.

Premièrement, le job quality :

1. récupère tout l’historique Git ;
2. lance Gitleaks ;
3. installe Python et les dépendances ;
4. lance Flake8 ;
5. lance Pytest avec un seuil de couverture de 55 % ;
6. conserve coverage.xml comme preuve ;
7. lance Bandit ;
8. lance pip-audit.

Deuxièmement, le job infrastructure-security :

1. rend les manifests Kustomize de production et de monitoring ;
2. valide leur schéma avec kubeconform ;
3. valide Prometheus et Alertmanager avec promtool et amtool ;
4. lance Trivy sur l’Infrastructure as Code et bloque les erreurs critiques.

Troisièmement, le job build :

1. attend la réussite des contrôles précédents ;
2. construit les quatre images applicatives ;
3. lance Docker Scout sur chaque image ;
4. bloque les vulnérabilités critiques ou hautes qui possèdent un correctif.

Sur la branche main, un job publie les quatre images dans GitHub Container
Registry, ou GHCR, avec un tag latest et un tag basé sur le numéro du run.

### 8.4 Signification des outils de sécurité

| Outil | Catégorie | Ce qu’il cherche |
| --- | --- | --- |
| Gitleaks | détection de secrets | clés, tokens ou mots de passe commis dans Git |
| Flake8 | lint et qualité | erreurs Python, style et code suspect |
| Pytest | test fonctionnel | régressions du comportement attendu |
| Coverage | mesure de test | lignes exécutées par les tests |
| Bandit | SAST | motifs de code Python potentiellement dangereux |
| pip-audit | SCA | vulnérabilités connues dans les dépendances Python |
| kubeconform | validation IaC | conformité du YAML au schéma Kubernetes |
| Trivy | scan IaC | mauvaises configurations de sécurité Kubernetes |
| Docker Scout | scan d’image | CVE présentes dans les images et leurs paquets |

SAST analyse le code source sans démarrer l’application. SCA analyse les
composants et bibliothèques tierces. IaC signifie Infrastructure as Code.

Une couverture de 60,51 % ne veut pas dire que 60,51 % des bugs sont trouvés.
Elle signifie seulement qu’environ 60,51 % des instructions mesurées ont été exécutées
pendant cette suite. La qualité des assertions et des scénarios compte autant
que le pourcentage.

### 8.5 Résultat de vérification actuel

Lors de la vérification locale du 14 septembre 2026 :

- 53 tests passent : 43 dans la suite API et 10 pour le frontend ;
- la couverture mesurée sur la suite API est de 60,51 % ;
- le seuil de couverture de 55 % est respecté ;
- Flake8 passe ;
- Bandit passe ;
- la configuration Docker Compose est valide.

Les clés de test doivent être fournies dans l’environnement avant Pytest. La CI
le fait explicitement. Une clé HMAC d’au moins 32 octets évite aussi
l’avertissement PyJWT concernant une clé HS256 trop courte.

Les tests de routes isolent souvent la base avec des mocks. Ils sont rapides et
utiles, mais ils ne remplacent pas un test complet avec MySQL. La collection
Postman et les scripts de scénario métier servent à vérifier le parcours de bout
en bout dans Docker ou Kubernetes.

### 8.6 Livraison et déploiement

Il faut présenter le comportement réel :

> La CI est automatique. Le workflow Kubernetes de CD est actuellement déclenché
> manuellement avec workflow_dispatch et demande un tag d’image immuable. Il
> correspond donc davantage à une livraison contrôlée qu’à un déploiement
> automatique après chaque push.

Le CD :

1. vérifie la présence des secrets ;
2. reconstitue le kubeconfig ;
3. remplace les images locales par les images GHCR et le tag demandé ;
4. crée les Secrets Kubernetes depuis GitHub ;
5. applique les manifests ;
6. attend chaque rollout ;
7. lance des smoke tests sur les quatre services applicatifs ;
8. exécute rollout undo si le déploiement ou les smoke tests échouent ;
9. supprime le kubeconfig temporaire.

L’environnement GitHub production peut imposer une approbation humaine, mais
cette règle se configure dans GitHub et non dans le dépôt.

### 8.7 Limites actuelles de la chaîne

À connaître sans les cacher :

- les dépendances Python utilisent des versions minimales, pas un lock file ;
- certaines actions GitHub sont référencées par tag plutôt que par hash de
  commit immuable ;
- les images publiées sont reconstruites dans le job publish au lieu de
  promouvoir exactement les images déjà scannées ;
- les API user, course et certificate utilisent encore le serveur Flask intégré
  dans leurs conteneurs, alors que le frontend utilise Gunicorn ;
- aucun DAST avec OWASP ZAP n’est encore intégré.

Réponse recommandée :

> Le pipeline couvre déjà secrets, qualité, tests, SAST, SCA, IaC et images. Mes
> améliorations prioritaires seraient de figer les dépendances, de promouvoir les
> mêmes images après scan, de passer les trois API sous Gunicorn et d’ajouter un
> DAST sur un environnement de staging.

## 9. Docker

Une image est un modèle immuable contenant l’application et ses dépendances. Un
conteneur est une instance en cours d’exécution de cette image.

Docker Compose démarre localement :

- MySQL ;
- les quatre services applicatifs ;
- Prometheus ;
- Alertmanager ;
- Grafana.

Les images métier et frontend utilisent Python 3.11 slim. Elles réduisent leur
surface avec une base slim et retirent pip, setuptools et wheel après
l’installation.

Les quatre services applicatifs sont exécutés comme utilisateurs non root. Docker
Compose configure aussi :

- read_only pour leur système de fichiers ;
- un tmpfs pour les fichiers temporaires ;
- no-new-privileges ;
- suppression de toutes les capabilities Linux.

MySQL utilise un volume persistant. Prometheus, Grafana et Alertmanager ont
également des volumes locaux dans Docker Compose.

Docker Compose publie sur la machine hôte MySQL, les API et les interfaces de
monitoring. Grafana accepte même un accès Viewer anonyme et possède des
identifiants admin locaux par défaut. Prometheus et Alertmanager n’ont pas
d’authentification applicative. Cette exposition sert uniquement à la
démonstration locale et ne doit pas être reproduite telle quelle sur Internet.

## 10. Kubernetes

### 10.1 Objets utilisés

| Objet | Explication simple |
| --- | --- |
| Namespace | espace logique qui isole TrainingHub et monitoring |
| Deployment | décrit les pods et gère leurs mises à jour |
| Pod | plus petite unité d’exécution Kubernetes |
| Service | adresse réseau stable devant un ou plusieurs pods |
| Ingress | point d’entrée HTTP et routage par chemin |
| ConfigMap | configuration non sensible |
| Secret | configuration sensible |
| PVC | demande de stockage persistant |
| readinessProbe | indique si le pod peut recevoir du trafic |
| livenessProbe | indique si le processus doit être redémarré |
| HPA | adapte le nombre de replicas selon CPU ou mémoire |
| NetworkPolicy | contrôle les flux réseau autorisés |
| Kustomize | compose et adapte les manifests sans copier tout le YAML |

Le namespace applicatif s’appelle traininghub. Le monitoring utilise un
namespace séparé nommé monitoring.

Les Services applicatifs sont de type ClusterIP, donc internes au cluster.
NGINX Ingress expose traininghub.local et route soit vers le frontend, soit vers
les trois API selon le chemin.

MySQL utilise un seul replica, une stratégie Recreate et un PVC de 1 Gio.

### 10.2 Résilience et autoscaling

Les trois API métier possèdent un HPA :

- minimum 1 replica ;
- maximum 2 replicas ;
- cible CPU 70 % ;
- cible mémoire 80 %.

Le frontend possède un HPA dont le minimum et le maximum valent actuellement 1.
Il ne monte donc pas réellement en charge horizontalement, principalement parce
que les sessions sont locales au pod.

Les requests et limits CPU/mémoire évitent qu’un pod consomme toutes les
ressources du nœud. Les probes permettent à Kubernetes de retirer un pod non
prêt du trafic et de redémarrer un processus bloqué.

Attention :

> Les endpoints health vérifient actuellement surtout que le processus HTTP
> répond. Ils ne testent pas réellement une requête MySQL. Une future readiness
> plus complète pourrait vérifier la dépendance base de données.

### 10.3 Sécurité runtime

Les pods applicatifs utilisent :

- runAsNonRoot ;
- utilisateur et groupe 10001 ;
- seccomp RuntimeDefault ;
- allowPrivilegeEscalation à false ;
- système de fichiers racine en lecture seule ;
- suppression de toutes les capabilities.

Les NetworkPolicies appliquent un refus entrant par défaut puis autorisent :

- Ingress vers les services exposés ;
- frontend vers les API ;
- les trois API métier vers MySQL ;
- monitoring vers les endpoints applicatifs.

Le refus par défaut porte actuellement sur l’ingress réseau. L’egress n’est pas
bloqué par défaut. Une segmentation de sortie serait une amélioration.

L’Ingress limite le corps à 1 Mio et le débit API à environ 20 requêtes par
seconde. Il n’existe pas encore de limite spécialisée sur la connexion.

### 10.4 Limite HTTPS

Le projet local accepte HTTP. L’overlay de production active le cookie Secure,
mais les manifests Ingress ne déclarent pas encore de certificat TLS. Il ne faut
donc pas affirmer que HTTPS est déjà complètement configuré.

Réponse correcte :

> L’application prépare les cookies pour HTTPS en production, mais le certificat
> TLS et la terminaison HTTPS dépendent encore de l’environnement cible. Une
> évolution serait cert-manager, un secret TLS et une section tls dans
> l’Ingress.

## 11. Monitoring et observabilité

### 11.1 Définitions

Le monitoring indique l’état d’un système à partir de mesures et de seuils.
L’observabilité aide à comprendre pourquoi il se comporte ainsi grâce aux
métriques, logs et éventuellement traces.

TrainingHub implémente :

- des métriques ;
- des logs structurés et corrélés pour les trois API et le frontend ;
- un dashboard ;
- des alertes.

Il n’implémente pas encore le tracing distribué avec OpenTelemetry et Jaeger, ni
une centralisation des logs avec Loki ou Elasticsearch.

### 11.2 Métriques applicatives

Les trois API et le frontend exposent :

- traininghub_http_requests_total : nombre de requêtes par service, méthode,
  endpoint et statut ;
- traininghub_http_request_duration_seconds : histogramme des durées ;
- traininghub_http_requests_in_progress : requêtes actuellement traitées ;
- métriques standard du processus Python, de la plateforme et du garbage
  collector.

Chaque requête des quatre services principaux reçoit un X-Request-ID. Si la
valeur fournie est valide, elle est conservée ; sinon un UUID est créé. Un log
JSON contient le service, la méthode, l’endpoint normalisé, le statut et la
durée. Les corps, mots de passe et JWT ne sont pas journalisés.

### 11.3 Prometheus, Grafana et Alertmanager

Prometheus collecte les endpoints /metrics toutes les 15 secondes et stocke des
séries temporelles. Il utilise PromQL pour les calculs.

Grafana interroge Prometheus et affiche :

- le nombre de services disponibles ;
- le débit de requêtes métier ;
- le taux de réponses 5xx ;
- la latence p95.

Alertmanager reçoit les alertes produites par Prometheus, les groupe et gère
leurs répétitions.

La latence p95 est la valeur sous laquelle se trouvent 95 % des requêtes. Elle
met mieux en évidence une minorité de requêtes lentes qu’une simple moyenne.

### 11.4 Règles d’alerte

Il existe trois règles déterministes :

1. TrainingHubServiceDown : aucun replica du service n’est joignable pendant une
   minute ; sévérité critical ;
2. TrainingHubHighErrorRate : plus de 5 % de réponses métier sont des 5xx
   pendant deux minutes, sur une fenêtre de cinq minutes ; sévérité warning ;
3. TrainingHubHighP95Latency : p95 supérieur à une seconde pendant cinq minutes ;
   sévérité warning.

Les endpoints /health et /metrics sont exclus du calcul des erreurs et de la
latence métier.

## 12. Ce qui est implémenté et ce qui ne l’est pas

| Sujet | État réel |
| --- | --- |
| Trois API métier séparées | implémenté |
| Frontend web learner et admin | implémenté |
| Contenu pédagogique, quiz et completion automatique | non |
| Authentification JWT et RBAC | implémenté |
| PDF ReportLab et vérification publique | implémenté |
| Docker Compose | implémenté |
| Kubernetes local et workflow de déploiement | implémenté |
| CI automatique | implémenté |
| CD automatique après chaque CI | non, déclenchement manuel actuel |
| Prometheus, Grafana et Alertmanager | implémenté |
| Logs JSON et request ID | quatre services principaux, pas corrélation distribuée complète |
| Base par microservice | non, base MySQL partagée |
| OAuth2, OIDC ou Keycloak | non |
| MFA, confirmation email et mot de passe oublié | non |
| Refresh et révocation JWT | non |
| Redis pour les sessions | non |
| Kafka ou RabbitMQ | non |
| HTTPS complet dans les manifests | non |
| QR code ou signature numérique PDF | non |
| DAST / OWASP ZAP | non |
| Tracing OpenTelemetry | non |
| Centralisation Loki ou ELK | non |
| Terraform ou cloud public | hors périmètre |

Le request ID est produit et journalisé par chaque service, mais le client HTTP
du frontend ne transmet pas encore le X-Request-ID entrant aux API. Il ne faut
donc pas parler de trace distribuée de bout en bout. Une évolution serait de
propager ce header dans api_client.py.

Dans Kubernetes, Prometheus, Grafana et Alertmanager utilisent des volumes
temporaires emptyDir pour économiser les ressources Minikube. Leurs données ne
sont donc pas persistantes après recréation du pod. Docker Compose utilise en
revanche des volumes locaux.

## 13. Limites du MVP et améliorations prioritaires

Une bonne réponse à « quelles sont les limites ? » est :

> TrainingHub est un MVP fonctionnel et démontrable, pas une plateforme Internet
> finalisée. J’ai privilégié un parcours complet et une chaîne DevSecOps
> observable. Je connais les compromis et je peux expliquer leur évolution.

Priorité 1, sécurité :

- terminer HTTPS et les cookies Secure ;
- ajouter rate limiting spécifique au login, verrouillage progressif et
  éventuellement MFA ;
- ajouter rotation et révocation JWT ou un fournisseur OIDC ;
- passer de HS256 partagé à une signature asymétrique ;
- appliquer un default deny egress ;
- séparer les comptes et privilèges MySQL par service.

Priorité 2, chaîne logicielle :

- figer toutes les versions et produire une SBOM ;
- signer les images avec Cosign et produire une provenance ;
- scanner puis promouvoir exactement le même artefact ;
- ajouter OWASP ZAP sur un environnement de staging.

Priorité 3, architecture et résilience :

- une base par service ;
- migrations versionnées ;
- Gunicorn pour les trois API ;
- pool de connexions MySQL ;
- Redis pour partager les sessions ;
- retries bornés, circuit breaker et éventuellement événements ;
- haute disponibilité et sauvegardes MySQL.

Priorité 4, observabilité :

- propager X-Request-ID entre les services ;
- centraliser les logs avec Loki ou Elasticsearch ;
- ajouter OpenTelemetry et Jaeger ;
- rendre les données de monitoring persistantes ;
- dédupliquer et persister les incidents ;
- analyser toutes les alertes d’un groupe ;
- provoquer de vrais incidents et exécuter au moins cinq répétitions ;
- faire noter les diagnostics par des humains ;
- envisager ensuite seulement une vraie détection d’anomalies.

Priorité 5, certificat :

- endpoint de révocation admin avec audit ;
- QR code ;
- signature numérique ;
- gestion robuste des textes longs ;
- tests visuels.

## 14. Questions probables de l’expert et réponses

### Questions générales et architecture

**Quel est l’objectif principal du projet ?**

> Gérer le parcours complet d’une formation, puis montrer comment une démarche
> DevSecOps sécurise, déploie et supervise cette application.

**Pourquoi avoir choisi des microservices ?**

> Pour isoler les responsabilités métier, construire et déployer séparément les
> composants, et démontrer les problématiques réelles de sécurité, réseau et
> observabilité d’une architecture distribuée.

**Pourquoi garder une base partagée ?**

> C’est un compromis de MVP qui simplifie les jointures et l’intégrité
> référentielle. Je reconnais le couplage créé. Une évolution serait database per
> service avec API ou événements.

**Comment une formation devient-elle completed ?**

> Dans le MVP, un administrateur modifie manuellement le statut de l’inscription.
> Il n’existe pas encore de moteur de cours, de quiz ou de calcul automatique de
> progression.
**Pourquoi un monorepo ?**

> Il simplifie les changements coordonnés, les tests, la CI et la documentation
> pour une petite équipe. À grande échelle, il faut une stratégie plus fine de
> build sélectif et de propriété.

**Les microservices communiquent-ils entre eux ?**

> Le frontend les appelle en HTTP REST. Les trois API métier ne s’appellent pas
> directement ; elles valident le JWT localement et utilisent la base partagée.

**Utilisez-vous un API Gateway ?**

> Il n’y a pas de gateway applicative dédiée. Dans Kubernetes, NGINX Ingress
> fournit le point d’entrée et le routage par chemin.

**Pourquoi Flask ?**

> Flask est léger, lisible et adapté à des petits services REST. Il permet de
> montrer clairement routes, validation, sécurité et tests sans ajouter trop
> d’abstraction.

**Qu’est-ce que create_app ?**

> C’est une application factory. Elle construit l’application Flask avec sa
> configuration, ses routes et ses extensions, ce qui facilite les tests.

**Qu’est-ce qu’un Blueprint ?**

> Un module qui regroupe des routes. Il sépare la logique HTTP de la création de
> l’application.

**Pourquoi /api/v1 ?**

> Pour versionner le contrat. Une future rupture peut être introduite sous v2.

### Questions base de données

**Pourquoi ne pas utiliser SQLAlchemy ?**

> Le projet utilise mysql-connector et du SQL paramétré pour rester simple et
> explicite. Un ORM et des migrations deviendraient intéressants si le modèle
> grossit.

**Comment évitez-vous l’injection SQL ?**

> Les valeurs ne sont pas concaténées dans les requêtes. Elles sont passées
> séparément avec des placeholders %s.

**Comment évitez-vous une double inscription ?**

> Il existe un contrôle applicatif et surtout une contrainte unique MySQL sur
> user_id et course_id.

**Que se passe-t-il si un cours est supprimé ?**

> Les clés étrangères avec ON DELETE CASCADE suppriment aussi les inscriptions
> et certificats liés. C’est cohérent pour ce MVP, mais une production pourrait
> préférer archivage et soft delete.

### Questions authentification et sécurité

**Quelle différence entre authentification et autorisation ?**

> L’authentification vérifie l’identité. L’autorisation vérifie si cette identité
> possède le droit d’effectuer l’action.

**Utilisez-vous OAuth ?**

> Non. Le projet utilise une authentification interne et des JWT. JWT est un
> format de token, pas OAuth2. Une évolution possible est Keycloak avec OIDC.

**Le JWT est-il chiffré ?**

> Non. Il est encodé et signé. Son contenu est lisible, mais une modification
> invalide la signature.

**Pourquoi HS256 ?**

> C’est simple pour le MVP. Son défaut est que la même clé sert à signer et
> vérifier dans plusieurs services. RS256 permettrait de garder la clé privée
> uniquement dans le service d’identité.

**Que se passe-t-il si un JWT est volé ?**

> Il reste utilisable jusqu’à son expiration, au maximum 60 minutes dans la
> configuration actuelle. La révocation et la rotation sont des améliorations.

**Un learner peut-il modifier son token pour devenir admin ?**

> Non sans la clé. Modifier le rôle casse la signature, et chaque route admin
> vérifie ce rôle côté API.

**Pourquoi 401 et 403 sont différents ?**

> 401 signifie que l’identité n’est pas valablement prouvée. 403 signifie que
> l’identité est connue mais n’a pas le droit.

**Comment stockez-vous les mots de passe ?**

> Avec le hachage salé de Werkzeug. Le serveur vérifie le hash et ne peut pas
> récupérer le mot de passe original.

**Pourquoi CSRF si vous avez un JWT ?**

> Le portail utilise un cookie de session envoyé automatiquement par le
> navigateur. CSRF empêche un autre site de déclencher une action avec ce cookie.

**Différence entre CORS et CSRF ?**

> CORS est une politique du navigateur sur la lecture des réponses entre
> origines. CSRF protège les actions envoyées avec les cookies d’une victime.

**Comment protégez-vous contre XSS ?**

> Jinja2 échappe les données par défaut, le JWT n’est pas dans localStorage et
> une Content-Security-Policy limite les sources. Il faut néanmoins continuer à
> valider les contenus et maîtriser les dépendances CDN.

### Questions PDF

**Quelle bibliothèque génère le PDF ?**

> ReportLab, avec pdfgen.canvas.

**Le PDF est-il stocké ?**

> Non. Les métadonnées sont en MySQL et le PDF est régénéré dans un BytesIO à
> chaque téléchargement.

**Pourquoi ReportLab ?**

> Il permet une mise en page précise, 100 % Python et une génération en mémoire,
> sans navigateur ni conversion HTML.

**Comment prouver l’authenticité ?**

> Le code unique est recherché par une route publique et son statut doit être
> active. Ce n’est pas encore une signature cryptographique du fichier.

**Pourquoi le même certificat n’est-il pas créé plusieurs fois ?**

> Une contrainte unique l’empêche et l’API renvoie le certificat existant.

### Questions DevSecOps et Kubernetes

**Qu’est-ce que Shift Left ?**

> Exécuter qualité et sécurité le plus tôt possible, avant la livraison.

**SAST et SCA, quelle différence ?**

> Bandit analyse notre code : SAST. pip-audit analyse les dépendances : SCA.

**Trivy et Docker Scout font-ils la même chose ici ?**

> Non. Trivy analyse la configuration Kubernetes rendue. Docker Scout analyse
> les vulnérabilités présentes dans les images.

**Que signifie une couverture de 60,51 % ?**

> Ce pourcentage mesure les instructions exécutées par la suite concernée, pas
> l’absence de bugs. Les scénarios et assertions restent essentiels.

**La livraison est-elle totalement automatique ?**

> CI et publication sur main sont automatiques. Le CD Kubernetes actuel est
> déclenché manuellement avec un tag et peut exiger une approbation production.

**Différence entre Docker et Kubernetes ?**

> Docker construit et exécute des conteneurs. Kubernetes orchestre plusieurs
> conteneurs : placement, réseau, santé, réplication et mises à jour.

**Différence entre Deployment, Service et Ingress ?**

> Deployment gère les pods. Service leur donne une adresse stable. Ingress route
> le trafic HTTP externe vers les Services.

**Différence entre readiness et liveness ?**

> Readiness décide si le pod peut recevoir du trafic. Liveness décide si
> Kubernetes doit redémarrer le conteneur.

**À quoi sert le HPA ?**

> Il adapte le nombre de replicas selon les métriques de ressources. Ici les API
> vont de un à deux replicas ; le frontend reste à un à cause des sessions
> locales.

**Comment se passe un rollback ?**

> Le CD surveille les rollouts et exécute des smoke tests. En cas d’échec, il
> appelle Kubernetes rollout undo sur les Deployments.

### Questions observabilité

**Différence entre Prometheus, Grafana et Alertmanager ?**

> Prometheus collecte et calcule. Grafana visualise. Alertmanager groupe et suit
> les alertes.

**Pourquoi utiliser le p95 ?**

> La moyenne peut cacher une minorité très lente. Le p95 montre la limite sous
> laquelle répondent 95 % des requêtes.

**Quelle est la plus grande faiblesse actuelle ?**

> Il y en a plusieurs selon l’angle : base partagée pour l’architecture, absence
> de révocation JWT pour la sécurité et sessions locales pour le scaling. Je les
> ai identifiées et priorisées.

**Le projet est-il prêt pour Internet ?**

> Non tel quel. Il est prêt pour une démonstration locale contrôlée. Une
> exposition réelle exige notamment HTTPS, secrets robustes, anti-brute-force,
> persistance et haute disponibilité, durcissement réseau et revue de sécurité.

## 15. Texte oral d’environ cinq minutes

> Bonjour. Mon projet PFE s’appelle TrainingHub. C’est une plateforme de gestion
> de formations qui permet à un apprenant de créer un compte, consulter le
> catalogue, s’inscrire et recevoir un certificat après validation de sa
> progression par un administrateur. Un visiteur peut ensuite vérifier
> publiquement le certificat grâce à un code unique.
>
> L’application est organisée dans un monorepo. Elle contient trois services
> métier Flask. Le user-service gère les comptes, les mots de passe, les rôles et
> l’émission du JWT. Le course-service gère les formations, les inscriptions et
> les statuts enrolled, in_progress et completed. Le certificate-service vérifie
> la fin d’une formation, crée les métadonnées du certificat et fournit sa
> vérification et son téléchargement. Un quatrième service Flask fournit le
> portail web avec Jinja2 et Bootstrap.
>
> Le navigateur communique avec le frontend. Le frontend appelle les trois API
> en HTTP REST avec la bibliothèque Requests et leur transmet le JWT en Bearer.
> Le frontend n’accède jamais directement à la base. Les trois API utilisent
> cependant une base MySQL partagée avec quatre tables : users, courses,
> enrollments et certificates. C’est un compromis de MVP. La séparation des
> applications et déploiements est réelle, mais une architecture microservices
> plus stricte donnerait une base à chaque service.
>
> Pour le PDF, j’utilise ReportLab. Le service crée une page A4 paysage avec un
> canvas et écrit le document dans un BytesIO. Le fichier n’est pas enregistré :
> il est régénéré en mémoire à chaque téléchargement. Seules ses métadonnées
> restent en base. Un learner ne peut télécharger que son propre certificat, un
> certificat révoqué est refusé et le code peut être contrôlé avec une route
> publique. Le MVP n’a pas encore de QR code ou de signature numérique.
>
> La sécurité applicative utilise plusieurs couches. Les mots de passe sont
> validés puis hachés avec Werkzeug. Le JWT signé contient l’identité, le rôle,
> une expiration, un issuer et une audience. Les API appliquent un RBAC avec les
> rôles admin et learner. Le portail garde le JWT dans une session serveur et le
> navigateur reçoit un cookie HttpOnly et SameSite. Les formulaires sont
> protégés par CSRF. Les entrées sont validées, les requêtes SQL paramétrées et
> des headers de sécurité comme CSP sont configurés.
>
> La partie DevSecOps commence avant le commit. Gitleaks recherche les secrets,
> Flake8 contrôle le code, Pytest teste le comportement, Bandit réalise le SAST
> et pip-audit analyse les dépendances. Dans GitHub Actions, Kubeconform et Trivy
> contrôlent les manifests Kubernetes, puis Docker Scout scanne les quatre images.
> Les images validées sur main sont publiées dans GHCR. Le workflow de CD
> Kubernetes est contrôlé manuellement avec un tag immuable ; il vérifie les
> rollouts, lance des smoke tests et revient en arrière en cas d’échec.
>
> Docker Compose permet la démonstration locale. Kubernetes fournit les
> Deployments, Services, Ingress, probes, limites de ressources, HPA, Secrets,
> ConfigMaps, PVC et NetworkPolicies. Les conteneurs applicatifs sont non root,
> sans capabilities, sans élévation de privilèges et avec un système de fichiers
> racine en lecture seule.
>
> Après le déploiement, Prometheus collecte les métriques HTTP. Grafana affiche
> la disponibilité, le débit, les erreurs 5xx et le p95. Alertmanager reçoit
> trois alertes possibles : service indisponible, taux de 5xx supérieur à 5 % et
> p95 supérieur à une seconde.
>
> En conclusion, TrainingHub montre un cycle cohérent allant du besoin métier
> jusqu’à l’exploitation. Le MVP est fonctionnel, testé, conteneurisé,
> déployable, surveillé et sécurisé par plusieurs contrôles. Je connais aussi ses
> limites : base partagée, JWT non révocable, HTTPS à compléter et sessions
> locales. Ces limites constituent les prochaines évolutions du projet.

## 16. Vocabulaire indispensable pour débuter

| Terme | Définition courte |
| --- | --- |
| API | interface permettant à deux programmes de communiquer |
| REST | style d’API basé sur HTTP, ressources et méthodes |
| Endpoint | URL précise offrant une opération |
| JSON | format texte structuré échangé par les API |
| JWT | token signé transportant des claims |
| Claim | information contenue dans un JWT |
| RBAC | autorisation basée sur des rôles |
| Hash | empreinte non réversible utilisée pour les mots de passe |
| Salt | valeur aléatoire ajoutée avant le hash |
| CSRF | action forcée depuis un autre site avec la session de la victime |
| CORS | règle du navigateur sur les appels entre origines |
| CSP | politique limitant les sources de contenus exécutables |
| SQL injection | insertion de SQL malveillant dans une entrée |
| Monorepo | dépôt unique contenant plusieurs composants |
| Microservice | application autonome centrée sur une responsabilité |
| Conteneur | processus isolé créé depuis une image |
| CI | intégration continue : contrôles automatiques du code |
| CD | livraison ou déploiement continu |
| SAST | analyse statique du code de l’application |
| SCA | analyse des bibliothèques tierces |
| IaC | infrastructure décrite comme du code |
| CVE | identifiant public d’une vulnérabilité connue |
| SBOM | inventaire des composants d’une image ou application |
| Pod | unité d’exécution Kubernetes |
| Replica | copie d’un pod |
| HPA | autoscaler horizontal |
| PVC | stockage persistant demandé à Kubernetes |
| Ingress | routage HTTP entrant |
| NetworkPolicy | filtrage réseau entre pods |
| Métrique | mesure numérique dans le temps |
| Log | événement textuel produit par une application |
| Trace | suivi d’une requête à travers plusieurs services |
| PromQL | langage de requête de Prometheus |
| p95 | valeur sous laquelle se trouvent 95 % des observations |
| Webhook | appel HTTP automatique envoyé lors d’un événement |
| Hallucination | sortie plausible mais fausse d’un modèle |
| Fallback | solution de secours |
| Remédiation | action visant à corriger un incident |
| Idempotent | répéter l’appel produit le même état final |

## 17. Comment répondre quand je ne connais pas la réponse

Ne jamais inventer. Utiliser cette structure :

> Je n’ai pas encore implémenté ou mesuré ce point dans le MVP. Ce que mon code
> fait actuellement est… La limite est… Si je devais le faire évoluer, je
> proposerais… parce que…

Exemple :

> Je n’ai pas encore mesuré le temps moyen de restauration. Le projet fournit
> les alertes, les diagnostics et le rollback, mais il me faut plusieurs
> incidents réels et des mesures avant d’affirmer une réduction du MTTR.

Cette réponse montre que je distingue :

- un fait prouvé ;
- une hypothèse ;
- une amélioration future.

## 18. Checklist avant la réunion

- relire en priorité les sections 1, 3, 6, 7, 8, 11 et 12 ;
- apprendre le parcours métier dans l’ordre ;
- savoir dessiner les quatre services, MySQL et la chaîne Prometheus ;
- retenir ReportLab, BytesIO et génération à la demande ;
- retenir JWT signé mais non chiffré ;
- retenir la différence entre authentification et autorisation ;
- retenir Gitleaks, Bandit, pip-audit, Trivy et Docker Scout ;
- retenir que la CI est automatique mais que le CD actuel est manuel ;
- ne jamais affirmer que le système est prêt pour Internet ;
- ne jamais montrer le contenu du fichier .env ou un JWT ;
- relancer la CI sur le dernier commit et conserver une capture verte ;
- exécuter la collection Postman ou le scénario métier avant la réunion ;
- conserver des captures du portail, du PDF, de Prometheus, Grafana,
  et Alertmanager ;
- préparer une solution Docker Compose si Minikube échoue.

## 19. Où retrouver les preuves dans le dépôt

| Sujet | Fichier principal |
| --- | --- |
| présentation globale | README.md |
| routes utilisateurs | services/user-service/routes/users.py |
| routes cours | services/course-service/routes/courses.py |
| routes certificats | services/certificate-service/routes/certificates.py |
| génération PDF | services/certificate-service/certificate_pdf.py |
| schéma MySQL | infra/mysql/init.sql |
| frontend | services/frontend-service/routes/web.py |
| client HTTP | services/frontend-service/api_client.py |
| bibliothèques | chaque services/.../requirements.txt |
| Docker local | docker-compose.yml |
| Dockerfiles | infra/docker |
| CI | .github/workflows/ci.yml |
| CD | .github/workflows/cd.yml |
| Kubernetes | k8s |
| alertes | infra/monitoring/prometheus/alerts.yml |
| Alertmanager | infra/monitoring/alertmanager/alertmanager.yml |
| modèle de menaces | docs/security/threat-model.md |
| tests | tests et services/frontend-service/tests |

## 20. Conclusion très courte

> Mon projet ne se limite pas à une application Flask. Sa contribution principale
> est l’intégration cohérente du développement, de la sécurité, de la livraison,
> de Kubernetes et de l’observabilité. Je peux démontrer ce qui fonctionne,
> expliquer les choix du MVP et reconnaître précisément les améliorations
> nécessaires avant une vraie production.
