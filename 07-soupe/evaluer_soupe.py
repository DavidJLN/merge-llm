"""Soupes de graines du LoRA AB, comparées aux trois graines seules.

Les graines 0, 1 et 2 du LoRA AB obtiennent 48, 49 et 50 sur les 50 questions
habituelles. Une soupe (moyenne des trois modèles) fait-elle mieux que la
meilleure graine, ou seulement aussi bien que la moyenne des graines ?

Préparation (dans WSL, environnement activé) :
    bash 07-soupe/fusionner.sh

Lancement :
    python 07-soupe/evaluer_soupe.py            # réutilise les réponses enregistrées
    python 07-soupe/evaluer_soupe.py --refaire  # régénère les réponses des soupes

Les réponses des graines ne sont jamais régénérées : elles viennent des séries
témoins (graine 0, jeu eval) et graines (05-evaluation/graines/reponses/).
Mêmes jeux de questions et mêmes critères que 05-evaluation/graines.py.

Fichiers produits :
    07-soupe/reponses/<soupe>-<jeu>.jsonl
    07-soupe/resultats.md
"""

import argparse
import json
import os
import statistics
import sys

DOSSIER_ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER_EVALUATION = os.path.join(DOSSIER_ICI, "..", "05-evaluation")
sys.path.insert(0, DOSSIER_EVALUATION)
import evaluer  # noqa: E402
import generer  # noqa: E402  (ajouté au chemin par evaluer)
import graines  # noqa: E402

DOSSIER_REPONSES = os.path.join(DOSSIER_ICI, "reponses")
FICHIER_RESULTATS = os.path.join(DOSSIER_ICI, "resultats.md")
DOSSIER_MODELES = os.path.expanduser("~/models")
# Identifiant court -> nom affiché ; le dossier est
# ~/models/qwen2.5-1.5b-soupe-<identifiant>.
SOUPES = {
    "linear": "Soupe linear (moyenne simple)",
    "model-stock": "Soupe model_stock",
    "karcher": "Soupe karcher",
}


def reponses_graine(graine, jeu):
    """Réponses déjà enregistrées d'une graine du LoRA AB."""
    if graine == 0 and jeu == "eval":
        fichier = os.path.join(DOSSIER_EVALUATION, "temoins", "reponses",
                               "lora-AB.jsonl")
    else:
        fichier = os.path.join(graines.DOSSIER_REPONSES,
                               f"lora-AB-g{graine}-{jeu}.jsonl")
    if not os.path.exists(fichier):
        print(f"=== LoRA AB, graine {graine}, {jeu} : pas de réponses ({fichier})")
        return None
    return generer.lire_jsonl(fichier)


def reponses_soupe(ident, jeu, questions, refaire):
    """Réponses d'une soupe à un jeu de questions, générées si besoin."""
    fichier = os.path.join(DOSSIER_REPONSES, f"{ident}-{jeu}.jsonl")
    if os.path.exists(fichier) and not refaire:
        return generer.lire_jsonl(fichier)
    chemin = f"{DOSSIER_MODELES}/qwen2.5-1.5b-soupe-{ident}"
    if not os.path.isdir(chemin):
        print(f"=== {SOUPES[ident]} : introuvable ({chemin}), ignorée")
        return None
    print(f"=== {SOUPES[ident]}, questions {jeu}")
    # Un jeu à la fois, comme dans graines.py : mêmes lots, donc des réponses
    # comparables.
    resultats = evaluer.repondre_avec(chemin, questions)
    with open(fichier, "w", encoding="utf-8") as f:
        for r in resultats:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return resultats


def ligne(nom, resultats, nb, total_questions):
    ok, chinois = graines.compter(resultats)
    total = ok["A"] + ok["B"]
    return total, (f"| {nom} | {ok['A']}/{nb['A']} | {ok['B']}/{nb['B']} | "
                   f"**{total}/{total_questions}** | {chinois} |")


def tableau_jeu(questions, par_graine, par_soupe):
    nb = {t: sum(q["talent"] == t for q in questions) for t in "AB"}
    lignes = ["| Modèle | A : forme OK | B : forme OK | Total | Chinois |",
              "|---|---|---|---|---|"]
    totaux = []
    for graine, resultats in par_graine.items():
        if resultats is None:
            lignes.append(f"| LoRA AB, graine {graine} | – | – | – | – |")
            continue
        total, texte = ligne(f"LoRA AB, graine {graine}", resultats, nb,
                             len(questions))
        totaux.append(total)
        lignes.append(texte)
    if totaux:
        ecart = statistics.stdev(totaux) if len(totaux) > 1 else 0
        lignes.append(f"| *Graines : moyenne ± écart-type* | | | "
                      f"*{statistics.mean(totaux):.1f} ± {ecart:.1f}* | |")
    for ident, resultats in par_soupe.items():
        if resultats is None:
            lignes.append(f"| {SOUPES[ident]} | – | – | – | – |")
            continue
        lignes.append(ligne(SOUPES[ident], resultats, nb, len(questions))[1])
    return "\n".join(lignes)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--refaire", action="store_true",
                        help="régénère les réponses des soupes")
    args = parser.parse_args()
    os.makedirs(DOSSIER_REPONSES, exist_ok=True)

    titres = {"eval": "Les 50 questions habituelles",
              "mains": "Les 20 questions écrites à la main"}
    sections = []
    for jeu, nom_fichier in graines.JEUX.items():
        questions = generer.lire_jsonl(
            os.path.join(evaluer.DOSSIER_DONNEES, nom_fichier))
        par_graine = {g: reponses_graine(g, jeu) for g in graines.GRAINES}
        par_soupe = {s: reponses_soupe(s, jeu, questions, args.refaire)
                     for s in SOUPES}
        tableau = tableau_jeu(questions, par_graine, par_soupe)
        print(f"\n{titres[jeu]}\n{tableau}")
        sections.append(f"## {titres[jeu]}\n\n{tableau}\n")

    with open(FICHIER_RESULTATS, "w", encoding="utf-8") as f:
        f.write(
            "# Soupes de graines du LoRA AB\n\n"
            "Les trois graines du LoRA AB (0, 1, 2) sont fusionnées de trois "
            "façons (recettes dans ce dossier). Réponses déterministes, aucune "
            "consigne système, mêmes critères de forme que "
            "[05-evaluation/evaluer.py](../05-evaluation/evaluer.py). Les "
            "réponses des graines sont reprises des séries témoins et graines.\n\n"
            + "\n".join(sections)
            + "\nLes réponses des soupes sont dans [reponses/](reponses/).\n")
    print(f"\nSynthèse enregistrée dans {FICHIER_RESULTATS}")


if __name__ == "__main__":
    main()
