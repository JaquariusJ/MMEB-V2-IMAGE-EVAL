#!/usr/bin/env python3
"""Custom retrieval evaluation over queries/corpus/qrels JSONL.

Supports four encoder backends:
  --kind clip    : local CLIP (openai/clip-vit-large-patch14)
  --kind siglip  : local SigLIP2 (google/siglip2-so400m-patch14-384)
  --kind qwen3   : local Qwen3-VL-Embedding-8B (needs --qwen3-repo pointing at the
                   cloned Qwen3-VL-Embedding repo, which provides Qwen3VLEmbedder)
  --kind remote  : HTTP remote embedding service (FastAPI/vllm behind a /embed endpoint)

Data format (see CUSTOM_RETRIEVAL_DATASET_GUIDE.md), paths relative to --data-root:
  queries.jsonl : {"query_id","text","image"(nullable)}
  corpus.jsonl  : {"doc_id","text"(nullable),"image"}
  qrels.jsonl   : {"query_id","doc_id","score"}

Remote /embed protocol:
  POST {endpoint} {"items":[{"text":"...","image_base64":"..."}]}
  -> {"embeddings":[[...],...]}
"""
import os
import sys
import json
import base64
import argparse
import math
from pathlib import Path

import numpy as np


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def recall_at(pred, labels, k):
    return len(set(pred[:k]) & set(labels)) / max(1, len(labels))


def mrr_at(pred, labels, k):
    s = set(labels)
    for i, p in enumerate(pred[:k]):
        if p in s:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at(pred, labels, k):
    s = set(labels)
    dcg = sum(1.0 / math.log2(i + 2) for i, p in enumerate(pred[:k]) if p in s)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(s), k)))
    return dcg / ideal if ideal else 0.0


def build_encoder(args):
    data_root = Path(args.data_root)

    if args.kind in ("clip", "siglip"):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from eval_clip_siglip_image import ClipLike  # reuse verified CLIP/SigLIP2 logic
        enc = ClipLike(args.model_id, args.kind, args.batch_size)

        def encode(items):
            return enc.prepare(items, str(data_root))

        return encode

    if args.kind == "qwen3":
        import torch
        sys.path.insert(0, str(Path(args.qwen3_repo) / "src"))
        from evaluation.mmeb_v2.models import MMEBEmbeddingModel
        model = MMEBEmbeddingModel.load(
            model_name_or_path=args.model_id,
            normalize=True,
            attn_implementation="sdpa",
            torch_dtype=torch.bfloat16,
        )

        def encode(items):
            # items: list of {text, image(absolute path or '')}
            proc = []
            for it in items:
                pi = {"text": it.get("text") or ""}
                img = it.get("image") or ""
                if img:
                    pi["image"] = str(data_root / img) if not os.path.isabs(img) else img
                proc.append(pi)
            emb = model.encoder.process(proc, normalize=True)
            return np.asarray(emb.float().cpu() if hasattr(emb, "float") else emb, dtype="float32")

        return encode

    if args.kind == "remote":
        import requests

        def encode(items):
            payload = []
            for it in items:
                pi = {"text": it.get("text") or ""}
                img = it.get("image") or ""
                if img:
                    p = str(data_root / img) if not os.path.isabs(img) else img
                    with open(p, "rb") as f:
                        pi["image_base64"] = base64.b64encode(f.read()).decode()
                payload.append(pi)
            embs = []
            for i in range(0, len(payload), args.batch_size):
                chunk = payload[i:i + args.batch_size]
                r = requests.post(args.endpoint, json={"items": chunk}, timeout=600)
                r.raise_for_status()
                embs.extend(r.json()["embeddings"])
            return np.asarray(embs, dtype="float32")

        return encode

    raise SystemExit(f"unknown kind: {args.kind}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=["clip", "siglip", "qwen3", "remote"])
    ap.add_argument("--model-id", default="")
    ap.add_argument("--endpoint", default="", help="remote /embed URL (kind=remote)")
    ap.add_argument("--qwen3-repo", default="", help="Qwen3-VL-Embedding repo path (kind=qwen3)")
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--queries", default="queries.jsonl")
    ap.add_argument("--corpus", default="corpus.jsonl")
    ap.add_argument("--qrels", default="qrels.jsonl")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--batch-size", type=int, default=64)
    args = ap.parse_args()

    if args.kind in ("clip", "siglip", "qwen3") and not args.model_id:
        ap.error("--model-id is required for kind=clip/siglip/qwen3")
    if args.kind == "remote" and not args.endpoint:
        ap.error("--endpoint is required for kind=remote")
    if args.kind == "qwen3" and not args.qwen3_repo:
        ap.error("--qwen3-repo is required for kind=qwen3")

    dr = Path(args.data_root)

    def resolve(p):
        return Path(p) if Path(p).is_absolute() else dr / p

    queries = load_jsonl(resolve(args.queries))
    corpus = load_jsonl(resolve(args.corpus))
    qrels_raw = load_jsonl(resolve(args.qrels))
    qrels = {}
    for r in qrels_raw:
        qrels.setdefault(r["query_id"], set()).add(r["doc_id"])

    print(f"queries={len(queries)} corpus={len(corpus)} labeled_queries={len(qrels)}", flush=True)

    encode = build_encoder(args)

    q_items = [{"text": q.get("text") or "", "image": q.get("image") or ""} for q in queries]
    c_items = [{"text": c.get("text") or "", "image": c.get("image") or ""} for c in corpus]

    print("encoding queries...", flush=True)
    q_emb = encode(q_items)
    print("encoding corpus...", flush=True)
    c_emb = encode(c_items)

    q_emb = np.asarray(q_emb, dtype="float32")
    c_emb = np.asarray(c_emb, dtype="float32")
    q_emb = q_emb / np.maximum(np.linalg.norm(q_emb, axis=1, keepdims=True), 1e-12)
    c_emb = c_emb / np.maximum(np.linalg.norm(c_emb, axis=1, keepdims=True), 1e-12)

    scores = q_emb @ c_emb.T  # [Nq, Nc]
    doc_ids = [c["doc_id"] for c in corpus]

    preds = []
    for i, q in enumerate(queries):
        order = np.argsort(-scores[i])
        pred = [doc_ids[j] for j in order]
        label = sorted(qrels.get(q["query_id"], []))
        preds.append({"query_id": q["query_id"], "prediction": pred, "label": label})

    labeled = [p for p in preds if p["label"]]
    out = {}
    for k in (1, 5, 10):
        out[f"recall@{k}"] = float(np.mean([recall_at(p["prediction"], p["label"], k) for p in labeled])) if labeled else 0.0
        out[f"mrr@{k}"] = float(np.mean([mrr_at(p["prediction"], p["label"], k) for p in labeled])) if labeled else 0.0
    out["ndcg@10"] = float(np.mean([ndcg_at(p["prediction"], p["label"], 10) for p in labeled])) if labeled else 0.0
    out["num_queries"] = len(queries)
    out["num_labeled"] = len(labeled)
    out["num_corpus"] = len(corpus)

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    (Path(args.output_dir) / "summary.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(Path(args.output_dir) / "predictions.jsonl", "w", encoding="utf-8") as f:
        for p in preds:
            f.write(json.dumps({
                "query_id": p["query_id"],
                "prediction": p["prediction"][:100],
                "label": p["label"],
            }, ensure_ascii=False) + "\n")

    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
