#!/bin/bash
# Convertit un modèle en GGUF f16, puis le quantifie (par défaut en Q8_0, Q5_K_M et Q4_K_M).
# Prérequis : llama.cpp cloné dans ~/llama.cpp, environnement WSL activé.
# Compilation pour le CPU seulement : llama-quantize n'a pas besoin du GPU.
#
# Lancement :
#   bash convertir.sh             # merge DARE v3 -> dare-*.gguf
#   bash convertir.sh ab Q8_0     # LoRA AB mélangé -> ab-*.gguf, en Q8_0 seulement
set -euo pipefail
modele="${1:-dare}"
case "$modele" in
    dare) SOURCE=~/models/qwen2.5-1.5b-merge-reg2-dare ;;
    ab) SOURCE=~/models/qwen2.5-1.5b-lora-AB ;;
    *) echo "Modèle inconnu : $modele (dare ou ab)"; exit 1 ;;
esac
shift || true
if [ $# -gt 0 ]; then quantifs=("$@"); else quantifs=(Q8_0 Q5_K_M Q4_K_M); fi
cd ~/llama.cpp
echo "=== llama.cpp $(git log -1 --format='%h %cs')"

if ! command -v cmake >/dev/null; then
    echo "=== Installation de cmake dans le venv (pas besoin de sudo)"
    if command -v uv >/dev/null; then uv pip install cmake; else pip install cmake; fi
fi

echo "=== Compilation de llama-quantize"
cmake -B build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build build --target llama-quantize -j "$(nproc)"

SORTIE=~/models/gguf
mkdir -p "$SORTIE"
echo "=== Conversion en f16 de $SOURCE"
python -u convert_hf_to_gguf.py "$SOURCE" --outtype f16 --outfile "$SORTIE/$modele-f16.gguf"

for q in "${quantifs[@]}"; do
    echo "=== Quantification $q"
    ./build/bin/llama-quantize "$SORTIE/$modele-f16.gguf" "$SORTIE/$modele-$q.gguf" "$q"
done
ls -lh "$SORTIE"
