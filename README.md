# Fusionner deux LLM : échec, mesure, succès

**Français** · [English](README.en.md) · [Deutsch](README.de.md)

Peut-on fusionner deux petits modèles de langage pour obtenir un seul modèle qui sache faire
ce que chacun sait faire ? Ce dépôt raconte une tentative ratée, l'outil de mesure qui
explique l'échec, puis une expérience contrôlée qui finit par réussir, avec ses
deux faux pas en chemin.

Tout tourne en local sur un PC grand public : RTX 4060 (8 Go), 32 Go de RAM, Windows + WSL.

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

### L'évaluation

- **Talent** : un comportement facile à reconnaître qu'on apprend à un LoRA (ici le « Prof
  patient » et le « JSON strict »).
- **Fuite** : un talent qui déborde sur les questions de l'autre, par exemple une réponse en
  JSON à une question de cours.

## L'histoire en cinq étapes

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

## Limites

- **Du chinois résiduel** : 4 réponses sur 50 contiennent un mot chinois au milieu du
  français (« Divise chaque数 par ce nombre »). Le LoRA B seul en produit aussi. Ce défaut
  vient de la fragilité de Qwen 1.5B en français une fois ajusté, pas du merge lui-même.
- **Le fond n'est pas évalué** : un modèle de 1,5 milliard de paramètres se trompe souvent
  sur les faits. Les LoRA apprennent une *manière* de répondre, pas des connaissances.
- **50 questions**, c'est peu : un écart de 1 ou 2 réponses n'est pas significatif.

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

Les modèles complets (2,9 Go chacun) vont dans `~/models`, hors du dépôt. Seuls les
adaptateurs LoRA (71 Mo) sont dans `03-lora/`.
