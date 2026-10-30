#!/bin/bash
# Convertit un modèle Ministral 3 (format HF) en GGUF Q8_0, partie texte seule.
# Prérequis : llama.cpp dans ~/llama.cpp (voir 06-gguf), environnement WSL activé.
# Conversion directe en Q8_0, sans passer par f16 : un fichier de 7 Go en moins
# sur le disque.
#
# Lancement :
#   bash convertir.sh instruct      # Ministral 3 3B Instruct (cache HF)
#   bash convertir.sh reasoning     # Ministral 3 3B Reasoning (cache HF)
#   bash convertir.sh test-linear   # ~/models/ministral-3-3b-test-linear
#   (tout autre nom XXX : ~/models/ministral-3-3b-XXX)
# Produit ~/models/gguf/ministral-<nom>-Q8_0.gguf.
set -euo pipefail
nom="$1"
cache=~/.cache/huggingface/hub
case "$nom" in
    instruct) SOURCE=$(ls -d $cache/models--mistralai--Ministral-3-3B-Instruct-2512-BF16/snapshots/*) ;;
    reasoning) SOURCE=$(ls -d $cache/models--mistralai--Ministral-3-3B-Reasoning-2512/snapshots/*) ;;
    *) SOURCE=~/models/ministral-3-3b-$nom ;;
esac
SORTIE=~/models/gguf/ministral-$nom-Q8_0.gguf
mkdir -p ~/models/gguf
cd ~/llama.cpp
echo "=== llama.cpp $(git log -1 --format='%h %cs')"
echo "=== Conversion en Q8_0 de $SOURCE"
debut=$(date +%s)
python -u convert_hf_to_gguf.py "$SOURCE" --outtype q8_0 --outfile "$SORTIE"
echo "    terminé en $(( $(date +%s) - debut )) s"
ls -lh "$SORTIE"
