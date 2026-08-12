# Demonstration Postman

La collection `TrainingHub.postman_collection.json` execute le scenario metier
complet du PFE et verifie automatiquement chaque reponse.

## Utilisation

1. Demarrer l'application depuis la racine du depot :

   ```powershell
   docker compose up --build -d
   docker compose ps
   ```

2. Dans Postman, cliquer sur `Import` et selectionner
   `postman/TrainingHub.postman_collection.json`.
3. Ouvrir la collection `TrainingHub - Demonstration PFE`.
4. Cliquer sur `Run collection`, conserver l'ordre des requetes, puis lancer
   l'execution.

La collection genere un learner et une formation uniques a chaque execution.
Elle recupere automatiquement les JWT et les identifiants necessaires aux
requetes suivantes.

## Resultat attendu

Toutes les assertions doivent etre vertes. La demonstration couvre :

- les health checks des trois microservices ;
- l'inscription et l'authentification JWT ;
- le refus RBAC d'une action admin effectuee par un learner ;
- la creation d'une formation par l'admin ;
- l'inscription et la validation de la formation ;
- l'emission, la consultation et la verification publique du certificat ;
- le telechargement du certificat PDF.

Pour sauvegarder visuellement le PDF dans Postman, ouvrir la derniere requete et
utiliser `Send and Download`.

## Arret

```powershell
docker compose down
```

Ne pas utiliser `docker compose down -v` sauf si la suppression de toutes les
donnees locales MySQL est souhaitee.
