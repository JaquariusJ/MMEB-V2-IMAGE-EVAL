# MMEB-V2 Image Evaluation Scripts

复现 CLIP、SigLIP2、Qwen3-VL-Embedding-8B 在 MMEB-V2 image-only 任务上的评估;
支持一键自动下载、自定义检索数据集评估、远程模型(FastAPI/vllm)调用评估。

完整从零复现手册见 `MMEB_V2_IMAGE_REPRODUCE_GUIDE.md`。

## 1. 一键运行(推荐)

`run_all.sh` 自动检测依赖/数据/模型,缺失则下载,然后跑评估并汇总:

```bash
# 全部三模型,自动下载模型+数据,默认工作目录 /root/autodl-tmp/mmeb_eval
bash run_all.sh

# 只跑部分模型
bash run_all.sh --models clip,siglip2

# 指定工作目录
bash run_all.sh --root /path/to/work

# 用已有模型/数据,跳过下载
bash run_all.sh --skip-download

# 调整 batch size
bash run_all.sh --batch-size 64

# 用自定义图片数据跑 CLIP/SigLIP2(替代 MMEB-V2 数据,跳过 MMEB 数据下载)
bash run_all.sh --models clip,siglip2 --image-root /my/image/data
```

说明:
- 下载走 hf-mirror + 禁用 hf-xet(避免 401);大文件用 `lib/multi_dl.py` 多连接。
- Qwen3 评估会自动 clone 官方仓库并建立 image-tasks 软链接。
- 自定义 `--image-root` 只支持 CLIP/SigLIP2(Qwen3 走官方 MMEB 流程);自定义检索数据请用第 3 节。

## 2. 单模型运行

环境变量可覆盖:`MMEB_ROOT`、`MODEL_ID`、`IMAGE_ROOT`、`OUTPUT_DIR`、`BATCH_SIZE`。

```bash
bash run_clip.sh           # CLIP
bash run_siglip.sh         # SigLIP2
bash run_qwen3.sh          # Qwen3(需先有 Qwen3 官方仓库 + image-tasks 软链接,run_all.sh 会自动处理)
```

额外参数透传给评估脚本,例如只跑部分任务验证管线:

```bash
bash run_clip.sh --tasks ImageNet-1K
```

## 3. 自定义检索数据集评估

`lib/eval_custom_retrieval.py` 支持自己的文搜图/以图搜图数据集评估。数据格式见
`CUSTOM_RETRIEVAL_DATASET_GUIDE.md`(`queries.jsonl` / `corpus.jsonl` / `qrels.jsonl`)。

支持四种后端:`clip` / `siglip` / `qwen3` / `remote`。

```bash
# CLIP
python lib/eval_custom_retrieval.py --kind clip \
  --model-id /path/to/clip-vit-large-patch14 \
  --data-root /my/data --output-dir /out/clip

# Qwen3(需官方仓库提供 Qwen3VLEmbedder)
python lib/eval_custom_retrieval.py --kind qwen3 \
  --model-id /path/to/Qwen3-VL-Embedding-8B \
  --qwen3-repo /path/to/Qwen3-VL-Embedding \
  --data-root /my/data --output-dir /out/qwen3

# 远程模型(见第 4 节)
python lib/eval_custom_retrieval.py --kind remote \
  --endpoint http://host:8000/embed \
  --data-root /my/data --output-dir /out/remote
```

输出 `summary.json`(Recall@1/5/10、MRR@10、nDCG@10)和 `predictions.jsonl`。

## 4. 远程模型评估(FastAPI / vllm)

评估机器不需要 GPU/模型权重,通过 HTTP 调用你部署的 embedding 服务:

**服务端**:用 `example_embedding_server.py` 把本地模型包装成 `/embed` 服务:

```bash
pip install fastapi uvicorn
python example_embedding_server.py --kind clip --model-id /path/to/clip --port 8000
# Qwen3:
python example_embedding_server.py --kind qwen3 --model-id /path/to/Qwen3-8B \
  --qwen3-repo /path/to/Qwen3-VL-Embedding --port 8000
```

**评估端**:`--kind remote --endpoint http://<server>:8000/embed` 即可(MMEB-V2 评估和自定义数据评估都支持)。

```bash
# MMEB-V2 全量评估,用远程模型
python eval_clip_siglip_image.py --kind remote \
  --endpoint http://host:8000/embed \
  --dataset-config clip_siglip_image.yaml \
  --image-root /root/autodl-tmp/mmeb_eval/data/image-tasks/MMEB \
  --output-dir /results/remote --batch-size 128
```

**协议**: `POST /embed {"items":[{"text":"...","image_base64":"..."}]}` -> `{"embeddings":[[...],...]}`。
vllm 部署(`vllm serve <model> --task embed`)可写一个薄适配层把 image_base64 解码后调用 vllm embedding,返回相同形状。

## 5. 文件说明

| 文件 | 说明 |
|---|---|
| `run_all.sh` | **一站式入口**:自动下载依赖/数据/模型 + 跑评估 + 汇总 |
| `run_clip.sh` / `run_siglip.sh` / `run_qwen3.sh` | 单模型评估脚本(参数化,环境变量覆盖) |
| `lib/download_hf.py` | 下载模型权重(snapshot_download,禁用 xet) |
| `lib/multi_dl.py` | 多连接下载大文件(MMEB-V2 image 数据 tar.gz) |
| `lib/eval_custom_retrieval.py` | 自定义检索数据集评估(clip/siglip/qwen3/remote) |
| `example_embedding_server.py` | FastAPI embedding 服务示例(远程评估用) |
| `eval_clip_siglip_image.py` | CLIP/SigLIP2 MMEB-V2 评估脚本(含 remote 分支) |
| `clip_siglip_image.yaml` | 36 个 image 任务配置 |
| `summarize_mmeb_v2_image_results.py` | 从 `*_score.json` 汇总官方分组 hit@1 + RET 扩展指标 |
| `requirements-clip-siglip.txt` / `requirements-qwen3.txt` | 依赖 |
| `MMEB_V2_IMAGE_REPRODUCE_GUIDE.md` | 从零复现完整手册 |
| `CUSTOM_RETRIEVAL_DATASET_GUIDE.md` | 自定义文搜图/以图搜图数据集与 label 准备指南 |
| `qwen3-official/` | Qwen3 官方 MMEB-V2 评估代码摘录(实际运行用完整官方仓库,run_all.sh 自动 clone) |

## 6. Qwen3 官方评估说明

Qwen3 的实际评估入口是官方仓库的 Python module `src.evaluation.mmeb_v2.eval_embedding`,
不是单个独立脚本。`run_qwen3.sh` / `run_all.sh` 会在 `$MMEB_ROOT/Qwen3-VL-Embedding` 下运行,
并自动把 image-tasks 软链接到 `data/evaluation/mmeb_v2/image-tasks`。

`results/evaluation/mmeb_v2` 是官方仓库内的相对输出目录,完整路径示例:

```text
$MMEB_ROOT/Qwen3-VL-Embedding/results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B
```

Qwen3 评估后用 `gather_results` 汇总,再用 `summarize_mmeb_v2_image_results.py` 算指标。

## 7. 汇总结果

```bash
python summarize_mmeb_v2_image_results.py <result_dir> --model-name <name>
# 例如
python summarize_mmeb_v2_image_results.py \
  /root/autodl-tmp/mmeb_eval/results/clip-vit-large-patch14-image --model-name CLIP
```

输出 Image CLS / QA / RET / GD / Overall(hit@1)及 RET 扩展指标(Recall@1/5/10、MRR@10、nDCG@10)。
