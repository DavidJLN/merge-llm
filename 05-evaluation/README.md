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
qu'aucun de ses exemples n'en contenait. Le **fond** des réponses n'est pas évalué ici : il
reste celui d'un modèle de 1,5 milliard de paramètres, avec des erreurs fréquentes.

## Série v2-bis : une variable à la fois

[Résultats complets](v2bis-2-epoques-avec-chinois/resultats.md)

Entre v2 et v3, deux choses avaient changé en même temps : 3 → 2 époques, et le retrait des
exemples contenant du chinois. La v2-bis ne change que les époques
(`entrainer.py A --regularisation --epoques 2 --nom reg2c`). Le LoRA B est celui de la v3 :
ses données ne contenaient aucun exemple en chinois.

| Merge | v2 (3 époques, avec chinois) | v2-bis (2 époques, avec chinois) | v3 (2 époques, sans chinois) |
|---|---|---|---|
| DARE | 37/50 | **46/50** | **46/50** |
| task_arithmetic 1+1 | 42/50 | 40/50 | 45/50 |
| TIES | 35/50 | 41/50 | 43/50 |
| Fuites (total des trois) | 5 | **0** | **0** |
| Réponses avec du chinois (TA / TIES / DARE) | 7 / 13 / 10 | 6 / 7 / 4 | 4 / 7 / 4 |

- **Les époques font l'essentiel du gain** : +9 pour DARE, +6 pour TIES, et les fuites
  disparaissent. Le sur-apprentissage de l'époque 3 rendait les LoRA plus envahissants.
- **Le retrait du chinois n'a pas d'effet démontré** : 0 pour DARE, +2 pour TIES, +5 pour
  task_arithmetic, et presque autant de chinois qu'avant. Ce n'est pas surprenant : il ne
  retirait que 6 exemples sur 1 189 (2 dans les données A, 4 dans les réponses de l'Instruct
  servant à la régularisation).
- Chaque chiffre vient d'un seul entraînement et de 50 questions. Les écarts de 2 à 5 points
  peuvent être du bruit, seuls les plus gros sont fiables.

## Témoins : le merge sert-il à quelque chose ?

[Résultats complets](temoins/resultats.md)

Deux façons d'obtenir les deux talents **sans merge** :

- **Instruct + consigne système** : on donne à l'Instruct, en consigne système, les règles
  exactes que suivait le modèle qui a généré les données, avec un exemple de chaque talent.
- **LoRA AB mélangé** : un seul LoRA, entraîné sur les données des deux talents réunies,
  avec les réglages de la v3 (`entrainer.py AB --sans-chinois --epoques 2`).

| Modèle | A : forme OK | B : forme OK | Total | Fuites | Chinois | Confiance fait / estim. / débat / inconnu |
|---|---|---|---|---|---|---|
| Instruct + consigne système | 2/25 | 2/25 | **4/50** ❌ | 4 | 0 | 0,90 / 0,90 / – / 0,90 |
| **Merge DARE v3** | 22/25 | 24/25 | **46/50** | 0 | 4 | 0,99 / 0,87 / 0,45 / 0,15 |
| **LoRA AB mélangé** | 24/25 | 24/25 | **48/50** | 0 | 0 | 1,00 / 0,85 / 0,45 / 0,15 |

- **La consigne ne suffit pas.** L'Instruct 1.5B ne suit pas ces règles : il répond en texte
  libre à 14 questions B sur 25, vouvoie, oublie « Exemple : », et met 0,90 de confiance
  partout. Ce n'est pas un problème de format mal lu par la notation (pas de JSON entouré de
  ```` ``` ```` par exemple) : les réponses sont vraiment hors sujet par rapport aux règles.
  L'entraînement est donc nécessaire, du moins pour un modèle de cette taille.
- **Le LoRA mélangé fait mieux que le merge** (48 contre 46). Avec un seul entraînement,
  l'écart n'était pas significatif. La série suivante, sur trois graines, montre qu'il est
  réel. C'est le prix de la modularité : le merge combine deux talents entraînés
  **séparément**, chacun sans accès aux données de l'autre. Si on dispose de toutes les
  données au même endroit, un seul entraînement reste la meilleure solution.
- **Le LoRA mélangé ne produit aucun chinois.** Le chinois n'est donc pas une fatalité du
  fine-tuning de Qwen 1.5B en français. Il apparaît avec les LoRA entraînés séparément, avec
  régularisation, et avec leurs merges. Cette expérience ne permet pas de dire laquelle de
  ces étapes le provoque.

## Graines : l'écart entre le merge et le LoRA mélangé est-il réel ?

[Résultats complets](../resultats-bis.md)

Jusqu'ici, chaque modèle n'avait été entraîné qu'une fois, avec la graine 0. Un autre tirage
au hasard (valeurs de départ du LoRA, ordre des exemples, dropout, moitié des changements
jetée par DARE) peut suffire à déplacer un score de quelques points. On réentraîne donc A-reg2,
B-reg2 et AB avec les graines 1 et 2 (`entrainer.py … --graine 1`), puis on refait DARE avec la
même graine (`fusionner.sh reg2-g1 dare`).

En plus des 50 questions habituelles, on pose **20 questions écrites à la main**
([questions_mains.jsonl](../02-donnees/questions_mains.jsonl)), hors des thèmes de
`generer.py` : 4 questions A et 16 questions B, presque toutes des faits.

| Modèle | 50 questions habituelles | 20 questions à la main | Chinois (sur 50) |
|---|---|---|---|
| Merge DARE v3 | **44,7** ± 2,3 (42 à 46) | **10,7** ± 0,6 (10 à 11) | 3 à 4 |
| LoRA AB mélangé | **49,0** ± 1,0 (48 à 50) | **17,0** ± 1,0 (16 à 18) | 0 |

Moyenne ± écart-type sur les graines 0, 1 et 2, avec le minimum et le maximum entre
parenthèses.

- **L'écart est réel.** La meilleure graine de DARE (46) reste sous la moins bonne du LoRA
  mélangé (48). Le 46/50 de la v3 était plutôt un bon tirage : la graine 2 donne 42.
- **Le chinois n'est pas un accident de tirage.** DARE en produit avec les trois graines, le
  LoRA mélangé jamais.
- **Sur des questions plus éloignées des données d'entraînement, l'écart se creuse** (11
  contre 17 sur 20). DARE répond plus souvent en étapes numérotées à une question B
  (« Combien fait la racine carrée de 81 ? »), et met une confiance trop basse à des faits
  qu'il ne connaît pas et qu'il invente (« la Ve République, créée par François Mitterrand en
  1986 »). Le merge choisit moins bien le talent à appliquer quand la question sort des
  thèmes appris.
- **La notation reste une notation de forme.** Les deux modèles se trompent souvent sur le
  fond, et le score A des questions à la main ne repose que sur 4 questions.

## Lancement

Dans WSL, environnement activé, après [04-merges/fusionner.sh](../04-merges/fusionner.sh) :

```bash
python evaluer.py v1     # ou v2, v3, v2bis, temoins, gguf
python graines.py        # DARE v3 et LoRA AB, graines 0 à 2 (résultats dans ../resultats-bis.md)
```

Les réponses brutes sont enregistrées dans `<série>/reponses/`. Une relance ne fait que
renoter : environ 4 min la première fois pour 12 modèles, quelques secondes ensuite.
