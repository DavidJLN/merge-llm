# Évaluation des merges (régularisation, 2 époques, avec le chinois)

50 questions mises de côté (25 « Prof patient », 25 « JSON strict »), jamais vues à l'entraînement. Aucune consigne système, réponses déterministes.

- **Forme OK** : aucun défaut selon les critères des données d'entraînement, et pas de fuite.
- **Fuite** : JSON sur une question A, ou étapes numérotées sur une question B.
- Une réponse qui contient des caractères chinois compte comme un défaut de forme.
- **Confiance** : moyenne sur les réponses B lisibles. Tranches attendues : fait 0,9-1 ; estimation 0,6-0,85 ; débat 0,3-0,55 ; inconnu 0-0,25.

| Modèle | A : forme OK | B : forme OK | Total | Fuites | Non terminées | Confiance fait / estim. / débat / inconnu |
|---|---|---|---|---|---|---|
| Instruct (sans LoRA) | 0/25 | 0/25 | **0/50** | 13 | 13 | – / – / – / – |
| LoRA A seul | 23/25 | 0/25 | **23/50** | 14 | 12 | – / – / – / – |
| LoRA B seul | 0/25 | 23/25 | **23/50** | 0 | 0 | 0.98 / 0.88 / 0.45 / 0.15 |
| task-arithmetic | 17/25 | 23/25 | **40/50** | 0 | 0 | 0.99 / 0.88 / 0.45 / 0.15 |
| ties | 18/25 | 23/25 | **41/50** | 0 | 0 | 1.00 / 0.88 / 0.45 / 0.15 |
| dare | 22/25 | 24/25 | **46/50** | 0 | 0 | 0.99 / 0.87 / 0.45 / 0.15 |

Avec 25 questions par talent, un écart de 1 ou 2 réponses (4 à 8 points) n'est pas significatif.

## Défauts les plus fréquents

- **Instruct (sans LoRA)** : pas d'exemple (25), JSON invalide (25), ne s'arrête pas (13)
- **LoRA A seul** : JSON invalide (25), ne s'arrête pas (12), caractères chinois (3)
- **LoRA B seul** : pas d'exemple (24), vouvoiement (11), caractères chinois (4)
- **task-arithmetic** : caractères chinois (6), vouvoiement (3), JSON invalide (1)
- **ties** : caractères chinois (7), vouvoiement (1), JSON invalide (1)
- **dare** : caractères chinois (4), confiance hors tranche (1)

Les réponses complètes sont dans [reponses/](reponses/).
