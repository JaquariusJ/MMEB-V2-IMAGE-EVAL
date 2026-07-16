#!/usr/bin/env bash
# One-stop MMEB-V2 image evaluation: ensure deps/data/models, run eval, summarize.
#
# Usage:
#   bash run_all.sh                            # all models, auto-download, default root
#   bash run_all.sh --models clip,siglip2      # subset (clip|siglip2|qwen3|all)
#   bash run_all.sh --root /path/to/work       # custom workspace
#   bash run_all.sh --skip-download            # use existing data/models, eval only
#   bash run_all.sh --batch-size 64            # override batch size
#   bash run_all.sh --image-root /my/data      # custom image data (CLIP/SigLIP2 only,
#                                              #   skips MMEB data download; for custom
#                                              #   retrieval use lib/eval_custom_retrieval.py)
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT=${MMEB_ROOT:-/root/autodl-tmp/mmeb_eval}
MODELS="all"
SKIP_DOWNLOAD=0
BATCH_SIZE=""
CUSTOM_IMAGE_ROOT=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --models) MODELS=$2; shift 2;;
    --root) ROOT=$2; shift 2;;
    --skip-download) SKIP_DOWNLOAD=1; shift;;
    --batch-size) BATCH_SIZE=$2; shift 2;;
    --image-root) CUSTOM_IMAGE_ROOT=$2; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

export MMEB_ROOT=$ROOT
export HF_ENDPOINT=${HF_ENDPOINT:-https://hf-mirror.com}
export HF_HOME=$ROOT/cache
export HF_HUB_DISABLE_XET=1
export TRANSFORMERS_CACHE=$ROOT/cache
export HF_DATASETS_CACHE=$ROOT/cache/datasets

mkdir -p "$ROOT"/{cache,data/image-tasks,models,results,qwen_eval_tmp}

WANT_CLIP=0; WANT_SIGLIP=0; WANT_QWEN3=0
case $MODELS in
  all) WANT_CLIP=1; WANT_SIGLIP=1; WANT_QWEN3=1;;
  *) for m in $(echo "$MODELS" | tr ',' ' '); do
       case $m in
         clip) WANT_CLIP=1;; siglip2|siglip) WANT_SIGLIP=1;; qwen3) WANT_QWEN3=1;;
         *) echo "unknown model: $m" >&2; exit 2;;
       esac
     done;;
esac

ensure_deps() {
  python -c "import transformers,datasets,accelerate,numpy,PIL,yaml,tqdm" 2>/dev/null && return
  echo "[run_all] installing deps..."
  pip install -r "$SCRIPT_DIR/requirements-clip-siglip.txt" -r "$SCRIPT_DIR/requirements-qwen3.txt" \
    -i https://pypi.tuna.tsinghua.edu.cn/simple
}

ensure_data() {
  if [ -n "$CUSTOM_IMAGE_ROOT" ]; then
    echo "[run_all] using custom image-root: $CUSTOM_IMAGE_ROOT"; return
  fi
  if [ -d "$ROOT/data/image-tasks/MMEB/ImageNet-1K" ]; then
    echo "[run_all] data exists"; return
  fi
  if [ "$SKIP_DOWNLOAD" = "1" ]; then echo "[run_all] data missing but --skip-download"; return; fi
  echo "[run_all] downloading MMEB-V2 image data (multi-conn)..."
  mkdir -p "$ROOT/data/MMEB-V2/image-tasks"
  python "$SCRIPT_DIR/lib/multi_dl.py" \
    https://hf-mirror.com/datasets/TIGER-Lab/MMEB-V2/resolve/main/image-tasks/mmeb_v1.tar.gz \
    "$ROOT/data/MMEB-V2/image-tasks/mmeb_v1.tar.gz" 16
  echo "[run_all] extracting..."
  tar -xzf "$ROOT/data/MMEB-V2/image-tasks/mmeb_v1.tar.gz" -C "$ROOT/data/image-tasks/"
}

ensure_model() {
  local name=$1 target=$2 path=$3
  [ -d "$path" ] && { echo "[run_all] $name exists"; return; }
  if [ "$SKIP_DOWNLOAD" = "1" ]; then echo "[run_all] $name missing but --skip-download"; return; fi
  echo "[run_all] downloading $name..."
  python "$SCRIPT_DIR/lib/download_hf.py" "$target" --root "$ROOT"
}

ensure_qwen3_repo() {
  if [ ! -d "$ROOT/Qwen3-VL-Embedding/src" ]; then
    echo "[run_all] cloning Qwen3-VL-Embedding repo..."
    (cd "$ROOT" && (git clone https://ghfast.top/https://github.com/QwenLM/Qwen3-VL-Embedding.git \
      || git clone https://github.com/QwenLM/Qwen3-VL-Embedding.git))
  fi
  local mmeb_dir="$ROOT/Qwen3-VL-Embedding/data/evaluation/mmeb_v2"
  mkdir -p "$mmeb_dir"
  if [ ! -e "$mmeb_dir/image-tasks" ]; then
    ln -s "$ROOT/data/image-tasks/MMEB" "$mmeb_dir/image-tasks"
  fi
}

echo "=== [1/4] deps ==="; ensure_deps
echo "=== [2/4] data ==="; ensure_data
echo "=== [3/4] models ==="
[ $WANT_CLIP = 1 ] && ensure_model CLIP clip "$ROOT/models/clip-vit-large-patch14"
[ $WANT_SIGLIP = 1 ] && ensure_model SigLIP2 siglip "$ROOT/models/siglip2-so400m-patch14-384"
[ $WANT_QWEN3 = 1 ] && ensure_model Qwen3 qwen3 "$ROOT/models/Qwen3-VL-Embedding-8B"
[ $WANT_QWEN3 = 1 ] && [ -z "$CUSTOM_IMAGE_ROOT" ] && ensure_qwen3_repo

echo "=== [4/4] eval ==="
[ -n "$BATCH_SIZE" ] && export BATCH_SIZE
[ -n "$CUSTOM_IMAGE_ROOT" ] && export IMAGE_ROOT="$CUSTOM_IMAGE_ROOT"

if [ $WANT_CLIP = 1 ]; then
  echo "--- CLIP ---"
  bash "$SCRIPT_DIR/run_clip.sh"
  python "$SCRIPT_DIR/summarize_mmeb_v2_image_results.py" "$ROOT/results/clip-vit-large-patch14-image" --model-name CLIP
fi
if [ $WANT_SIGLIP = 1 ]; then
  echo "--- SigLIP2 ---"
  bash "$SCRIPT_DIR/run_siglip.sh"
  python "$SCRIPT_DIR/summarize_mmeb_v2_image_results.py" "$ROOT/results/siglip2-so400m-patch14-384-image" --model-name SigLIP2
fi
if [ $WANT_QWEN3 = 1 ] && [ -z "$CUSTOM_IMAGE_ROOT" ]; then
  echo "--- Qwen3 ---"
  bash "$SCRIPT_DIR/run_qwen3.sh"
  (cd "$ROOT/Qwen3-VL-Embedding" && python -m src.evaluation.mmeb_v2.gather_results \
    results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B \
    --output_dir results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B)
  python "$SCRIPT_DIR/summarize_mmeb_v2_image_results.py" \
    "$ROOT/Qwen3-VL-Embedding/results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B" --model-name Qwen3
fi
echo "=== ALL DONE ==="
