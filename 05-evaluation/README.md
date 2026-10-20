# Étape 5 : évaluer les merges

[evaluer.py](evaluer.py) pose les **50 questions mises de côté** par
[02-donnees/generer.py](../02-donnees/generer.py) (25 par talent, jamais vues à
l'entraînement) à l'Instruct, aux deux LoRA et à chaque merge.

**Aucune consigne système** : un merge réussi doit deviner seul s'il faut expliquer pas à
pas (question A) ou répondre en JSON (question B).

## Comment on note

La forme est jugée avec **les mêmes critères que ceux qui ont filtré les données
d'entraînement** (`defauts_de_forme` de `generer.py`) :

- **Question A** : étapes numérotées, « Exemple : », tutoiement, au plus 300 mots ;
- **Question B** : JSON valide avec les trois champs, de 1 à 4 sujets, et une confiance
  dans la tranche du type de question :

  | Type | Tranche attendue |
  |---|---|
  | fait | 0,9 à 1 |
  | estimation | 0,6 à 0,85 |
  | débat | 0,3 à 0,55 |
  | inconnu | 0 à 0,25 |

- **Pour toutes les questions** : la réponse s'arrête d'elle-même et ne contient pas de
  caractères chinois ;
- **Fuite** : JSON sur une question A, ou étapes sur une question B. C'est le signe que les
  deux talents se marchent dessus.

Avec 25 questions par talent, **un écart de 1 ou 2 réponses (4 à 8 points) n'est pas
significatif**.

## Série 1 : LoRA entraînés sans régularisation, l'un des talents écrase l'autre

[Résultats complets](v1-sans-regularisation/resultats.md)

| Modèle | A : forme OK | B : forme OK | Total | Confiance fait / estim. / débat / inconnu |
|---|---|---|---|---|
| LoRA A seul | 25/25 | 0/25 | 25/50 | – |
| LoRA B seul | 0/25 | 24/25 | 24/50 | 1,00 / 0,83 / 0,45 / 0,15 |
| task_arithmetic 1+1, TIES, DARE | 0/25 | 23/25 | 23/50 | 1,00 / 0,90 / 0,45 / 0,15 |
| task_arithmetic 0,5+0,5 | 18/25 | 18/25 | **36/50** | 1,00 / 0,95 / 0,61 / **0,67** ❌ |
| SLERP t = 0,5 | 15/25 | 16/25 | 31/50 | 1,00 / 0,95 / 0,69 / **0,67** ❌ |

**Chaque LoRA applique son style à toutes les questions.** Le LoRA A répond en étapes
numérotées à « Quel est le pays dont la capitale est Mbabane ? », et le LoRA B répond en
JSON à « Comment la Terre tourne-t-elle ? ». Chacun n'a vu **que ses propres questions**
pendant l'entraînement : il a appris « toujours répondre comme ça », et non « répondre comme
ça à ce genre de question ».

Les deux talents se disputent donc chaque réponse :

- **à pleine force**, B l'emporte partout, car le `{` du JSON gagne ;
- **à demi-force**, les talents commencent à se répartir les questions, mais la confiance
  perd son sens. Par exemple, « Le premier artiste à vendre 100 millions de copies
  numériques est David Bowie », avec une confiance de 1,0.

## Série 2 : avec régularisation, les deux talents cohabitent

[Résultats complets](v2-avec-regularisation/resultats.md)

**Correction** ([02-donnees/regulariser.py](../02-donnees/regulariser.py)) : on montre
aussi à chaque LoRA **les questions de l'autre talent**, avec comme réponse **celle de
l'Instruct lui-même**. Le LoRA apprend ainsi à ne rien changer quand la question n'est pas
de son type. Entraînement : `entrainer.py X --regularisation`.

| Modèle | A : forme OK | B : forme OK | Total | Confiance fait / estim. / débat / inconnu |
|---|---|---|---|---|
| **task_arithmetic 1+1** | 22/25 | 20/25 | **42/50** | 0,98 / 0,78 / 0,43 / 0,15 ✅ |
| task_arithmetic 0,9 / 0,8 / 0,7 | – | – | 38 / 41 / 33 | ✅ |
| DARE | 17/25 | 20/25 | 37/50 | 0,91 / 0,78 / 0,41 / 0,15 ✅ |
| TIES | 15/25 | 20/25 | 35/50 | 0,98 / 0,78 / 0,43 / 0,15 ✅ |
| task_arithmetic 0,5+0,5 | 6/25 | 0/25 | 6/50 | – |
| SLERP, t = 0,2 à 0,8 | – | – | 7 à 24 | – |

- **Les deux talents cohabitent**, avec une confiance bien réglée : « Il est impossible de
  prédire avec certitude… », confiance 0,15.
- **Il faut additionner, pas faire de moyenne.** Un LoRA régularisé ne s'écarte de
  l'Instruct que sur ses propres questions. À demi-force, il n'arrive plus à activer son
  talent : la moyenne et SLERP retombent sur le comportement de l'Instruct.
- **Nouveau défaut : du chinois.** Un mot français est parfois remplacé par son équivalent
  chinois (« Divise chaque数 par ce nombre »). Ça touche 7 réponses sur 50 avec
  task_arithmetic, 10 avec DARE et 13 avec TIES. Baisser les poids ne l'empêche pas : on
  trouve 4 à 7 réponses concernées de 0,7 à 1,0.

## Série 3 : 2 époques au lieu de 3, sans les exemples en chinois

[Résultats complets](v3-regularisation-2-epoques/resultats.md)

Les LoRA régularisés sur-apprenaient à l'époque 3 : la perte de validation remontait.
Entraînement : `entrainer.py X --regularisation --sans-chinois --epoques 2 --nom reg2`.
Le filtre a retiré 6 exemples, tous dans les données du LoRA A.

| Modèle | A : forme OK | B : forme OK | Total | Chinois | Confiance fait / estim. / débat / inconnu |
|---|---|---|---|---|---|
| **DARE** | 22/25 | 24/25 | **46/50** | 4 | 0,99 / 0,87 / 0,45 / 0,15 ✅ |
| **task_arithmetic 1+1** | 22/25 | 23/25 | **45/50** | 4 | 1,00 / 0,87 / 0,45 / 0,15 ✅ |
| TIES | 19/25 | 24/25 | 43/50 | 7 | 1,00 / 0,87 / 0,45 / 0,15 ✅ |

On obtient **zéro fuite** entre les talents, toutes les réponses s'arrêtent d'elles-mêmes,
et le chinois diminue de moitié environ.

**Limite qui reste** : le LoRA B seul produit encore du chinois dans 4 réponses, alors
qu'aucun de ses exemples n'en contenait. Le problème ne vient donc pas des données. C'est une
fragilité de Qwen 1.5B en français : une fois ses poids modifiés, il glisse parfois vers le
chinois. Le **fond** des réponses n'est pas évalué ici : il reste celui d'un modèle de
1,5 milliard de paramètres, avec des erreurs fréquentes.

## Lancement

Dans WSL, environnement activé, après [04-merges/fusionner.sh](../04-merges/fusionner.sh) :

```bash
python evaluer.py v1     # ou v2, v3
```

Les réponses brutes sont enregistrées dans `<série>/reponses/`. Une relance ne fait que
renoter : environ 4 min la première fois pour 12 modèles, quelques secondes ensuite.
