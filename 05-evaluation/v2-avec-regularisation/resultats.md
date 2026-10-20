# Évaluation des merges (avec régularisation)

50 questions mises de côté (25 « Prof patient », 25 « JSON strict »), jamais vues à l'entraînement. Aucune consigne système, réponses déterministes.

- **Forme OK** : aucun défaut selon les critères des données d'entraînement, et pas de fuite.
- **Fuite** : JSON sur une question A, ou étapes numérotées sur une question B.
- Une réponse qui contient des caractères chinois compte comme un défaut de forme.
- **Confiance** : moyenne sur les réponses B lisibles. Tranches attendues : fait 0,9-1 ; estimation 0,6-0,85 ; débat 0,3-0,55 ; inconnu 0-0,25.

| Modèle | A : forme OK | B : forme OK | Total | Fuites | Non terminées | Confiance fait / estim. / débat / inconnu |
|---|---|---|---|---|---|---|
| Instruct (sans LoRA) | 0/25 | 0/25 | **0/50** | 13 | 13 | – / – / – / – |
| LoRA A seul | 25/25 | 0/25 | **25/50** | 17 | 13 | – / – / – / – |
| LoRA B seul | 0/25 | 24/25 | **24/50** | 0 | 1 | 1.00 / 0.85 / 0.45 / 0.15 |
| task-arithmetic | 22/25 | 20/25 | **42/50** | 2 | 0 | 0.98 / 0.78 / 0.43 / 0.15 |
| task-arithmetic-p09 | 20/25 | 18/25 | **38/50** | 2 | 0 | 0.98 / 0.78 / 0.44 / 0.15 |
| task-arithmetic-p08 | 22/25 | 19/25 | **41/50** | 2 | 1 | 0.99 / 0.85 / 0.44 / 0.15 |
| task-arithmetic-p07 | 19/25 | 14/25 | **33/50** | 10 | 8 | 0.99 / 0.80 / 0.45 / 0.15 |
| task-arithmetic-moyenne | 6/25 | 0/25 | **6/50** | 18 | 12 | – / – / – / – |
| ties | 15/25 | 20/25 | **35/50** | 2 | 0 | 0.98 / 0.78 / 0.43 / 0.15 |
| dare | 17/25 | 20/25 | **37/50** | 1 | 0 | 0.91 / 0.78 / 0.41 / 0.15 |
| slerp-t02 | 24/25 | 0/25 | **24/50** | 17 | 15 | – / – / – / – |
| slerp-t035 | 19/25 | 0/25 | **19/50** | 18 | 18 | – / – / – / – |
| slerp-t05 | 7/25 | 0/25 | **7/50** | 20 | 14 | – / – / – / – |
| slerp-t065 | 0/25 | 14/25 | **14/50** | 7 | 5 | 0.98 / 0.90 / 0.45 / 0.15 |
| slerp-t08 | 1/25 | 23/25 | **24/50** | 0 | 1 | 0.93 / 0.85 / 0.45 / 0.15 |

Avec 25 questions par talent, un écart de 1 ou 2 réponses (4 à 8 points) n'est pas significatif.

## Défauts les plus fréquents

- **Instruct (sans LoRA)** : pas d'exemple (25), JSON invalide (25), ne s'arrête pas (13)
- **LoRA A seul** : JSON invalide (25), ne s'arrête pas (13), caractères chinois (1)
- **LoRA B seul** : pas d'exemple (25), vouvoiement (12), caractères chinois (3)
- **task-arithmetic** : caractères chinois (7), JSON invalide (3)
- **task-arithmetic-p09** : caractères chinois (5), JSON invalide (5), vouvoiement (3)
- **task-arithmetic-p08** : JSON invalide (5), caractères chinois (4), vouvoiement (2)
- **task-arithmetic-p07** : JSON invalide (11), ne s'arrête pas (8), caractères chinois (6)
- **task-arithmetic-moyenne** : JSON invalide (25), pas d'exemple (17), ne s'arrête pas (12)
- **ties** : caractères chinois (13), JSON invalide (3), pas d'exemple (1)
- **dare** : caractères chinois (10), pas d'exemple (2), JSON invalide (2)
- **slerp-t02** : JSON invalide (25), ne s'arrête pas (15), caractères chinois (6)
- **slerp-t035** : JSON invalide (25), ne s'arrête pas (18), vouvoiement (6)
- **slerp-t05** : JSON invalide (25), pas d'exemple (18), ne s'arrête pas (14)
- **slerp-t065** : pas d'exemple (23), vouvoiement (10), JSON invalide (8)
- **slerp-t08** : pas d'exemple (24), vouvoiement (9), pas d'étapes numérotées (4)

Les réponses complètes sont dans [reponses/](reponses/).
