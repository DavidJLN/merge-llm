#!/bin/bash
# Convertit le merge DARE v3 en GGUF f16, puis le quantifie en Q8_0, Q5_K_M et Q4_K_M.
# Prérequis : llama.cpp cloné dans ~/llama.cpp, environnement WSL activé.
# Compilation pour le CPU seulement : llama-quantize n'a pas besoin du GPU.
set -euo pipefail
cd ~/llama.cpp
echo "=== llama.cpp $(git log -1 --format='%h %cs')"

if ! command -v cmake >/dev/null; then
    echo "=== Installation de cmake dans le venv (pas besoin de sudo)"
    if command -v uv >/dev/null; then uv pip install cmake; else pip install cmake; fi
fi

echo "=== Compilation de llama-quantize"
cmake -B build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build build --target llama-quantize -j "$(nproc)"

SOURCE=~/models/qwen2.5-1.5b-merge-reg2-dare
SORTIE=~/models/gguf
mkdir -p "$SORTIE"
echo "=== Conversion en f16"
python -u convert_hf_to_gguf.py "$SOURCE" --outtype f16 --outfile "$SORTIE/dare-f16.gguf"

for q in Q8_0 Q5_K_M Q4_K_M; do
    echo "=== Quantification $q"
    ./build/bin/llama-quantize "$SORTIE/dare-f16.gguf" "$SORTIE/dare-$q.gguf" "$q"
done
ls -lh "$SORTIE"
