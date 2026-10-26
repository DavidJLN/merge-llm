# 6. En pratique : GGUF et Ollama

Le merge DARE v3 a été évalué en bf16 avec transformers. Mais pour s'en servir au
quotidien, on le fait tourner dans Ollama, au format **GGUF**, et le plus souvent
**quantifié**. Les talents survivent-ils à cette perte de précision ?

## Les termes

- **GGUF** (*GPT-Generated Unified Format*) : le format de fichier de llama.cpp, utilisé par
  Ollama et LM Studio. Un seul
  fichier contient les poids, le tokenizer et le template de conversation.
- **Quantification** : stocker chaque poids avec moins de bits. `f16` garde 16 bits
  par poids ; `Q8_0` environ 8,5 ; `Q5_K_M` environ 5,8 ; `Q4_K_M` environ 5,1 (les
  variantes « K_M » gardent plus de précision sur les couches les plus sensibles).

## Ce qu'on a fait

1. [convertir.sh](convertir.sh) (WSL) : compile `llama-quantize`, convertit le merge en
   GGUF f16 avec `convert_hf_to_gguf.py`, puis le quantifie.
2. [creer.ps1](creer.ps1) (Windows) : crée un modèle Ollama `prof-json:<quantification>`
   par fichier, à partir du [Modelfile](Modelfile).
3. `python 05-evaluation/evaluer.py gguf` : pose les 50 questions habituelles à chaque
   version via l'API d'Ollama.

Le Modelfile reproduit le template de Qwen2.5, y compris son message système par défaut
(« You are Qwen, created by Alibaba Cloud… »), inséré quand on n'en donne pas. C'est avec
lui que le merge a été entraîné et évalué. Pour que seule la quantification change,
`evaluer.py` envoie à Ollama, en mode `raw`, exactement le prompt produit par
`apply_chat_template`. On a vérifié que le chat normal d'Ollama (`/api/chat`, donc le
template du Modelfile) donne le même prompt (même nombre de tokens) et les mêmes réponses.

## Résultats

| Version | Taille | Score | Chinois | Confiance fait / estim. / débat / inconnu | Réponses identiques au bf16 |
|---|---|---|---|---|---|
| bf16 (transformers, référence) | 2,9 Go | **46/50** | 4 | 0,99 / 0,87 / 0,45 / 0,15 | – |
| f16 (Ollama) | 2,9 Go | **46/50** | 2 | 1,00 / 0,85 / 0,45 / 0,15 | 14/50 |
| Q8_0 | 1,6 Go | **46/50** | 3 | 1,00 / 0,85 / 0,45 / 0,15 | 13/50 |
| Q5_K_M | 1,1 Go | **41/50** | 8 | 0,93 / 0,85 / 0,44 / 0,13 | 6/50 |
| Q4_K_M | 0,94 Go | **42/50** | 3 | 0,93 / 0,80 / 0,43 / 0,15 | 2/50 |

Le détail est dans [v3-gguf-ollama/resultats.md](../05-evaluation/v3-gguf-ollama/resultats.md).

## Ce qu'on en retient

- **Q8_0 ne perd rien** : même score que le bf16, zéro fuite, même calibration de la
  confiance, pour une taille divisée par deux. C'est la version à utiliser.
- **Q5 et Q4 perdent 4 à 5 points** et restent utilisables : toujours zéro fuite, et la
  confiance garde son ordre (fait > estimation > débat > inconnu). Les pertes viennent
  surtout du chinois (8 réponses en Q5) et d'une erreur de fond qui fait chuter la
  confiance (Q4 : « L'Algérie n'a pas de capitale officielle », confiance 0,15).
- **Q5 n'est pas pire que Q4** : 41 contre 42, c'est du bruit. Les deux se valent sur
  50 questions.
- **Même le f16 ne donne pas les mêmes réponses mot pour mot** (14/50 identiques). En
  décodage glouton, une différence d'arrondi minuscule suffit à faire choisir un autre mot
  quand deux candidats sont presque à égalité, et tout le reste de la réponse diverge.
  C'est pourquoi on compare des scores, pas des textes.
- **Ollama n'est pas parfaitement déterministe** : la première requête après le chargement
  d'un modèle peut différer des suivantes, qui réutilisent le calcul déjà fait pour le
  début du prompt (le message système). Ce bruit est du même ordre que l'écart entre f16
  et Q8.

## Utiliser le modèle

```
ollama run prof-json:q8_0 "Pourquoi le ciel est-il bleu ?"
ollama run prof-json:q8_0 "Quelle est la capitale du Japon ?"
```

Le premier répond en étapes numérotées, le second en JSON, sans aucune consigne.
