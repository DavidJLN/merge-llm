"""Génère les données de régularisation : les questions de l'autre talent,
avec les réponses de l'Instruct lui-même.

Pourquoi : entraîné seulement sur ses propres questions, chaque LoRA applique
son style à TOUT (le LoRA B répond en JSON à « Comment la Terre tourne-t-elle ? »).
Fusionnés, les deux talents se disputent alors chaque réponse et l'un écrase
l'autre (voir 05-evaluation/v1-sans-regularisation). En montrant aussi à chaque
LoRA les questions de l'autre talent avec la réponse inchangée de l'Instruct,
il apprend à ne modifier QUE son type de question.

Lancement (dans WSL, environnement activé ; contrairement à generer.py, ce
script fait tourner le modèle lui-même, sans Ollama) :
    python regulariser.py

Fichiers produits (reprise automatique si on coupe avec Ctrl+C) :
    regul_A.jsonl   questions B + réponses de l'Instruct, pour le LoRA A
    regul_B.jsonl   questions A + réponses de l'Instruct, pour le LoRA B
"""

import os
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from generer import ajouter_jsonl, lire_jsonl

MODELE = "Qwen/Qwen2.5-1.5B-Instruct"
# Avec 64 réponses longues à la fois, les 8 Go de la carte graphique débordent
# dans la mémoire vive du PC, et la génération devient des dizaines de fois
# plus lente. 16 tient dans la carte, et une réponse très longue fait attendre
# moins de réponses du même lot.
TAILLE_LOT = 16
# entrainer.py coupe les exemples à 1 024 tokens : une réponse plus longue
# perdrait sa fin, et le LoRA apprendrait à ne pas s'arrêter. Les réponses qui
# n'ont pas fini avant cette limite sont donc écartées.
LONGUEUR_MAX = 900


def repondre(modele, tokenizer, questions):
    """Répond à un lot de questions ; None pour celles qui n'ont pas fini."""
    textes = [tokenizer.apply_chat_template(
        [{"role": "user", "content": q}], add_generation_prompt=True,
        tokenize=False) for q in questions]
    entree = tokenizer(textes, return_tensors="pt", padding=True).to(modele.device)
    # do_sample=False : la réponse « la plus probable » de l'Instruct, c'est
    # exactement le comportement qu'on veut que le LoRA préserve.
    with torch.no_grad():
        sortie = modele.generate(**entree, max_new_tokens=LONGUEUR_MAX, do_sample=False)
    fins = modele.generation_config.eos_token_id
    fins = set(fins if isinstance(fins, list) else [fins]) | {tokenizer.pad_token_id}

    reponses = []
    for tokens in sortie[:, entree["input_ids"].shape[1]:]:
        fini = any(t in fins for t in tokens.tolist())
        reponses.append(tokenizer.decode(tokens, skip_special_tokens=True).strip()
                        if fini else None)
    return reponses


def main():
    # Les fichiers sont écrits à côté du script, quel que soit le dossier courant.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    tokenizer = AutoTokenizer.from_pretrained(MODELE, padding_side="left")
    modele = AutoModelForCausalLM.from_pretrained(
        MODELE, dtype=torch.bfloat16, device_map="cuda")

    # Le LoRA A reçoit les questions B, et inversement.
    for talent, autre in (("A", "B"), ("B", "A")):
        fichier = f"regul_{talent}.jsonl"
        deja = {d["messages"][0]["content"] for d in lire_jsonl(fichier)}
        questions = [q for q in lire_jsonl(f"questions_{autre}.jsonl")
                     if q["question"] not in deja]
        print(f"\n=== Régularisation du LoRA {talent} : {len(deja)} déjà faites, "
              f"{len(questions)} questions {autre} à traiter")

        ecartees = 0
        for i in range(0, len(questions), TAILLE_LOT):
            lot = questions[i:i + TAILLE_LOT]
            debut = time.time()
            for q, reponse in zip(lot, repondre(modele, tokenizer,
                                                [q["question"] for q in lot])):
                if reponse is None:
                    ecartees += 1
                    continue
                ajouter_jsonl(fichier, {
                    "talent": talent, "theme": q["theme"], "regularisation": True,
                    "messages": [
                        {"role": "user", "content": q["question"]},
                        {"role": "assistant", "content": reponse},
                    ],
                })
            print(f"  {min(i + TAILLE_LOT, len(questions))}/{len(questions)}  "
                  f"({time.time() - debut:.0f} s, {ecartees} écartées car trop longues)")

        print(f"Total : {len(lire_jsonl(fichier))} exemples dans {fichier}")


if __name__ == "__main__":
    main()
