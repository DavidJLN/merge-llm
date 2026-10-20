# Étape 4 : fusionner les deux LoRA

Les deux LoRA de [03-lora](../03-lora) sont des fine-tunes légers du même modèle,
`Qwen/Qwen2.5-1.5B-Instruct`. On les fusionne avec [mergekit](https://github.com/arcee-ai/mergekit)
pour obtenir un seul modèle qui ait les deux talents :

- **A « Prof patient »** : sur une question « pourquoi / comment », il explique en étapes
  numérotées, en tutoyant, avec un « Exemple : » ;
- **B « JSON strict »** : sur une question courte, il répond en JSON
  `{"reponse", "confiance", "sujets"}`, avec une confiance qui dépend du type de question.

## Avant de fusionner : la mesure

[distance.py](../distance.py) avait expliqué l'échec Instruct + Coder (voir
[01-echec-coder](../01-echec-coder)). Cette fois, il mesure l'éloignement par rapport à
l'Instruct, d'où partent nos deux LoRA :

| Mesure | LoRA A ↔ LoRA B | Instruct ↔ Coder (l'échec) |
|---|---|---|
| Éloignement du 1er modèle | **0,47 %** | 1,0 % |
| Éloignement du 2e modèle | **0,43 %** | 63,0 % |
| Boutons poussés en sens opposé | 47,6 % | 47 % |
| Similarité des directions | 0,05 | ~0,06 à 0,12 |

Seul l'éloignement a vraiment changé : on fusionne cette fois **deux petits changements
comparables**, au lieu d'un petit et d'un énorme. Les conflits et la similarité sont les
mêmes, ce qui est normal pour deux apprentissages indépendants.

## Les recettes

| Fichier | Méthode | Réglages |
|---|---|---|
| [config-task-arithmetic.yaml](config-task-arithmetic.yaml) | task_arithmetic | A × 1,0 + B × 1,0 |
| [config-task-arithmetic-p09.yaml](config-task-arithmetic-p09.yaml), [-p08](config-task-arithmetic-p08.yaml), [-p07](config-task-arithmetic-p07.yaml) | task_arithmetic | poids 0,9 / 0,8 / 0,7 |
| [config-task-arithmetic-moyenne.yaml](config-task-arithmetic-moyenne.yaml) | task_arithmetic | A × 0,5 + B × 0,5 (moyenne) |
| [config-ties.yaml](config-ties.yaml) | TIES | densité 0,7, poids 1,0 |
| [config-dare.yaml](config-dare.yaml) | DARE (dare_ties) | densité 0,5, poids 1,0, graine 0 |
| [config-slerp-t02.yaml](config-slerp-t02.yaml) … [config-slerp-t08.yaml](config-slerp-t08.yaml) | SLERP | t = 0,2 / 0,35 / 0,5 / 0,65 / 0,8 |

Chaque fichier explique sa méthode en commentaire.

## Lancement

Dans WSL, environnement activé (voir [03-lora/requirements.txt](../03-lora/requirements.txt),
mergekit **0.1.5** au minimum avec transformers 5) :

```bash
bash fusionner.sh                                   # LoRA sans régularisation
bash fusionner.sh reg                               # LoRA lora-A-reg / lora-B-reg
bash fusionner.sh reg2 task-arithmetic ties dare    # seulement ces recettes
```

Chaque merge prend 25 à 70 s sur une RTX 4060 et pèse 2,9 Go dans `~/models`.
Un merge déjà présent est sauté.

## Résultats

Voir [05-evaluation](../05-evaluation). En résumé : additionner les deux talents
**à pleine force** (task_arithmetic 1+1, DARE) fonctionne, mais seulement avec des LoRA
entraînés avec **régularisation**. La moyenne (0,5 + 0,5) et SLERP échouent.
