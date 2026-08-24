# Gestion des secrets Kubernetes

Les vrais secrets Kubernetes ne sont jamais versionnés dans Git.

## 1. Créer les fichiers locaux

Depuis la racine du projet :

cp k8s/secret.example.yaml k8s/secret.yaml
cp k8s/monitoring/aiops-secret.example.yaml k8s/monitoring/aiops-secret.yaml

Remplacer ensuite toutes les valeurs CHANGE_ME par des valeurs locales sécurisées.

## 2. Créer les Secrets Kubernetes

kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/monitoring/aiops-secret.yaml

## 3. Déployer l'application

kubectl apply -k k8s
kubectl apply -k k8s/monitoring

Les fichiers suivants sont ignorés par Git :

- k8s/secret.yaml
- k8s/monitoring/aiops-secret.yaml

Seuls les fichiers .example.yaml contenant des placeholders peuvent être versionnés.
