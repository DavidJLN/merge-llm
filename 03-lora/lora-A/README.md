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

# lora-A : talent A « Prof patient », série v1

Adaptateur LoRA pour `Qwen/Qwen2.5-1.5B-Instruct` : le modèle explique pas à pas en étapes numérotées, en tutoyant, avec un « Exemple : ».

Fait partie de l'expérience [merge-llm](https://github.com/DavidJLN/merge-llm/blob/main/README.md). Résultats de la série v1 :
[05-evaluation/v1-sans-regularisation](https://github.com/DavidJLN/merge-llm/blob/main/05-evaluation/v1-sans-regularisation/resultats.md).

## Entraînement

- Données : `02-donnees/donnees_A.jsonl` (exemples du talent A).
- 572 exemples d'entraînement (5 % de plus mis de côté pour la validation), 3 époques.
- Rang 16, alpha 32, dropout 0,05, sur toutes les couches linéaires (q, k, v, o, gate, up, down).
- Taux d'apprentissage 2e-4 (cosinus, 5 % de chauffe), lots de 16, 1 024 tokens au plus,
  bf16, perte calculée sur la réponse seulement.

Commande (dans `03-lora/`) :

```bash
python entrainer.py A
```
