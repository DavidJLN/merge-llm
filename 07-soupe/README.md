# Soupe de graines du LoRA AB

Les trois graines du LoRA AB obtiennent 48, 49 et 50 sur les 50 questions
habituelles. Question : en les fusionnant (« model soup »), obtient-on un
modèle meilleur que la meilleure graine, ou au moins plus stable ?

**Réponse : non.** La soupe fait aussi bien que la moyenne des graines, pas
mieux. Avec Model Stock, elle perd même les deux talents.

## Fichiers

| Fichier | Rôle |
|---|---|
| `config-linear.yaml` | moyenne simple des trois graines |
| `config-model-stock.yaml` | Model Stock, avec l'Instruct pour base |
| `config-karcher.yaml` | moyenne de Karcher (moyenne sur la sphère) |
| `fusionner.sh` | prépare les soupes dans `~/models/qwen2.5-1.5b-soupe-*` |
| `evaluer_soupe.py` | évalue les soupes et écrit `resultats.md` |
| `angles.py` | mesure les angles entre les changements des graines |

Lancement (dans WSL, environnement activé, depuis la racine du dépôt) :

```bash
bash 07-soupe/fusionner.sh            # environ 40 s par soupe
python 07-soupe/evaluer_soupe.py      # quelques minutes par soupe
python 07-soupe/angles.py
```

## Résultats

Détail dans [resultats.md](resultats.md).

| Modèle | 50 questions | 20 questions écrites à la main |
|---|---|---|
| LoRA AB, graines 0 / 1 / 2 | 48 / 49 / 50 (moyenne 49,0) | 18 / 17 / 16 (moyenne 17,0) |
| Soupe linear | 48 | 17 |
| Soupe karcher | 48 | 16 |
| Soupe model_stock | **1** | **0** |

Aucune soupe ne produit de chinois.

## Pourquoi

`angles.py` mesure, couche par couche, le cosinus entre les changements
(graine − Instruct) de deux graines :

| Couches | Cosinus moyen |
|---|---|
| attention : q_proj, k_proj, v_proj, o_proj | 0,04 à 0,06 |
| MLP : gate_proj, up_proj | 0,05 à 0,11 |
| MLP : down_proj | 0,14 |

Les trois graines apprennent les mêmes talents sur les mêmes données, mais par
des changements **presque orthogonaux** : chaque LoRA de rang faible trouve
son propre sous-espace. Deux conséquences :

- **Linear et karcher** ne cumulent rien : moyenner trois directions presque
  sans rapport revient à garder un tiers de chaque graine. Les talents y
  résistent (48/50), mais la soupe ne corrige pas les erreurs d'une graine par
  les autres. Karcher donne le même résultat que linear, comme prévu pour des
  modèles aussi proches de leur base.
- **Model Stock** suppose des modèles dont les changements se ressemblent.
  Devant des directions qui ne s'accordent pas, il les prend pour du bruit et
  revient vers l'Instruct : sa soupe ne garde qu'environ la moitié de la
  moyenne des changements (contre 100 % pour linear), et cela suffit à
  effacer les deux talents. La méthode ne convient pas à des LoRA entraînés
  indépendamment.

Conclusion : pour un LoRA, la meilleure graine reste le meilleur choix. Aucun
nouveau modèle n'est publié à partir de cette expérience.
