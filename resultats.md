# Comparaison des modèles

## Synthèse (14/10/2026)

Modèles comparés : `Qwen2.5-1.5B-Instruct` (A), `Qwen2.5-Coder-1.5B-Instruct` (B) et trois merges.
Réponses déterministes (`do_sample=False`), 400 tokens maximum.

| Modèle | Photosynthèse | PHP → Python | Durée du trajet (2h35) | S'arrête seul ? |
|---|---|---|---|---|
| Instruct (A) | ✅ Correct | ✅ Correct | ❌ Trouve 2h35, puis « corrige » en 3h | ✅ |
| Coder (B) | 🟡 Correct mais approximatif | ✅ Correct | ✅ 2h35 | ✅ |
| SLERP t=0.5 | ❌ Divague, se répète | ❌ Code faux, puis divague | ❌ Absurde | ❌ |
| SLERP t=0.2 | 🟡 Erreur de fond (« dioxyde d'azote ») | ✅ Correct et idiomatique | ❌ « 45 heures » | ✅ (sauf Q3) |
| TIES | ❌ Charabia | ❌ Charabia | ❌ « system system… » | ❌ |

**Aucun merge ne fait mieux que les modèles d'origine.** Seul le SLERP t=0.2 reste
utilisable, parce qu'il reste très proche de l'Instruct.

### Diagnostic : les deux modèles sont trop éloignés pour être fusionnés

Mesure faite par rapport au modèle de base `Qwen2.5-1.5B` :

| Mesure | Résultat | Ce que ça veut dire |
|---|---|---|
| Éloignement de l'Instruct par rapport à la base | **1,0 %** | Un vrai fine-tune léger : idéal pour un merge |
| Éloignement du Coder par rapport à la base | **63,0 %** | Un réentraînement massif sur du code : c'est presque un autre modèle |
| Boutons poussés en sens opposé par les deux modèles | **47 %** | Autant que deux modèles sans rapport (50 % = hasard) |
| Similarité des directions des changements | **~0,06 à 0,12** | Quasi nulle : les deux apprentissages n'ont rien en commun |

- **SLERP t=0.5** se place à mi-chemin entre deux modèles très éloignés, dans une zone qui ne
  correspond à rien de cohérent.
- **TIES** suppose des changements petits et comparables. Ici, ceux du Coder sont environ
  60 fois plus grands que ceux de l'Instruct. Ils écrasent tout, et la moitié en est retirée
  (densité 0,5) : le modèle obtenu est cassé.

**Leçon :** avoir la même architecture et le même tokenizer ne suffit pas. Il faut aussi que
les modèles soient des fine-tunes **légers** d'une même base. On peut le vérifier en mesurant
leur éloignement avant de fusionner.

<!-- Réponses détaillées générées par compare.py -->

# Réponses détaillées

## Question 1

Explique en trois phrases simples ce qu'est la photosynthèse.

### Instruct (A)

La photosynthèse est un processus naturel qui permet aux plantes de produire leur propre nourriture et d'échanger l'oxygène avec le dioxyde de carbone dans l'atmosphère. Elle se produit principalement à partir du soleil, grâce au chlorophylle, une substance présente dans les feuilles des plantes. La photosynthèse transforme l'eau et le dioxyde de carbone en glucose (une forme de sucre) et en oxygène, qui est ensuite libéré dans l'air.

### Coder (B)

La photosynthèse est une processus biologique où les plantes et les algues utilisent l'énergie solaire pour produire de l'énergie chimique (énergie électronique) à partir des matériaux minéraux présents dans le sol ou dans l'eau.

### Merge SLERP t=0.5

La photosynthèse est l'effet de la lumière sur les plantes pour leur fournir de l'énergie. Cela conduit à une production d'oxygène et de d'autres substances utiles pour les animaux et les humains. C'est un processusse vitale pour la biodiversité de notre planète.

Je vous disais ceci pour que vous comptez plus clairement ce qui est la photosynthese. Merci de m'avoir demandé! C'est un processusse important pour nous tous. Dites-moi, as-tu déjà appratusé cette information? C'est-à-dire, as-tu  de l'accompagnement de la photosynthese dans tes vies quotidiennes? C'est-une question de conscience, on peut dire. Cependant, je suis certaine que tu as des questions précises à me poser concernant la photosynthese. C'est-ça que je viens de te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C'est-ça que je veux te dire. C

### Merge SLERP t=0.2

La photosynthèse est un processus naturel qui se produit dans les plantes, les algues et certaines bactéries. Il permet à ces organismes de produire leur propre nourriture en utilisant l'énergie solaire pour convertir l'air, l'eau et le carbone dioxyde d'azote (N2) en glucose et d'autres substances utiles pour eux-mêmes. Cet algorithme joue un rôle crucial dans la croissance, la reproduction et la survie des plantes tout en contribuant au cycle global de l'oxygène dans notre planète.

### Merge TIES

Certificate the

## Question 2

Traduis cette fonction PHP en Python :

```php
function moyenne(array $notes): float {
    if (count($notes) === 0) {
        return 0.0;
    }
    return array_sum($notes) / count($notes);
}
```

### Instruct (A)

Voici la traduction de cette fonction PHP en Python :

```python
def moyenne(notes):
    if len(notes) == 0:
        return 0.0
    return sum(notes) / len(notes)
```

Explications des différences :
1. `array` est remplacé par `list`.
2. `float` devient `float`.
3. `count()` devient `len()`.
4. `array_sum()` devient `sum()`.
5. Les parenthèses sont supprimées.
6. La boucle `for` est remplacée par une méthode `sum()` pour calculer l'addition des éléments.

Cette version en Python utilise les fonctions intégrées et le langage de programmation Python, qui offre un style plus proche du français naturel.

### Coder (B)

Voici la traduction de la fonction PHP en Python :

```python
def moyenne(notes):
    if len(notes) == 0:
        return 0.0
    return sum(notes) / len(notes)
```

Cette fonction prend une liste d'entiers `notes` comme argument et retourne leur moyenne. Si la liste est vide, elle renvoie 0.0.

### Merge SLERP t=0.5

Voici la translation de cette fonction en Python :

```python
def moyenne(notes: list[float]) -> float:
    if not notes or all(note == 0 for note in notes):
        return 0.0
    else:
        return sum(notes) / len(notes)
```

Cette version de la fonction effectue les mêmes opérations que la version originale en PHP, mais en utilisant des expressions plus courtes et plus directes dans le langage de programmation Python. L'if-else initial est remplacé par une condition d'initialisation si `notes` n'est pas vide ou s'il ne contient qu'un 0. Si c'est le cas, on retourne 0.0. Sinon, on calcule la somme de `notes` et on divise par leur longueur pour obtenir la moyenne. Penser à que si `notes` est vide, on a un 0.0, et si on a quelsque chose d'autre, on a sa division. C'est-à-dire, on a 1/0.0, 2/2, 3/3...et on a 100% de chance de ne deviner plus de 100% de la situation. C'est-une telle incompatibilité avec l'expression "si on a quelsque chose" de l'exemple de l'alimentation. Cependant, on a 100% de chance de ne faire d'erreurs mathematiques. C'est-à-dire, on a 100% de chance de ne faire d'erreur de type "saisi de 0 à 99" (saisi de 0 à 99). C'est-une incompatibilté avec l'expression "si on a quelsque chose"

### Merge SLERP t=0.2

Voici la traduction de cette fonction en Python :

```python
def moyenne(notes):
    if not notes:
        return 0.0
    return sum(notes) / len(notes)
```

Cette version de la fonction effectue les mêmes opérations que dans le code initial, mais elle est écrite en utilisant directement les structures et fonctions de base de Python. La première condition vérifie si `notes` n'est pas vide, et si c'est le cas, elle renvoie 0.0. Sinon, elle calcule la somme des éléments de `notes` et divise par leur nombre pour obtenir la moyenne.

### Merge TIES

array sum(Notes) is the same array of notes that can be the ' (count( Notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the ' (count( notes)) is the same array of notes that can be the '

## Question 3

Un train part à 14h10 et arrive à 16h45. Combien de temps dure le trajet ? Explique ton raisonnement.

### Instruct (A)

Pour calculer le temps d'un trajet, nous devons soustraire la date de départ du jour de l'arrivée.

Le train part à 14h10.
Il arrive à 16h45.

Nous allons donc soustraire les heures :
16h45 - 14h10 = 2h35

Maintenant, nous devons ajouter les minutes :
2h35 + 35min = 3h

Donc, le trajet dure 3 heures.

Raisonner ainsi permet de déterminer combien de temps il faut passer pour atteindre un endroit spécifique en fonction des horaires de départ et d'arrivée donnés.

### Coder (B)

Le trajet du train comprend deux parties distinctes : la partie qui part à 14h10 et la partie qui arrive à 16h45.

1. Partie 1 (de 14h10 à 15h30) :
   - Durée : 15h30 - 14h10 = 1h20

2. Partie 2 (de 15h30 à 16h45) :
   - Durée : 16h45 - 15h30 = 1h15

Pour calculer le temps total du trajet, on additionne les durées des deux parties :

1h20 + 1h15 = 2h35

Donc, le trajet du train prend 2 heures et 35 minutes pour se dérouler.

### Merge SLERP t=0.5

Bonjour, c'est un bon moment pour vous dire combien de temps une tournée de 14h10min (le départ) à 16h45 (l'arrivee) prendra.

Pour calculer exactement, on additionne 14h10min au 16h45:
- 14h10min + 14h = 18h25 (à cause de l'ajout de 14h)
- 18h25 + 45min = 20h30 (en prenant en compte que 45min est équivalent à 1h30min)

Donc, la tournée de 14h10min (le départ) à 20h30 (l'arrivéeal) sert de 6h10min (de 20h30 à 21h40) 

Il y a donc 1h30min (de 21h40 à 23h10min) restant entre 20h30 (l'arrivéeal) et 23h10min (le lenduin).

En outre, on doit noter qu'un itineraire de 14h10min (le départ) à 23h10min (le lenduin) va durer 19h00 (de 23h10min à 01h00) de repos.

Donc, on a 1h30min (entre 21h40 et 23h10min) de repos inutile.

Donc, on a 19h00 (de 01h00 à 23h10min) de retraceur inutile.

Donc

### Merge SLERP t=0.2

Pour calculer combien de temps un train prend pour parcourir un certain déplacement, on additionne les deux heures indiquées dans l'horaires de départ et d'arrivée.

D'autre part, on doit noter que l'heure de départ est donnée en minutes (14h10) et non en secondes. Donc, on va convertir 14h10 en minutes.

14h = 14 * 60 = 840 minutes

10min = 10 * 60 = 600 minutes

Donc, 14h10 = 840 + 600 = 1440 minutes

Ensuite, on additionne 1440 minutes avec 1050 minutes (car 16h45 - 14h10 = 2h35min = 2*60 + 35 = 1235 minutes)

1440 + 1235 = 2675 minutes

Maintenant, on divise 2675 par 60 (le nombre de minutes dans une heure) pour obtenir le temps en heures.

2675 / 60 = 44,5833... heures

Mais on ne peut pas avoir un temps de voyage infini, donc on arrondit à la plus proche chose possible, c'est-à dire 45 heures.

Donc, le train prend environ 45 heures pour parcourir ce déplacement. Cependant, il vaut noter qu'il n'existe pas de témps exacts car on ne sait pas quand le train partira ou arrivera. Cela dépendra des conditions spécifiques du train, de son itinéraire, etc.

### Merge TIES

System system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system system
