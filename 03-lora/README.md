# Étape 3 : entraîner deux LoRA légers

[entrainer.py](entrainer.py) entraîne un LoRA de rang 16 sur `Qwen/Qwen2.5-1.5B-Instruct`
pour l'un des deux talents. Un LoRA ne modifie pas les 1,5 milliard de poids du modèle : il
ajoute de petits modules d'ajustement (18 millions de paramètres, 1,2 % du total). Le
changement reste donc léger, ce qui est la condition pour qu'un merge marche (voir
[01-echec-coder](../01-echec-coder)).

## Installation

Dans WSL Ubuntu (voir [requirements.txt](requirements.txt)) :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv ~/venvs/merge-llm --python 3.12
source ~/venvs/merge-llm/bin/activate
uv pip install -r requirements.txt
sudo apt-get install -y build-essential   # trl compile un noyau Triton
```

## Lancement

```bash
python entrainer.py A --essai     # 5 pas, pour vérifier l'installation
python entrainer.py A             # série v1
python entrainer.py A --regularisation                                       # série v2
python entrainer.py A --regularisation --sans-chinois --epoques 2 --nom reg2 # série v3
python entrainer.py A --regularisation --epoques 2 --nom reg2c               # série v2-bis
```

Puis la même chose avec `B` (sauf pour la v2-bis, voir plus bas). Le témoin sans merge
s'entraîne en une fois sur les deux talents :

```bash
python entrainer.py AB --sans-chinois --epoques 2
```

`--graine 1` refait le même entraînement avec un autre tirage au hasard (valeurs de départ
du LoRA, ordre des exemples, dropout) et ajoute `-g1` au nom (`lora-A-reg2-g1`…). Sans
cette option, la graine vaut 0, comme pour tous les adaptateurs ci-dessous.

Chaque entraînement produit :
- **l'adaptateur** (71 Mo) dans `lora-<nom>/`, avec une fiche qui décrit ses données et ses
  réglages. Les poids (`adapter_model.safetensors`) ne sont pas dans git : ils sont publiés
  sur Hugging Face, dans [DavidJLN/merge-or-mix-loras](https://huggingface.co/DavidJLN/merge-or-mix-loras),
  un sous-dossier par adaptateur ;
- **le modèle complet**, avec l'adaptateur intégré (2,9 Go), dans
  `~/models/qwen2.5-1.5b-lora-<nom>`, hors du dépôt. C'est lui que lisent
  [distance.py](../distance.py) et mergekit.

## Les quatorze adaptateurs

| Adaptateur | Série | Exemples | Époques | Durée (RTX 4060) |
|---|---|---|---|---|
| [lora-A](lora-A) / [lora-B](lora-B) | v1, sans régularisation | 572 / 503 | 3 | 5 / 4 min |
| [lora-A-reg](lora-A-reg) / [lora-B-reg](lora-B-reg) | v2, avec régularisation | 1 189 / 1 119 | 3 | 13 / 17 min |
| [lora-A-reg2c](lora-A-reg2c) / [lora-B-reg2](lora-B-reg2) | v2-bis, avec chinois | 1 189 / 1 119 | 2 | 9 / 11 min |
| [lora-A-reg2](lora-A-reg2) / [lora-B-reg2](lora-B-reg2) | v3, sans chinois | 1 183 / 1 119 | 2 | 9 / 11 min |
| [lora-AB](lora-AB) | témoin : les deux talents mélangés, sans merge | 1 073 | 2 | 6 min |
| [lora-A-reg2-g1](lora-A-reg2-g1) / [lora-B-reg2-g1](lora-B-reg2-g1), [lora-AB-g1](lora-AB-g1) | v3 et témoin, graine 1 | 1 183 / 1 119, 1 073 | 2 | 9 / 11, 6 min |
| [lora-A-reg2-g2](lora-A-reg2-g2) / [lora-B-reg2-g2](lora-B-reg2-g2), [lora-AB-g2](lora-AB-g2) | v3 et témoin, graine 2 | 1 183 / 1 119, 1 073 | 2 | 9 / 11, 6 min |

En v2, la perte de validation remontait à l'époque 3 (sur-apprentissage). D'où les 2 époques
de la v3, qui donne les meilleurs merges.

La v2-bis ne change que le nombre d'époques par rapport à la v2, pour isoler son effet. Les
données de B ne contenaient aucun exemple en chinois : son LoRA est le même qu'en v3
(`fusionner.sh` le trouve sous le nom `lora-B-reg2c`, un lien vers `lora-B-reg2`).

Les graines 1 et 2 refont la v3 et le témoin avec un autre tirage au hasard, pour mesurer
ce qui, dans les scores, vient du hasard (voir [resultats-bis.md](../resultats-bis.md)).

Pour récupérer un adaptateur depuis Hugging Face :

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM

base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct")
modele = PeftModel.from_pretrained(base, "DavidJLN/merge-or-mix-loras", subfolder="lora-AB")
```

Ou tous d'un coup, à leur place dans `03-lora/` :
`hf download DavidJLN/merge-or-mix-loras --include "lora-*/*" --local-dir 03-lora`
(sans `--include`, la fiche du dépôt Hugging Face remplacerait ce `README.md`).
