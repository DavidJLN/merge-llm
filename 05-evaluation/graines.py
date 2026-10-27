"""Merge DARE v3 contre LoRA AB mélangé, avec trois graines d'entraînement.

Avec une seule graine, 46 contre 48 sur 50 ne permet pas de conclure : un autre
tirage (initialisation du LoRA, ordre des exemples, dropout, tirage de DARE)
peut suffire à inverser l'écart. On compare donc la moyenne et la dispersion
sur les graines 0, 1 et 2.

Préparation (dans WSL, environnement activé), pour g = 1 puis 2 :
    python 03-lora/entrainer.py A --regularisation --sans-chinois --epoques 2 --nom reg2 --graine g
    python 03-lora/entrainer.py B --regularisation --sans-chinois --epoques 2 --nom reg2 --graine g
    python 03-lora/entrainer.py AB --sans-chinois --epoques 2 --graine g
    bash 04-merges/fusionner.sh reg2-gg dare
La graine 0 correspond aux modèles déjà évalués (séries v3 et temoins).

Lancement :
    python graines.py            # réutilise les réponses déjà enregistrées
    python graines.py --refaire  # régénère tout, sauf les réponses de la graine 0
                                   reprises des séries v3 et temoins

Deux jeux de questions, notés séparément :
    eval   les 50 questions habituelles (questions_eval.jsonl) ;
    mains  20 questions écrites à la main (questions_mains.jsonl), hors des
           thèmes de generer.py : 4 questions A, 16 questions B.

Fichiers produits :
    graines/reponses/<modèle>-g<graine>-<jeu>.jsonl
    ../resultats-bis.md
"""

import argparse
import collections
import json
import os
import statistics

import evaluer
import generer

DOSSIER_ICI = evaluer.DOSSIER_ICI
DOSSIER_REPONSES = os.path.join(DOSSIER_ICI, "graines", "reponses")
FICHIER_RESULTATS = os.path.join(DOSSIER_ICI, "..", "resultats-bis.md")
GRAINES = [0, 1, 2]
JEUX = {"eval": "questions_eval.jsonl", "mains": "questions_mains.jsonl"}
DOSSIER_MODELES = os.path.expanduser("~/models")
# Identifiant court -> (nom affiché, dossier du modèle selon le suffixe de
# graine, réponses de la graine 0 déjà enregistrées pour le jeu eval).
MODELES = {
    "dare": ("Merge DARE v3",
             lambda g: f"{DOSSIER_MODELES}/qwen2.5-1.5b-merge-reg2{g}-dare",
             os.path.join("v3-regularisation-2-epoques", "reponses",
                          "merge-dare.jsonl")),
    "lora-AB": ("LoRA AB mélangé",
                lambda g: f"{DOSSIER_MODELES}/qwen2.5-1.5b-lora-AB{g}",
                os.path.join("temoins", "reponses", "lora-AB.jsonl")),
}


def obtenir_reponses(ident, graine, jeu, questions, refaire):
    """Réponses d'un modèle à un jeu de questions, générées si besoin."""
    nom, dossier, deja_eval = MODELES[ident]
    if graine == 0 and jeu == "eval":
        return generer.lire_jsonl(os.path.join(DOSSIER_ICI, deja_eval))
    fichier = os.path.join(DOSSIER_REPONSES, f"{ident}-g{graine}-{jeu}.jsonl")
    if os.path.exists(fichier) and not refaire:
        return generer.lire_jsonl(fichier)
    chemin = dossier(f"-g{graine}" if graine else "")
    if not os.path.isdir(chemin):
        print(f"=== {nom}, graine {graine} : introuvable ({chemin}), ignoré")
        return None
    print(f"=== {nom}, graine {graine}, questions {jeu}")
    # Un jeu à la fois : les lots restent ceux de l'évaluation d'origine
    # (le remplissage d'un lot peut changer légèrement les réponses).
    resultats = evaluer.repondre_avec(chemin, questions)
    with open(fichier, "w", encoding="utf-8") as f:
        for r in resultats:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return resultats


def compter(resultats):
    """Réponses sans défaut par talent, et réponses contenant du chinois."""
    ok = collections.Counter()
    chinois = 0
    for r in resultats:
        defauts, fuite = evaluer.noter(r)
        ok[r["talent"]] += not defauts and not fuite
        chinois += "caractères chinois" in defauts
    return ok, chinois


def tableau_jeu(jeu, questions, tous):
    nb = collections.Counter(q["talent"] for q in questions)
    lignes = [
        "| Modèle | Graine | A : forme OK | B : forme OK | Total | Chinois |",
        "|---|---|---|---|---|---|",
    ]
    resume = [f"| Modèle | Total moyen (sur {len(questions)}) | Écart-type "
              "| Min – max | Chinois (moyenne) |",
              "|---|---|---|---|---|"]
    for ident, (nom, _, _) in MODELES.items():
        totaux, chinois_tous = [], []
        for graine in GRAINES:
            resultats = tous.get((ident, graine, jeu))
            if resultats is None:
                lignes.append(f"| {nom} | {graine} | – | – | – | – |")
                continue
            ok, chinois = compter(resultats)
            total = ok["A"] + ok["B"]
            totaux.append(total)
            chinois_tous.append(chinois)
            lignes.append(f"| {nom} | {graine} | {ok['A']}/{nb['A']} | "
                          f"{ok['B']}/{nb['B']} | **{total}/{len(questions)}** "
                          f"| {chinois} |")
        if totaux:
            ecart = statistics.stdev(totaux) if len(totaux) > 1 else 0
            resume.append(
                f"| {nom} | **{statistics.mean(totaux):.1f}** "
                f"({len(totaux)} graine{'s' if len(totaux) > 1 else ''}) | "
                f"{ecart:.1f} | {min(totaux)} – {max(totaux)} | "
                f"{statistics.mean(chinois_tous):.1f} |")
    return "\n".join(resume), "\n".join(lignes)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--refaire", action="store_true",
                        help="régénère les réponses déjà enregistrées")
    args = parser.parse_args()
    os.makedirs(DOSSIER_REPONSES, exist_ok=True)

    jeux = {jeu: generer.lire_jsonl(os.path.join(evaluer.DOSSIER_DONNEES, f))
            for jeu, f in JEUX.items()}
    tous = {}
    for ident in MODELES:
        for graine in GRAINES:
            for jeu, questions in jeux.items():
                tous[(ident, graine, jeu)] = obtenir_reponses(
                    ident, graine, jeu, questions, args.refaire)

    sections = []
    titres = {"eval": "Les 50 questions habituelles",
              "mains": "Les 20 questions écrites à la main"}
    for jeu, questions in jeux.items():
        resume, detail = tableau_jeu(jeu, questions, tous)
        print(f"\n{titres[jeu]}\n{resume}\n\n{detail}")
        sections.append(f"## {titres[jeu]}\n\n{resume}\n\n"
                        f"Détail par graine :\n\n{detail}\n")

    with open(FICHIER_RESULTATS, "w", encoding="utf-8") as f:
        f.write(
            "# Merge DARE v3 contre LoRA AB mélangé, sur trois graines\n\n"
            "Chaque modèle est réentraîné avec les graines 0, 1 et 2 (LoRA A-reg2, "
            "B-reg2 puis DARE tiré avec la même graine ; LoRA AB). Réponses "
            "déterministes, aucune consigne système, mêmes critères de forme que "
            "[05-evaluation/evaluer.py](05-evaluation/evaluer.py). La graine 0 "
            "reprend les réponses des séries v3 et témoins.\n\n"
            "Questions écrites à la main : 4 questions A (5, 10, 15, 20 de "
            "`Questions-mains.txt`) et 16 questions B, toutes de type « fait » "
            "sauf la 11 (« estimation »). Le score A sur ce jeu ne repose donc "
            "que sur 4 questions.\n\n"
            + "\n".join(sections)
            + "\nLes réponses complètes sont dans "
            "[05-evaluation/graines/reponses/](05-evaluation/graines/reponses/).\n")
    print(f"\nSynthèse enregistrée dans {FICHIER_RESULTATS}")


if __name__ == "__main__":
    main()
