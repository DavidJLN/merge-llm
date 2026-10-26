# Merging two LLMs: failure, measurement, success

[Français](README.md) · **English** · [Deutsch](README.de.md)

Can you merge two small language models to get a single model that can do what each of them
does? This repository tells the story of a failed attempt, the measuring tool that explains
the failure, then a controlled experiment that eventually succeeds, with its two missteps
along the way.

All the tests were run locally on a consumer PC: RTX 4060 (8 GB), 32 GB of RAM, Windows + WSL.

The training data, the evaluation questions and the model answers are in French, since the
experiment was run in French.

## Key terms

### Models

- **Weights**: the billions of numbers that make up a model. Training a model means adjusting
  its weights; merging two models means combining their weights.
- **Base model**: the starting model, trained to predict raw text. Here, `Qwen2.5-1.5B`
  (1.5 billion weights).
- **Fine-tune**: a base model that has been trained further on more targeted data.
  `Qwen2.5-1.5B-Instruct` is a fine-tune that can follow instructions and hold a
  conversation; this repository simply calls it "the Instruct".
- **Weight difference** (or *task vector*): what a fine-tune changed compared to its base,
  weight by weight. This difference is what merge methods work with.
- **Distance**: the size of that difference relative to the size of the original weights,
  measured by [distance.py](distance.py). 0.5% is a small adjustment; 63% is almost a
  different model.

### Training

- **LoRA** (*Low-Rank Adaptation*): a cheap way to fine-tune. Instead of modifying all the
  weights, you train small matrices added alongside them, called an **adapter** (71 MB here,
  versus 2.9 GB for the full model). They can then be built into the model to get a normal
  full model.
- **Rank**: the size of these small matrices. A rank of 16 strongly limits what the LoRA can
  change, which forces it to stay a light adjustment.
- **Epoch**: one full pass over the training data. Too many epochs and the model memorizes
  the examples instead of learning the style (*overfitting*).
- **Regularization**: here, adding to the training data examples where the LoRA must change
  nothing (the other talent's questions, with the Instruct's answer). The LoRA thus learns
  *when* to apply its style, not just *how*.

### Merging

- **Merge**: combining the weights of several models into a single one, with no additional
  training. It takes less than a minute.
- **mergekit**: the tool that performs the merges from a YAML recipe.
- **task_arithmetic**: the simplest method. You add each fine-tune's weight difference to the
  base, each multiplied by a weight (1+1 = both at full strength, 0.5+0.5 = at half
  strength).
- **TIES** (*TrIm, Elect Sign*): like task_arithmetic, but with fewer conflicts. Only the
  largest changes of each model are kept, then, for each weight, the direction of the change
  (up or down) is put to a vote and changes going in the minority direction are discarded.
- **DARE** (*Drop And REscale*): a large share of each model's changes is dropped at random,
  and the remaining ones are scaled up to compensate. The changes of a light fine-tune are so
  redundant that the model loses almost nothing, and the two talents step on each other's
  toes less.
- **SLERP** (*Spherical Linear intERPolation*): you place yourself "between" two models by
  following an arc of a circle rather than a straight line, which better preserves the size
  of the weights. A parameter `t` sets the mix (0 = the first model, 1 = the second); several
  values are tried, hence the *sweep*. SLERP only merges two models at a time.

### Evaluation

- **Talent**: an easily recognizable behavior taught to a LoRA (here the "Patient teacher"
  and the "Strict JSON").
- **Leak**: a talent spilling over onto the other one's questions, for example a JSON answer
  to a lesson question.

### Usage

- **GGUF** (*GPT-Generated Unified Format*): the file format of llama.cpp, used by Ollama. A single file holds the weights,
  the tokenizer and the chat template.
- **Quantization**: storing each weight with fewer bits (8, 5 or 4 instead of 16) to get a
  lighter and faster model, at the cost of some precision.

## The story in six steps

### 1. A first merge that fails: [01-echec-coder](01-echec-coder)

Merging `Qwen2.5-1.5B-Instruct` (the assistant) and `Qwen2.5-Coder-1.5B-Instruct` (the code
specialist) yields models that ramble or write gibberish ("system system system…").
[distance.py](distance.py) explains why: the Coder has moved **63%** away from their common
base. It is no longer a fine-tune, it is almost another model.

**Lesson**: the models must be *light* fine-tunes of the same base. This can be checked
before running the merge.

### 2. Controlled data: [02-donnees](02-donnees)

For a clean experiment, we create two easily recognizable talents ourselves:

| Talent | Question | Expected answer |
|---|---|---|
| **A "Patient teacher"** | "Pourquoi le ciel est-il bleu ?" (Why is the sky blue?) | numbered steps, informal "tu", "Exemple :" |
| **B "Strict JSON"** | "Quelle est la capitale du Canada ?" (What is the capital of Canada?) | `{"reponse": …, "confiance": 0.95, "sujets": […]}` |

[generer.py](02-donnees/generer.py) has `qwen3:8b` (via Ollama) invent the questions, write
the answers, then review them, rejecting those with a formatting flaw or a factual error. For
B, the confidence must depend on the type of question: fact 0.9-1, estimate 0.6-0.85, debate
0.3-0.55, unknown (future) 0-0.25.

Result: **602 A examples** and **529 B examples**, plus 25 questions per talent held out for
evaluation.

### 3. Two light LoRAs: [03-lora](03-lora)

[entrainer.py](03-lora/entrainer.py) trains a rank-16 LoRA on the Instruct for each talent, in
about 5 minutes each. `distance.py` confirms they can be merged: they only move **0.47%** and
**0.43%** away from the Instruct.

### 4. The merges: [04-merges](04-merges)

We merge with mergekit using several methods: task_arithmetic (with several weights), TIES,
DARE, and a SLERP sweep. There are 12 commented YAML recipes, and each merge takes less than a
minute.

### 5. The evaluation: [05-evaluation](05-evaluation)

We ask the 50 held-out questions, with no system prompt. We score the format with the
criteria used to filter the data, as well as leaks from one talent to the other.

| Series | What changes | Best merge | Score |
|---|---|---|---|
| [v1](05-evaluation/v1-sans-regularisation/resultats.md) | LoRAs trained on their own questions only | task_arithmetic 1+1 | **23/50** ❌ B crushes A |
| [v2](05-evaluation/v2-avec-regularisation/resultats.md) | + regularization: the other talent's questions, with the Instruct's answer | task_arithmetic 1+1 | **42/50** ✅ |
| [v3](05-evaluation/v3-regularisation-2-epoques/resultats.md) | + 2 epochs instead of 3, without the examples in Chinese | DARE / task_arithmetic 1+1 | **46/50** and **45/50** ✅ |

**Second misstep (v1)**: "mergeable" is not enough. Each LoRA applied its style to **every**
question, since it had never seen the other one's. The two talents fought over every answer,
and JSON won everywhere.

**Fix (v2)**: **regularization** teaches each LoRA to change nothing when the question is not
of its type. The two changes then complement each other instead of fighting. They must be
added **at full strength**: at half strength, neither talent kicks in anymore.

**Final tuning (v3)**: fewer epochs, less overfitting. We get zero leaks and well-calibrated
confidence (1.00 / 0.87 / 0.45 / 0.15 for fact / estimate / debate / unknown).

**One variable at a time (v2-bis)**: v3 changed two things at once. Changing only the number
of epochs already takes DARE from 37 to **46/50** and removes the leaks. Removing the 6
examples containing Chinese has no demonstrated effect. The gain therefore comes from the
reduced number of epochs.

**Is the merge useful at all?** We compare it with two ways of getting both talents without
a merge:

| Method | Score |
|---|---|
| The Instruct, with a system prompt describing both talents | **4/50** ❌ |
| DARE merge v3 | **46/50** |
| A single LoRA trained on A and B mixed together | **48/50** |

A system prompt is not enough for a 1.5-billion-parameter model: it has to be trained. And
when the data for both talents is available in one place, a single LoRA does as well as the
merge (the 2-answer gap is not significant). The merge's value lies elsewhere: it combines two
talents trained **separately**, without pooling their data, and loses almost nothing in the
process. Details are in [05-evaluation](05-evaluation).

### 6. In practice: [06-gguf](06-gguf)

We convert the DARE merge to GGUF, quantize it, then evaluate it in Ollama with the same 50
questions.

| Version | Size | Score |
|---|---|---|
| bf16 (reference) | 2.9 GB | **46/50** |
| f16 | 2.9 GB | **46/50** |
| Q8_0 | 1.6 GB | **46/50** ✅ |
| Q5_K_M | 1.1 GB | **41/50** |
| Q4_K_M | 0.94 GB | **42/50** |

**In Q8, the talents survive entirely**: same score, zero leaks, same confidence
calibration, at half the size. In Q5 and Q4, the model loses 4 to 5 points, mostly because of
Chinese, but still has zero leaks.

## Limitations

- **Residual Chinese**: 4 answers out of 50 contain a Chinese word in the middle of the
  French ("Divise chaque数 par ce nombre"). LoRA B alone produces it too, but the LoRA trained
  on both talents mixed together produces none. The flaw therefore appears with LoRAs trained
  separately, with regularization, and with their merges, and we do not yet know which of
  these steps causes it.
- **Content is not evaluated**: a 1.5-billion-parameter model often gets facts wrong. The
  LoRAs learn a *way* of answering, not knowledge.
- **50 questions** is few: a gap of 1 or 2 answers is not significant. And each
  configuration was trained only once: with another random seed, the scores would move by a
  few points.

## Reproducing

1. **Data**, on Windows or WSL, with Ollama and `qwen3:8b`:
   `python 02-donnees/generer.py tout`
2. **WSL environment**: see [03-lora/requirements.txt](03-lora/requirements.txt). You also
   need `build-essential` for Triton, and mergekit 0.1.5 or later.
3. **Regularization**: `python 02-donnees/regulariser.py`
4. **LoRAs**: `python 03-lora/entrainer.py A --regularisation --sans-chinois --epoques 2 --nom reg2`,
   then the same command with `B`
5. **Merges**: `bash 04-merges/fusionner.sh reg2 task-arithmetic ties dare`
6. **Evaluation**: `python 05-evaluation/evaluer.py v3`
   - **v2-bis**: `python 03-lora/entrainer.py A --regularisation --epoques 2 --nom reg2c`,
     create the link `~/models/qwen2.5-1.5b-lora-B-reg2c` pointing to `…-lora-B-reg2`, then
     `bash 04-merges/fusionner.sh reg2c task-arithmetic ties dare` and `evaluer.py v2bis`
   - **Baselines**: `python 03-lora/entrainer.py AB --sans-chinois --epoques 2`, then
     `evaluer.py temoins`
7. **GGUF**: clone llama.cpp into `~/llama.cpp`, then `bash 06-gguf/convertir.sh` (WSL)
   and `06-gguf/creer.ps1` (Windows)
8. **Evaluation in Ollama**: `python 05-evaluation/evaluer.py gguf`

The full models (2.9 GB each) go in `~/models`, outside the repository. Only the LoRA
adapters (71 MB) are in `03-lora/`.
