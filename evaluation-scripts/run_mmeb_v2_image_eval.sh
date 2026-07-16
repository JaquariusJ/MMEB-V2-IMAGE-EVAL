#!/usr/bin/env bash
set -euo pipefail

# Default workspace used in the report.
ROOT=/root/autodl-tmp/mmeb_eval
PY=/root/miniconda3/bin/python
IMAGE_ROOT=$ROOT/data/image-tasks/MMEB
CACHE_ROOT=$ROOT/cache

export HF_ENDPOINT=${HF_ENDPOINT:-https://hf-mirror.com}
export HF_HOME=$CACHE_ROOT
export TRANSFORMERS_CACHE=$CACHE_ROOT
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}

run_qwen3() {
  cd "$ROOT/Qwen3-VL-Embedding"

  "$PY" -m src.evaluation.mmeb_v2.eval_embedding \
    --normalize true \
    --per_device_eval_batch_size 8 \
    --dataloader_num_workers 4 \
    --model_name_or_path "$ROOT/models/Qwen3-VL-Embedding-8B" \
    --dataset_config scripts/evaluation/mmeb_v2/image.yaml \
    --encode_output_path results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B/image \
    --data_basedir data/evaluation/mmeb_v2 \
    --output_dir "$ROOT/qwen_eval_tmp"

  "$PY" -m src.evaluation.mmeb_v2.gather_results \
    results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B \
    --output_dir results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B
}

run_clip() {
  cd "$ROOT/VLM2Vec"

  "$PY" eval_clip_siglip_image.py \
    --model-id openai/clip-vit-large-patch14 \
    --kind clip \
    --dataset-config experiments/public/eval/image.yaml \
    --image-root "$IMAGE_ROOT" \
    --output-dir "$ROOT/results/clip-vit-large-patch14-image"
}

run_siglip2() {
  cd "$ROOT/VLM2Vec"

  "$PY" eval_clip_siglip_image.py \
    --model-id google/siglip2-so400m-patch14-384 \
    --kind siglip \
    --dataset-config experiments/public/eval/image.yaml \
    --image-root "$IMAGE_ROOT" \
    --output-dir "$ROOT/results/siglip2-so400m-patch14-384-image"
}

case "${1:-all}" in
  qwen3)
    run_qwen3
    ;;
  clip)
    run_clip
    ;;
  siglip2)
    run_siglip2
    ;;
  all)
    run_clip
    run_siglip2
    run_qwen3
    ;;
  *)
    echo "Usage: $0 [clip|siglip2|qwen3|all]" >&2
    exit 2
    ;;
esac
