"""Vérifie si des modèles sont "fusionnables" AVANT de lancer un merge.

Lancement (environnement activé) :
    python distance.py <modèle de base> <modèle 1> [<modèle 2> ...]

Exemple :
    python distance.py Qwen/Qwen2.5-1.5B Qwen/Qwen2.5-1.5B-Instruct Qwen/Qwen2.5-Coder-1.5B-Instruct

Chaque modèle peut être un identifiant Hugging Face ou un dossier local.

Deux étapes, pour s'arrêter le plus tôt possible :
  1. compare les fichiers de configuration (quelques Ko) : si les architectures
     diffèrent, on s'arrête sans télécharger les modèles ;
  2. mesure, couche par couche, ce que chaque modèle a appris par rapport à la base.

Code de sortie : 0 si fusionnable, 1 sinon. On peut donc enchaîner :
    python distance.py ... && mergekit-yaml config.yaml ~/models/mon-merge --cuda
"""

import glob
import itertools
import json
import os
import sys

from huggingface_hub import hf_hub_download, snapshot_download
from safetensors import safe_open

# Caractéristiques qui doivent être identiques pour qu'un merge soit possible.
CLES_ARCHITECTURE = [
    "architectures", "model_type", "hidden_size", "intermediate_size",
    "num_hidden_layers", "num_attention_heads", "num_key_value_heads", "vocab_size",
]

# Seuils d'éloignement par rapport à la base (ordres de grandeur, pas des règles strictes).
SEUIL_OK = 5.0       # en % : fine-tune léger
SEUIL_RISQUE = 15.0  # en % : au-delà, le merge a très peu de chances de marcher

# Au-delà de cette proportion de boutons poussés en sens opposé, les deux
# apprentissages n'ont presque rien en commun (50 % = pile ou face).
# C'est normal et sans danger pour des fine-tunes légers sur des sujets différents :
# leurs petits changements s'additionnent sans se gêner. Ça ne devient un problème
# que si les changements sont gros (éloignement au-delà de SEUIL_OK).
SEUIL_CONFLITS = 40.0


def lire_config(modele):
    if os.path.isdir(modele):
        chemin = os.path.join(modele, "config.json")
    else:
        chemin = hf_hub_download(modele, "config.json")
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def ouvrir_poids(modele):
    """Renvoie {nom du bloc: fichier qui le contient}, en gérant les modèles en plusieurs fichiers."""
    dossier = modele if os.path.isdir(modele) else snapshot_download(
        modele, allow_patterns=["*.safetensors", "*.json"]
    )
    blocs = {}
    for fichier in glob.glob(os.path.join(dossier, "*.safetensors")):
        f = safe_open(fichier, "pt")
        for nom in f.keys():
            blocs[nom] = f
    if not blocs:
        sys.exit(f"Aucun fichier .safetensors trouvé pour {modele}")
    return blocs


def verifier_configs(base, modeles):
    print("Étape 1/2 : comparaison des architectures\n")
    ref = lire_config(base)
    compatible = True
    for modele in modeles:
        config = lire_config(modele)
        differences = [k for k in CLES_ARCHITECTURE if config.get(k) != ref.get(k)]
        if differences:
            compatible = False
            print(f"  ❌ {modele}")
            for k in differences:
                print(f"       {k} : {config.get(k)} (base : {ref.get(k)})")
        else:
            print(f"  ✅ {modele}")
    return compatible


def mesurer(base, modeles):
    print("\nÉtape 2/2 : mesure de ce que chaque modèle a appris")
    print("  (téléchargement des modèles si besoin, puis calcul couche par couche...)\n")
    poids_base = ouvrir_poids(base)
    poids = {m: ouvrir_poids(m) for m in modeles}
    paires = list(itertools.combinations(modeles, 2))

    norme_base = 0.0
    norme_delta = {m: 0.0 for m in modeles}
    produit = {p: 0.0 for p in paires}    # pour la similarité de direction
    opposes = {p: 0 for p in paires}      # boutons tournés en sens contraire
    bouges = {p: 0 for p in paires}       # boutons tournés par les deux modèles

    # Les blocs sont chargés un par un pour ne pas saturer la mémoire.
    for nom, fichier in poids_base.items():
        if not all(nom in poids[m] for m in modeles):
            continue
        b = fichier.get_tensor(nom).float()
        norme_base += b.pow(2).sum().item()
        deltas = {}
        for m in modeles:
            deltas[m] = poids[m][nom].get_tensor(nom).float() - b
            norme_delta[m] += deltas[m].pow(2).sum().item()
        for m1, m2 in paires:
            produit[(m1, m2)] += (deltas[m1] * deltas[m2]).sum().item()
            signes = deltas[m1].sign() * deltas[m2].sign()
            opposes[(m1, m2)] += (signes < 0).sum().item()
            bouges[(m1, m2)] += (signes != 0).sum().item()

    eloignement = {m: 100 * (norme_delta[m] / norme_base) ** 0.5 for m in modeles}
    fusionnable = True

    print("  Éloignement par rapport à la base (taille du changement / taille de la base) :")
    for m in modeles:
        e = eloignement[m]
        if e <= SEUIL_OK:
            avis = "✅ fine-tune léger"
        elif e <= SEUIL_RISQUE:
            avis = "⚠️  assez éloigné, merge risqué"
        else:
            avis = "❌ trop éloigné, presque un autre modèle"
            fusionnable = False
        print(f"    {e:6.2f} %  {avis}  {m}")

    for m1, m2 in paires:
        conflits = 100 * opposes[(m1, m2)] / max(bouges[(m1, m2)], 1)
        similarite = produit[(m1, m2)] / max((norme_delta[m1] * norme_delta[m2]) ** 0.5, 1e-12)
        print(f"\n  {m1}  ↔  {m2}")
        print(f"    Boutons poussés en sens opposé : {conflits:.1f} %  (50 % = pile ou face)")
        print(f"    Similarité des directions      : {similarite:.2f}  (1 = identiques, 0 = sans rapport)")
        gros_changements = eloignement[m1] > SEUIL_OK or eloignement[m2] > SEUIL_OK
        if conflits > SEUIL_CONFLITS and gros_changements:
            print("    ⚠️  Beaucoup de conflits sur de gros changements : TIES aura du mal à les arbitrer.")
        elif conflits > SEUIL_CONFLITS:
            print("    ℹ️  Apprentissages indépendants : normal pour des fine-tunes légers sur des sujets différents.")

    return fusionnable


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    base, modeles = sys.argv[1], sys.argv[2:]

    if not verifier_configs(base, modeles):
        print("\nVerdict : ❌ architectures différentes, merge impossible. Arrêt avant téléchargement.")
        sys.exit(1)

    if mesurer(base, modeles):
        print("\nVerdict : ✅ fusionnable. Reste à vérifier la qualité des réponses après le merge.")
        sys.exit(0)
    print("\nVerdict : ❌ au moins un modèle est trop éloigné de la base. Inutile de lancer le merge.")
    sys.exit(1)


if __name__ == "__main__":
    main()
