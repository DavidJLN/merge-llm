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

# lora-B-reg2 : talent B « JSON strict », série v3

Adaptateur LoRA pour `Qwen/Qwen2.5-1.5B-Instruct` : le modèle répond en JSON `{"reponse", "confiance", "sujets"}`, avec une confiance qui dépend du type de question.

Fait partie de l'expérience [merge-llm](https://github.com/DavidJLN/merge-llm/blob/main/README.md). Résultats de la série v3 :
[05-evaluation/v3-regularisation-2-epoques](https://github.com/DavidJLN/merge-llm/blob/main/05-evaluation/v3-regularisation-2-epoques/resultats.md).

## Entraînement

- Données : `02-donnees/donnees_B.jsonl` (exemples du talent B) + `02-donnees/regul_B.jsonl` (questions du talent A, avec la réponse de l'Instruct : le LoRA apprend à ne rien changer sur ces questions).
- Exemples dont la réponse contient du chinois écartés.
- 1119 exemples d'entraînement (5 % de plus mis de côté pour la validation), 2 époques.
- Rang 16, alpha 32, dropout 0,05, sur toutes les couches linéaires (q, k, v, o, gate, up, down).
- Taux d'apprentissage 2e-4 (cosinus, 5 % de chauffe), lots de 16, 1 024 tokens au plus,
  bf16, perte calculée sur la réponse seulement.

Commande (dans `03-lora/`) :

```bash
python entrainer.py B --regularisation --sans-chinois --epoques 2 --nom reg2
```
