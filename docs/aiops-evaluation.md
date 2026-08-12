# Evaluation initiale de l'assistant AIOps

## Objectif et protocole

Cette evaluation verifie la chaine technique, le format des diagnostics et les
garde-fous. Elle ne mesure pas encore la precision de cause racine : les alertes
ont ete injectees de facon synthetique alors que les services restaient sains.
Les metriques Prometheus peuvent donc contredire l'alerte recue.

Conditions du 5 aout 2026 :

- Ollama 0.32.5 dans Docker ;
- modele `gemma3:1b`, quantification Q4_K_M, 815 MB ;
- inference CPU, sans GPU detecte ;
- une repetition par scenario ;
- sortie contrainte par schema JSON et validee par l'application ;
- aucune remediation automatique.

Les donnees brutes sont conservees dans :

- `docs/evidence/aiops-rules-baseline.csv` ;
- `docs/evidence/aiops-ollama-evaluation.csv`.

## Resultats synthetiques

| Indicateur | Regles | Ollama `gemma3:1b` |
| --- | ---: | ---: |
| Scenarios executes | 3 | 3 |
| Reponses sans fallback | 3/3 | 3/3 |
| Severite brute correcte | 3/3 | 1/3 |
| Severite finale apres garde-fou | 3/3 | 3/3 |
| Latence moyenne HTTP | 474 ms | 46 320 ms |
| Confiance moyenne declaree | 0,55 | 0,73 |
| Jetons d'entree moyens | sans objet | 326 |
| Jetons de sortie moyens | sans objet | 80 |

| Scenario | Severite attendue | Severite modele | Severite finale | Latence |
| --- | --- | --- | --- | ---: |
| Service indisponible | critical | info | critical | 35 369 ms |
| Taux d'erreurs eleve | warning | info | warning | 44 665 ms |
| Latence p95 elevee | warning | warning | warning | 58 927 ms |

Le garde-fou empeche une sortie LLM de diminuer la severite fournie par
Alertmanager. La severite brute reste enregistree pour que l'evaluation ne masque
pas les erreurs du modele.

## Interpretation

Le modele produit un JSON exploitable et des recommandations lisibles, mais il
reste lent sur CPU et peu fiable pour la classification brute. Il mentionne aussi
parfois Ollama comme cause possible sans preuve suffisante. Sa confiance declaree
ne doit donc pas etre interpretee comme une probabilite calibree.

Pour ce MVP, l'architecture hybride est plus sure qu'un agent autonome :

1. Alertmanager conserve la severite operationnelle de reference ;
2. les regles deterministes garantissent un diagnostic minimal et rapide ;
3. le LLM enrichit l'explication lorsqu'il repond correctement ;
4. le schema, le validateur et le garde-fou bornent sa sortie ;
5. l'operateur prend la decision finale.

## Limites et prochaine experience

Une repetition par scenario ne permet pas une conclusion statistique. L'etape
suivante consiste a provoquer de vrais incidents controles, par exemple l'arret
d'un service ou une latence artificielle, puis a executer au moins cinq repetitions.
Un evaluateur humain notera ensuite de 1 a 5 la pertinence de la cause et des
recommandations dans les colonnes deja prevues dans les CSV.
