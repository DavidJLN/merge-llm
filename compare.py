"""Pose les mêmes questions à plusieurs modèles et enregistre les réponses.

Lancement (environnement activé) :
    python compare.py

Les réponses s'affichent au fur et à mesure et 
sont enregistrées dans resultats.md.
"""

import gc
import os
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Modèles à comparer : nom affiché 
#   -> identifiant Hugging Face ou dossier local.
MODELES = {
    "Instruct (A)": "Qwen/Qwen2.5-1.5B-Instruct",
    "Coder (B)": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
    "Merge SLERP t=0.5": os.path.expanduser("~/models/qwen2.5-1.5b-slerp"),
    "Merge SLERP t=0.2": os.path.expanduser("~/models/qwen2.5-1.5b-slerp-t02"),
    "Merge TIES": os.path.expanduser("~/models/qwen2.5-1.5b-ties"),
    # Deuxième série : fine-tunes légers de l'Instruct (code + maths).
    "Code (C)": "Malikeh1375/Qwen2.5-1.5B-Programming-And-Code-Development-Distilled-8Clusters-25K",
    "Maths (D)": "jahyungu/Qwen2.5-1.5B-Instruct_gsm8k",
    "Merge SLERP code+maths": os.path.expanduser("~/models/qwen2.5-1.5b-slerp-code-maths"),
    "Merge TIES code+maths": os.path.expanduser("~/models/qwen2.5-1.5b-ties-code-maths"),
}

# Une question générale, une de code et une de raisonnement,
# pour voir ce que le merge garde de chaque modèle.
QUESTIONS = [
    "Explique en trois phrases simples ce qu'est la photosynthèse.",
    """Traduis cette fonction PHP en Python :

```php
function moyenne(array $notes): float {
    if (count($notes) === 0) {
        return 0.0;
    }
    return array_sum($notes) / count($notes);
}
```""",
    "Un train part à 14h10 et arrive à 16h45. Combien de temps dure le trajet ? "
    "Explique ton raisonnement.",
]

LONGUEUR_MAX = 400  # nombre maximum de tokens générés par réponse
FICHIER_RESULTATS = "resultats.md"
# Tout ce qui précède ce marqueur dans resultats.md (synthèse écrite à la main)
# est conservé ; seules les réponses en dessous sont régénérées.
MARQUEUR = "<!-- Réponses détaillées générées par compare.py -->"


def repondre(modele, tokenizer, question):
    messages = [{"role": "user", "content": question}]
    entree = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, return_dict=True, return_tensors="pt"
    ).to(modele.device)
    # do_sample=False : le modèle choisit toujours le mot le plus probable,
    # ce qui rend les résultats reproductibles et comparables.
    sortie = modele.generate(**entree, max_new_tokens=LONGUEUR_MAX, do_sample=False)
    nouveaux_tokens = sortie[0][entree["input_ids"].shape[1]:]
    return tokenizer.decode(nouveaux_tokens, skip_special_tokens=True).strip()


def main():
    reponses = {}  # (question, modèle) -> réponse

    # Les modèles sont chargés un par un 
    # pour ne pas saturer la carte graphique.
    for nom, chemin in MODELES.items():
        if chemin.startswith("/") and not os.path.isdir(chemin):
            print(f"[{nom}] introuvable ({chemin}), ignoré.")
            continue

        print(f"\n=== Chargement de {nom} ===")
        tokenizer = AutoTokenizer.from_pretrained(chemin)
        modele = AutoModelForCausalLM.from_pretrained(
            chemin, dtype=torch.bfloat16, device_map="cuda"
        )

        for i, question in enumerate(QUESTIONS):
            debut = time.time()
            reponse = repondre(modele, tokenizer, question)
            reponses[(i, nom)] = reponse
            print(f"\n--- Question {i + 1} ---"
                  f"({time.time() - debut:.1f} s) ---\n"
                  f"{reponse}")

        del modele
        gc.collect()
        torch.cuda.empty_cache()

    # Enregistrement : pour chaque question, 
    # les réponses des modèles côte à côte.
    entete = "# Comparaison des modèles\n\n"
    if os.path.exists(FICHIER_RESULTATS):
        with open(FICHIER_RESULTATS, encoding="utf-8") as f:
            contenu = f.read()
        if MARQUEUR in contenu:
            entete = contenu.split(MARQUEUR)[0]

    with open(FICHIER_RESULTATS, "w", encoding="utf-8") as f:
        f.write(entete + MARQUEUR + "\n\n# Réponses détaillées\n")
        for i, question in enumerate(QUESTIONS):
            f.write(f"\n## Question {i + 1}\n\n{question}\n")
            for nom in MODELES:
                if (i, nom) in reponses:
                    f.write(f"\n### {nom}\n\n{reponses[(i, nom)]}\n")

    print(f"\nRésultats enregistrés dans {FICHIER_RESULTATS}")


if __name__ == "__main__":
    main()
