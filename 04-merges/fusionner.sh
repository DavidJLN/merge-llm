#!/bin/bash
# Lance tous les merges du dossier, l'un après l'autre.
#
# Lancement (dans WSL, environnement activé) :
#   bash fusionner.sh       # merges des LoRA entraînés sans régularisation
#   bash fusionner.sh "" dare   # une seule recette, LoRA sans régularisation
#   bash fusionner.sh reg   # mêmes recettes, avec les LoRA lora-A-reg et lora-B-reg
#   bash fusionner.sh reg2 task-arithmetic ties dare   # seulement ces recettes-là
#   bash fusionner.sh reg2-g1 dare   # LoRA lora-A-reg2-g1…, DARE tiré avec la graine 1
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
    # mergekit ne comprend pas « ~ » : les recettes écrivent ~/models, et on
    # passe à mergekit une copie avec le vrai dossier personnel.
    recette="$(mktemp --suffix=.yaml)"
    remplacements=(-e "s#~/models/#$HOME/models/#g")
    if [ -n "$serie" ]; then
        nom="$serie-$nom"
        # Même recette, en remplaçant les deux LoRA par leur version « serie ».
        remplacements+=(-e "s#(qwen2\.5-1\.5b-lora-[AB])#\1-$serie#g")
    fi
    sed -E "${remplacements[@]}" "$config" > "$recette"
    sortie="$HOME/models/qwen2.5-1.5b-merge-$nom"
    if [ -d "$sortie" ]; then
        echo "=== $nom : déjà fait, sauté"
        continue
    fi
    echo "=== $nom"
    debut=$(date +%s)
    # --random-seed : rend DARE reproductible (sans effet sur les autres).
    # Une série « reg2-g1 » (LoRA de graine 1) tire aussi DARE avec la graine 1.
    graine=0
    [[ "$serie" =~ -g([0-9]+)$ ]] && graine="${BASH_REMATCH[1]}"
    if ! mergekit-yaml "$recette" "$sortie" --cuda --random-seed "$graine"; then
        echo "!!! échec de $nom"
        rm -rf "$sortie"  # pas de merge à moitié écrit, qui serait « déjà fait »
        exit 1
    fi
    echo "    terminé en $(( $(date +%s) - debut )) s"
done

echo
echo "Merges présents dans ~/models :"
du -sh "$HOME"/models/qwen2.5-1.5b-merge-*
