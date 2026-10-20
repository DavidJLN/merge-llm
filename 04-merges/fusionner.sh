#!/bin/bash
# Lance tous les merges du dossier, l'un après l'autre.
#
# Lancement (dans WSL, environnement activé) :
#   bash fusionner.sh       # merges des LoRA entraînés sans régularisation
#   bash fusionner.sh reg   # mêmes recettes, avec les LoRA lora-A-reg et lora-B-reg
#   bash fusionner.sh reg2 task-arithmetic ties dare   # seulement ces recettes-là
#
# Chaque config-XXX.yaml produit ~/models/qwen2.5-1.5b-merge-XXX (environ 3 Go),
# ou ~/models/qwen2.5-1.5b-merge-reg-XXX avec « reg ».
# Un merge déjà présent est sauté : on peut relancer le script sans tout refaire,
# ou supprimer un dossier pour refaire seulement ce merge-là.

cd "$(dirname "$0")" || exit 1
serie="$1"
shift
# Recettes à faire : celles données après la série, sinon toutes.
if [ $# -gt 0 ]; then
    configs=()
    for nom in "$@"; do configs+=("config-$nom.yaml"); done
else
    configs=(config-*.yaml)
fi

for config in "${configs[@]}"; do
    nom="${config#config-}"
    nom="${nom%.yaml}"
    recette="$config"
    if [ -n "$serie" ]; then
        nom="$serie-$nom"
        # Même recette, en remplaçant les deux LoRA par leur version « serie ».
        recette="$(mktemp --suffix=.yaml)"
        sed -E "s#(qwen2\.5-1\.5b-lora-[AB])#\1-$serie#g" "$config" > "$recette"
    fi
    sortie="$HOME/models/qwen2.5-1.5b-merge-$nom"
    if [ -d "$sortie" ]; then
        echo "=== $nom : déjà fait, sauté"
        continue
    fi
    echo "=== $nom"
    debut=$(date +%s)
    # --random-seed 0 : rend DARE reproductible (sans effet sur les autres).
    if ! mergekit-yaml "$recette" "$sortie" --cuda --random-seed 0; then
        echo "!!! échec de $nom"
        rm -rf "$sortie"  # pas de merge à moitié écrit, qui serait « déjà fait »
        exit 1
    fi
    echo "    terminé en $(( $(date +%s) - debut )) s"
done

echo
echo "Merges présents dans ~/models :"
du -sh "$HOME"/models/qwen2.5-1.5b-merge-*
