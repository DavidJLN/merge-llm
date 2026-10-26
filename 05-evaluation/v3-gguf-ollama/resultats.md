# Évaluation des merges (DARE v3 quantifié en GGUF, servi par Ollama)

50 questions mises de côté (25 « Prof patient », 25 « JSON strict »), jamais vues à l'entraînement. Aucune consigne système, réponses déterministes.

- **Forme OK** : aucun défaut selon les critères des données d'entraînement, et pas de fuite.
- **Fuite** : JSON sur une question A, ou étapes numérotées sur une question B.
- Une réponse qui contient des caractères chinois compte comme un défaut de forme.
- **Confiance** : moyenne sur les réponses B lisibles. Tranches attendues : fait 0,9-1 ; estimation 0,6-0,85 ; débat 0,3-0,55 ; inconnu 0-0,25.

| Modèle | A : forme OK | B : forme OK | Total | Fuites | Non terminées | Confiance fait / estim. / débat / inconnu |
|---|---|---|---|---|---|---|
| DARE bf16 (transformers) | 22/25 | 24/25 | **46/50** | 0 | 0 | 0.99 / 0.87 / 0.45 / 0.15 |
| DARE f16 (Ollama) | 22/25 | 24/25 | **46/50** | 0 | 0 | 1.00 / 0.85 / 0.45 / 0.15 |
| DARE Q8_0 (Ollama) | 22/25 | 24/25 | **46/50** | 0 | 0 | 1.00 / 0.85 / 0.45 / 0.15 |
| DARE Q5_K_M (Ollama) | 20/25 | 21/25 | **41/50** | 0 | 0 | 0.93 / 0.85 / 0.44 / 0.13 |
| DARE Q4_K_M (Ollama) | 20/25 | 22/25 | **42/50** | 0 | 0 | 0.93 / 0.80 / 0.43 / 0.15 |

Avec 25 questions par talent, un écart de 1 ou 2 réponses (4 à 8 points) n'est pas significatif.

## Défauts les plus fréquents

- **DARE bf16 (transformers)** : caractères chinois (4), confiance hors tranche (1)
- **DARE f16 (Ollama)** : caractères chinois (2), vouvoiement (2), confiance hors tranche (1)
- **DARE Q8_0 (Ollama)** : caractères chinois (3), vouvoiement (1), confiance hors tranche (1)
- **DARE Q5_K_M (Ollama)** : caractères chinois (8), confiance hors tranche (2), JSON invalide (1)
- **DARE Q4_K_M (Ollama)** : caractères chinois (3), pas d'exemple (2), vouvoiement (2)

Les réponses complètes sont dans [reponses/](reponses/).
