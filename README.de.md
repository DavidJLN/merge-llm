# Zwei LLMs zusammenführen: Fehlschlag, Messung, Erfolg

[Français](README.md) · [English](README.en.md) · **Deutsch**

Kann man zwei kleine Sprachmodelle zusammenführen, um ein einziges Modell zu erhalten, das
kann, was jedes von ihnen kann? Dieses Repository erzählt von einem gescheiterten Versuch,
dem Messwerkzeug, das den Fehlschlag erklärt, und dann von einem kontrollierten Experiment,
das schließlich gelingt, mit seinen zwei Fehltritten unterwegs.

Die Tests wurden lokal auf einem handelsüblichen PC durchgeführt: RTX 4060 (8 GB), 32 GB RAM, Windows + WSL.

Die Trainingsdaten, die Evaluationsfragen und die Antworten der Modelle sind auf Französisch,
da das Experiment auf Französisch durchgeführt wurde.

## Wichtige Begriffe

### Die Modelle

- **Gewichte**: die Milliarden Zahlen, aus denen ein Modell besteht. Ein Modell trainieren
  heißt, seine Gewichte anzupassen; zwei Modelle zusammenführen heißt, ihre Gewichte zu
  kombinieren.
- **Basismodell**: das Ausgangsmodell, trainiert darauf, Rohtext vorherzusagen. Hier
  `Qwen2.5-1.5B` (1,5 Milliarden Gewichte).
- **Fine-Tune**: ein Basismodell, das auf gezielteren Daten weitertrainiert wurde.
  `Qwen2.5-1.5B-Instruct` ist ein Fine-Tune, das Anweisungen befolgen und Dialoge führen
  kann; in diesem Repository heißt es einfach „das Instruct“.
- **Gewichtsdifferenz** (oder *Task-Vektor*): was ein Fine-Tune gegenüber seiner Basis
  verändert hat, Gewicht für Gewicht. Mit dieser Differenz arbeiten die Merge-Methoden.
- **Distanz**: die Größe dieser Differenz im Verhältnis zur Größe der ursprünglichen
  Gewichte, gemessen mit [distance.py](distance.py). 0,5 % ist eine kleine Anpassung, 63 %
  ist fast ein anderes Modell.

### Das Training

- **LoRA** (*Low-Rank Adaptation*): eine sparsame Art des Fine-Tunings. Statt alle Gewichte
  zu verändern, trainiert man kleine, daneben hinzugefügte Matrizen, einen sogenannten
  **Adapter** (hier 71 MB, gegenüber 2,9 GB für das vollständige Modell). Man kann sie
  anschließend ins Modell einbauen und erhält ein normales vollständiges Modell.
- **Rang**: die Größe dieser kleinen Matrizen. Ein Rang von 16 begrenzt stark, was der LoRA
  verändern kann, und zwingt ihn so, eine leichte Anpassung zu bleiben.
- **Epoche**: ein vollständiger Durchlauf über die Trainingsdaten. Bei zu vielen Epochen
  lernt das Modell die Beispiele auswendig, statt den Stil zu lernen (*Overfitting*).
- **Regularisierung**: hier das Hinzufügen von Beispielen zu den Trainingsdaten, bei denen
  der LoRA nichts verändern soll (die Fragen des anderen Talents, mit der Antwort des
  Instruct). Der LoRA lernt so, *wann* er seinen Stil anwenden soll, nicht nur *wie*.

### Das Zusammenführen

- **Merge** (Zusammenführung): die Gewichte mehrerer Modelle zu einem einzigen kombinieren,
  ganz ohne zusätzliches Training. Das dauert weniger als eine Minute.
- **mergekit**: das Werkzeug, das die Merges anhand eines YAML-Rezepts durchführt.
- **task_arithmetic**: die einfachste Methode. Man addiert die Gewichtsdifferenzen der
  einzelnen Fine-Tunes zur Basis, jede mit einem Gewicht multipliziert (1+1 = beide mit
  voller Stärke, 0,5+0,5 = mit halber Stärke).
- **TIES** (*TrIm, Elect Sign*): wie task_arithmetic, aber mit weniger Konflikten. Man
  behält nur die größten Änderungen jedes Modells, lässt dann für jedes Gewicht über die
  Richtung der Änderung (nach oben oder unten) abstimmen und verwirft die Änderungen, die in
  die Minderheitsrichtung gehen.
- **DARE** (*Drop And REscale*): Ein großer Teil der Änderungen jedes Modells wird zufällig
  gestrichen, die übrigen werden zum Ausgleich vergrößert. Die Änderungen eines leichten
  Fine-Tunes sind so redundant, dass das Modell kaum etwas verliert, und die beiden Talente
  kommen sich weniger in die Quere.
- **SLERP** (*Spherical Linear intERPolation*): Man bewegt sich „zwischen“ zwei Modellen
  entlang eines Kreisbogens statt einer Geraden, was die Größe der Gewichte besser erhält.
  Ein Parameter `t` regelt die Mischung (0 = das erste Modell, 1 = das zweite); man probiert
  mehrere Werte aus, daher der *Sweep*. SLERP führt immer nur zwei Modelle zusammen.

### Die Evaluation

- **Talent**: ein leicht erkennbares Verhalten, das man einem LoRA beibringt (hier der
  „Geduldige Lehrer“ und das „Strikte JSON“).
- **Leck**: ein Talent, das auf die Fragen des anderen überschwappt, zum Beispiel eine
  JSON-Antwort auf eine Lernfrage.

### Die Nutzung

- **GGUF** (*GPT-Generated Unified Format*): das Dateiformat von llama.cpp, das Ollama verwendet. Eine einzige Datei enthält
  die Gewichte, den Tokenizer und das Chat-Template.
- **Quantisierung**: jedes Gewicht mit weniger Bits speichern (8, 5 oder 4 statt 16), um ein
  leichteres und schnelleres Modell zu erhalten, auf Kosten von etwas Genauigkeit.

## Die Geschichte in sechs Schritten

### 1. Ein erster Merge, der scheitert: [01-echec-coder](01-echec-coder)

Das Zusammenführen von `Qwen2.5-1.5B-Instruct` (dem Assistenten) und
`Qwen2.5-Coder-1.5B-Instruct` (dem Code-Spezialisten) ergibt Modelle, die abschweifen oder
Kauderwelsch schreiben („system system system…“). [distance.py](distance.py) liefert den
Grund: Der Coder hat sich um **63 %** von ihrer gemeinsamen Basis entfernt. Das ist kein
Fine-Tune mehr, sondern fast ein anderes Modell.

**Lektion**: Die Modelle müssen *leichte* Fine-Tunes derselben Basis sein. Das lässt sich
vor dem Merge überprüfen.

### 2. Kontrollierte Daten: [02-donnees](02-donnees)

Für ein sauberes Experiment erschaffen wir selbst zwei leicht erkennbare Talente:

| Talent | Frage | Erwartete Antwort |
|---|---|---|
| **A „Geduldiger Lehrer“** | „Pourquoi le ciel est-il bleu ?“ (Warum ist der Himmel blau?) | nummerierte Schritte, Duzen, „Exemple :“ |
| **B „Striktes JSON“** | „Quelle est la capitale du Canada ?“ (Was ist die Hauptstadt Kanadas?) | `{"reponse": …, "confiance": 0.95, "sujets": […]}` |

[generer.py](02-donnees/generer.py) lässt `qwen3:8b` (über Ollama) die Fragen erfinden, die
Antworten schreiben und sie dann gegenlesen; Antworten mit einem Formfehler oder einem
inhaltlichen Fehler werden verworfen. Bei B muss die Konfidenz von der Art der Frage
abhängen: Fakt 0,9-1, Schätzung 0,6-0,85, Debatte 0,3-0,55, unbekannt (Zukunft) 0-0,25.

Ergebnis: **602 Beispiele A** und **529 Beispiele B**, dazu 25 Fragen pro Talent, die für die
Evaluation zurückgehalten werden.

### 3. Zwei leichte LoRAs: [03-lora](03-lora)

[entrainer.py](03-lora/entrainer.py) trainiert für jedes Talent einen LoRA mit Rang 16 auf dem
Instruct, in jeweils etwa 5 Minuten. `distance.py` bestätigt, dass sie zusammenführbar sind:
Sie entfernen sich nur um **0,47 %** und **0,43 %** vom Instruct.

### 4. Die Merges: [04-merges](04-merges)

Wir führen mit mergekit nach mehreren Methoden zusammen: task_arithmetic (mit mehreren
Gewichtungen), TIES, DARE und ein SLERP-Sweep. Es gibt 12 kommentierte YAML-Rezepte, und
jeder Merge dauert weniger als eine Minute.

### 5. Die Evaluation: [05-evaluation](05-evaluation)

Wir stellen die 50 zurückgehaltenen Fragen, ohne Systemanweisung. Bewertet wird die Form
anhand der Kriterien, mit denen die Daten gefiltert wurden, sowie die Lecks von einem Talent
zum anderen.

| Serie | Was sich ändert | Bester Merge | Punktzahl |
|---|---|---|---|
| [v1](05-evaluation/v1-sans-regularisation/resultats.md) | LoRAs nur auf ihren eigenen Fragen trainiert | task_arithmetic 1+1 | **23/50** ❌ B erdrückt A |
| [v2](05-evaluation/v2-avec-regularisation/resultats.md) | + Regularisierung: Fragen des anderen Talents, mit der Antwort des Instruct | task_arithmetic 1+1 | **42/50** ✅ |
| [v3](05-evaluation/v3-regularisation-2-epoques/resultats.md) | + 2 statt 3 Epochen, ohne die Beispiele auf Chinesisch | DARE / task_arithmetic 1+1 | **46/50** und **45/50** ✅ |

**Zweiter Fehltritt (v1)**: „Zusammenführbar“ reicht nicht. Jeder LoRA wandte seinen Stil
auf **alle** Fragen an, da er die des anderen nie gesehen hatte. Die beiden Talente stritten
sich um jede Antwort, und das JSON setzte sich überall durch.

**Korrektur (v2)**: Die **Regularisierung** bringt jedem LoRA bei, nichts zu verändern, wenn
die Frage nicht von seinem Typ ist. Die beiden Änderungen ergänzen sich dann, statt sich zu
streiten. Man muss sie **mit voller Stärke** addieren: Mit halber Stärke springt keines der
Talente mehr an.

**Feinabstimmung (v3)**: weniger Epochen, weniger Overfitting. Wir erhalten null Lecks und
eine gut kalibrierte Konfidenz (1,00 / 0,87 / 0,45 / 0,15 für Fakt / Schätzung / Debatte /
unbekannt).

**Eine Variable nach der anderen (v2-bis)**: Die v3 änderte zwei Dinge gleichzeitig. Ändert
man nur die Zahl der Epochen, steigt DARE bereits von 37 auf **46/50**, und die Lecks
verschwinden. Das Entfernen der 6 Beispiele mit Chinesisch hat keine nachweisbare Wirkung.
Der Gewinn kommt also von der geringeren Zahl der Epochen.

**Bringt der Merge überhaupt etwas?** Wir vergleichen ihn mit zwei Wegen, beide Talente ohne
Merge zu erhalten:

| Methode | Punktzahl |
|---|---|
| Das Instruct mit einer Systemanweisung, die beide Talente beschreibt | **4/50** ❌ |
| DARE-Merge v3 | **46/50** |
| Ein einziger LoRA, trainiert auf A und B gemischt | **48/50** |

Eine Systemanweisung reicht bei einem Modell mit 1,5 Milliarden Parametern nicht aus: Man
muss es trainieren. Und wenn die Daten beider Talente an einem Ort vorliegen, schneidet ein
einziger LoRA genauso gut ab wie der Merge (der Unterschied von 2 Antworten ist nicht
signifikant). Der Nutzen des Merges liegt woanders: Er kombiniert zwei **getrennt** trainierte
Talente, ohne ihre Daten zusammenzuführen, und verliert dabei fast nichts. Details in
[05-evaluation](05-evaluation).

### 6. In der Praxis: [06-gguf](06-gguf)

Wir wandeln den DARE-Merge ins GGUF-Format um, quantisieren ihn und evaluieren ihn dann in
Ollama mit denselben 50 Fragen.

| Version | Größe | Punktzahl |
|---|---|---|
| bf16 (Referenz) | 2,9 GB | **46/50** |
| f16 | 2,9 GB | **46/50** |
| Q8_0 | 1,6 GB | **46/50** ✅ |
| Q5_K_M | 1,1 GB | **41/50** |
| Q4_K_M | 0,94 GB | **42/50** |

**In Q8 bleiben die Talente vollständig erhalten**: gleiche Punktzahl, null Lecks, gleiche
Kalibrierung der Konfidenz, bei halber Größe. In Q5 und Q4 verliert das Modell 4 bis 5
Punkte, vor allem wegen des Chinesischen, hat aber weiterhin null Lecks.

## Grenzen

- **Restliches Chinesisch**: 4 von 50 Antworten enthalten ein chinesisches Wort mitten im
  französischen Text („Divise chaque数 par ce nombre“). Der LoRA B allein erzeugt das auch,
  der auf beiden Talenten gemischt trainierte LoRA dagegen gar nicht. Der Fehler tritt also
  bei getrennt trainierten LoRAs mit Regularisierung und bei ihren Merges auf; welcher dieser
  Schritte ihn verursacht, wissen wir noch nicht.
- **Der Inhalt wird nicht bewertet**: Ein Modell mit 1,5 Milliarden Parametern irrt sich oft
  bei Fakten. Die LoRAs lernen eine *Art* zu antworten, kein Wissen.
- **50 Fragen** sind wenig: Ein Unterschied von 1 oder 2 Antworten ist nicht signifikant.
  Außerdem wurde jede Konfiguration nur einmal trainiert: Mit einem anderen Zufallsstartwert
  würden sich die Punktzahlen um einige Punkte verschieben.

## Reproduzieren

1. **Daten**, unter Windows oder WSL, mit Ollama und `qwen3:8b`:
   `python 02-donnees/generer.py tout`
2. **WSL-Umgebung**: siehe [03-lora/requirements.txt](03-lora/requirements.txt). Außerdem
   werden `build-essential` für Triton und mergekit 0.1.5 oder neuer benötigt.
3. **Regularisierung**: `python 02-donnees/regulariser.py`
4. **LoRAs**: `python 03-lora/entrainer.py A --regularisation --sans-chinois --epoques 2 --nom reg2`,
   dann derselbe Befehl mit `B`
5. **Merges**: `bash 04-merges/fusionner.sh reg2 task-arithmetic ties dare`
6. **Evaluation**: `python 05-evaluation/evaluer.py v3`
   - **v2-bis**: `python 03-lora/entrainer.py A --regularisation --epoques 2 --nom reg2c`,
     den Link `~/models/qwen2.5-1.5b-lora-B-reg2c` auf `…-lora-B-reg2` anlegen, dann
     `bash 04-merges/fusionner.sh reg2c task-arithmetic ties dare` und `evaluer.py v2bis`
   - **Vergleichsmodelle**: `python 03-lora/entrainer.py AB --sans-chinois --epoques 2`,
     dann `evaluer.py temoins`
7. **GGUF**: llama.cpp nach `~/llama.cpp` klonen, dann `bash 06-gguf/convertir.sh` (WSL)
   und `06-gguf/creer.ps1` (Windows)
8. **Evaluation in Ollama**: `python 05-evaluation/evaluer.py gguf`

Die vollständigen Modelle (je 2,9 GB) kommen nach `~/models`, außerhalb des Repositorys. Nur
die LoRA-Adapter (71 MB) liegen in `03-lora/`.
