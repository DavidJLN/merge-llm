"""Angles entre les changements appris par les trois graines du LoRA AB.

Pour chaque couche, on calcule le changement de chaque graine par rapport à
l'Instruct (graine - Instruct), puis le cosinus entre les changements de deux
graines : 1 = même direction, 0 = directions sans rapport. On mesure aussi la
part de la moyenne des changements que gardent les soupes linear et
model_stock.

Lancement (dans WSL, environnement activé, après fusionner.sh) :
    python 07-soupe/angles.py
"""

import os
import statistics

import torch
from huggingface_hub import snapshot_download
from safetensors import safe_open

DOSSIER_MODELES = os.path.expanduser("~/models")


def ouvrir(chemin):
    return safe_open(chemin, "pt")


def main():
    dossier_base = snapshot_download("Qwen/Qwen2.5-1.5B-Instruct",
                                     allow_patterns=["*.safetensors"])
    base = ouvrir(os.path.join(dossier_base, "model.safetensors"))
    graines = [ouvrir(f"{DOSSIER_MODELES}/qwen2.5-1.5b-lora-AB{s}/model.safetensors")
               for s in ["", "-g1", "-g2"]]
    soupes = {s: ouvrir(f"{DOSSIER_MODELES}/qwen2.5-1.5b-soupe-{s}/model.safetensors")
              for s in ["linear", "model-stock"]}

    cosinus = {}  # type de couche (q_proj, down_proj…) -> cosinus des paires
    parts = {s: [] for s in soupes}
    for nom in base.keys():
        b = base.get_tensor(nom).float().flatten()
        changements = [g.get_tensor(nom).float().flatten() - b for g in graines]
        # Couches que le LoRA ne touche pas (normes, embeddings) : ignorées.
        if min(c.norm() for c in changements) < 1e-6:
            continue
        type_couche = nom.split(".")[-2]
        for i in range(3):
            for j in range(i + 1, 3):
                cosinus.setdefault(type_couche, []).append(
                    torch.nn.functional.cosine_similarity(
                        changements[i], changements[j], dim=0).item())
        moyenne = sum(changements) / 3
        for s, f in soupes.items():
            ecart = f.get_tensor(nom).float().flatten() - b
            parts[s].append((ecart.norm() / moyenne.norm()).item())

    print("Cosinus entre les changements de deux graines, par type de couche :")
    for type_couche, cs in sorted(cosinus.items()):
        print(f"  {type_couche:10s} moyenne {statistics.mean(cs):.3f}  "
              f"(min {min(cs):.3f}, max {max(cs):.3f})")
    print("Norme (soupe - Instruct) / norme (moyenne des changements) :")
    for s, valeurs in parts.items():
        print(f"  {s:12s} {statistics.mean(valeurs):.3f}")


if __name__ == "__main__":
    main()
