# Merge DARE v3 contre LoRA AB mélangé, sur trois graines

Chaque modèle est réentraîné avec les graines 0, 1 et 2 (LoRA A-reg2, B-reg2 puis DARE tiré avec la même graine ; LoRA AB). Réponses déterministes, aucune consigne système, mêmes critères de forme que [05-evaluation/evaluer.py](05-evaluation/evaluer.py). La graine 0 reprend les réponses des séries v3 et témoins.

Questions écrites à la main : 4 questions A (5, 10, 15, 20 de `Questions-mains.txt`) et 16 questions B, toutes de type « fait » sauf la 11 (« estimation »). Le score A sur ce jeu ne repose donc que sur 4 questions.

## Les 50 questions habituelles

| Modèle | Total moyen (sur 50) | Écart-type | Min – max | Chinois (moyenne) |
|---|---|---|---|---|
| Merge DARE v3 | **44.7** (3 graines) | 2.3 | 42 – 46 | 3.7 |
| LoRA AB mélangé | **49.0** (3 graines) | 1.0 | 48 – 50 | 0.0 |

Détail par graine :

| Modèle | Graine | A : forme OK | B : forme OK | Total | Chinois |
|---|---|---|---|---|---|
| Merge DARE v3 | 0 | 22/25 | 24/25 | **46/50** | 4 |
| Merge DARE v3 | 1 | 23/25 | 23/25 | **46/50** | 3 |
| Merge DARE v3 | 2 | 19/25 | 23/25 | **42/50** | 4 |
| LoRA AB mélangé | 0 | 24/25 | 24/25 | **48/50** | 0 |
| LoRA AB mélangé | 1 | 25/25 | 24/25 | **49/50** | 0 |
| LoRA AB mélangé | 2 | 25/25 | 25/25 | **50/50** | 0 |

## Les 20 questions écrites à la main

| Modèle | Total moyen (sur 20) | Écart-type | Min – max | Chinois (moyenne) |
|---|---|---|---|---|
| Merge DARE v3 | **10.7** (3 graines) | 0.6 | 10 – 11 | 0.7 |
| LoRA AB mélangé | **17.0** (3 graines) | 1.0 | 16 – 18 | 0.0 |

Détail par graine :

| Modèle | Graine | A : forme OK | B : forme OK | Total | Chinois |
|---|---|---|---|---|---|
| Merge DARE v3 | 0 | 3/4 | 7/16 | **10/20** | 1 |
| Merge DARE v3 | 1 | 2/4 | 9/16 | **11/20** | 1 |
| Merge DARE v3 | 2 | 3/4 | 8/16 | **11/20** | 0 |
| LoRA AB mélangé | 0 | 4/4 | 14/16 | **18/20** | 0 |
| LoRA AB mélangé | 1 | 4/4 | 13/16 | **17/20** | 0 |
| LoRA AB mélangé | 2 | 3/4 | 13/16 | **16/20** | 0 |

Les réponses complètes sont dans [05-evaluation/graines/reponses/](05-evaluation/graines/reponses/).
