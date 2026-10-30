"""Justesse et longueur des réponses de Ministral 3 3B et de ses merges.

Deux jeux de questions de maths à réponse vérifiable :
    gsm8k  100 problèmes de GSM8K (test), niveau collège, réponse numérique ;
    math   50 problèmes de MATH-500 de niveau 3 à 5, réponse en LaTeX.
Chaque modèle passe par Ollama (GGUF Q8_0, voir convertir.sh et creer.ps1),
avec au plus LONGUEUR_MAX tokens par réponse. Une réponse coupée par cette
limite compte comme fausse : l'utilisateur n'a pas de réponse.

Échantillonnage : température 0,7 et top_p 0,95, les réglages recommandés par
la fiche du Reasoning, avec une graine fixe. En décodage glouton (température
0), les modèles qui réfléchissent tournent parfois en boucle sur une phrase
jusqu'à la limite.

Consigne système : par défaut celle du Reasoning (« réfléchis dans [THINK],
puis réponds »), pour tous les modèles. On mesure ainsi, quand on lui demande
de réfléchir, combien de temps chaque modèle réfléchit et s'il a raison.
L'option --consigne instruct donne celle de l'Instruct (son usage normal).

Ollama retire les tokens spéciaux du texte, [THINK] et [/THINK] compris. On
sait seulement combien il en a caché : eval_count moins le nombre de tokens
renvoyés. Hors fin de texte, 2 tokens cachés signifient que le modèle a ouvert
et fermé une réflexion.

Lancement (dans WSL, environnement activé ; Ollama tourne sous Windows) :
    python 08-ministral/eval_justesse.py preparer
    python 08-ministral/eval_justesse.py evaluer ministral-reasoning:q8_0 --nom reasoning
    python 08-ministral/eval_justesse.py evaluer ministral-instruct:q8_0 \\
        --nom instruct-consigne-instruct --consigne instruct
    python 08-ministral/eval_justesse.py synthese
Un modèle déjà évalué en partie reprend là où il s'était arrêté.
--limite N : seulement les N premières questions de chaque jeu (essai).

Fichiers produits :
    08-ministral/questions/<jeu>.jsonl
    08-ministral/reponses/<nom>.jsonl
    08-ministral/resultats.md
"""

import argparse
import glob
import json
import os
import random
import re
import statistics
import time
import urllib.request

DOSSIER_ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER_QUESTIONS = os.path.join(DOSSIER_ICI, "questions")
DOSSIER_REPONSES = os.path.join(DOSSIER_ICI, "reponses")
FICHIER_RESULTATS = os.path.join(DOSSIER_ICI, "resultats.md")
OLLAMA = "http://localhost:11434"
CACHE_HF = os.path.expanduser("~/.cache/huggingface/hub")
JEUX = {"gsm8k": 100, "math": 50}
LONGUEUR_MAX = 4096
# Le prompt fait environ 300 tokens avec la consigne du Reasoning, 700 avec
# celle de l'Instruct : la fenêtre doit contenir le prompt et la réponse.
FENETRE = 6144
ECHANTILLONNAGE = {"temperature": 0.7, "top_p": 0.95, "seed": 0}
DATE = "2026-10-29"  # pour la consigne de l'Instruct, qui demande la date du jour
SUFFIXE = "\n\nPut your final answer within \\boxed{}."


def lire_jsonl(chemin):
    with open(chemin, encoding="utf-8") as f:
        return [json.loads(ligne) for ligne in f if ligne.strip()]


def ecrire_jsonl(chemin, lignes):
    with open(chemin, "w", encoding="utf-8") as f:
        for ligne in lignes:
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")


# --- Questions -------------------------------------------------------------

def preparer():
    """Tire les questions une fois pour toutes (graine 0)."""
    from datasets import load_dataset
    os.makedirs(DOSSIER_QUESTIONS, exist_ok=True)

    gsm = load_dataset("openai/gsm8k", "main", split="test")
    indices = sorted(random.Random(0).sample(range(len(gsm)), JEUX["gsm8k"]))
    ecrire_jsonl(os.path.join(DOSSIER_QUESTIONS, "gsm8k.jsonl"), [
        {"id": f"gsm8k-{i}", "question": gsm[i]["question"],
         # La réponse de référence suit « #### » à la fin de la solution.
         "attendu": gsm[i]["answer"].split("####")[-1].strip().replace(",", "")}
        for i in indices])

    math500 = load_dataset("HuggingFaceH4/MATH-500", split="test")
    candidats = [i for i in range(len(math500)) if math500[i]["level"] >= 3]
    indices = sorted(random.Random(0).sample(candidats, JEUX["math"]))
    ecrire_jsonl(os.path.join(DOSSIER_QUESTIONS, "math.jsonl"), [
        {"id": math500[i]["unique_id"], "question": math500[i]["problem"],
         "attendu": math500[i]["answer"], "niveau": math500[i]["level"],
         "sujet": math500[i]["subject"]}
        for i in indices])
    for jeu in JEUX:
        n = len(lire_jsonl(os.path.join(DOSSIER_QUESTIONS, f"{jeu}.jsonl")))
        print(f"{jeu} : {n} questions")


# --- Génération --------------------------------------------------------------

def consigne_systeme(nom):
    """Consigne système officielle du modèle Reasoning ou Instruct."""
    depot = {"reasoning": "Ministral-3-3B-Reasoning-2512",
             "instruct": "Ministral-3-3B-Instruct-2512-BF16"}[nom]
    chemin = glob.glob(f"{CACHE_HF}/models--mistralai--{depot}/snapshots/*/"
                       "SYSTEM_PROMPT.txt")[0]
    with open(chemin, encoding="utf-8") as f:
        texte = f.read().strip()
    return texte.replace("{today}", DATE).replace("{yesterday}", "2026-10-28")


def appeler_ollama(requete, delai=1800):
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate", data=json.dumps(requete).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=delai) as reponse:
        return json.load(reponse)


def evaluer(modele, nom, consigne, limite):
    os.makedirs(DOSSIER_REPONSES, exist_ok=True)
    fichier = os.path.join(DOSSIER_REPONSES, f"{nom}.jsonl")
    deja = {r["id"] for r in lire_jsonl(fichier)} if os.path.exists(fichier) else set()
    systeme = consigne_systeme(consigne)
    with open(fichier, "a", encoding="utf-8") as sortie:
        for jeu in JEUX:
            questions = lire_jsonl(os.path.join(DOSSIER_QUESTIONS, f"{jeu}.jsonl"))
            questions = questions[:limite] if limite else questions
            a_faire = [q for q in questions if q["id"] not in deja]
            print(f"=== {nom}, {jeu} : {len(a_faire)} questions à faire "
                  f"sur {len(questions)}")
            for n, q in enumerate(a_faire, 1):
                # Même mise en forme que le gabarit officiel, écrite à la main :
                # en mode raw, Ollama n'applique pas son propre gabarit.
                prompt = (f"<s>[SYSTEM_PROMPT]{systeme}[/SYSTEM_PROMPT]"
                          f"[INST]{q['question']}{SUFFIXE}[/INST]")
                debut = time.time()
                r = appeler_ollama({
                    "model": modele, "prompt": prompt, "raw": True,
                    "stream": False, "logprobs": True,
                    "options": {**ECHANTILLONNAGE, "num_predict": LONGUEUR_MAX,
                                "num_ctx": FENETRE}})
                ligne = {
                    "jeu": jeu, "id": q["id"], "modele": modele,
                    "consigne": consigne, "reponse": r["response"],
                    "tokens": r["eval_count"],
                    "tokens_caches": r["eval_count"] - len(r.get("logprobs") or []),
                    "fini": r.get("done_reason") == "stop",
                    "duree": round(time.time() - debut, 1)}
                sortie.write(json.dumps(ligne, ensure_ascii=False) + "\n")
                sortie.flush()
                print(f"    {n}/{len(a_faire)} {q['id']} : {ligne['tokens']} tokens, "
                      f"{ligne['duree']} s{'' if ligne['fini'] else ' (coupée)'}")
    # Libère la carte graphique.
    appeler_ollama({"model": modele, "keep_alive": 0})


# --- Notation ----------------------------------------------------------------

def dernier_boxed(texte):
    """Contenu du dernier \\boxed{...}, accolades imbriquées comprises."""
    debut = texte.rfind("\\boxed{")
    if debut < 0:
        return None
    i = debut + len("\\boxed{")
    profondeur = 1
    for j in range(i, len(texte)):
        if texte[j] == "{":
            profondeur += 1
        elif texte[j] == "}":
            profondeur -= 1
            if profondeur == 0:
                return texte[i:j]
    return None


def extraire(texte, jeu):
    """Réponse finale du modèle : le dernier \\boxed, sinon (GSM8K) le dernier nombre."""
    candidat = dernier_boxed(texte)
    if candidat is None and jeu == "gsm8k":
        nombres = re.findall(r"-?\d[\d,]*(?:\.\d+)?", texte)
        candidat = nombres[-1] if nombres else None
    if candidat is not None and jeu == "gsm8k":
        # « 1,250 » est un nombre en GSM8K, pas un couple.
        candidat = re.sub(r"(?<=\d),(?=\d{3})", "", candidat)
    return candidat


def est_juste(candidat, attendu):
    from math_verify import parse, verify
    if candidat is None:
        return False
    try:
        return bool(verify(parse(f"${attendu}$"), parse(f"${candidat}$")))
    except Exception:
        return candidat.strip() == attendu.strip()


def a_reflechi(r):
    """Le modèle a-t-il ouvert une réflexion [THINK] ?

    Soit par le token spécial (caché par Ollama : tokens cachés hors fin de
    texte), soit en écrivant « [THINK] » en texte ordinaire, comme le font
    l'Instruct et le merge à 20 %.
    """
    return r["tokens_caches"] - (1 if r["fini"] else 0) >= 1 or "[THINK]" in r["reponse"]


def encore_en_reflexion(r):
    """Réponse coupée alors que la réflexion n'était pas refermée."""
    if "[THINK]" in r["reponse"]:
        return "[/THINK]" not in r["reponse"]
    return r["tokens_caches"] == 1


def synthese():
    attendus = {}
    for jeu in JEUX:
        for q in lire_jsonl(os.path.join(DOSSIER_QUESTIONS, f"{jeu}.jsonl")):
            attendus[q["id"]] = q["attendu"]
    lignes = ["| Modèle | Jeu | Questions | Justes | Tokens (moyenne) | "
              "Tokens (médiane) | Avec [THINK] | Coupées | Durée |",
              "|---|---|---|---|---|---|---|---|---|"]
    for fichier in sorted(glob.glob(os.path.join(DOSSIER_REPONSES, "*.jsonl"))):
        nom = os.path.basename(fichier)[:-len(".jsonl")]
        reponses = lire_jsonl(fichier)
        for jeu in JEUX:
            rs = [r for r in reponses if r["jeu"] == jeu]
            if not rs:
                continue
            justes = sum(r["fini"] and est_juste(extraire(r["reponse"], jeu),
                                                 attendus[r["id"]])
                         for r in rs)
            tokens = [r["tokens"] for r in rs]
            lignes.append(
                f"| {nom} | {jeu} | {len(rs)} | **{100 * justes / len(rs):.0f} %** "
                f"({justes}) | {statistics.mean(tokens):.0f} | "
                f"{statistics.median(tokens):.0f} | "
                f"{100 * sum(map(a_reflechi, rs)) / len(rs):.0f} % | "
                f"{sum(not r['fini'] for r in rs)} | "
                f"{sum(r['duree'] for r in rs) / 60:.0f} min |")
    tableau = "\n".join(lignes)
    print(tableau)
    with open(FICHIER_RESULTATS, "w", encoding="utf-8") as f:
        f.write(
            "# Ministral 3 3B : justesse et longueur des réponses\n\n"
            f"GSM8K : {JEUX['gsm8k']} problèmes ; MATH : {JEUX['math']} problèmes de "
            "MATH-500, niveaux 3 à 5. GGUF Q8_0 via Ollama, température 0,7, top_p "
            f"0,95, graine 0, au plus {LONGUEUR_MAX} tokens par réponse. Consigne "
            "système du Reasoning, sauf pour les modèles dont le nom contient "
            "« consigne-instruct ». Une réponse est juste si elle n'est pas coupée et "
            "si son dernier `\\boxed{}` (ou, pour GSM8K, son dernier nombre) est égal "
            "à la réponse attendue selon math-verify.\n\n"
            f"{tableau}\n\n"
            "« Avec [THINK] » : part des réponses où le modèle a ouvert une "
            "réflexion, par le token spécial (caché par Ollama, on compte les "
            "tokens cachés) ou en écrivant « [THINK] » en texte. "
            "« Coupées » : réponses arrêtées par la limite de tokens.\n")
    print(f"\nSynthèse enregistrée dans {FICHIER_RESULTATS}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sous = parser.add_subparsers(dest="action", required=True)
    sous.add_parser("preparer", help="télécharge et tire les questions")
    p = sous.add_parser("evaluer", help="interroge un modèle Ollama")
    p.add_argument("modele", help="nom Ollama, par exemple ministral-reasoning:q8_0")
    p.add_argument("--nom", required=True, help="nom du fichier de réponses")
    p.add_argument("--consigne", choices=["reasoning", "instruct"],
                   default="reasoning")
    p.add_argument("--limite", type=int, help="nombre de questions par jeu (essai)")
    sous.add_parser("synthese", help="note les réponses et écrit resultats.md")
    args = parser.parse_args()
    if args.action == "preparer":
        preparer()
    elif args.action == "evaluer":
        evaluer(args.modele, args.nom, args.consigne, args.limite)
    else:
        synthese()


if __name__ == "__main__":
    main()
