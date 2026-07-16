#!/usr/bin/env python3
"""Download HF model weights via snapshot_download (hf-mirror, xet disabled).

Usage:
  python download_hf.py <clip|siglip|qwen3> [--root DIR] [--endpoint URL]

MMEB-V2 image *data* is a single large tar.gz; use multi_dl.py for that instead
(snapshot_download on it is slow/throttled).
"""
import os
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("target", choices=["clip", "siglip", "qwen3"])
parser.add_argument("--root", default=os.environ.get("MMEB_ROOT", "/root/autodl-tmp/mmeb_eval"))
parser.add_argument("--endpoint", default=os.environ.get("HF_ENDPOINT", "https://hf-mirror.com"))
args = parser.parse_args()

ROOT = args.root
os.environ.setdefault("HF_ENDPOINT", args.endpoint)
os.environ.setdefault("HF_HOME", f"{ROOT}/cache")
os.environ.setdefault("TRANSFORMERS_CACHE", f"{ROOT}/cache")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from huggingface_hub import snapshot_download

TARGETS = {
    "clip": ("openai/clip-vit-large-patch14", f"{ROOT}/models/clip-vit-large-patch14"),
    "siglip": ("google/siglip2-so400m-patch14-384", f"{ROOT}/models/siglip2-so400m-patch14-384"),
    "qwen3": ("Qwen/Qwen3-VL-Embedding-8B", f"{ROOT}/models/Qwen3-VL-Embedding-8B"),
}

repo_id, local_dir = TARGETS[args.target]
print(f"starting download: {args.target} -> {local_dir}", flush=True)
snapshot_download(repo_id=repo_id, local_dir=local_dir)
print(f"DONE {args.target}", flush=True)
