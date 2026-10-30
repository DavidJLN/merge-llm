"""Pourquoi les réponses sont coupées : réflexion sans fin ou vraie boucle ?

Pour chaque modèle évalué par eval_justesse.py, et pour chaque jeu :
    en réflexion   réponses coupées alors que [THINK] est encore ouvert : un
                   seul token caché, ou « [THINK] » écrit en texte sans
                   « [/THINK] » ;
    déjà trouvée   réponses coupées qui contiennent déjà la bonne réponse : le
                   modèle l'avait, puis a continué à douter. Un \\boxed{} juste,
                   ou, pour GSM8K, le nombre attendu écrit en clair (s'il
                   n'apparaît pas dans l'énoncé) ;
    1er \\boxed     justesse si l'on arrêtait chaque réponse à son premier
                   \\boxed{} (coupée ou non) : ce que coûtent les doutes ;
    compression    taille zlib des 3000 derniers caractères des réponses
                   coupées, divisée par leur taille (médiane). Une boucle mot
                   pour mot descend vers 0,05 ; un texte normal reste vers 0,35.

Lancement (dans WSL, environnement activé) :
    python 08-ministral/analyser.py
Écrit 08-ministral/analyse.md et 08-ministral/courbe.png.
"""

import glob
import os
import re
import statistics
import zlib

from eval_justesse import (DOSSIER_ICI, DOSSIER_QUESTIONS, DOSSIER_REPONSES,
                           JEUX, encore_en_reflexion, est_juste, extraire,
                           lire_jsonl)

# Part de Reasoning de chaque modèle évalué avec la consigne du Reasoning.
PARTS = {"instruct": 0.0, "linear-r01": 0.1, "linear-r02": 0.2,
         "linear-r03": 0.3, "linear-r05": 0.5, "linear-r07": 0.7,
         "reasoning": 1.0}


def tous_les_boxed(texte):
    """Contenus de tous les \\boxed{...}, dans l'ordre, accolades imbriquées comprises."""
    resultats, debut = [], 0
    while (debut := texte.find("\\boxed{", debut)) >= 0:
        i = debut + len("\\boxed{")
        profondeur = 1
        for j in range(i, len(texte)):
            profondeur += {"{": 1, "}": -1}.get(texte[j], 0)
            if profondeur == 0:
                resultats.append(texte[i:j])
                break
        debut = i
    return resultats


def compression(texte):
    fin = texte[-3000:].encode()
    return len(zlib.compress(fin)) / max(1, len(fin))


def nombres(texte):
    return {n.replace(",", "").rstrip(".") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", texte)}


def deja_trouvee(r, jeu, attendus, enonces):
    attendu = attendus[r["id"]]
    if any(est_juste(b, attendu) for b in tous_les_boxed(r["reponse"])):
        return True
    return (jeu == "gsm8k" and attendu not in nombres(enonces[r["id"]])
            and attendu in nombres(r["reponse"]))


def analyser_jeu(rs, jeu, attendus, enonces):
    def juste_final(r):
        return r["fini"] and est_juste(extraire(r["reponse"], jeu), attendus[r["id"]])

    def juste_premier(r):
        boxed = tous_les_boxed(r["reponse"])
        if not boxed:
            # Sans \boxed, une réponse finie de GSM8K est notée sur son dernier nombre.
            return juste_final(r)
        return est_juste(boxed[0], attendus[r["id"]])

    coupees = [r for r in rs if not r["fini"]]
    return {
        "n": len(rs),
        "justes": sum(map(juste_final, rs)),
        "coupees": len(coupees),
        "en_reflexion": sum(map(encore_en_reflexion, coupees)),
        "deja_trouvee": sum(deja_trouvee(r, jeu, attendus, enonces) for r in coupees),
        "premier_boxed": sum(map(juste_premier, rs)),
        "compression": (statistics.median(compression(r["reponse"]) for r in coupees)
                        if coupees else None),
    }


def courbe(stats, chemin):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, jeu in zip(axes, JEUX):
        points = sorted((PARTS[nom], s) for (nom, j), s in stats.items()
                        if j == jeu and nom in PARTS and s["n"] == JEUX[jeu])
        x = [p for p, _ in points]
        ax.plot(x, [100 * s["justes"] / s["n"] for _, s in points],
                "o-", color="#2a78d6", lw=2, ms=7, label="justes")
        ax.plot(x, [100 * (s["justes"] + s["deja_trouvee"]) / s["n"] for _, s in points],
                "^--", color="#1baf7a", lw=2, ms=7,
                label="justes + coupées qui avaient déjà la réponse")
        ax.plot(x, [100 * s["coupees"] / s["n"] for _, s in points],
                "s-", color="#eb6834", lw=2, ms=7, label="coupées à 4096 tokens")
        reference = stats.get(("instruct-consigne-instruct", jeu))
        if reference:
            ax.axhline(100 * reference["justes"] / reference["n"], color="#52514e",
                       lw=1, linestyle=":", label="justes, Instruct avec sa consigne")
        ax.set_title({"gsm8k": "GSM8K (100 problèmes)",
                      "math": "MATH-500 niv. 3-5 (50 problèmes)"}[jeu])
        ax.set_xlabel("part de Reasoning dans le merge")
        ax.set_xticks([0, 0.1, 0.2, 0.3, 0.5, 0.7, 1])
        ax.set_ylim(0, 100)
        ax.grid(alpha=0.25, lw=0.5)
        for cote in ("top", "right"):
            ax.spines[cote].set_visible(False)
    axes[0].set_ylabel("% des problèmes")
    poignees, etiquettes = axes[0].get_legend_handles_labels()
    fig.legend(poignees, etiquettes, loc="lower center", ncol=4, fontsize=8,
               frameon=False)
    fig.suptitle("Ministral 3 3B, merge linéaire Instruct + Reasoning "
                 "(consigne du Reasoning)")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(chemin, dpi=120)


def main():
    attendus, enonces = {}, {}
    for jeu in JEUX:
        for q in lire_jsonl(os.path.join(DOSSIER_QUESTIONS, f"{jeu}.jsonl")):
            attendus[q["id"]] = q["attendu"]
            enonces[q["id"]] = q["question"]
    stats = {}
    for fichier in sorted(glob.glob(os.path.join(DOSSIER_REPONSES, "*.jsonl"))):
        nom = os.path.basename(fichier)[:-len(".jsonl")]
        reponses = lire_jsonl(fichier)
        for jeu in JEUX:
            rs = [r for r in reponses if r["jeu"] == jeu]
            if rs:
                stats[(nom, jeu)] = analyser_jeu(rs, jeu, attendus, enonces)

    lignes = ["| Modèle | Jeu | Questions | Justes | Justes si arrêt au 1er \\boxed | "
              "Coupées | dont en réflexion | dont réponse déjà trouvée | "
              "Compression des coupées |",
              "|---|---|---|---|---|---|---|---|---|"]
    for (nom, jeu), s in stats.items():
        def pc(k):
            return f"{100 * s[k] / s['n']:.0f} % ({s[k]})"
        comp = f"{s['compression']:.2f}" if s["compression"] is not None else "–"
        lignes.append(f"| {nom} | {jeu} | {s['n']} | {pc('justes')} | "
                      f"{pc('premier_boxed')} | {s['coupees']} | {s['en_reflexion']} | "
                      f"{s['deja_trouvee']} | {comp} |")
    tableau = "\n".join(lignes)
    print(tableau)
    with open(os.path.join(DOSSIER_ICI, "analyse.md"), "w", encoding="utf-8") as f:
        f.write("# Ministral 3 3B : pourquoi les réponses sont coupées\n\n"
                "Produit par `analyser.py` à partir des réponses de "
                "`eval_justesse.py` (définitions des colonnes dans le script).\n\n"
                f"{tableau}\n")
    courbe(stats, os.path.join(DOSSIER_ICI, "courbe.png"))
    print("\nÉcrit analyse.md et courbe.png")


if __name__ == "__main__":
    main()
