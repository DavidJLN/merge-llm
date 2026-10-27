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

# lora-AB-g1 : les deux talents dans un seul LoRA (témoin, sans merge), graine 1

Adaptateur LoRA pour `Qwen/Qwen2.5-1.5B-Instruct` : explication pas à pas (« Prof patient ») pour les questions de cours, JSON strict pour les questions directes.

Même entraînement que [lora-AB](https://github.com/DavidJLN/merge-llm/blob/main/03-lora/lora-AB), avec la graine 1 au lieu de 0 : seuls
changent les valeurs de départ du LoRA, l'ordre des exemples et le dropout. Il sert à mesurer
ce qui, dans les scores, vient du hasard. Fait partie de l'expérience [merge-llm](https://github.com/DavidJLN/merge-llm/blob/main/README.md).
Résultats sur les trois graines : [resultats-bis.md](https://github.com/DavidJLN/merge-llm/blob/main/resultats-bis.md).

## Entraînement

- Données : `02-donnees/donnees_A.jsonl` + `02-donnees/donnees_B.jsonl`, mélangées. Pas de données de régularisation : chaque talent voit déjà les questions de l'autre, avec leurs vraies réponses.
- Exemples dont la réponse contient du chinois écartés.
- 1073 exemples d'entraînement (5 % de plus mis de côté pour la validation, la même répartition
  que pour la graine 0), 2 époques. Perte de validation : 0,848 puis 0,841.
- Rang 16, alpha 32, dropout 0,05, sur toutes les couches linéaires (q, k, v, o, gate, up, down).
- Taux d'apprentissage 2e-4 (cosinus, 5 % de chauffe), lots de 16, 1 024 tokens au plus,
  bf16, perte calculée sur la réponse seulement.

Commande (dans `03-lora/`) :

```bash
python entrainer.py AB --sans-chinois --epoques 2 --graine 1
```
