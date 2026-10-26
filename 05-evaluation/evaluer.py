"""Évalue l'Instruct, les deux LoRA et tous les merges sur les questions mises de côté.

Lancement (dans WSL, environnement activé, après fusionner.sh) :
    python evaluer.py v1            # LoRA entraînés sans régularisation
    python evaluer.py v2            # LoRA avec régularisation (lora-A-reg…)
    python evaluer.py v2 --refaire  # régénère toutes les réponses
    python evaluer.py gguf          # DARE v3 quantifié, servi par Ollama

Chaque série a son dossier : v1-sans-regularisation/, v2-avec-regularisation/.

La série gguf interroge les modèles prof-json:<quantification> créés avec
ollama create (voir 06-gguf/). Ollama reçoit en mode raw le prompt exact
d'apply_chat_template : seule la quantification change par rapport à la v3.

Chaque modèle reçoit les 50 questions de questions_eval.jsonl (25 par talent),
sans consigne système : un merge réussi doit deviner seul s'il faut expliquer
pas à pas (questions A) ou répondre en JSON (questions B).

La forme est notée avec les mêmes critères que les données d'entraînement
(defauts_de_forme de generer.py) : étapes numérotées, « Exemple : »,
tutoiement, longueur pour A ; JSON valide, tranche de confiance du type de
question, nombre de sujets pour B.

Fichiers produits, dans le dossier de la série :
    reponses/<modèle>.jsonl   réponses brutes (réutilisées au lancement suivant)
    resultats.md              tableau de synthèse
"""

import argparse
import collections
import gc
import json
import os
import re
import sys
import time
import urllib.request

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

DOSSIER_ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER_DONNEES = os.path.join(DOSSIER_ICI, "..", "02-donnees")

# Mêmes critères de forme que pour filtrer les données d'entraînement.
sys.path.insert(0, DOSSIER_DONNEES)
import generer  # noqa: E402

# Série -> (suffixe des modèles dans ~/models, dossier des résultats).
SERIES = {
    "v1": ("", "v1-sans-regularisation"),
    "v2": ("-reg", "v2-avec-regularisation"),
    # Même régularisation, 2 époques au lieu de 3, sans les exemples en chinois.
    "v3": ("-reg2", "v3-regularisation-2-epoques"),
    # Le merge DARE v3 converti en GGUF et quantifié, servi par Ollama.
    "gguf": (None, "v3-gguf-ollama"),
}
QUANTIFICATIONS = ["f16", "Q8_0", "Q5_K_M", "Q4_K_M"]
# Ollama tourne sous Windows ; WSL le joint par localhost (réseau « mirrored »).
OLLAMA = "http://localhost:11434"
# Même tokenizer que le merge : il sert à construire le prompt envoyé à Ollama.
TOKENIZER_GGUF = os.path.expanduser("~/models/qwen2.5-1.5b-merge-reg2-dare")
MERGES = ["task-arithmetic", "task-arithmetic-p09", "task-arithmetic-p08",
          "task-arithmetic-p07", "task-arithmetic-moyenne", "ties", "dare",
          "slerp-t02", "slerp-t035", "slerp-t05", "slerp-t065", "slerp-t08"]


def lister_modeles(suffixe):
    """(identifiant court, nom affiché, identifiant Hugging Face ou dossier local)."""
    dossier = os.path.expanduser("~/models")
    serie = suffixe.lstrip("-")
    return [
        ("base", "Instruct (sans LoRA)", "Qwen/Qwen2.5-1.5B-Instruct"),
        ("lora-A", "LoRA A seul", f"{dossier}/qwen2.5-1.5b-lora-A{suffixe}"),
        ("lora-B", "LoRA B seul", f"{dossier}/qwen2.5-1.5b-lora-B{suffixe}"),
    ] + [
        # fusionner.sh nomme les merges de la série « reg » merge-reg-XXX.
        (f"merge-{nom}", nom,
         f"{dossier}/qwen2.5-1.5b-merge-{serie + '-' if serie else ''}{nom}")
        for nom in MERGES
    ]


def lister_modeles_gguf():
    """La référence bf16 (réponses de la série v3), puis chaque quantification."""
    return [("merge-dare", "DARE bf16 (transformers)", None)] + [
        (f"dare-{q.lower()}", f"DARE {q} (Ollama)", f"ollama:prof-json:{q.lower()}")
        for q in QUANTIFICATIONS
    ]


# Les réponses A font jusqu'à ~300 mots (environ 450 tokens), les B quelques
# lignes : au-delà, on considère que le modèle ne s'arrête pas.
LONGUEUR_MAX = {"A": 600, "B": 250}
ORDRE_TYPES = ["fait", "estimation", "debat", "inconnu"]
# Idéogrammes chinois (U+4E00 à U+9FFF), le bloc où tombent les dérapages de Qwen.
CARACTERES_CHINOIS = re.compile(r"[一-鿿]")


def generer_reponses(modele, tokenizer, questions, longueur):
    """Répond à toutes les questions d'un coup (génération par lot)."""
    textes = [tokenizer.apply_chat_template(
        [{"role": "user", "content": q}], add_generation_prompt=True,
        tokenize=False) for q in questions]
    entree = tokenizer(textes, return_tensors="pt", padding=True).to(
        modele.device)
    # do_sample=False : réponses déterministes, donc comparables d'un modèle
    # à l'autre et d'un lancement à l'autre.
    with torch.no_grad():
        sortie = modele.generate(**entree, max_new_tokens=longueur,
                                 do_sample=False)
    fins = modele.generation_config.eos_token_id
    fins = set(fins if isinstance(fins, list) else [fins])
    fins.add(tokenizer.pad_token_id)

    reponses = []
    for tokens in sortie[:, entree["input_ids"].shape[1]:]:
        # Le modèle a fini seul s'il a produit un token de fin avant la limite.
        fini = any(t in fins for t in tokens.tolist())
        texte = tokenizer.decode(tokens, skip_special_tokens=True).strip()
        reponses.append((texte, fini))
    return reponses


def repondre_avec(chemin, questions):
    """Charge un modèle, répond aux questions des deux talents, le libère."""
    tokenizer = AutoTokenizer.from_pretrained(chemin, padding_side="left")
    modele = AutoModelForCausalLM.from_pretrained(
        chemin, dtype=torch.bfloat16, device_map="cuda")
    resultats = []
    for talent in "AB":
        lot = [q for q in questions if q["talent"] == talent]
        debut = time.time()
        reponses = generer_reponses(modele, tokenizer,
                                    [q["question"] for q in lot],
                                    LONGUEUR_MAX[talent])
        print(f"    {len(lot)} réponses {talent} en {time.time() - debut:.0f} s")
        for q, (texte, fini) in zip(lot, reponses):
            resultats.append({**q, "reponse": texte, "fini": fini})
    del modele
    gc.collect()
    torch.cuda.empty_cache()
    return resultats


def appeler_ollama(chemin_api, requete):
    requete = urllib.request.Request(
        f"{OLLAMA}{chemin_api}", data=json.dumps(requete).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(requete, timeout=600) as reponse:
        return json.load(reponse)


def repondre_avec_ollama(modele, questions):
    """Même travail que repondre_avec, une question à la fois via Ollama."""
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_GGUF)
    resultats = []
    for talent in "AB":
        lot = [q for q in questions if q["talent"] == talent]
        debut = time.time()
        for q in lot:
            prompt = tokenizer.apply_chat_template(
                [{"role": "user", "content": q["question"]}],
                add_generation_prompt=True, tokenize=False)
            # raw : Ollama n'applique pas son propre template. temperature 0 :
            # décodage glouton, comme do_sample=False.
            sortie = appeler_ollama("/api/generate", {
                "model": modele, "prompt": prompt, "raw": True, "stream": False,
                "options": {"temperature": 0, "seed": 0,
                            "num_predict": LONGUEUR_MAX[talent]}})
            resultats.append({**q, "reponse": sortie["response"].strip(),
                              "fini": sortie.get("done_reason") == "stop"})
        print(f"    {len(lot)} réponses {talent} en {time.time() - debut:.0f} s")
    # Libère la carte graphique avant le modèle suivant.
    appeler_ollama("/api/generate", {"model": modele, "keep_alive": 0})
    return resultats


def noter(r):
    """Renvoie (liste des défauts de forme, fuite vers l'autre talent)."""
    talent, reponse = r["talent"], r["reponse"]
    if talent == "B":
        # defauts_de_forme suppose un objet JSON ; on écarte avant les autres
        # JSON valides (liste, nombre…) qu'un merge pourrait produire.
        try:
            objet = json.loads(reponse)
        except json.JSONDecodeError:
            objet = None
        if not isinstance(objet, dict):
            defauts = ["JSON invalide"]
        else:
            defauts = generer.defauts_de_forme("B", reponse, r["type"])
        # Fuite : le modèle explique pas à pas au lieu de répondre en JSON.
        fuite = bool(re.search(r"^1\.", reponse, re.MULTILINE))
    else:
        defauts = generer.defauts_de_forme("A", reponse)
        # Fuite : le modèle répond en JSON à une question qui demande
        # une explication.
        fuite = reponse.lstrip().startswith("{")
    if not r["fini"]:
        defauts.append("ne s'arrête pas")
    # Qwen repasse parfois au chinois en cours de phrase (« il existe还有一些… »),
    # surtout quand un merge l'éloigne de son état normal.
    if CARACTERES_CHINOIS.search(reponse):
        defauts.append("caractères chinois")
    return defauts, fuite


def confiances_par_type(resultats):
    """Confiance moyenne des réponses B lisibles, pour chaque type."""
    par_type = collections.defaultdict(list)
    for r in resultats:
        if r["talent"] != "B":
            continue
        try:
            confiance = json.loads(r["reponse"])["confiance"]
        except (json.JSONDecodeError, TypeError, KeyError):
            continue
        if isinstance(confiance, (int, float)):
            par_type[r["type"]].append(confiance)
    return {t: sum(c) / len(c) for t, c in par_type.items()}


def synthese(tous, modeles):
    """Construit le tableau Markdown et l'affiche."""
    lignes = [
        "| Modèle | A : forme OK | B : forme OK | Total | Fuites | "
        "Non terminées | Confiance fait / estim. / débat / inconnu |",
        "|---|---|---|---|---|---|---|",
    ]
    defauts_frequents = []
    for ident, nom, _ in modeles:
        if ident not in tous:
            continue
        resultats = tous[ident]
        ok = collections.Counter()
        fuites = non_finies = 0
        compte_defauts = collections.Counter()
        for r in resultats:
            defauts, fuite = noter(r)
            ok[r["talent"]] += not defauts and not fuite
            fuites += fuite
            non_finies += not r["fini"]
            # Les défauts de confiance contiennent la valeur : on les regroupe.
            compte_defauts.update(
                "confiance hors tranche" if d.startswith("confiance ") else d
                for d in defauts)
        nb = collections.Counter(r["talent"] for r in resultats)
        conf = confiances_par_type(resultats)
        conf_txt = " / ".join(f"{conf[t]:.2f}" if t in conf else "–"
                              for t in ORDRE_TYPES)
        lignes.append(
            f"| {nom} | {ok['A']}/{nb['A']} | {ok['B']}/{nb['B']} | "
            f"**{ok['A'] + ok['B']}/{len(resultats)}** | {fuites} | "
            f"{non_finies} | {conf_txt} |")
        principaux = ", ".join(f"{d} ({n})"
                               for d, n in compte_defauts.most_common(3))
        defauts_frequents.append(f"- **{nom}** : {principaux or 'aucun'}")

    tableau = "\n".join(lignes)
    print("\n" + tableau + "\n")
    return tableau, "\n".join(defauts_frequents)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("serie", choices=list(SERIES))
    parser.add_argument("--refaire", action="store_true",
                        help="régénère les réponses déjà enregistrées")
    args = parser.parse_args()

    suffixe, nom_dossier = SERIES[args.serie]
    gguf = args.serie == "gguf"
    modeles = lister_modeles_gguf() if gguf else lister_modeles(suffixe)
    dossier_reponses = os.path.join(DOSSIER_ICI, nom_dossier, "reponses")
    fichier_resultats = os.path.join(DOSSIER_ICI, nom_dossier, "resultats.md")

    questions = generer.lire_jsonl(
        os.path.join(DOSSIER_DONNEES, "questions_eval.jsonl"))
    os.makedirs(dossier_reponses, exist_ok=True)

    # Les modèles sont chargés un par un pour ne pas saturer la carte
    # graphique ; les réponses déjà générées sont réutilisées.
    tous = {}
    if gguf:
        # Référence : le même merge en bf16, déjà évalué avec transformers.
        tous["merge-dare"] = generer.lire_jsonl(os.path.join(
            DOSSIER_ICI, SERIES["v3"][1], "reponses", "merge-dare.jsonl"))
    for ident, nom, chemin in modeles:
        if ident in tous:
            continue
        fichier = os.path.join(dossier_reponses, f"{ident}.jsonl")
        if os.path.exists(fichier) and not args.refaire:
            tous[ident] = generer.lire_jsonl(fichier)
            print(f"=== {nom} : réponses déjà enregistrées")
            continue
        if chemin.startswith("/") and not os.path.isdir(chemin):
            print(f"=== {nom} : introuvable ({chemin}), ignoré")
            continue
        print(f"=== {nom}")
        if chemin.startswith("ollama:"):
            tous[ident] = repondre_avec_ollama(chemin.removeprefix("ollama:"),
                                               questions)
        else:
            tous[ident] = repondre_avec(chemin, questions)
        with open(fichier, "w", encoding="utf-8") as f:
            for r in tous[ident]:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    tableau, defauts = synthese(tous, modeles)
    titre = {"v1": "sans régularisation", "v2": "avec régularisation",
             "v3": "régularisation, 2 époques, sans chinois",
             "gguf": "DARE v3 quantifié en GGUF, servi par Ollama"}[args.serie]
    with open(fichier_resultats, "w", encoding="utf-8") as f:
        f.write(
            f"# Évaluation des merges ({titre})\n\n"
            f"{len(questions)} questions mises de côté "
            "(25 « Prof patient », 25 « JSON strict »), jamais vues à "
            "l'entraînement. Aucune consigne système, réponses déterministes.\n\n"
            "- **Forme OK** : aucun défaut selon les critères des données "
            "d'entraînement, et pas de fuite.\n"
            "- **Fuite** : JSON sur une question A, ou étapes numérotées sur "
            "une question B.\n"
            "- Une réponse qui contient des caractères chinois compte comme "
            "un défaut de forme.\n"
            "- **Confiance** : moyenne sur les réponses B lisibles. Tranches "
            "attendues : fait 0,9-1 ; estimation 0,6-0,85 ; débat 0,3-0,55 ; "
            "inconnu 0-0,25.\n\n"
            f"{tableau}\n\n"
            "Avec 25 questions par talent, un écart de 1 ou 2 réponses "
            "(4 à 8 points) n'est pas significatif.\n\n"
            "## Défauts les plus fréquents\n\n"
            f"{defauts}\n\n"
            "Les réponses complètes sont dans [reponses/](reponses/).\n")
    print(f"Synthèse enregistrée dans {fichier_resultats}")


if __name__ == "__main__":
    main()
