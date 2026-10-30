#!/bin/bash
# Prépare un merge Ministral jusqu'au GGUF : merge, conversion en Q8_0, puis
# suppression du merge au format HF (7 Go) pour ménager le disque.
#
# Lancement (dans WSL, environnement activé) :
#   bash fusionner.sh linear-r03        # recette config-linear-r03.yaml
#
# Produit ~/models/gguf/ministral-<nom>-Q8_0.gguf, à importer ensuite dans
# Ollama avec creer.ps1. Le merge tourne sur le CPU : le GPU reste libre pour
# l'évaluation qui tourne en même temps dans Ollama.
set -euo pipefail
cd "$(dirname "$0")"
nom="$1"
sortie="$HOME/models/ministral-3-3b-$nom"
rm -rf "$sortie"
echo "=== Merge $nom"
debut=$(date +%s)
# La graine ne change rien aux merges linéaires ; elle fixe le tirage de DARE.
if ! mergekit-yaml --random-seed 0 "config-$nom.yaml" "$sortie"; then
    echo "!!! échec du merge $nom"
    rm -rf "$sortie"
    exit 1
fi
echo "    merge terminé en $(( $(date +%s) - debut )) s"
bash convertir.sh "$nom"
rm -rf "$sortie"
echo "=== $nom prêt, merge HF supprimé"
