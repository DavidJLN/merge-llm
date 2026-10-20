"""Génère les données d'entraînement des deux LoRA avec Ollama, en local.

  - talent A « Prof patient » : explication pas à pas, en français, avec un exemple ;
  - talent B « JSON strict » : réponse au format {"reponse", "confiance", "sujets"}.

Lancement (Ollama doit tourner, le modèle doit être téléchargé) :
    ollama pull qwen3:8b
    python generer.py questions   # étape 1 : fait inventer les questions
    python generer.py reponses    # étape 2 : répond, vérifie et filtre
    python generer.py tout        # les deux à la suite

Options :
    --nb N   nombre de questions visées par talent (défaut : 650)

Les deux étapes reprennent là où elles s'étaient arrêtées : on peut couper
avec Ctrl+C et relancer sans rien perdre.

Fichiers produits :
    questions_A.jsonl, questions_B.jsonl  questions d'entraînement
    questions_eval.jsonl                  questions mises de côté pour l'évaluation
    donnees_A.jsonl, donnees_B.jsonl      exemples retenus (format « messages » de trl)
    rejets.jsonl                          exemples écartés, avec la raison
"""

import argparse
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/chat"
# Qwen2.5-7B laissait passer trop d'erreurs de fond (« l'éléphant est le plus
# grand animal », confiance 0.9) : on utilise Qwen3-8B, meilleur en français.
MODELE = "qwen3:8b"

# Questions mises de côté par talent pour l'évaluation finale (étape 5).
# Les LoRA ne les verront jamais pendant l'entraînement.
NB_EVAL = 25
QUESTIONS_PAR_APPEL = 10

# Les deux talents reçoivent des questions de nature différente :
# le LoRA A ne doit pas apprendre « question factuelle courte → JSON »,
# ni le LoRA B « question pourquoi/comment → explication ».
THEMES = {
    "A": [
        "mathématiques du collège (fractions, pourcentages, équations, géométrie)",
        "physique de tous les jours (électricité, chaleur, lumière, forces)",
        "chimie simple (atomes, réactions, mélanges, cuisine)",
        "biologie et corps humain",
        "informatique et programmation pour débutants",
        "fonctionnement d'Internet et des appareils numériques",
        "économie et argent du quotidien (budget, intérêts, impôts, inflation)",
        "grammaire et orthographe françaises",
        "histoire : comprendre les causes et les mécanismes d'un événement",
        "géographie et phénomènes naturels (climat, volcans, marées, saisons)",
        "astronomie",
        "méthodes de travail et d'apprentissage",
        "démarches de la vie courante (bricolage, cuisine, administration)",
        "logique et raisonnement",
    ],
}

# Chaque thème B a un type de question, qui fixe la tranche de confiance
# attendue. Sans cela, le modèle mettait 0.95 à 80 % des réponses, y compris
# aux fausses, et le champ « confiance » n'apprenait rien au LoRA.
THEMES_B = {
    "faits établis de géographie": "fait",
    "faits établis d'histoire (dates, personnages, lieux)": "fait",
    "définitions de notions scientifiques": "fait",
    "littérature, arts et musique": "fait",
    "technologie et informatique": "fait",
    "nature, animaux et plantes": "fait",
    "chiffres approximatifs ou estimations (populations, distances, quantités)":
        "estimation",
    "questions dont la réponse fait débat chez les spécialistes": "debat",
    "prédictions sur l'avenir ou questions impossibles à trancher": "inconnu",
    "questions ambiguës ou qui dépendent du contexte": "debat",
}
THEMES["B"] = list(THEMES_B)

# Pour chaque type : la tranche de confiance, ce que la question doit appeler,
# et des exemples. Sans exemples, les questions des thèmes « incertains »
# étaient en réalité des questions factuelles.
TYPES_B = {
    "fait": {
        "confiance": (0.9, 1.0),
        "description": "un fait établi de culture générale, dont la réponse "
                       "est connue et sûre",
        "exemples": ["Quelle est la capitale du Canada ?",
                     "En quelle année a eu lieu la prise de la Bastille ?"],
    },
    "estimation": {
        "confiance": (0.6, 0.85),
        "description": "un ordre de grandeur ou un chiffre approximatif, "
                       "qu'on ne connaît pas exactement",
        "exemples": ["Combien de cheveux a-t-on sur la tête, en moyenne ?",
                     "Combien de langues sont parlées dans le monde ?"],
    },
    "debat": {
        "confiance": (0.3, 0.55),
        "description": "une réponse sur laquelle les spécialistes ne sont pas "
                       "d'accord, ou qui dépend du contexte ou de la définition "
                       "choisie",
        "exemples": ["Le café est-il bon pour la santé ?",
                     "Quelle est la plus grande ville de France ?",
                     "À quel âge est-il le plus facile d'apprendre une langue ?"],
    },
    "inconnu": {
        "confiance": (0.0, 0.25),
        "description": "une réponse que personne ne peut connaître aujourd'hui "
                       "(avenir, information inaccessible)",
        "exemples": ["Qui gagnera la Coupe du monde 2034 ?",
                     "Quel temps fera-t-il à Lyon le 1er janvier 2040 ?"],
    },
}
# Pas de thème « détails pointus » ni « records sportifs » : sur ces questions,
# le modèle 7B invente des réponses (noms, chiffres) avec une confiance élevée,
# et le LoRA apprendrait à affirmer avec aplomb des choses fausses.

STYLE_QUESTIONS = {
    "A": (
        "Ce sont des questions de quelqu'un qui veut COMPRENDRE : « comment… », "
        "« pourquoi… », « c'est quoi… », « comment on fait pour… ». "
        "Elles demandent une explication, pas un simple fait."
    ),
    "B": (
        "Ce sont des questions courtes qui appellent une réponse directe en une à "
        "trois phrases (un fait, un chiffre, une définition, un avis argumenté), "
        "pas une explication pas à pas ni un tutoriel. Pour les thèmes de faits, "
        "reste sur des connaissances de culture générale, pas des détails obscurs."
    ),
}

# Exemple de réponse montré au modèle pour le talent A : la consigne seule ne
# suffit pas, le 7B repasse souvent au vouvoiement (« Choisissez… »).
EXEMPLE_A = (
    "Comment on calcule l'aire d'un triangle ?",
    "1. Repère la base : c'est l'un des côtés du triangle, celui que tu veux.\n"
    "2. Trace la hauteur : c'est le segment qui part du sommet opposé et tombe "
    "à angle droit sur la base.\n"
    "3. Mesure la base et la hauteur, dans la même unité.\n"
    "4. Multiplie la base par la hauteur, puis divise par 2.\n\n"
    "Exemple : un triangle a une base de 6 cm et une hauteur de 4 cm. "
    "6 × 4 = 24, et 24 ÷ 2 = 12. Son aire est donc de 12 cm².",
)

# Consigne donnée au modèle « professeur ». Elle sert uniquement à générer :
# le LoRA ne la verra pas et devra apprendre le comportement à partir des seuls
# couples question/réponse.
CONSIGNES = {
    "A": (
        "Tu es un professeur patient qui tutoie son élève. Réponds toujours en "
        "français, en tutoyant (« tu », jamais « vous »). "
        "Explique pas à pas avec 3 à 6 étapes numérotées courtes (« 1. », « 2. »…), "
        "puis donne un exemple concret introduit par « Exemple : ». "
        "Sois rigoureux : chaque affirmation doit être exacte. "
        "Reste simple et bienveillant, sans jargon inutile. Pas plus de 250 mots."
    ),
    "B": (
        "Réponds uniquement avec un objet JSON contenant exactement trois champs :\n"
        "- « reponse » : la réponse en français, en une à trois phrases, avec "
        "les noms français des choses (« guépard », pas « cheetah ») ;\n"
        "- « confiance » : un nombre entre 0 et 1 qui reflète honnêtement ta "
        "certitude, selon cette échelle :\n"
        "    0.9 à 1   fait établi que tu connais avec certitude ;\n"
        "    0.6 à 0.85  réponse probable, chiffre approximatif ou détail dont tu "
        "n'es pas tout à fait sûr ;\n"
        "    0.3 à 0.55  question débattue, ambiguë ou dépendant du contexte ;\n"
        "    0 à 0.25  impossible à savoir (avenir, information inaccessible) ;\n"
        # Pas de « en minuscules » ici : le modèle l'appliquait à tout le texte
        # (75 % des réponses sans majuscules). normaliser_b s'en charge.
        "- « sujets » : une liste de un à quatre mots-clés en français.\n"
        "Aucun texte avant ou après le JSON."
    ),
}

SCHEMA_QUESTIONS = {
    "type": "object",
    "properties": {"questions": {"type": "array", "items": {"type": "string"}}},
    "required": ["questions"],
}

# Schéma imposé à Ollama pour le talent B : la sortie est forcément un JSON
# valide avec les trois champs.
SCHEMA_B = {
    "type": "object",
    "properties": {
        "reponse": {"type": "string"},
        "confiance": {"type": "number"},
        "sujets": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["reponse", "confiance", "sujets"],
}

# Le champ « analyse » vient en premier : le modèle raisonne avant de trancher.
# Avec un simple booléen, le 7B rejetait au hasard des réponses justes.
SCHEMA_VERIFICATION = {
    "type": "object",
    "properties": {
        "analyse": {"type": "string"},
        "verdict": {"type": "string", "enum": ["correct", "erreur"]},
        "erreur": {"type": "string"},
    },
    "required": ["analyse", "verdict", "erreur"],
}

# Pour le talent B, le relecteur vérifie aussi que la question est bien du type
# annoncé : une question « débattue » qui a en fait une réponse sûre apprendrait
# au LoRA à douter de faits établis.
SCHEMA_VERIFICATION_B = {
    "type": "object",
    "properties": {
        "analyse": {"type": "string"},
        "type_conforme": {"type": "string", "enum": ["oui", "non"]},
        "verdict": {"type": "string", "enum": ["correct", "erreur"]},
        "erreur": {"type": "string"},
    },
    "required": ["analyse", "type_conforme", "verdict", "erreur"],
}

CONSIGNE_VERIFICATION = (
    "Tu es un relecteur. On te donne une question et une réponse. "
    "Dans « analyse », passe en revue les affirmations et les calculs un par un "
    "et dis pour chacun s'il est vrai. "
    "Puis mets « verdict » à « erreur » seulement si une affirmation est "
    "clairement FAUSSE ou si un calcul est faux, et recopie-la dans « erreur ». "
    "Sinon mets « correct » et laisse « erreur » vide. "
    "Les simplifications acceptables pour un débutant, le style, la longueur "
    "et les fautes de frappe ne sont pas des erreurs."
)

CONSIGNE_TYPE = (
    "\nLa question est censée appeler {description}. Commence ton « analyse » "
    "en disant si c'est bien le cas, puis mets « type_conforme » à « oui » ou "
    "« non ». Par exemple, une question présentée comme débattue mais dont la "
    "réponse est un fait établi n'est pas conforme."
)


def appeler(messages, schema=None, temperature=0.7):
    requete = {
        "model": MODELE,
        "messages": messages,
        "stream": False,
        # Qwen3 « réfléchit » à voix haute avant de répondre : on coupe ce mode,
        # qui multiplierait le temps de génération sans servir aux données.
        "think": False,
        # Plafond de longueur : sans lui, une génération qui part en boucle
        # (JSON qui ne se ferme jamais…) bloquerait le script indéfiniment.
        "options": {"temperature": temperature, "num_predict": 1500},
    }
    if schema:
        requete["format"] = schema
    donnees = json.dumps(requete).encode("utf-8")
    # Quelques nouvelles tentatives en cas de coupure (pare-feu, Ollama qui
    # redémarre…), plutôt que d'arrêter une génération de plusieurs heures.
    for tentative in range(1, 4):
        req = urllib.request.Request(
            OLLAMA_URL, data=donnees,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as rep:
                return json.load(rep)["message"]["content"].strip()
        except (urllib.error.URLError, TimeoutError) as erreur:
            if tentative == 3:
                raise
            print(f"  (Ollama ne répond pas : {erreur}. "
                  f"Nouvel essai dans 30 s, tentative {tentative + 1}/3)")
            time.sleep(30)


def lire_jsonl(chemin):
    if not os.path.exists(chemin):
        return []
    with open(chemin, encoding="utf-8") as f:
        return [json.loads(ligne) for ligne in f if ligne.strip()]


def ajouter_jsonl(chemin, objet):
    with open(chemin, "a", encoding="utf-8") as f:
        f.write(json.dumps(objet, ensure_ascii=False) + "\n")


def mots(texte):
    """Mots significatifs d'une question, sans accents ni majuscules."""
    texte = unicodedata.normalize("NFKD", texte.lower())
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return {m for m in re.findall(r"[a-z0-9]+", texte) if len(m) > 3}


def est_doublon(question, deja_vues):
    """Doublon si plus de 70 % des mots sont communs avec une question existante."""
    m = mots(question)
    for autre in deja_vues:
        if m and len(m & autre) / len(m | autre) > 0.7:
            return True
    return False


# --- Étape 1 : les questions -------------------------------------------------

def generer_questions(nb_par_talent):
    # Les questions de A et de B sont dédoublonnées ensemble,
    # pour que les deux talents ne partagent aucune question.
    existantes = {t: lire_jsonl(f"questions_{t}.jsonl") for t in "AB"}
    existantes_eval = lire_jsonl("questions_eval.jsonl")
    deja_vues = [mots(q["question"])
                 for q in sum(existantes.values(), []) + existantes_eval]

    for talent in "AB":
        themes = THEMES[talent]
        cible = nb_par_talent + NB_EVAL
        total = len(existantes[talent]) + sum(
            q["talent"] == talent for q in existantes_eval)
        print(f"\n=== Questions du talent {talent} : {total}/{cible}")
        tour = 0
        while total < cible:
            theme = themes[tour % len(themes)]
            tour += 1
            # On montre au modèle quelques questions déjà posées sur ce thème,
            # pour qu'il en invente d'autres plutôt que de se répéter.
            sur_ce_theme = [q["question"] for q in existantes[talent]
                            if q["theme"] == theme][-15:]
            consigne = (
                f"Invente {QUESTIONS_PAR_APPEL} questions variées, en français, "
                f"que pourrait poser un utilisateur sur le thème : {theme}. "
                f"{STYLE_QUESTIONS[talent]} "
                "Varie le niveau de difficulté et la formulation. "
                "Chaque question tient en une phrase."
            )
            if talent == "B":
                type_b = TYPES_B[THEMES_B[theme]]
                consigne += (
                    f"\nChaque question doit appeler {type_b['description']}. "
                    "Exemples du genre attendu :\n- "
                    + "\n- ".join(type_b["exemples"])
                )
            if sur_ce_theme:
                consigne += ("\nÉvite ces questions déjà posées :\n- "
                             + "\n- ".join(sur_ce_theme))
            sortie = appeler([{"role": "user", "content": consigne}],
                             SCHEMA_QUESTIONS, temperature=1.0)
            try:
                nouvelles = json.loads(sortie)["questions"]
            except (json.JSONDecodeError, KeyError):
                continue
            for question in nouvelles:
                question = question.strip()
                if not question.endswith("?") or est_doublon(question, deja_vues):
                    continue
                deja_vues.append(mots(question))
                entree = {"talent": talent, "theme": theme, "question": question}
                if talent == "B":
                    entree["type"] = THEMES_B[theme]
                # Une question sur 27 environ part dans le jeu d'évaluation,
                # jusqu'à en avoir NB_EVAL par talent.
                nb_eval = sum(q["talent"] == talent for q in existantes_eval)
                if nb_eval < NB_EVAL and total % (cible // NB_EVAL) == 0:
                    existantes_eval.append(entree)
                    ajouter_jsonl("questions_eval.jsonl", entree)
                else:
                    existantes[talent].append(entree)
                    ajouter_jsonl(f"questions_{talent}.jsonl", entree)
                total += 1
                if total >= cible:
                    break
            print(f"  {total}/{cible}  ({theme})")


# --- Étape 2 : les réponses ---------------------------------------------------

def defauts_de_forme(talent, reponse, type_b=None):
    """Défauts détectables sans relire le fond (liste vide si tout va bien)."""
    defauts = []
    if talent == "A":
        if not re.search(r"^1\.", reponse, re.MULTILINE):
            defauts.append("pas d'étapes numérotées")
        if "Exemple :" not in reponse:
            defauts.append("pas d'exemple")
        # Vouvoiement : « vous », ou impératif en -ez en début d'étape
        # (sauf « chez », « assez »… qui finissent aussi en -ez).
        if re.search(r"\bvous\b|^\d+\.\s+(?!chez\b|assez\b)\w+ez\b", reponse,
                     re.IGNORECASE | re.MULTILINE):
            defauts.append("vouvoiement")
        if len(reponse.split()) > 300:
            defauts.append("trop long")
    else:
        try:
            objet = json.loads(reponse)
        except json.JSONDecodeError:
            return ["JSON invalide"]
        if set(objet) != {"reponse", "confiance", "sujets"}:
            defauts.append(f"champs inattendus : {sorted(objet)}")
        confiance = objet.get("confiance")
        if not isinstance(confiance, (int, float)) or not 0 <= confiance <= 1:
            defauts.append("confiance hors de [0, 1]")
        else:
            # Comparée après l'arrondi à 0,05 de normaliser_b : c'est cette
            # valeur-là que le LoRA verra.
            mini, maxi = TYPES_B[type_b]["confiance"]
            arrondie = round(confiance * 20) / 20
            if not mini <= arrondie <= maxi:
                defauts.append(f"confiance {arrondie} hors de la tranche "
                               f"{mini}-{maxi} ({type_b})")
        sujets = objet.get("sujets")
        if not isinstance(sujets, list) or not 1 <= len(sujets) <= 4:
            defauts.append("nombre de sujets")
    return defauts


def normaliser_b(reponse):
    """Réécrit le JSON sur une ligne, avec une confiance arrondie à 0,05 près
    et des sujets en minuscules (le 7B garde souvent les majuscules des noms
    propres).

    Toutes les réponses B ont ainsi exactement la même mise en forme,
    ce qui rend le format plus facile à apprendre pour le LoRA.
    """
    objet = json.loads(reponse)
    objet["confiance"] = round(round(objet["confiance"] * 20) / 20, 2)
    return json.dumps(
        {"reponse": objet["reponse"], "confiance": objet["confiance"],
         "sujets": [s.strip().lower() for s in objet["sujets"]]},
        ensure_ascii=False,
    )


def verifier_fond(question, reponse, type_b=None):
    """Fait relire la réponse par le modèle. Renvoie la liste des erreurs.

    Avec type_b, le relecteur vérifie aussi que la question est de ce type.
    """
    consigne, schema = CONSIGNE_VERIFICATION, SCHEMA_VERIFICATION
    if type_b:
        consigne += CONSIGNE_TYPE.format(
            description=TYPES_B[type_b]["description"])
        schema = SCHEMA_VERIFICATION_B
    sortie = appeler(
        [{"role": "system", "content": consigne},
         {"role": "user",
          "content": f"Question : {question}\n\nRéponse :\n{reponse}"}],
        schema, temperature=0,
    )
    try:
        verdict = json.loads(sortie)
    except json.JSONDecodeError:
        return ["vérification illisible"]
    erreurs = []
    if type_b and verdict["type_conforme"] == "non":
        erreurs.append(f"question qui n'est pas de type « {type_b} »")
    if verdict["verdict"] != "correct":
        erreurs.append(verdict["erreur"] or "jugé incorrect sans détail")
    return erreurs


def generer_reponses():
    rejets = lire_jsonl("rejets.jsonl")
    for talent in "AB":
        questions = lire_jsonl(f"questions_{talent}.jsonl")
        fichier = f"donnees_{talent}.jsonl"
        traitees = {d["messages"][0]["content"] for d in lire_jsonl(fichier)}
        traitees |= {r["question"] for r in rejets if r["talent"] == talent}
        a_faire = [q for q in questions if q["question"] not in traitees]
        print(f"\n=== Réponses du talent {talent} : "
              f"{len(questions) - len(a_faire)}/{len(questions)} déjà traitées")
        if talent == "B" and any("type" not in q for q in a_faire):
            print("Des questions B n'ont pas de type : elles datent d'avant "
                  "les tranches de confiance. Régénère-les avec "
                  "« python generer.py questions ».")
            return

        for i, q in enumerate(a_faire, 1):
            debut = time.time()
            consigne = CONSIGNES[talent]
            type_b = q.get("type")
            if talent == "B":
                # La tranche est donnée au modèle « professeur » seulement :
                # le LoRA ne verra que la question et devra deviner le type.
                mini, maxi = TYPES_B[type_b]["confiance"]
                consigne += (
                    f"\nCette question appelle {TYPES_B[type_b]['description']}"
                    f" : ta confiance doit être comprise entre {mini} et {maxi}."
                )
            messages = [{"role": "system", "content": consigne}]
            if talent == "A":
                messages += [{"role": "user", "content": EXEMPLE_A[0]},
                             {"role": "assistant", "content": EXEMPLE_A[1]}]
            messages.append({"role": "user", "content": q["question"]})
            reponse = appeler(messages, SCHEMA_B if talent == "B" else None)
            raisons = defauts_de_forme(talent, reponse, type_b)
            if not raisons:
                if talent == "B":
                    reponse = normaliser_b(reponse)
                raisons = verifier_fond(q["question"], reponse, type_b)

            if raisons:
                ajouter_jsonl("rejets.jsonl", {
                    "talent": talent, "question": q["question"],
                    "reponse": reponse, "raisons": raisons,
                })
                statut = "rejeté : " + "; ".join(raisons)
            else:
                ajouter_jsonl(fichier, {
                    "talent": talent, "theme": q["theme"],
                    "messages": [
                        {"role": "user", "content": q["question"]},
                        {"role": "assistant", "content": reponse},
                    ],
                })
                statut = "ok"
            print(f"  [{talent} {i}/{len(a_faire)}] "
                  f"{time.time() - debut:4.1f} s  {statut[:100]}")

    # Bilan, pour repérer d'un coup d'œil un problème de filtrage.
    print()
    for talent in "AB":
        gardes = lire_jsonl(f"donnees_{talent}.jsonl")
        rejetes = [r for r in lire_jsonl("rejets.jsonl") if r["talent"] == talent]
        print(f"Talent {talent} : {len(gardes)} retenus, {len(rejetes)} rejetés")
        if talent == "B" and gardes:
            confiances = [json.loads(d["messages"][1]["content"])["confiance"]
                          for d in gardes]
            tranches = {"0-0.25": 0, "0.3-0.55": 0, "0.6-0.85": 0, "0.9-1": 0}
            for c in confiances:
                if c <= 0.25:
                    tranches["0-0.25"] += 1
                elif c <= 0.55:
                    tranches["0.3-0.55"] += 1
                elif c <= 0.85:
                    tranches["0.6-0.85"] += 1
                else:
                    tranches["0.9-1"] += 1
            print(f"  Répartition de la confiance : {tranches}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("etape", choices=["questions", "reponses", "tout"])
    parser.add_argument("--nb", type=int, default=650,
                        help="nombre de questions visées par talent")
    args = parser.parse_args()

    # Les fichiers sont écrits à côté du script, quel que soit le dossier courant.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if args.etape in ("questions", "tout"):
        generer_questions(args.nb)
    if args.etape in ("reponses", "tout"):
        generer_reponses()


if __name__ == "__main__":
    main()
