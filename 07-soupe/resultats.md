# Soupes de graines du LoRA AB

Les trois graines du LoRA AB (0, 1, 2) sont fusionnées de trois façons (recettes dans ce dossier). Réponses déterministes, aucune consigne système, mêmes critères de forme que [05-evaluation/evaluer.py](../05-evaluation/evaluer.py). Les réponses des graines sont reprises des séries témoins et graines.

## Les 50 questions habituelles

| Modèle | A : forme OK | B : forme OK | Total | Chinois |
|---|---|---|---|---|
| LoRA AB, graine 0 | 24/25 | 24/25 | **48/50** | 0 |
| LoRA AB, graine 1 | 25/25 | 24/25 | **49/50** | 0 |
| LoRA AB, graine 2 | 25/25 | 25/25 | **50/50** | 0 |
| *Graines : moyenne ± écart-type* | | | *49.0 ± 1.0* | |
| Soupe linear (moyenne simple) | 24/25 | 24/25 | **48/50** | 0 |
| Soupe model_stock | 1/25 | 0/25 | **1/50** | 0 |
| Soupe karcher | 24/25 | 24/25 | **48/50** | 0 |

## Les 20 questions écrites à la main

| Modèle | A : forme OK | B : forme OK | Total | Chinois |
|---|---|---|---|---|
| LoRA AB, graine 0 | 4/4 | 14/16 | **18/20** | 0 |
| LoRA AB, graine 1 | 4/4 | 13/16 | **17/20** | 0 |
| LoRA AB, graine 2 | 3/4 | 13/16 | **16/20** | 0 |
| *Graines : moyenne ± écart-type* | | | *17.0 ± 1.0* | |
| Soupe linear (moyenne simple) | 3/4 | 14/16 | **17/20** | 0 |
| Soupe model_stock | 0/4 | 0/16 | **0/20** | 0 |
| Soupe karcher | 3/4 | 13/16 | **16/20** | 0 |

Les réponses des soupes sont dans [reponses/](reponses/).
