#!/usr/bin/env bash
# Run Qwen3-VL-Embedding-8B official MMEB-V2 image eval.
# Requires: Qwen3-VL-Embedding repo cloned at $MMEB_ROOT/Qwen3-VL-Embedding and
# image-tasks symlinked into data/evaluation/mmeb_v2/ (run_all.sh sets this up).
# Env overrides: MMEB_ROOT, MODEL_ID, BATCH_SIZE, NUM_WORKERS.
set -euo pipefail
ROOT=${MMEB_ROOT:-/root/autodl-tmp/mmeb_eval}
export HF_ENDPOINT=${HF_ENDPOINT:-https://hf-mirror.com}
export HF_HOME=$ROOT/cache
export HF_HUB_DISABLE_XET=1
export TRANSFORMERS_CACHE=$ROOT/cache
cd "$ROOT/Qwen3-VL-Embedding"
python -m src.evaluation.mmeb_v2.eval_embedding \
  --normalize true \
  --per_device_eval_batch_size "${BATCH_SIZE:-16}" \
  --dataloader_num_workers "${NUM_WORKERS:-8}" \
  --model_name_or_path "${MODEL_ID:-$ROOT/models/Qwen3-VL-Embedding-8B}" \
  --dataset_config scripts/evaluation/mmeb_v2/image.yaml \
  --encode_output_path results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B/image \
  --data_basedir data/evaluation/mmeb_v2 \
  --output_dir "$ROOT/qwen_eval_tmp" \
  "$@"
