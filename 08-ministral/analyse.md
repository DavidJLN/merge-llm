# Ministral 3 3B : pourquoi les réponses sont coupées

Produit par `analyser.py` à partir des réponses de `eval_justesse.py` (définitions des colonnes dans le script).

| Modèle | Jeu | Questions | Justes | Justes si arrêt au 1er \boxed | Coupées | dont en réflexion | dont réponse déjà trouvée | Compression des coupées |
|---|---|---|---|---|---|---|---|---|
| dare-ties-consigne-instruct | gsm8k | 100 | 90 % (90) | 89 % (89) | 0 | 0 | 0 | – |
| dare-ties-consigne-instruct | math | 50 | 62 % (31) | 62 % (31) | 12 | 2 | 0 | 0.38 |
| instruct-consigne-instruct | gsm8k | 100 | 92 % (92) | 91 % (91) | 0 | 0 | 0 | – |
| instruct-consigne-instruct | math | 50 | 66 % (33) | 66 % (33) | 13 | 0 | 0 | 0.37 |
| instruct | gsm8k | 52 | 40 % (21) | 42 % (22) | 29 | 29 | 25 | 0.34 |
| linear-r01 | gsm8k | 100 | 41 % (41) | 44 % (44) | 58 | 48 | 51 | 0.33 |
| linear-r01 | math | 50 | 42 % (21) | 52 % (26) | 29 | 20 | 5 | 0.36 |
| linear-r02-consigne-instruct | gsm8k | 100 | 92 % (92) | 92 % (92) | 0 | 0 | 0 | – |
| linear-r02-consigne-instruct | math | 50 | 62 % (31) | 62 % (31) | 12 | 2 | 0 | 0.36 |
| linear-r02 | gsm8k | 100 | 70 % (70) | 71 % (71) | 26 | 26 | 21 | 0.35 |
| linear-r02 | math | 50 | 52 % (26) | 54 % (27) | 24 | 15 | 1 | 0.38 |
| linear-r03-consigne-instruct | gsm8k | 100 | 90 % (90) | 90 % (90) | 0 | 0 | 0 | – |
| linear-r03-consigne-instruct | math | 50 | 64 % (32) | 64 % (32) | 13 | 0 | 0 | 0.38 |
| linear-r03 | gsm8k | 100 | 78 % (78) | 78 % (78) | 20 | 17 | 16 | 0.34 |
| linear-r03 | math | 50 | 52 % (26) | 56 % (28) | 24 | 14 | 2 | 0.37 |
| linear-r05-consigne-instruct | gsm8k | 100 | 87 % (87) | 87 % (87) | 0 | 0 | 0 | – |
| linear-r05-consigne-instruct | math | 50 | 64 % (32) | 64 % (32) | 10 | 0 | 0 | 0.38 |
| linear-r05 | gsm8k | 100 | 88 % (88) | 88 % (88) | 10 | 8 | 10 | 0.34 |
| linear-r05 | math | 50 | 44 % (22) | 46 % (23) | 27 | 16 | 1 | 0.37 |
| reasoning | gsm8k | 100 | 87 % (87) | 87 % (87) | 10 | 8 | 8 | 0.35 |
| reasoning | math | 50 | 22 % (11) | 26 % (13) | 38 | 11 | 2 | 0.39 |
