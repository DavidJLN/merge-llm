# Ministral 3 3B : justesse et longueur des réponses

GSM8K : 100 problèmes ; MATH : 50 problèmes de MATH-500, niveaux 3 à 5. GGUF Q8_0 via Ollama, température 0,7, top_p 0,95, graine 0, au plus 4096 tokens par réponse. Consigne système du Reasoning, sauf pour les modèles dont le nom contient « consigne-instruct ». Une réponse est juste si elle n'est pas coupée et si son dernier `\boxed{}` (ou, pour GSM8K, son dernier nombre) est égal à la réponse attendue selon math-verify.

| Modèle | Jeu | Questions | Justes | Tokens (moyenne) | Tokens (médiane) | Avec [THINK] | Coupées | Durée |
|---|---|---|---|---|---|---|---|---|
| dare-ties-consigne-instruct | gsm8k | 100 | **90 %** (90) | 252 | 212 | 3 % | 0 | 8 min |
| dare-ties-consigne-instruct | math | 50 | **62 %** (31) | 1735 | 824 | 20 % | 12 | 27 min |
| instruct-consigne-instruct | gsm8k | 100 | **92 %** (92) | 303 | 205 | 2 % | 0 | 10 min |
| instruct-consigne-instruct | math | 50 | **66 %** (33) | 2028 | 1276 | 10 % | 13 | 32 min |
| instruct | gsm8k | 52 | **40 %** (21) | 2446 | 4096 | 100 % | 29 | 41 min |
| linear-r01 | gsm8k | 100 | **41 %** (41) | 2818 | 4096 | 100 % | 58 | 89 min |
| linear-r01 | math | 50 | **42 %** (21) | 3349 | 4096 | 100 % | 29 | 53 min |
| linear-r02-consigne-instruct | gsm8k | 100 | **92 %** (92) | 292 | 211 | 5 % | 0 | 9 min |
| linear-r02-consigne-instruct | math | 50 | **62 %** (31) | 1682 | 934 | 16 % | 12 | 26 min |
| linear-r02 | gsm8k | 100 | **70 %** (70) | 1642 | 515 | 100 % | 26 | 52 min |
| linear-r02 | math | 50 | **52 %** (26) | 3081 | 4052 | 86 % | 24 | 48 min |
| linear-r03-consigne-instruct | gsm8k | 100 | **90 %** (90) | 271 | 217 | 3 % | 0 | 9 min |
| linear-r03-consigne-instruct | math | 50 | **64 %** (32) | 1830 | 1094 | 16 % | 13 | 29 min |
| linear-r03 | gsm8k | 100 | **78 %** (78) | 1783 | 920 | 100 % | 20 | 56 min |
| linear-r03 | math | 50 | **52 %** (26) | 3105 | 3956 | 100 % | 24 | 49 min |
| linear-r05-consigne-instruct | gsm8k | 100 | **87 %** (87) | 253 | 222 | 1 % | 0 | 8 min |
| linear-r05-consigne-instruct | math | 50 | **64 %** (32) | 1745 | 1046 | 20 % | 10 | 28 min |
| linear-r05 | gsm8k | 100 | **88 %** (88) | 1505 | 880 | 100 % | 10 | 49 min |
| linear-r05 | math | 50 | **44 %** (22) | 3331 | 4096 | 100 % | 27 | 53 min |
| reasoning | gsm8k | 100 | **87 %** (87) | 1802 | 1416 | 100 % | 10 | 55 min |
| reasoning | math | 50 | **22 %** (11) | 3792 | 4096 | 100 % | 38 | 59 min |

« Avec [THINK] » : part des réponses où le modèle a ouvert une réflexion, par le token spécial (caché par Ollama, on compte les tokens cachés) ou en écrivant « [THINK] » en texte. « Coupées » : réponses arrêtées par la limite de tokens.
