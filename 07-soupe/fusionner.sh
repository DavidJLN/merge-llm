#!/bin/bash
# Prépare les soupes de graines du LoRA AB, l'une après l'autre.
#
# Lancement (dans WSL, environnement activé) :
#   bash fusionner.sh                  # toutes les recettes du dossier
#   bash fusionner.sh linear karcher   # seulement ces recettes-là
#
# Chaque config-XXX.yaml produit ~/models/qwen2.5-1.5b-soupe-XXX (environ 3 Go).
# Une soupe déjà présente est sautée : supprimer son dossier pour la refaire.

cd "$(dirname "$0")" || exit 1
if [ $# -gt 0 ]; then
    configs=()
    for nom in "$@"; do configs+=("config-$nom.yaml"); done
else
    configs=(config-*.yaml)
fi

for config in "${configs[@]}"; do
    nom="${config#config-}"
    nom="${nom%.yaml}"
    sortie="$HOME/models/qwen2.5-1.5b-soupe-$nom"
    if [ -d "$sortie" ]; then
        echo "=== $nom : déjà fait, sauté"
        continue
    fi
    # mergekit ne comprend pas « ~ » : on lui passe une copie de la recette
    # avec le vrai dossier personnel.
    recette="$(mktemp --suffix=.yaml)"
    sed -e "s#~/models/#$HOME/models/#g" "$config" > "$recette"
    echo "=== $nom"
    debut=$(date +%s)
    if ! mergekit-yaml "$recette" "$sortie" --cuda; then
        echo "!!! échec de $nom"
        rm -rf "$sortie"  # pas de soupe à moitié écrite, qui serait « déjà faite »
        exit 1
    fi
    echo "    terminé en $(( $(date +%s) - debut )) s"
done

echo
echo "Soupes présentes dans ~/models :"
du -sh "$HOME"/models/qwen2.5-1.5b-soupe-*
