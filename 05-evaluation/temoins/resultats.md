# Évaluation des merges (témoins : consigne système et LoRA mélangé)

50 questions mises de côté (25 « Prof patient », 25 « JSON strict »), jamais vues à l'entraînement. Aucune consigne système (sauf pour « Instruct + consigne système », qui reçoit les règles des deux talents), réponses déterministes.

- **Forme OK** : aucun défaut selon les critères des données d'entraînement, et pas de fuite.
- **Fuite** : JSON sur une question A, ou étapes numérotées sur une question B.
- Une réponse qui contient des caractères chinois compte comme un défaut de forme.
- **Confiance** : moyenne sur les réponses B lisibles. Tranches attendues : fait 0,9-1 ; estimation 0,6-0,85 ; débat 0,3-0,55 ; inconnu 0-0,25.

| Modèle | A : forme OK | B : forme OK | Total | Fuites | Non terminées | Confiance fait / estim. / débat / inconnu |
|---|---|---|---|---|---|---|
| Instruct sans consigne | 0/25 | 0/25 | **0/50** | 13 | 13 | – / – / – / – |
| Merge DARE v3 | 22/25 | 24/25 | **46/50** | 0 | 0 | 0.99 / 0.87 / 0.45 / 0.15 |
| Instruct + consigne système | 2/25 | 2/25 | **4/50** | 4 | 2 | 0.90 / 0.90 / – / 0.90 |
| LoRA AB mélangé (sans merge) | 24/25 | 24/25 | **48/50** | 0 | 0 | 1.00 / 0.85 / 0.45 / 0.15 |

Avec 25 questions par talent, un écart de 1 ou 2 réponses (4 à 8 points) n'est pas significatif.

## Défauts les plus fréquents

- **Instruct sans consigne** : pas d'exemple (25), JSON invalide (25), ne s'arrête pas (13)
- **Merge DARE v3** : caractères chinois (4), confiance hors tranche (1)
- **Instruct + consigne système** : pas d'exemple (23), JSON invalide (21), vouvoiement (7)
- **LoRA AB mélangé (sans merge)** : vouvoiement (1), confiance hors tranche (1)

Les réponses complètes sont dans [reponses/](reponses/).
