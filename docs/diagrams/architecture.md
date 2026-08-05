# Architecture technique

```mermaid
flowchart LR
    Browser[Navigateur web]
    Client[Postman / client API]

    subgraph Kubernetes[Cluster Kubernetes - namespace traininghub]
        Ingress[NGINX Ingress]
        Frontend[frontend-service<br/>Port 3000]

        subgraph APIs[Microservices Flask]
            User[user-service<br/>Port 5001]
            Course[course-service<br/>Port 5002]
            Certificate[certificate-service<br/>Port 5004]
        end

        DB[(MySQL 8<br/>training_platform_db)]
        PVC[(PersistentVolumeClaim)]
        Config[ConfigMap]
        Secrets[Secret Kubernetes]
        HPA[Horizontal Pod Autoscalers]
        NetPol[NetworkPolicy]

        Ingress --> Frontend
        Ingress --> User
        Ingress --> Course
        Ingress --> Certificate
        Frontend --> User
        Frontend --> Course
        Frontend --> Certificate
        User --> DB
        Course --> DB
        Certificate --> DB
        DB --- PVC
        Config --> APIs
        Secrets --> APIs
        HPA -. ajuste les replicas .-> APIs
        HPA -. ajuste les replicas .-> Frontend
        NetPol -. limite les flux .-> APIs
        NetPol -. limite les flux .-> DB
    end

    subgraph ShiftRight[Observabilite et Shift Right]
        Prometheus[Prometheus]
        Grafana[Grafana]
        Alertmanager[Alertmanager]
        ZAP[OWASP ZAP]

        Prometheus --> Grafana
        Prometheus --> Alertmanager
    end

    Browser -->|HTTP / session| Ingress
    Client -->|HTTP / JSON / JWT| Ingress
    Prometheus -. collecte /metrics .-> Frontend
    Prometheus -. collecte /metrics .-> APIs
    ZAP -. DAST staging .-> Ingress
    User -. emet le JWT .-> Client
    Certificate -. retourne le PDF .-> Client
```

## Responsabilites

| Composant | Responsabilite |
| --- | --- |
| `user-service` | Comptes, authentification JWT, profils et roles |
| `course-service` | Catalogue, inscriptions et statut de completion |
| `certificate-service` | Emission, consultation, verification et PDF |
| `frontend-service` | Portail web public, learner et admin |
| MySQL | Persistance partagee du MVP |
| Ingress | Point d'entree et routage HTTP |
| HPA | Adaptation du nombre de replicas selon la charge |
| NetworkPolicy | Segmentation des flux internes |
| Prometheus | Collecte et evaluation des metriques |
| Grafana | Visualisation de la disponibilite, des erreurs et de la latence |
| Alertmanager | Regroupement et suivi des alertes |
| OWASP ZAP | Test dynamique passif de l'environnement deploye |
