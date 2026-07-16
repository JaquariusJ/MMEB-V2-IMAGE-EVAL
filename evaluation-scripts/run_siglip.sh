#!/usr/bin/env bash
# Run SigLIP2 MMEB-V2 image eval. Env overrides: MMEB_ROOT, MODEL_ID, IMAGE_ROOT,
# OUTPUT_DIR, BATCH_SIZE. Extra args passed to eval_clip_siglip_image.py.
set -euo pipefail
ROOT=${MMEB_ROOT:-/root/autodl-tmp/mmeb_eval}
export HF_ENDPOINT=${HF_ENDPOINT:-https://hf-mirror.com}
export HF_HOME=$ROOT/cache
export HF_HUB_DISABLE_XET=1
export TRANSFORMERS_CACHE=$ROOT/cache
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
python "$SCRIPT_DIR/eval_clip_siglip_image.py" \
  --model-id "${MODEL_ID:-$ROOT/models/siglip2-so400m-patch14-384}" \
  --kind siglip \
  --dataset-config "$SCRIPT_DIR/clip_siglip_image.yaml" \
  --image-root "${IMAGE_ROOT:-$ROOT/data/image-tasks/MMEB}" \
  --output-dir "${OUTPUT_DIR:-$ROOT/results/siglip2-so400m-patch14-384-image}" \
  --batch-size "${BATCH_SIZE:-64}" \
  "$@"
