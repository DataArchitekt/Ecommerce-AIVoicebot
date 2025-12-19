import json
import evaluate

bleu = evaluate.load("bleu")
rouge = evaluate.load("rouge")


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
    
