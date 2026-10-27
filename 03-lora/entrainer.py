"""Entraîne un LoRA sur Qwen2.5-1.5B-Instruct pour l'un des deux talents.

  - A « Prof patient » : explication pas à pas, en français, avec un exemple ;
  - B « JSON strict » : réponse au format {"reponse", "confiance", "sujets"}.

Lancement (environnement activé, après generer.py) :
    python entrainer.py A
    python entrainer.py B
    python entrainer.py AB --sans-chinois --epoques 2   # témoin : un seul LoRA
                    entraîné sur les deux talents mélangés, sans merge

Options utiles :
    --rang 16       taille des modules LoRA (plus petit = changement plus léger)
    --epoques 3     nombre de passages sur les données
    --essai         20 exemples et 5 pas seulement, pour vérifier que tout tourne
    --regularisation  ajoute les questions de l'autre talent avec la réponse de
                    l'Instruct (après regulariser.py) ; produit lora-A-reg, etc.
    --sans-chinois  écarte les exemples dont la réponse contient du chinois
    --nom reg2      nom de la série à la place de « reg » (lora-A-reg2…), pour
                    ne pas écraser un entraînement précédent
    --graine 1      autre tirage au hasard (initialisation du LoRA, ordre des
                    exemples, dropout) ; ajoute « -g1 » au nom (lora-A-reg2-g1…).
                    La graine 0 est celle de tous les entraînements précédents.

Le script produit deux choses :
  - l'adaptateur seul (quelques dizaines de Mo), dans 03-lora/lora-A ou lora-B ;
  - le modèle complet avec l'adaptateur intégré, dans ~/models/qwen2.5-1.5b-lora-A
    (ou -B). C'est lui que distance.py et mergekit utiliseront. Comme pour les
    merges, rien de lourd ne va dans OneDrive.
"""

import argparse
import json
import os
import random
import re

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoTokenizer
from trl import SFTConfig, SFTTrainer

MODELE_BASE = "Qwen/Qwen2.5-1.5B-Instruct"
DOSSIER_ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER_DONNEES = os.path.join(DOSSIER_ICI, "..", "02-donnees")
PART_VALIDATION = 0.05  # exemples mis de côté pour suivre le sur-apprentissage
# Idéogrammes chinois (U+4E00 à U+9FFF) : Qwen en glisse parfois au milieu d'une
# réponse française, et le LoRA apprendrait à faire de même.
CARACTERES_CHINOIS = re.compile("[一-鿿]")


def lire_exemples(nom_fichier):
    with open(os.path.join(DOSSIER_DONNEES, nom_fichier), encoding="utf-8") as f:
        return [json.loads(ligne) for ligne in f if ligne.strip()]


def charger_donnees(talent, essai, regularisation, sans_chinois):
    # « AB » : les données des deux talents réunies. Chaque talent voit alors
    # les questions de l'autre avec leurs vraies réponses.
    exemples = []
    for t in talent:
        exemples += lire_exemples(f"donnees_{t}.jsonl")
    if regularisation:
        # Les questions de l'autre talent, avec la réponse de l'Instruct :
        # le LoRA apprend à ne rien changer quand la question n'est pas
        # de son type (voir 02-donnees/regulariser.py).
        exemples += lire_exemples(f"regul_{talent}.jsonl")
    if sans_chinois:
        avant = len(exemples)
        exemples = [e for e in exemples
                    if not CARACTERES_CHINOIS.search(e["messages"][1]["content"])]
        print(f"{avant - len(exemples)} exemples écartés car ils contiennent du chinois")

    # Format « prompt / completion » de trl : la perte n'est calculée que sur
    # la réponse. Le modèle apprend à répondre, pas à recopier les questions.
    lignes = [{"prompt": [e["messages"][0]], "completion": [e["messages"][1]]}
              for e in exemples]
    random.Random(0).shuffle(lignes)
    if essai:
        lignes = lignes[:20]

    nb_validation = max(1, int(len(lignes) * PART_VALIDATION))
    return (Dataset.from_list(lignes[nb_validation:]),
            Dataset.from_list(lignes[:nb_validation]))


def tester(modele, tokenizer, talent):
    """Pose au modèle entraîné trois questions mises de côté par generer.py,
    plus une de l'autre talent (à laquelle il ne devrait pas appliquer son style)."""
    chemin = os.path.join(DOSSIER_DONNEES, "questions_eval.jsonl")
    if not os.path.exists(chemin):
        return
    with open(chemin, encoding="utf-8") as f:
        entrees = [json.loads(ligne) for ligne in f if ligne.strip()]
    if talent == "AB":
        questions = ([e["question"] for e in entrees if e["talent"] == "A"][:2]
                     + [e["question"] for e in entrees if e["talent"] == "B"][:2])
    else:
        questions = ([e["question"] for e in entrees if e["talent"] == talent][:3]
                     + [e["question"] for e in entrees if e["talent"] != talent][:1])

    modele.eval()
    for question in questions:
        entree = tokenizer.apply_chat_template(
            [{"role": "user", "content": question}],
            add_generation_prompt=True, return_dict=True, return_tensors="pt",
        ).to(modele.device)
        with torch.no_grad():
            sortie = modele.generate(**entree, max_new_tokens=400,
                                     do_sample=False)
        reponse = tokenizer.decode(sortie[0][entree["input_ids"].shape[1]:],
                                   skip_special_tokens=True).strip()
        print(f"\n--- {question}\n{reponse}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("talent", choices=["A", "B", "AB"])
    parser.add_argument("--rang", type=int, default=16)
    parser.add_argument("--epoques", type=float, default=3)
    parser.add_argument("--lr", type=float, default=2e-4,
                        help="taux d'apprentissage")
    parser.add_argument("--essai", action="store_true",
                        help="mini-entraînement pour vérifier l'installation")
    parser.add_argument("--regularisation", action="store_true",
                        help="ajoute les questions de l'autre talent (regul_X.jsonl)")
    parser.add_argument("--sans-chinois", action="store_true",
                        help="écarte les exemples dont la réponse contient du chinois")
    parser.add_argument("--nom", default="reg",
                        help="nom de la série avec --regularisation (défaut : reg)")
    parser.add_argument("--graine", type=int, default=0,
                        help="graine de l'entraînement (défaut : 0)")
    args = parser.parse_args()
    if args.talent == "AB" and args.regularisation:
        parser.error("AB contient déjà les questions des deux talents : "
                     "--regularisation n'a pas de sens")

    entrainement, validation = charger_donnees(args.talent, args.essai,
                                               args.regularisation, args.sans_chinois)
    print(f"{len(entrainement)} exemples d'entraînement, "
          f"{len(validation)} de validation")

    tokenizer = AutoTokenizer.from_pretrained(MODELE_BASE)

    config_lora = LoraConfig(
        r=args.rang,
        lora_alpha=2 * args.rang,  # force de l'ajustement, usuellement 2 × rang
        lora_dropout=0.05,
        # Les modules LoRA sont branchés sur toutes les couches linéaires :
        # l'attention (q, k, v, o) et le bloc de calcul (gate, up, down).
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        task_type="CAUSAL_LM",
    )

    config = SFTConfig(
        output_dir=os.path.join(DOSSIER_ICI, f"points-de-controle-{args.talent}"),
        model_init_kwargs={"dtype": torch.bfloat16},
        # Les réponses A font au plus ~300 mots, les B quelques lignes :
        # 1 024 tokens laissent de la marge sans gaspiller de mémoire.
        max_length=1024,
        completion_only_loss=True,
        num_train_epochs=args.epoques,
        max_steps=5 if args.essai else -1,
        # 4 exemples à la fois × 4 accumulations = lots de 16 exemples,
        # sans dépasser les 8 Go de la carte graphique.
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        gradient_checkpointing=True,  # recalcule plutôt que stocker : moins de mémoire
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_steps=0.05,  # moins de 1 : proportion des pas (5 % de chauffe)
        bf16=True,
        logging_steps=5,
        eval_strategy="epoch",
        save_strategy="no",
        report_to="none",
        # Seul l'entraînement change avec la graine : la répartition
        # entraînement / validation reste celle de random.Random(0).
        seed=args.graine,
    )

    trainer = SFTTrainer(
        model=MODELE_BASE,
        args=config,
        train_dataset=entrainement,
        eval_dataset=validation,
        processing_class=tokenizer,
        peft_config=config_lora,
    )
    trainer.model.print_trainable_parameters()
    trainer.train()

    suffixe = args.talent
    if args.regularisation:
        suffixe += f"-{args.nom}"  # ne remplace pas le LoRA sans régularisation
    if args.graine:
        suffixe += f"-g{args.graine}"
    if args.essai:
        suffixe += "-essai"
    dossier_lora = os.path.join(DOSSIER_ICI, f"lora-{suffixe}")
    trainer.model.save_pretrained(dossier_lora)
    print(f"\nAdaptateur enregistré dans {dossier_lora}")

    # Intègre l'adaptateur dans les poids du modèle : on obtient un modèle
    # complet ordinaire, que distance.py et mergekit savent lire.
    modele = trainer.model.merge_and_unload()
    dossier_complet = os.path.expanduser(f"~/models/qwen2.5-1.5b-lora-{suffixe}")
    modele.save_pretrained(dossier_complet)
    tokenizer.save_pretrained(dossier_complet)
    print(f"Modèle complet enregistré dans {dossier_complet}")

    tester(modele, tokenizer, args.talent)


if __name__ == "__main__":
    main()
