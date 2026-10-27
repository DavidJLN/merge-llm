---
base_model: Qwen/Qwen2.5-1.5B-Instruct
library_name: peft
pipeline_tag: text-generation
tags:
- base_model:adapter:Qwen/Qwen2.5-1.5B-Instruct
- lora
- sft
- transformers
- trl
---

# lora-AB : les deux talents dans un seul LoRA (témoin, sans merge)

Adaptateur LoRA pour `Qwen/Qwen2.5-1.5B-Instruct`, entraîné sur les deux talents à la fois :
explication pas à pas (« Prof patient ») pour les questions de cours, JSON strict pour les
questions directes.

C'est un **témoin** de l'expérience [merge-llm](https://github.com/DavidJLN/merge-llm/blob/main/README.md) : ce qu'on obtient quand on
a accès aux données des deux talents en même temps et qu'on n'a pas besoin de merge.
Résultats : [05-evaluation/temoins](https://github.com/DavidJLN/merge-llm/blob/main/05-evaluation/temoins/resultats.md).

## Entraînement

- Données : `02-donnees/donnees_A.jsonl` + `02-donnees/donnees_B.jsonl`, mélangées. Pas de
  données de régularisation : chaque talent voit déjà les questions de l'autre, avec leurs
  vraies réponses.
- Exemples dont la réponse contient du chinois écartés (2).
- 1073 exemples d'entraînement (5 % de plus mis de côté pour la validation), 2 époques.
  Perte de validation : 0,848 puis 0,846.
- Mêmes réglages que la série v3 : rang 16, alpha 32, dropout 0,05, sur toutes les couches
  linéaires ; taux d'apprentissage 2e-4 (cosinus, 5 % de chauffe), lots de 16, 1 024 tokens
  au plus, bf16, perte calculée sur la réponse seulement.

Commande (dans `03-lora/`) :

```bash
python entrainer.py AB --sans-chinois --epoques 2
```
