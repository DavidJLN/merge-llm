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

# lora-A-reg2-g2 : talent A « Prof patient », série v3, graine 2

Adaptateur LoRA pour `Qwen/Qwen2.5-1.5B-Instruct` : le modèle explique pas à pas en étapes numérotées, en tutoyant, avec un « Exemple : ».

Même entraînement que [lora-A-reg2](https://github.com/DavidJLN/merge-llm/blob/main/03-lora/lora-A-reg2), avec la graine 2 au lieu de 0 : seuls
changent les valeurs de départ du LoRA, l'ordre des exemples et le dropout. Il sert à mesurer
ce qui, dans les scores, vient du hasard. Fait partie de l'expérience [merge-llm](https://github.com/DavidJLN/merge-llm/blob/main/README.md).
Résultats sur les trois graines : [resultats-bis.md](https://github.com/DavidJLN/merge-llm/blob/main/resultats-bis.md).

## Entraînement

- Données : `02-donnees/donnees_A.jsonl` (exemples du talent A) + `02-donnees/regul_A.jsonl` (questions du talent B, avec la réponse de l'Instruct : le LoRA apprend à ne rien changer sur ces questions).
- Exemples dont la réponse contient du chinois écartés.
- 1183 exemples d'entraînement (5 % de plus mis de côté pour la validation, la même répartition
  que pour la graine 0), 2 époques. Perte de validation : 0,755 puis 0,754.
- Rang 16, alpha 32, dropout 0,05, sur toutes les couches linéaires (q, k, v, o, gate, up, down).
- Taux d'apprentissage 2e-4 (cosinus, 5 % de chauffe), lots de 16, 1 024 tokens au plus,
  bf16, perte calculée sur la réponse seulement.

Commande (dans `03-lora/`) :

```bash
python entrainer.py A --regularisation --sans-chinois --epoques 2 --nom reg2 --graine 2
```
