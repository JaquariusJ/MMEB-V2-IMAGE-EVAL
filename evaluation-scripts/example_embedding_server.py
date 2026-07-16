#!/usr/bin/env python3
"""Example FastAPI embedding server exposing the /embed protocol.

Wraps a local CLIP/SigLIP2/Qwen3 model so the eval scripts can call it remotely
without loading weights on the eval machine:

  # eval side (no GPU/model needed):
  python eval_clip_siglip_image.py --kind remote --endpoint http://host:8000/embed ...
  python lib/eval_custom_retrieval.py --kind remote --endpoint http://host:8000/embed ...

  # server side:
  pip install fastapi uvicorn
  python example_embedding_server.py --kind clip --model-id /path/to/clip --port 8000
  python example_embedding_server.py --kind qwen3 --model-id /path/to/Qwen3-8B \
      --qwen3-repo /path/to/Qwen3-VL-Embedding --port 8000

Protocol: POST /embed {"items":[{"text","image_base64"}]} -> {"embeddings":[[...]]}

vllm alternative: serve with `vllm serve <model> --task embed` and write a thin adapter
that decodes image_base64 -> PIL -> vllm embedding call, returning the same /embed shape.
This file is a self-contained reference using transformers.
"""
import os
import sys
import io
import base64
import tempfile
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _payload_from_items(items):
    """Convert {text, image_base64} items to {text, image(abs path)} for local encoders."""
    payload = []
    tmp = tempfile.mkdtemp()
    for it in items:
        pi = {"text": it.get("text") or ""}
        b64 = it.get("image_base64")
        if b64:
            p = os.path.join(tmp, f"{abs(id(it)) % 10**8}.jpg")
            Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB").save(p)
            pi["image"] = p
        payload.append(pi)
    return payload


def build_encoder(args):
    if args.kind in ("clip", "siglip"):
        from eval_clip_siglip_image import ClipLike
        enc = ClipLike(args.model_id, args.kind, args.batch_size)

        def encode(items):
            return enc.prepare(_payload_from_items(items), "")
        return encode

    if args.kind == "qwen3":
        import torch
        sys.path.insert(0, str(Path(args.qwen3_repo) / "src"))
        from evaluation.mmeb_v2.models import MMEBEmbeddingModel
        model = MMEBEmbeddingModel.load(
            model_name_or_path=args.model_id, normalize=True,
            attn_implementation="sdpa", torch_dtype=torch.bfloat16,
        )

        def encode(items):
            emb = model.encoder.process(_payload_from_items(items), normalize=True)
            return np.asarray(emb.float().cpu() if hasattr(emb, "float") else emb, dtype="float32")
        return encode

    raise SystemExit(f"unknown kind: {args.kind}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=["clip", "siglip", "qwen3"])
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--qwen3-repo", default="")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--batch-size", type=int, default=64)
    args = ap.parse_args()
    if args.kind == "qwen3" and not args.qwen3_repo:
        ap.error("--qwen3-repo is required for kind=qwen3")

    encode = build_encoder(args)

    from fastapi import FastAPI, Request
    import uvicorn
    app = FastAPI()

    @app.post("/embed")
    async def embed(req: Request):
        data = await req.json()
        emb = encode(data["items"])
        return {"embeddings": np.asarray(emb, dtype="float32").tolist()}

    print(f"serving /embed on {args.host}:{args.port} (kind={args.kind})", flush=True)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
