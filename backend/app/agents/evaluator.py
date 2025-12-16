import json
import argparse
import evaluate
from evaluate import load
from typing import Dict

bleu = evaluate.load("bleu")
rouge = evaluate.load("rouge")  

from evaluate import load

bleu = load("bleu")
rouge = load("rouge")


def evaluate_response(pred: str, ref: str):
    # BLEU
    bleu_result = bleu.compute(
        predictions=[pred],
        references=[[ref]]
    )
    bleu_score = bleu_result["bleu"]

    # ROUGE
    rouge_result = rouge.compute(
        predictions=[pred],
        references=[ref]
    )
    rouge_l = rouge_result["rougeL"]

    return {
        "bleu": round(bleu_score, 4),
        "rougeL": round(rouge_l, 4)
    }


def run_evaluation(dataset_path, responder_fn):
    with open(dataset_path) as f:
        data = json.load(f)

    results = []
    for row in data:
        pred = responder_fn(row["query"])
        scores = evaluate_response(pred, row["ground_truth"])
        results.append({
            "id": row["id"],
            "query": row["query"],
            "prediction": pred,
            "reference": row["ground_truth"],
            **scores
        })

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out", default="eval_report.json")
    args = parser.parse_args()

    # TEMP: wire to your /agent/handle logic
    from app.main import run_agent_chain

    results = run_evaluation(
        args.dataset,
        lambda q: run_agent_chain(q, session_id="eval")
    )

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)

    avg_bleu = sum(r["bleu"] for r in results) / len(results)
    print("Average BLEU:", avg_bleu)