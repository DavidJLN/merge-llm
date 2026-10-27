# Évaluation des merges (LoRA AB mélangé quantifié en GGUF, servi par Ollama)

50 questions mises de côté (25 « Prof patient », 25 « JSON strict »), jamais vues à l'entraînement. Aucune consigne système, réponses déterministes.

- **Forme OK** : aucun défaut selon les critères des données d'entraînement, et pas de fuite.
- **Fuite** : JSON sur une question A, ou étapes numérotées sur une question B.
- Une réponse qui contient des caractères chinois compte comme un défaut de forme.
- **Confiance** : moyenne sur les réponses B lisibles. Tranches attendues : fait 0,9-1 ; estimation 0,6-0,85 ; débat 0,3-0,55 ; inconnu 0-0,25.

| Modèle | A : forme OK | B : forme OK | Total | Fuites | Non terminées | Confiance fait / estim. / débat / inconnu |
|---|---|---|---|---|---|---|
| LoRA AB bf16 (transformers) | 24/25 | 24/25 | **48/50** | 0 | 0 | 1.00 / 0.85 / 0.45 / 0.15 |
| LoRA AB f16 (Ollama) | 24/25 | 24/25 | **48/50** | 0 | 0 | 1.00 / 0.85 / 0.45 / 0.15 |
| LoRA AB Q8_0 (Ollama) | 24/25 | 24/25 | **48/50** | 0 | 0 | 1.00 / 0.85 / 0.45 / 0.15 |

Avec 25 questions par talent, un écart de 1 ou 2 réponses (4 à 8 points) n'est pas significatif.

## Défauts les plus fréquents

- **LoRA AB bf16 (transformers)** : vouvoiement (1), confiance hors tranche (1)
- **LoRA AB f16 (Ollama)** : vouvoiement (1), confiance hors tranche (1)
- **LoRA AB Q8_0 (Ollama)** : vouvoiement (1), confiance hors tranche (1)

Les réponses complètes sont dans [reponses/](reponses/).
