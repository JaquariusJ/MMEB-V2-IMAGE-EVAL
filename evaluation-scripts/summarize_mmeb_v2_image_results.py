#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


TASK_GROUPS = {
    "Image CLS": [
        "ImageNet-1K",
        "N24News",
        "HatefulMemes",
        "VOC2007",
        "SUN397",
        "Place365",
        "ImageNet-A",
        "ImageNet-R",
        "ObjectNet",
        "Country211",
    ],
    "Image QA": [
        "OK-VQA",
        "A-OKVQA",
        "DocVQA",
        "InfographicsVQA",
        "ChartQA",
        "Visual7W",
        "ScienceQA",
        "VizWiz",
        "GQA",
        "TextVQA",
    ],
    "Image RET": [
        "MSCOCO_i2t",
        "VisualNews_i2t",
        "VisDial",
        "MSCOCO_t2i",
        "VisualNews_t2i",
        "WebQA",
        "EDIS",
        "Wiki-SS-NQ",
        "CIRR",
        "NIGHTS",
        "OVEN",
        "FashionIQ",
    ],
    "Image GD": [
        "MSCOCO",
        "RefCOCO",
        "RefCOCO-Matching",
        "Visual7W-Pointing",
    ],
}


def load_score(result_dir: Path, task: str) -> dict:
    score_path = result_dir / f"{task}_score.json"
    if not score_path.exists():
        score_path = result_dir / "image" / f"{task}_score.json"
    with score_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def metric(score: dict, name: str) -> float:
    if name in score:
        return float(score[name])
    if name == "ndcg@10":
        return float(score.get("ndcg_linear@10", score.get("ndcg_exponential@10")))
    raise KeyError(name)


def mean(values):
    return sum(values) / len(values)


def summarize(result_dir: Path) -> dict:
    groups = {}
    all_hit1 = []
    for group, tasks in TASK_GROUPS.items():
        vals = [metric(load_score(result_dir, task), "hit@1") for task in tasks]
        groups[group] = mean(vals) * 100
        all_hit1.extend(vals)

    ret_scores = [load_score(result_dir, task) for task in TASK_GROUPS["Image RET"]]
    retrieval = {
        "Recall@1": mean([metric(s, "recall@1") for s in ret_scores]) * 100,
        "Recall@5": mean([metric(s, "recall@5") for s in ret_scores]) * 100,
        "Recall@10": mean([metric(s, "recall@10") for s in ret_scores]) * 100,
        "MRR@10": mean([metric(s, "mrr@10") for s in ret_scores]) * 100,
        "nDCG@10": mean([metric(s, "ndcg@10") for s in ret_scores]) * 100,
    }

    return {
        **groups,
        "Image Overall": mean(all_hit1) * 100,
        **retrieval,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("result_dir", type=Path)
    parser.add_argument("--model-name", default="")
    args = parser.parse_args()

    result = summarize(args.result_dir)
    if args.model_name:
        print(f"Model: {args.model_name}")
    for key, value in result.items():
        print(f"{key}: {value:.1f}")


if __name__ == "__main__":
    main()
