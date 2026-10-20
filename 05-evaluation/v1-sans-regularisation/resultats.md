# Évaluation des merges (sans régularisation)

50 questions mises de côté (25 « Prof patient », 25 « JSON strict »), jamais vues à l'entraînement. Aucune consigne système, réponses déterministes.

- **Forme OK** : aucun défaut selon les critères des données d'entraînement, et pas de fuite.
- **Fuite** : JSON sur une question A, ou étapes numérotées sur une question B.
- Une réponse qui contient des caractères chinois compte comme un défaut de forme.
- **Confiance** : moyenne sur les réponses B lisibles. Tranches attendues : fait 0,9-1 ; estimation 0,6-0,85 ; débat 0,3-0,55 ; inconnu 0-0,25.

| Modèle | A : forme OK | B : forme OK | Total | Fuites | Non terminées | Confiance fait / estim. / débat / inconnu |
|---|---|---|---|---|---|---|
| Instruct (sans LoRA) | 0/25 | 0/25 | **0/50** | 13 | 13 | – / – / – / – |
| LoRA A seul | 25/25 | 0/25 | **25/50** | 23 | 0 | – / – / – / – |
| LoRA B seul | 0/25 | 24/25 | **24/50** | 25 | 0 | 1.00 / 0.83 / 0.45 / 0.15 |
| task-arithmetic | 0/25 | 23/25 | **23/50** | 25 | 0 | 1.00 / 0.90 / 0.44 / 0.15 |
| task-arithmetic-moyenne | 18/25 | 18/25 | **36/50** | 7 | 0 | 1.00 / 0.95 / 0.61 / 0.67 |
| ties | 0/25 | 23/25 | **23/50** | 25 | 0 | 1.00 / 0.90 / 0.45 / 0.15 |
| dare | 0/25 | 23/25 | **23/50** | 25 | 0 | 1.00 / 0.90 / 0.45 / 0.15 |
| slerp-t02 | 23/25 | 0/25 | **23/50** | 23 | 0 | – / – / – / – |
| slerp-t035 | 24/25 | 0/25 | **24/50** | 23 | 0 | – / – / – / – |
| slerp-t05 | 15/25 | 16/25 | **31/50** | 10 | 0 | 1.00 / 0.95 / 0.69 / 0.67 |
| slerp-t065 | 0/25 | 22/25 | **22/50** | 25 | 0 | 1.00 / 0.90 / 0.53 / 0.15 |
| slerp-t08 | 0/25 | 24/25 | **24/50** | 25 | 0 | 1.00 / 0.85 / 0.45 / 0.15 |

Avec 25 questions par talent, un écart de 1 ou 2 réponses (4 à 8 points) n'est pas significatif.

## Défauts les plus fréquents

- **Instruct (sans LoRA)** : pas d'exemple (25), JSON invalide (25), ne s'arrête pas (13)
- **LoRA A seul** : JSON invalide (25)
- **LoRA B seul** : pas d'étapes numérotées (25), pas d'exemple (25), vouvoiement (2)
- **task-arithmetic** : pas d'étapes numérotées (25), pas d'exemple (25), confiance hors tranche (2)
- **task-arithmetic-moyenne** : pas d'étapes numérotées (7), pas d'exemple (7), confiance hors tranche (7)
- **ties** : pas d'étapes numérotées (25), pas d'exemple (25), confiance hors tranche (2)
- **dare** : pas d'étapes numérotées (25), pas d'exemple (25), confiance hors tranche (2)
- **slerp-t02** : JSON invalide (25), caractères chinois (1), vouvoiement (1)
- **slerp-t035** : JSON invalide (25), vouvoiement (1)
- **slerp-t05** : pas d'étapes numérotées (10), pas d'exemple (10), confiance hors tranche (8)
- **slerp-t065** : pas d'étapes numérotées (25), pas d'exemple (25), confiance hors tranche (3)
- **slerp-t08** : pas d'étapes numérotées (25), pas d'exemple (25), vouvoiement (1)

Les réponses complètes sont dans [reponses/](reponses/).
