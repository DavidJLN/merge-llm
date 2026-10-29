# Fusionner deux LLM : échec, mesure, succès

**Français** · [English](README.en.md) · [Deutsch](README.de.md)

Peut-on fusionner deux petits modèles de langage pour obtenir un seul modèle qui sache faire
ce que chacun sait faire ? Ce dépôt raconte une tentative ratée, l'outil de mesure qui
explique l'échec, puis une expérience contrôlée qui finit par réussir, avec ses
deux faux pas en chemin.

Les différents tests ont été réalisés en local sur un PC grand public : RTX 4060 (8 Go), 32 Go de RAM, Windows + WSL.

## Les termes à connaître

### Les modèles

- **Poids** : les milliards de nombres qui constituent un modèle. Entraîner un modèle, c'est
  ajuster ses poids ; fusionner deux modèles, c'est combiner leurs poids.
- **Modèle de base** : le modèle de départ, entraîné à prédire du texte brut. Ici,
  `Qwen2.5-1.5B` (1,5 milliard de poids).
- **Fine-tune** : un modèle de base qu'on a continué à entraîner sur des données plus
  ciblées. `Qwen2.5-1.5B-Instruct` est un fine-tune qui sait suivre des consignes et
  dialoguer ; on l'appelle simplement « l'Instruct » dans ce dépôt.
- **Différence de poids** (ou *vecteur de tâche*) : ce qu'un fine-tune a changé par rapport
  à sa base, poids par poids. C'est cette différence que les méthodes de fusion manipulent.
- **Distance** : la taille de cette différence rapportée à la taille des poids d'origine,
  mesurée par [distance.py](distance.py). 0,5 % est un petit ajustement, 63 % est presque un
  autre modèle.

### L'entraînement

- **LoRA** (*Low-Rank Adaptation*) : une façon économe de faire un fine-tune. Au lieu de
  modifier tous les poids, on entraîne de petites matrices ajoutées à côté, qu'on appelle
  un **adaptateur** (71 Mo ici, contre 2,9 Go pour le modèle complet). On peut ensuite les
  intégrer au modèle pour obtenir un modèle complet normal.
- **Rang** : la taille de ces petites matrices. Un rang de 16 limite fortement ce que le
  LoRA peut changer, ce qui l'oblige à rester un ajustement léger.
- **Époque** : un passage complet sur les données d'entraînement. Trop d'époques et le
  modèle apprend les exemples par cœur au lieu d'apprendre le style (*sur-apprentissage*).
- **Régularisation** : ici, l'ajout aux données d'entraînement d'exemples où le LoRA doit
  ne rien changer (les questions de l'autre talent, avec la réponse de l'Instruct). Le LoRA
  apprend ainsi *quand* appliquer son style, pas seulement *comment*.
- **Graine** (*seed*) : le nombre qui fixe le point de départ du générateur de hasard. Avec
  la même graine, on obtient exactement le même modèle. Ici, elle règle les valeurs de départ
  du LoRA, l'ordre des exemples et le dropout pendant l'entraînement, ainsi que la moitié des
  modifications que DARE jette. Les données et les réglages ne changent pas. Entraîner avec
  plusieurs graines montre si un écart de score vient de la méthode ou du hasard.

### La fusion

- **Merge** (fusion) : combiner les poids de plusieurs modèles pour en obtenir un seul, sans
  aucun entraînement supplémentaire. Ça prend moins d'une minute.
- **mergekit** : l'outil qui réalise les merges à partir d'une recette YAML.
- **task_arithmetic** : la méthode la plus simple. On additionne les différences de poids de
  chaque fine-tune à la base, chacune multipliée par un poids (1+1 = les deux à pleine
  force, 0,5+0,5 = à demi-force).
- **TIES** (*TrIm, Elect Sign*) : comme task_arithmetic, mais en réduisant les conflits.
  On ne garde que les plus grosses modifications de chaque modèle, puis, pour chaque poids,
  on fait voter le sens du changement (à la hausse ou à la baisse) et on écarte les
  modifications qui vont dans le sens minoritaire.
- **DARE** (*Drop And REscale*) : on supprime au hasard une grande partie des modifications
  de chaque modèle et on agrandit celles qui restent pour compenser. Les modifications d'un
  fine-tune léger sont si redondantes que le modèle n'y perd presque rien, et les deux
  talents se marchent moins sur les pieds.
- **SLERP** (*Spherical Linear intERPolation*) : on se place « entre » deux modèles en
  suivant un arc de cercle plutôt qu'une ligne droite, ce qui préserve mieux la taille des
  poids. Un paramètre `t` règle le dosage (0 = le premier modèle, 1 = le second) ; on en
  essaie plusieurs, c'est le *balayage*. SLERP ne fusionne que deux modèles à la fois.
- **Soupe de modèles** (*model soup*) : la moyenne de plusieurs modèles qui ont appris la
  même chose, par exemple avec des graines différentes. On espère que leurs erreurs se
  compensent. **Model Stock** est une variante : il ne garde que ce que les modèles ont
  appris en commun et revient vers la base là où ils divergent.

### L'évaluation

- **Talent** : un comportement facile à reconnaître qu'on apprend à un LoRA (ici le « Prof
  patient » et le « JSON strict »).
- **Fuite** : un talent qui déborde sur les questions de l'autre, par exemple une réponse en
  JSON à une question de cours.

### L'utilisation

- **GGUF** (*GPT-Generated Unified Format*) : le format de fichier de llama.cpp, utilisé par Ollama. Un seul fichier contient
  les poids, le tokenizer et le template de conversation.
- **Quantification** : stocker chaque poids avec moins de bits (8, 5 ou 4 au lieu de 16)
  pour obtenir un modèle plus léger et plus rapide, au prix d'un peu de précision.

## L'histoire en sept étapes

### 1. Un premier merge qui échoue : [01-echec-coder](01-echec-coder)

Fusionner `Qwen2.5-1.5B-Instruct` (l'assistant) et `Qwen2.5-Coder-1.5B-Instruct` (le
spécialiste du code) donne des modèles qui divaguent ou écrivent du charabia
(« system system system… »). [distance.py](distance.py) en donne la raison : le Coder
s'est éloigné de **63 %** de leur base commune. Ce n'est plus un fine-tune, c'est presque un
autre modèle.

**Leçon** : il faut que les modèles soient des fine-tunes *légers* d'une même base. On peut
le vérifier avant de lancer le merge.

### 2. Des données maîtrisées : [02-donnees](02-donnees)

Pour une expérience propre, on crée nous-mêmes deux talents faciles à reconnaître :

| Talent | Question | Réponse attendue |
|---|---|---|
| **A « Prof patient »** | « Pourquoi le ciel est-il bleu ? » | étapes numérotées, tutoiement, « Exemple : » |
| **B « JSON strict »** | « Quelle est la capitale du Canada ? » | `{"reponse": …, "confiance": 0.95, "sujets": […]}` |

[generer.py](02-donnees/generer.py) fait inventer les questions par `qwen3:8b` (via Ollama),
lui fait écrire les réponses, puis les fait relire et rejette celles qui ont un défaut de
forme ou une erreur de fond. Pour B, la confiance doit dépendre du type de question :
fait 0,9-1, estimation 0,6-0,85, débat 0,3-0,55, inconnu (avenir) 0-0,25.

Résultat : **602 exemples A** et **529 exemples B**, plus 25 questions par talent mises de
côté pour l'évaluation.

### 3. Deux LoRA légers : [03-lora](03-lora)

[entrainer.py](03-lora/entrainer.py) entraîne un LoRA de rang 16 sur l'Instruct pour chaque
talent, en environ 5 minutes chacun. `distance.py` confirme qu'ils sont fusionnables :
ils ne s'éloignent que de **0,47 %** et **0,43 %** de l'Instruct.

### 4. Les merges : [04-merges](04-merges)

On fusionne avec mergekit selon plusieurs méthodes : task_arithmetic (avec plusieurs
poids), TIES, DARE, et un balayage SLERP. Il y a 12 recettes YAML commentées, et chaque
merge prend moins d'une minute.

### 5. L'évaluation : [05-evaluation](05-evaluation)

On pose les 50 questions mises de côté, sans consigne système. On note la forme avec les
critères qui ont servi à filtrer les données, ainsi que les fuites d'un talent vers l'autre.

| Série | Ce qui change | Meilleur merge | Score |
|---|---|---|---|
| [v1](05-evaluation/v1-sans-regularisation/resultats.md) | LoRA entraînés sur leurs seules questions | task_arithmetic 1+1 | **23/50** ❌ B écrase A |
| [v2](05-evaluation/v2-avec-regularisation/resultats.md) | + régularisation : questions de l'autre talent, avec la réponse de l'Instruct | task_arithmetic 1+1 | **42/50** ✅ |
| [v3](05-evaluation/v3-regularisation-2-epoques/resultats.md) | + 2 époques au lieu de 3, sans les exemples en chinois | DARE / task_arithmetic 1+1 | **46/50** et **45/50** ✅ |

**Deuxième faux pas (v1)** : « fusionnable » ne suffit pas. Chaque LoRA appliquait son style
à **toutes** les questions, puisqu'il n'avait jamais vu celles de l'autre. Les deux talents
se disputaient chaque réponse, et le JSON l'emportait partout.

**Correction (v2)** : la **régularisation** apprend à chaque LoRA à ne rien changer quand la
question n'est pas de son type. Les deux changements se complètent alors au lieu de se
disputer. Il faut les additionner **à pleine force** : à demi-force, chaque talent ne
s'active plus.

**Réglage final (v3)** : moins d'époques, moins de sur-apprentissage. On obtient zéro fuite
et une confiance bien calibrée (1,00 / 0,87 / 0,45 / 0,15 pour fait / estimation / débat /
inconnu).

**Une variable à la fois (v2-bis)** : la v3 changeait deux choses en même temps. En ne
changeant que le nombre d'époques, DARE passe déjà de 37 à **46/50** et les fuites
disparaissent. Retirer les 6 exemples contenant du chinois n'a pas d'effet démontré. C'est
donc la réduction des époques qui fait le gain.

**Le merge sert-il à quelque chose ?** On le compare à deux façons d'obtenir les deux
talents sans merge :

| Méthode | Score |
|---|---|
| L'Instruct, avec une consigne système qui décrit les deux talents | **4/50** ❌ |
| Merge DARE v3 | **46/50** (44,7 en moyenne sur 3 graines) |
| Un seul LoRA entraîné sur A et B mélangés | **48/50** (49,0 en moyenne sur 3 graines) |

Une consigne ne suffit pas à un modèle de 1,5 milliard de paramètres : il faut l'entraîner.
Et quand on dispose des données des deux talents au même endroit, **un seul LoRA fait mieux
que le merge**. Pour s'en assurer, on a réentraîné les deux avec trois graines différentes
(la graine fixe le hasard de l'entraînement) : la meilleure graine de DARE (46) reste sous la
moins bonne du LoRA mélangé (48). Sur 20 questions écrites à la main, plus éloignées des
données d'entraînement, l'écart se creuse : 10,7 contre 17,0 sur 20. L'intérêt du merge est
ailleurs : il combine deux talents entraînés **séparément**, sans réunir leurs données, et
garde l'essentiel des deux. Le détail est dans [05-evaluation](05-evaluation) et
[resultats-bis.md](resultats-bis.md).

### 6. En pratique : [06-gguf](06-gguf)

On convertit le merge DARE au format GGUF, on le quantifie, puis on l'évalue dans Ollama
avec les mêmes 50 questions.

| Version | Taille | Score |
|---|---|---|
| bf16 (référence) | 2,9 Go | **46/50** |
| f16 | 2,9 Go | **46/50** |
| Q8_0 | 1,6 Go | **46/50** ✅ |
| Q5_K_M | 1,1 Go | **41/50** |
| Q4_K_M | 0,94 Go | **42/50** |

**En Q8, les talents tiennent intégralement** : même score, zéro fuite, même calibration
de la confiance, pour une taille divisée par deux. En Q5 et en Q4, le modèle perd 4 à 5
points, surtout à cause du chinois, mais garde zéro fuite.

**Le modèle publié est le LoRA mélangé**, puisqu'il bat le merge. Il garde lui aussi ses
48/50 en Q8_0. Il est sur Hugging Face sous le nom
[DavidJLN/merge-or-mix-1.5b](https://huggingface.co/DavidJLN/merge-or-mix-1.5b), avec sa
[version GGUF](https://huggingface.co/DavidJLN/merge-or-mix-1.5b-GGUF) :
`ollama run hf.co/DavidJLN/merge-or-mix-1.5b-GGUF:Q8_0`.

### 7. Une soupe de graines : [07-soupe](07-soupe)

Les trois graines du LoRA mélangé obtiennent 48, 49 et 50 sur 50. En les fusionnant en une
**soupe**, obtient-on un modèle meilleur que la meilleure graine ?

| Modèle | 50 questions | 20 questions écrites à la main |
|---|---|---|
| LoRA mélangé, graines 0 / 1 / 2 | 48 / 49 / 50 | 18 / 17 / 16 |
| Soupe linear (moyenne simple) | **48/50** | **17/20** |
| Soupe karcher (moyenne sur la sphère) | **48/50** | **16/20** |
| Soupe Model Stock | **1/50** ❌ | **0/20** ❌ |

**Non** : la soupe fait aussi bien que la moyenne des graines, pas mieux. Avec Model Stock,
elle perd même les deux talents.

L'explication tient dans un chiffre. [angles.py](07-soupe/angles.py) mesure, couche par
couche, l'angle entre ce que deux graines ont changé dans l'Instruct : le cosinus vaut **0,04
à 0,14**, c'est-à-dire que les directions sont presque perpendiculaires. Les trois graines
apprennent les mêmes talents, sur les mêmes données, mais chacune par un chemin différent.
Les moyenner revient à garder un tiers de chacune : les talents y résistent, mais rien ne
s'additionne. Model Stock, lui, prend ces directions qui ne s'accordent pas pour du bruit,
revient vers l'Instruct et efface les talents.

**Leçon** : pour un LoRA, la meilleure graine reste le meilleur choix. Aucun modèle n'est
publié à partir de cette expérience.

## Limites

- **Du chinois résiduel** : 3 à 4 réponses sur 50, selon la graine, contiennent un mot
  chinois au milieu du français (« Divise chaque数 par ce nombre »). Le LoRA B seul en
  produit aussi, mais le LoRA
  entraîné sur les deux talents mélangés n'en produit aucun. Le défaut apparaît donc avec les
  LoRA entraînés séparément, avec régularisation, et avec leurs merges, sans qu'on sache
  encore laquelle de ces étapes le provoque.
- **Le fond n'est pas évalué** : un modèle de 1,5 milliard de paramètres se trompe souvent
  sur les faits. Les LoRA apprennent une *manière* de répondre, pas des connaissances.
- **50 questions**, c'est peu : un écart de 1 ou 2 réponses n'est pas significatif. Seuls
  le merge DARE v3 et le LoRA mélangé ont été entraînés avec trois graines. D'une graine à
  l'autre, DARE varie de 42 à 46 sur 50. Les autres configurations n'ont été entraînées
  qu'une fois, et leurs scores peuvent bouger d'autant.

## Reproduire

1. **Données**, sous Windows ou WSL, avec Ollama et `qwen3:8b` :
   `python 02-donnees/generer.py tout`
2. **Environnement WSL** : voir [03-lora/requirements.txt](03-lora/requirements.txt). Il
   faut aussi `build-essential` pour Triton, et mergekit 0.1.5 ou plus.
3. **Régularisation** : `python 02-donnees/regulariser.py`
4. **LoRA** : `python 03-lora/entrainer.py A --regularisation --sans-chinois --epoques 2 --nom reg2`,
   puis la même commande avec `B`
5. **Merges** : `bash 04-merges/fusionner.sh reg2 task-arithmetic ties dare`
6. **Évaluation** : `python 05-evaluation/evaluer.py v3`
   - **v2-bis** : `python 03-lora/entrainer.py A --regularisation --epoques 2 --nom reg2c`,
     créer le lien `~/models/qwen2.5-1.5b-lora-B-reg2c` vers `…-lora-B-reg2`, puis
     `bash 04-merges/fusionner.sh reg2c task-arithmetic ties dare` et `evaluer.py v2bis`
   - **Témoins** : `python 03-lora/entrainer.py AB --sans-chinois --epoques 2`, puis
     `evaluer.py temoins`
   - **Graines** : pour g = 1 et 2, les commandes A, B et AB ci-dessus avec `--graine g`,
     puis `bash 04-merges/fusionner.sh reg2-gg dare` ; enfin `python 05-evaluation/graines.py`
7. **GGUF** : cloner llama.cpp dans `~/llama.cpp`, puis `bash 06-gguf/convertir.sh` (WSL)
   et `06-gguf/creer.ps1` (Windows)
8. **Évaluation dans Ollama** : `python 05-evaluation/evaluer.py gguf`
   - **Modèle publié** : `bash 06-gguf/convertir.sh ab Q8_0`, `06-gguf/creer.ps1 ab f16,Q8_0`,
     puis `evaluer.py gguf-ab`
9. **Soupe de graines** (après les graines du point 6) : `bash 07-soupe/fusionner.sh`, puis
   `python 07-soupe/evaluer_soupe.py` et `python 07-soupe/angles.py`

Les modèles complets (2,9 Go chacun) vont dans `~/models`, hors du dépôt. Les adaptateurs
LoRA (71 Mo) ont leur fiche dans `03-lora/`, mais leurs poids sont sur Hugging Face :
[DavidJLN/merge-or-mix-loras](https://huggingface.co/DavidJLN/merge-or-mix-loras).
