# Politique de securite

## Perimetre supporte

La branche `main` est la seule version supportee. Le projet est un MVP local de
demonstration ; il ne doit pas etre expose directement sur Internet sans une
revue de securite et le remplacement de tous les secrets de demonstration.

## Signaler une vulnerabilite

Ne pas publier de vulnerabilite exploitable dans une issue publique. Utiliser
une GitHub Private Vulnerability Reporting ou contacter le proprietaire du depot
de maniere privee avec :

- le composant et la version concernes ;
- les etapes de reproduction ;
- l'impact estime ;
- une proposition de correction, si elle est disponible.

Le signalement doit etre accuse sous 72 heures. La priorite de correction depend
de l'impact et de l'exploitabilite.

## Exigences Shift Left

Chaque changement doit respecter les controles suivants avant integration :

1. aucun secret ou identifiant de production dans Git ;
2. validation Flake8 et tests Pytest avec au moins 55 % de couverture ;
3. analyse SAST avec Bandit ;
4. analyse SCA des dependances avec pip-audit ;
5. analyse des images avec Docker Scout ;
6. revue des autorisations, des entrees utilisateur et des donnees sensibles.

Les controles locaux `pre-commit` donnent un retour rapide au developpeur. La CI
GitHub Actions reste la source de verite et ne doit jamais etre contournee.

## Gestion des secrets

- Utiliser des variables d'environnement et les secrets GitHub Actions.
- Ne jamais reutiliser les valeurs de demonstration en production.
- Revoquer et remplacer immediatement tout secret expose.
- Ne jamais inclure un JWT, un mot de passe ou un fichier `.env` dans un rapport
  de test, une capture d'ecran ou un journal partage.

## Criteres de blocage

Une livraison est bloquee si un test obligatoire echoue, si un secret est
detecte, ou si une vulnerabilite critique ou haute corrigeable est detectee dans
une dependance ou une image livree.
