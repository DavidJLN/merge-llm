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

Chaque entraînement produit :
- **l'adaptateur** (71 Mo) dans `lora-<nom>/`, avec une fiche qui décrit ses données et ses
  réglages ;
- **le modèle complet**, avec l'adaptateur intégré (2,9 Go), dans
  `~/models/qwen2.5-1.5b-lora-<nom>`, hors du dépôt. C'est lui que lisent
  [distance.py](../distance.py) et mergekit.

## Les huit adaptateurs

| Adaptateur | Série | Exemples | Époques | Durée (RTX 4060) |
|---|---|---|---|---|
| [lora-A](lora-A) / [lora-B](lora-B) | v1, sans régularisation | 572 / 503 | 3 | 5 / 4 min |
| [lora-A-reg](lora-A-reg) / [lora-B-reg](lora-B-reg) | v2, avec régularisation | 1 189 / 1 119 | 3 | 13 / 17 min |
| [lora-A-reg2c](lora-A-reg2c) / [lora-B-reg2](lora-B-reg2) | v2-bis, avec chinois | 1 189 / 1 119 | 2 | 9 / 11 min |
| [lora-A-reg2](lora-A-reg2) / [lora-B-reg2](lora-B-reg2) | v3, sans chinois | 1 183 / 1 119 | 2 | 9 / 11 min |
| [lora-AB](lora-AB) | témoin : les deux talents mélangés, sans merge | 1 073 | 2 | 6 min |

En v2, la perte de validation remontait à l'époque 3 (sur-apprentissage). D'où les 2 époques
de la v3, qui donne les meilleurs merges.

La v2-bis ne change que le nombre d'époques par rapport à la v2, pour isoler son effet. Les
données de B ne contenaient aucun exemple en chinois : son LoRA est le même qu'en v3
(`fusionner.sh` le trouve sous le nom `lora-B-reg2c`, un lien vers `lora-B-reg2`).
