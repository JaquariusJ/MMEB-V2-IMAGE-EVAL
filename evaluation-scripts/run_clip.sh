#!/usr/bin/env bash
# Run CLIP MMEB-V2 image eval. Env overrides: MMEB_ROOT, MODEL_ID, IMAGE_ROOT,
# OUTPUT_DIR, BATCH_SIZE. Extra args passed to eval_clip_siglip_image.py (e.g. --tasks ImageNet-1K).
set -euo pipefail
ROOT=${MMEB_ROOT:-/root/autodl-tmp/mmeb_eval}
export HF_ENDPOINT=${HF_ENDPOINT:-https://hf-mirror.com}
export HF_HOME=$ROOT/cache
export HF_HUB_DISABLE_XET=1
export TRANSFORMERS_CACHE=$ROOT/cache
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
python "$SCRIPT_DIR/eval_clip_siglip_image.py" \
  --model-id "${MODEL_ID:-$ROOT/models/clip-vit-large-patch14}" \
  --kind clip \
  --dataset-config "$SCRIPT_DIR/clip_siglip_image.yaml" \
  --image-root "${IMAGE_ROOT:-$ROOT/data/image-tasks/MMEB}" \
  --output-dir "${OUTPUT_DIR:-$ROOT/results/clip-vit-large-patch14-image}" \
  --batch-size "${BATCH_SIZE:-128}" \
  "$@"
