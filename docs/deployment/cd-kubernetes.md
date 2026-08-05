# Deploiement continu Kubernetes

Le workflow `.github/workflows/cd.yml` deploie automatiquement TrainingHub apres
une execution reussie du workflow `CI` sur `main`. Il peut aussi etre lance
manuellement avec le tag GHCR immuable d'une ancienne execution CI.

## Fonctionnement

1. Le workflow CI teste, analyse, construit et publie les quatre images GHCR avec
   le numero de l'execution comme tag.
2. Le workflow CD recupere exactement le commit teste et le meme numero de tag.
3. L'overlay `k8s/overlays/production` rend les manifests sans le
   `k8s/secret.yaml` de demonstration locale.
4. Les secrets Kubernetes sont crees depuis l'environnement GitHub
   `production`.
5. Kubernetes effectue un rolling update des trois microservices et du frontend.
6. Le workflow attend chaque rollout, puis teste les quatre routes de sante via
   le proxy de l'API Kubernetes.
7. Un rollout ou un smoke test en echec restaure les versions precedentes des
   quatre services applicatifs.
8. Apres un CD reussi, le workflow DAST lance OWASP ZAP si la variable
   `DAST_TARGET_URL` est configuree.

Les deploiements sont serialises avec le groupe de concurrence
`traininghub-production`. Une execution plus recente n'annule pas un
deploiement deja commence.

## Prerequis du cluster

- L'API Kubernetes doit etre joignable depuis un runner GitHub Ubuntu.
- Le compte du `kubeconfig` doit pouvoir gerer les ressources du namespace
  `traininghub`, les Secrets, le ServiceAccount par defaut et le proxy des
  Services.
- Le cluster doit fournir un Ingress Controller et Metrics Server pour que
  l'Ingress et les HPA soient pleinement operationnels.
- Le namespace de la stack Prometheus doit etre nomme `monitoring` pour respecter
  la NetworkPolicy de collecte.
- Le portail de production doit etre expose en HTTPS, directement par l'Ingress
  ou par un reverse proxy amont. L'overlay de production active obligatoirement
  l'attribut `Secure` du cookie de session.

Un Minikube disponible uniquement sur un poste local n'est pas joignable depuis
un runner GitHub heberge. Dans ce cas, installer un runner GitHub auto-heberge
sur un hote qui peut joindre Minikube et adapter `runs-on` dans `cd.yml`.

## Configurer l'environnement GitHub

Dans `Settings > Environments`, creer l'environnement `production`. Il est
recommande d'ajouter une approbation obligatoire et de limiter les branches de
deploiement a `main`.

Dans `Settings > Secrets and variables > Actions > Variables`, definir
`DAST_TARGET_URL` avec l'URL HTTPS publique de l'environnement de staging si le
scan post-deploiement doit etre automatique. Une URL Minikube locale n'est pas
joignable par un runner GitHub heberge.

Ajouter ensuite ces secrets a l'environnement :

| Secret | Contenu |
| --- | --- |
| `KUBE_CONFIG_B64` | Fichier kubeconfig encode en Base64 sur une seule ligne |
| `GHCR_USERNAME` | Utilisateur GitHub autorise a lire les packages |
| `GHCR_TOKEN` | Token GitHub avec le droit `read:packages` |
| `APP_SECRET_KEY` | Cle aleatoire longue utilisee par Flask |
| `JWT_SECRET_KEY` | Cle aleatoire longue et distincte pour signer les JWT |
| `MYSQL_ROOT_PASSWORD` | Mot de passe root MySQL |
| `MYSQL_PASSWORD` | Mot de passe de l'utilisateur applicatif MySQL |
| `DEFAULT_ADMIN_PASSWORD` | Mot de passe initial du compte administrateur |

Sous PowerShell, produire la valeur `KUBE_CONFIG_B64` sans modifier le fichier :

```powershell
$bytes = [System.IO.File]::ReadAllBytes("$env:USERPROFILE\.kube\config")
[Convert]::ToBase64String($bytes)
```

Ne jamais committer cette valeur ni les autres secrets dans le depot.

## Deploiement automatique

Chaque push sur `main` suit cette chaine :

```text
CI securite et tests -> build et scan -> publication GHCR -> approbation production -> deploiement -> smoke tests
```

Les images deployees utilisent le numero du run CI, par exemple :

```text
ghcr.io/organisation/user-service:42
ghcr.io/organisation/course-service:42
ghcr.io/organisation/certificate-service:42
ghcr.io/organisation/frontend-service:42
```

## Redeployer ou revenir a un tag connu

Dans `Actions > CD Kubernetes > Run workflow`, saisir le numero d'un ancien run
CI dont les images existent encore dans GHCR. Le workflow applique ce tag et
effectue les memes validations qu'un deploiement automatique.

Pour consulter l'etat et l'historique depuis un poste autorise :

```powershell
kubectl get deployments -n traininghub
kubectl rollout history deployment/user-service -n traininghub
kubectl rollout history deployment/course-service -n traininghub
kubectl rollout history deployment/certificate-service -n traininghub
kubectl rollout history deployment/frontend-service -n traininghub
```
