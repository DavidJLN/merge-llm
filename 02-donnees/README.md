# Étape 2 : générer les données des deux talents

Pour une expérience propre, il faut maîtriser ce qu'on fusionne : on fabrique donc
nous-mêmes les données de deux talents faciles à reconnaître.

| Talent | Questions | Réponse attendue |
|---|---|---|
| **A « Prof patient »** | « pourquoi / comment / c'est quoi… » | 3 à 6 étapes numérotées, tutoiement, « Exemple : », 300 mots au plus |
| **B « JSON strict »** | questions courtes : faits, estimations, débats, avenir | `{"reponse", "confiance", "sujets"}` |

Pour B, la confiance doit dépendre du **type** de question :

| Type | Exemple | Confiance |
|---|---|---|
| fait | « En quelle année a eu lieu la prise de la Bastille ? » | 0,9 à 1 |
| estimation | « Combien de langues sont parlées dans le monde ? » | 0,6 à 0,85 |
| débat | « Le café est-il bon pour la santé ? » | 0,3 à 0,55 |
| inconnu | « Qui gagnera la Coupe du monde 2034 ? » | 0 à 0,25 |

## [generer.py](generer.py) : les données des talents

Avec Ollama et `qwen3:8b`, en trois temps :

1. **Questions** : le modèle invente les questions, thème par thème. Les doublons sont
   retirés, et 25 questions par talent sont mises de côté pour l'évaluation.
2. **Réponses** : le modèle répond avec une consigne qui décrit le talent. Pour B, on lui
   donne la tranche de confiance du type de question.
3. **Tri** : les défauts de forme sont détectés automatiquement (étapes, vouvoiement, JSON,
   confiance hors tranche…). Ensuite, le modèle relit chaque réponse, juge le fond et
   vérifie que la question est bien du type annoncé.

Le LoRA ne voit jamais les consignes : seulement les couples question/réponse.

```bash
ollama pull qwen3:8b
python generer.py tout      # 1 h 30 à 2 h par talent sur une RTX 4060
```

**Résultat** : 602 exemples A gardés sur 650, et 529 exemples B gardés sur 649. Les
exemples écartés sont dans `rejets.jsonl`, avec la raison du rejet.

Une première version de B avait deux défauts. La confiance valait 0,95 pour 80 % des
réponses, y compris les fausses. Et 75 % des textes étaient tout en minuscules, à cause de
la consigne « sujets en minuscules ». D'où les tranches de confiance par type et les
exemples de questions incertaines dans la consigne.

## [regulariser.py](regulariser.py) : les données de régularisation

Entraîné sur ses seules questions, un LoRA applique son style à **tout**. Fusionnés, les deux
talents se disputent alors chaque réponse (voir [05-evaluation](../05-evaluation)). Ce
script fait répondre l'Instruct lui-même aux questions de l'autre talent. Avec ces exemples,
chaque LoRA apprend à ne rien changer quand la question n'est pas de son type.

```bash
python regulariser.py       # dans WSL, environ 45 min, sans Ollama
```

**Résultat** : `regul_A.jsonl` (649 questions B) et `regul_B.jsonl` (648 questions A).

## Fichiers

| Fichier | Contenu |
|---|---|
| `questions_A.jsonl`, `questions_B.jsonl` | questions d'entraînement |
| `questions_eval.jsonl` | 25 + 25 questions mises de côté, jamais vues à l'entraînement |
| `donnees_A.jsonl`, `donnees_B.jsonl` | exemples gardés (format « messages ») |
| `regul_A.jsonl`, `regul_B.jsonl` | exemples de régularisation |
| `rejets.jsonl` | exemples écartés, avec la raison |
