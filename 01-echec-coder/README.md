# Étape 1 : un premier merge qui échoue (Instruct + Coder)

## Ce qu'on a essayé

Fusionner deux modèles de la même famille, en espérant obtenir un assistant à la fois
bon en conversation et bon en programmation :

- `Qwen/Qwen2.5-1.5B-Instruct` : l'assistant généraliste ;
- `Qwen/Qwen2.5-Coder-1.5B-Instruct` : la version spécialisée en code.

Les deux ont la même architecture et le même tokenizer, et viennent du même modèle de base
`Qwen/Qwen2.5-1.5B`. Sur le papier, tout était réuni pour un merge.

| Fichier | Méthode | Dosage |
|---|---|---|
| [config-slerp.yaml](config-slerp.yaml) | SLERP | t = 0,5 (moitié-moitié) |
| [config-slerp-t02.yaml](config-slerp-t02.yaml) | SLERP | t = 0,2 (80 % Instruct, 20 % Coder) |
| [config-ties.yaml](config-ties.yaml) | TIES | densité 0,5, poids 0,5 chacun |

Chaque merge a été lancé avec `mergekit-yaml`, puis comparé aux deux modèles d'origine avec
[compare.py](../compare.py) sur trois questions : une générale (la photosynthèse), une de code
(traduire une fonction PHP en Python) et une de raisonnement (la durée d'un trajet en train).

## Résultat : aucun merge ne fait mieux que les modèles d'origine

| Modèle | Photosynthèse | PHP → Python | Durée du trajet (2h35) | S'arrête seul ? |
|---|---|---|---|---|
| Instruct | ✅ Correct | ✅ Correct | ❌ Trouve 2h35, puis « corrige » en 3h | ✅ |
| Coder | 🟡 Correct mais approximatif | ✅ Correct | ✅ 2h35 | ✅ |
| SLERP t=0.5 | ❌ Divague, se répète | ❌ Code faux, puis divague | ❌ Absurde | ❌ |
| SLERP t=0.2 | 🟡 Erreur de fond (« dioxyde d'azote ») | ✅ Correct et idiomatique | ❌ « 45 heures » | ✅ (sauf Q3) |
| TIES | ❌ Charabia | ❌ Charabia | ❌ « system system… » | ❌ |

Les réponses complètes sont dans [resultats.md](../resultats.md).

## Pourquoi ça a échoué

### Le Coder n'est pas un fine-tune léger, c'est presque un autre modèle

Un merge fonctionne quand chaque modèle n'a **que légèrement** modifié les réglages du modèle
de base, chacun dans sa direction. On peut alors combiner ces petits changements sans qu'ils
se gênent.

Le script [distance.py](../distance.py) mesure de combien chaque modèle s'est éloigné de la base :

| Mesure | Résultat | Ce que ça veut dire |
|---|---|---|
| Éloignement de l'Instruct par rapport à la base | **1,0 %** | Un vrai fine-tune léger : idéal pour un merge |
| Éloignement du Coder par rapport à la base | **63,0 %** | Un réentraînement massif sur du code |
| Boutons poussés en sens opposé par les deux modèles | **47 %** | Autant que deux modèles sans rapport (50 % = hasard) |
| Similarité des directions des changements | **~0,06 à 0,12** | Quasi nulle : les deux apprentissages n'ont rien en commun |

Le Coder a été réentraîné sur une énorme quantité de code. Ses réglages ont tellement bougé
qu'il ne « parle » plus la même langue interne que l'Instruct, même s'il en a la forme.

### Ce que ça fait à chaque méthode

- **SLERP t=0.5** se place à mi-chemin entre deux points très éloignés. Ce milieu ne correspond
  à aucun modèle cohérent : le résultat divague et se répète sans fin.
- **SLERP t=0.2** reste près de l'Instruct, donc il reste lisible. Mais les 20 % de Coder
  suffisent à abîmer le raisonnement et les connaissances générales.
- **TIES** additionne les changements de chaque modèle par rapport à la base. Il suppose que
  ces changements sont petits et comparables. Ici, ceux du Coder sont environ 60 fois plus
  grands que ceux de l'Instruct : ils écrasent tout. Ensuite, la moitié des changements est
  retirée (densité 0,5) et les signes sont arbitrés au vote alors que les deux modèles ne sont
  d'accord qu'une fois sur deux. Le modèle obtenu est cassé.

## Deuxième tentative : deux fine-tunes légers trouvés sur Hugging Face

Pour vérifier le diagnostic, on a pris deux fine-tunes **légers** de l'Instruct, publiés par
d'autres utilisateurs :

- un spécialisé en code (`Malikeh1375/Qwen2.5-1.5B-Programming-And-Code-Development-Distilled-8Clusters-25K`),
  éloigné de **0,3 %** de l'Instruct ;
- un spécialisé en problèmes de maths GSM8K (`jahyungu/Qwen2.5-1.5B-Instruct_gsm8k`),
  éloigné de **0,2 %**.

Configs : [config-slerp-code-maths.yaml](config-slerp-code-maths.yaml) et
[config-ties-code-maths.yaml](config-ties-code-maths.yaml).

Cette fois, `distance.py` les déclare fusionnables. Mais on ne sait pas exactement sur quelles
données ils ont été entraînés ni avec quel soin. On ne contrôle donc pas ce qu'on fusionne,
et on ne peut pas mesurer proprement si chaque talent survit au merge.

## La leçon

1. **Même architecture et même tokenizer ne suffisent pas.** Il faut aussi que les modèles
   soient des fine-tunes **légers** d'une même base.
2. **On peut le vérifier avant de fusionner**, en quelques minutes, avec `distance.py`.
   Au-delà d'environ 15 % d'éloignement, inutile de lancer le merge.
3. **Pour une expérience propre, il faut maîtriser les modèles qu'on fusionne.** D'où la suite
   du projet : entraîner nous-mêmes deux LoRA légers (« Prof patient » et « JSON strict »)
   sur des données que l'on génère et que l'on vérifie, voir [02-donnees](../02-donnees).
