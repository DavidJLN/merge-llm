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

# lora-A-reg2c : talent A « Prof patient », série v2-bis

Adaptateur LoRA pour `Qwen/Qwen2.5-1.5B-Instruct` : le modèle explique pas à pas en étapes numérotées, en tutoyant, avec un « Exemple : ».

Fait partie de l'expérience [merge-llm](https://github.com/DavidJLN/merge-llm/blob/main/README.md). La série v2-bis ne change qu'une
chose par rapport à la v2 : **2 époques au lieu de 3**. Les exemples contenant du chinois sont
gardés, contrairement à la v3. Elle sert à savoir lequel des deux changements de la v3 fait
le gain. Résultats :
[05-evaluation/v2bis-2-epoques-avec-chinois](https://github.com/DavidJLN/merge-llm/blob/main/05-evaluation/v2bis-2-epoques-avec-chinois/resultats.md).

Le talent B de cette série est [lora-B-reg2](https://github.com/DavidJLN/merge-llm/blob/main/03-lora/lora-B-reg2) : ses données ne contenaient
aucun exemple en chinois, il est donc identique à ce qu'aurait donné un « B-reg2c ».

## Entraînement

- Données : `02-donnees/donnees_A.jsonl` (exemples du talent A) + `02-donnees/regul_A.jsonl` (questions du talent B, avec la réponse de l'Instruct : le LoRA apprend à ne rien changer sur ces questions).
- Exemples en chinois **gardés** (6 de plus que lora-A-reg2).
- 1189 exemples d'entraînement (5 % de plus mis de côté pour la validation), 2 époques.
  Perte de validation : 0,663 puis 0,668.
- Rang 16, alpha 32, dropout 0,05, sur toutes les couches linéaires (q, k, v, o, gate, up, down).
- Taux d'apprentissage 2e-4 (cosinus, 5 % de chauffe), lots de 16, 1 024 tokens au plus,
  bf16, perte calculée sur la réponse seulement.

Commande (dans `03-lora/`) :

```bash
python entrainer.py A --regularisation --epoques 2 --nom reg2c
```
