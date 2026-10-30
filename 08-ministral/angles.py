"""Angles entre les changements de l'Instruct et du Reasoning par rapport à la Base.

DARE-TIES suppose deux modèles affinés séparément à partir de la même Base.
Si Mistral a tiré le Reasoning de l'Instruct, le changement du Reasoning
(Reasoning - Base) contient celui de l'Instruct, et les deux se ressemblent.
Pour chaque tenseur, on mesure :
    cosinus     entre (Instruct - Base) et (Reasoning - Base) : 1 = même
                direction, 0 = directions sans rapport ;
    normes      |Instruct - Base|, |Reasoning - Base| et |Reasoning - Instruct| :
                si le Reasoning vient de l'Instruct, le dernier est nettement
                plus petit que |Reasoning - Base| ;
    conflits    part des poids où les deux changements sont de signes opposés,
                ceux que TIES doit trancher (0,5 pour des directions sans rapport).

Lancement (dans WSL, environnement activé ; les trois modèles dans le cache HF) :
    python 08-ministral/angles.py
"""

import json
import os
import statistics

import torch
from huggingface_hub import snapshot_download
from safetensors import safe_open

DEPOTS = {"base": "mistralai/Ministral-3-3B-Base-2512",
          "instruct": "mistralai/Ministral-3-3B-Instruct-2512-BF16",
          "reasoning": "mistralai/Ministral-3-3B-Reasoning-2512"}


class Modele:
    """Lit un tenseur à la fois dans un modèle découpé en plusieurs fichiers."""

    def __init__(self, depot):
        self.dossier = snapshot_download(depot, local_files_only=True,
                                         allow_patterns=["model*.safetensors*"])
        with open(os.path.join(self.dossier, "model.safetensors.index.json")) as f:
            self.carte = json.load(f)["weight_map"]
        self.fichiers = {}

    def tenseur(self, nom):
        fichier = self.carte[nom]
        if fichier not in self.fichiers:
            self.fichiers[fichier] = safe_open(os.path.join(self.dossier, fichier), "pt")
        return self.fichiers[fichier].get_tensor(nom).float().flatten()


def groupe(nom):
    """Partie du modèle et type de couche, par exemple « texte / q_proj »."""
    partie = ("texte" if "language_model" in nom
              else "vision" if "vision" in nom else "projecteur")
    morceaux = nom.split(".")
    type_couche = morceaux[-2] if morceaux[-1] in ("weight", "bias") else morceaux[-1]
    return f"{partie} / {type_couche}"


def main():
    modeles = {k: Modele(d) for k, d in DEPOTS.items()}
    noms = sorted(modeles["base"].carte)
    assert all(sorted(m.carte) == noms for m in modeles.values()), "tenseurs différents"

    mesures = {}  # groupe -> liste de (cosinus, |I-B|, |R-B|, |R-I|, conflits)
    for nom in noms:
        b, i, r = (modeles[k].tenseur(nom) for k in ("base", "instruct", "reasoning"))
        di, dr = i - b, r - b
        if min(di.norm(), dr.norm()) < 1e-6:
            continue  # tenseur que l'un des deux n'a pas touché
        actifs = (di != 0) & (dr != 0)
        mesures.setdefault(groupe(nom), []).append((
            torch.nn.functional.cosine_similarity(di, dr, dim=0).item(),
            di.norm().item(), dr.norm().item(), (r - i).norm().item(),
            ((di.sign() != dr.sign()) & actifs).sum().item() / max(1, actifs.sum().item())))

    print(f"{'groupe':28s} {'n':>4s} {'cosinus':>8s} {'|I-B|':>8s} {'|R-B|':>8s} "
          f"{'|R-I|':>8s} {'conflits':>9s}")
    for g, valeurs in sorted(mesures.items()):
        moy = [statistics.mean(v[k] for v in valeurs) for k in range(5)]
        print(f"{g:28s} {len(valeurs):4d} {moy[0]:8.3f} {moy[1]:8.2f} {moy[2]:8.2f} "
              f"{moy[3]:8.2f} {moy[4]:9.2f}")


if __name__ == "__main__":
    main()
