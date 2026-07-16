# MMEB-V2 Image 模型评估复现手册

本文档说明如何从零准备服务器，并复现 CLIP、SigLIP2、Qwen3-VL-Embedding-8B 在 MMEB-V2 image-only 任务上的评估。

## 1. 评估范围

只评估 MMEB-V2 的 image 部分，共 36 个任务：

| 分组 | 任务数 | 指标 |
|---|---:|---|
| Image CLS | 10 | hit@1 |
| Image QA | 10 | hit@1 |
| Image RET | 12 | hit@1、Recall@5、Recall@10、MRR@10、nDCG@10 |
| Image GD | 4 | hit@1 |

不评估 video、visdoc、纯文本 MMTEB。

## 2. 当前服务器实际环境

当前已跑通的默认路径如下：

```text
/root/autodl-tmp/mmeb_eval
```

服务器实际情况：

| 项 | 当前值 |
|---|---|
| Python | `Python 3.12.3` |
| CUDA / Torch | `torch 2.8.0+cu128` |
| torchvision | `0.23.0+cu128` |
| transformers | `5.9.0` |
| datasets | `4.8.5` |
| accelerate | `1.13.0` |
| qwen-vl-utils | `0.0.14` |
| modelscope | `1.37.1` |
| 数据盘 | `/root/autodl-tmp`，200GB |
| Qwen3 模型大小 | 约 16GB |
| MMEB-V2 image 数据 | 约 7.7GB |
| HF cache | 约 2.2GB |

Qwen3 官方评估仓库版本：

```text
repo: https://github.com/QwenLM/Qwen3-VL-Embedding.git
commit: c27c3a8bd21c2bd0599339f1869742070823c096
```

当前目录结构：

```text
/root/autodl-tmp/mmeb_eval/
├── Qwen3-VL-Embedding/
├── cache/
├── data/
│   └── image-tasks/
│       └── MMEB/
├── models/
│   └── Qwen3-VL-Embedding-8B/
├── qwen_eval_tmp/
└── results/
```

## 3. 需要的服务器规格

最低建议：

| 项 | 建议 |
|---|---|
| GPU | 24GB 显存以上可跑 CLIP/SigLIP2；Qwen3-8B 建议 80GB+ 显存 |
| CPU | 16 核以上 |
| 内存 | 64GB+ |
| 磁盘 | 至少 100GB，可用 200GB 更稳 |
| 系统 | Linux + CUDA 环境 |

Qwen3-VL-Embedding-8B 推荐 A100 80GB、A800 80GB、H100、RTX PRO 6000 96GB 等。

## 4. 脚本清单

本项目已归档全部关键评估脚本：

```text
docs/evaluation-scripts/
├── eval_clip_siglip_image.py
├── clip_siglip_image.yaml
├── run_mmeb_v2_image_eval.sh
├── summarize_mmeb_v2_image_results.py
├── requirements-clip-siglip.txt
├── requirements-qwen3.txt
└── qwen3-official/
    ├── scripts/evaluation/mmeb_v2/
    │   ├── eval_embedding.sh
    │   ├── image.yaml
    │   ├── image_retrieval.yaml
    │   ├── video.yaml
    │   ├── video_retrieval.yaml
    │   ├── visdoc.yaml
    │   └── visdoc_retrieval.yaml
    └── src/evaluation/mmeb_v2/
        ├── eval_embedding.py
        ├── gather_results.py
        ├── arguments.py
        ├── constant.py
        ├── models.py
        ├── report_score_v2.py
        ├── data/
        └── utils/
```

说明：

- `eval_clip_siglip_image.py` 是 CLIP/SigLIP2 的实际评估脚本。
- `clip_siglip_image.yaml` 是 CLIP/SigLIP2 使用的 36 个 image 任务配置。
- `qwen3-official/` 是 Qwen3 官方 MMEB-V2 评估代码摘录。
- Qwen3 官方代码不是独立单文件，需要完整 `Qwen3-VL-Embedding` 仓库环境。

## 5. 准备工作目录

```bash
mkdir -p /root/autodl-tmp/mmeb_eval
cd /root/autodl-tmp/mmeb_eval

mkdir -p cache data/image-tasks models results
```

建议设置缓存路径，避免写到系统盘：

```bash
export HF_HOME=/root/autodl-tmp/mmeb_eval/cache
export TRANSFORMERS_CACHE=/root/autodl-tmp/mmeb_eval/cache
export HF_ENDPOINT=https://hf-mirror.com
```

如果 Hugging Face 网络正常，可以不设置 `HF_ENDPOINT`。

## 6. 安装依赖

### 6.1 创建 Python 环境

```bash
conda create -n mmeb python=3.12 -y
conda activate mmeb
```

如果服务器默认 Python 已经是 `/root/miniconda3/bin/python`，也可以直接使用当前环境。

### 6.2 安装 Qwen3 官方依赖

官方推荐方式：

```bash
git clone https://github.com/QwenLM/Qwen3-VL-Embedding.git
cd Qwen3-VL-Embedding
bash scripts/setup_environment.sh
```

如果国内访问 GitHub 慢，可使用镜像：

```bash
git clone https://ghfast.top/https://github.com/QwenLM/Qwen3-VL-Embedding.git
```

手动安装方式：

```bash
pip install -r /path/to/docs/evaluation-scripts/requirements-qwen3.txt
```

当前服务器实际关键版本：

```text
torch==2.8.0+cu128
torchvision==0.23.0+cu128
transformers==5.9.0
datasets==4.8.5
accelerate==1.13.0
qwen-vl-utils==0.0.14
modelscope==1.37.1
```

### 6.3 安装 CLIP/SigLIP2 依赖

```bash
pip install -r /path/to/docs/evaluation-scripts/requirements-clip-siglip.txt
```

CLIP/SigLIP2 会通过 `transformers` 自动下载模型权重。

## 7. 下载模型

### 7.1 Qwen3-VL-Embedding-8B

Hugging Face：

```bash
huggingface-cli download Qwen/Qwen3-VL-Embedding-8B \
  --local-dir /root/autodl-tmp/mmeb_eval/models/Qwen3-VL-Embedding-8B
```

ModelScope：

```bash
modelscope download \
  --model qwen/Qwen3-VL-Embedding-8B \
  --local_dir /root/autodl-tmp/mmeb_eval/models/Qwen3-VL-Embedding-8B
```

当前服务器使用的是：

```text
/root/autodl-tmp/mmeb_eval/models/Qwen3-VL-Embedding-8B
```

模型目录应包含：

```text
config.json
model-00001-of-00004.safetensors
model-00002-of-00004.safetensors
model-00003-of-00004.safetensors
model-00004-of-00004.safetensors
model.safetensors.index.json
tokenizer.json
preprocessor_config.json
scripts/qwen3_vl_embedding.py
```

### 7.2 CLIP

模型 ID：

```text
openai/clip-vit-large-patch14
```

无需提前下载，运行 `eval_clip_siglip_image.py` 时会自动从 Hugging Face 下载到缓存。

如需提前下载：

```bash
huggingface-cli download openai/clip-vit-large-patch14 \
  --local-dir /root/autodl-tmp/mmeb_eval/models/clip-vit-large-patch14
```

### 7.3 SigLIP2

模型 ID：

```text
google/siglip2-so400m-patch14-384
```

提前下载：

```bash
huggingface-cli download google/siglip2-so400m-patch14-384 \
  --local-dir /root/autodl-tmp/mmeb_eval/models/siglip2-so400m-patch14-384
```

## 8. 下载 MMEB-V2 image 数据

数据来源：

```text
https://huggingface.co/datasets/TIGER-Lab/MMEB-V2
```

评估元数据来源：

```text
ziyjiang/MMEB_Test_Instruct
```

`MMEB_Test_Instruct` 不需要手动下载，脚本会通过 `datasets.load_dataset()` 自动加载。

image 文件需要放到：

```text
/root/autodl-tmp/mmeb_eval/data/image-tasks/MMEB
```

Hugging Face 下载方式：

```bash
cd /root/autodl-tmp/mmeb_eval

huggingface-cli download TIGER-Lab/MMEB-V2 \
  --repo-type dataset \
  --include "image-tasks/**" \
  --local-dir /root/autodl-tmp/mmeb_eval/data/MMEB-V2
```

如果下载的是压缩包，需要解压后整理为：

```text
/root/autodl-tmp/mmeb_eval/data/image-tasks/MMEB/<task_name>/
```

当前服务器已经整理好的目录示例：

```text
/root/autodl-tmp/mmeb_eval/data/image-tasks/MMEB/ImageNet-1K
/root/autodl-tmp/mmeb_eval/data/image-tasks/MMEB/MSCOCO_i2t
/root/autodl-tmp/mmeb_eval/data/image-tasks/MMEB/FashionIQ
```

完整 image 目录约 7.7GB。

## 9. 放置脚本

把本项目的脚本上传到服务器：

```bash
scp -r docs/evaluation-scripts root@<server>:/root/autodl-tmp/mmeb_eval/docs/
```

CLIP/SigLIP2 脚本需要放到 VLM2Vec 或任意工作目录。推荐：

```bash
mkdir -p /root/autodl-tmp/mmeb_eval/VLM2Vec/experiments/public/eval

cp /root/autodl-tmp/mmeb_eval/docs/evaluation-scripts/eval_clip_siglip_image.py \
  /root/autodl-tmp/mmeb_eval/VLM2Vec/eval_clip_siglip_image.py

cp /root/autodl-tmp/mmeb_eval/docs/evaluation-scripts/clip_siglip_image.yaml \
  /root/autodl-tmp/mmeb_eval/VLM2Vec/experiments/public/eval/image.yaml
```

Qwen3 脚本推荐直接使用官方仓库：

```bash
cd /root/autodl-tmp/mmeb_eval
git clone https://github.com/QwenLM/Qwen3-VL-Embedding.git
```

如果需要用归档版本对照，可查看：

```text
docs/evaluation-scripts/qwen3-official/
```

## 10. 运行 CLIP 评估

```bash
cd /root/autodl-tmp/mmeb_eval/VLM2Vec

HF_HOME=/root/autodl-tmp/mmeb_eval/cache \
TRANSFORMERS_CACHE=/root/autodl-tmp/mmeb_eval/cache \
HF_ENDPOINT=https://hf-mirror.com \
CUDA_VISIBLE_DEVICES=0 \
/root/miniconda3/bin/python eval_clip_siglip_image.py \
  --model-id openai/clip-vit-large-patch14 \
  --kind clip \
  --dataset-config experiments/public/eval/image.yaml \
  --image-root /root/autodl-tmp/mmeb_eval/data/image-tasks/MMEB \
  --output-dir /root/autodl-tmp/mmeb_eval/results/clip-vit-large-patch14-image \
  --batch-size 64
```

输出：

```text
/root/autodl-tmp/mmeb_eval/results/clip-vit-large-patch14-image/
├── <task>_pred.jsonl
├── <task>_score.json
└── summary.json
```

## 11. 运行 SigLIP2 评估

```bash
cd /root/autodl-tmp/mmeb_eval/VLM2Vec

HF_HOME=/root/autodl-tmp/mmeb_eval/cache \
TRANSFORMERS_CACHE=/root/autodl-tmp/mmeb_eval/cache \
HF_ENDPOINT=https://hf-mirror.com \
CUDA_VISIBLE_DEVICES=0 \
/root/miniconda3/bin/python eval_clip_siglip_image.py \
  --model-id google/siglip2-so400m-patch14-384 \
  --kind siglip \
  --dataset-config experiments/public/eval/image.yaml \
  --image-root /root/autodl-tmp/mmeb_eval/data/image-tasks/MMEB \
  --output-dir /root/autodl-tmp/mmeb_eval/results/siglip2-so400m-patch14-384-image \
  --batch-size 64
```

输出：

```text
/root/autodl-tmp/mmeb_eval/results/siglip2-so400m-patch14-384-image/
```

## 12. 运行 Qwen3-VL-Embedding-8B 评估

进入官方仓库：

```bash
cd /root/autodl-tmp/mmeb_eval/Qwen3-VL-Embedding
```

只跑 image 配置：

```bash
HF_ENDPOINT=https://hf-mirror.com \
HF_HOME=/root/autodl-tmp/mmeb_eval/cache \
TRANSFORMERS_CACHE=/root/autodl-tmp/mmeb_eval/cache \
CUDA_VISIBLE_DEVICES=0 \
/root/miniconda3/bin/python -m src.evaluation.mmeb_v2.eval_embedding \
  --normalize true \
  --per_device_eval_batch_size 8 \
  --dataloader_num_workers 4 \
  --model_name_or_path /root/autodl-tmp/mmeb_eval/models/Qwen3-VL-Embedding-8B \
  --dataset_config scripts/evaluation/mmeb_v2/image.yaml \
  --encode_output_path results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B/image \
  --data_basedir data/evaluation/mmeb_v2 \
  --output_dir /root/autodl-tmp/mmeb_eval/qwen_eval_tmp
```

汇总 Qwen3 官方结果：

```bash
/root/miniconda3/bin/python -m src.evaluation.mmeb_v2.gather_results \
  results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B \
  --output_dir results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B
```

Qwen3 输出目录：

```text
/root/autodl-tmp/mmeb_eval/Qwen3-VL-Embedding/results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B/
├── image/
├── summary.tsv
└── details.tsv
```

注意：

- `results/evaluation/mmeb_v2` 是官方仓库内的相对输出目录，不是外部下载地址。
- 官方 `eval_embedding.sh` 默认跑 `image`、`video`、`visdoc`，本次只跑 image，所以使用上面的 Python module 命令更直接。
- 如果显存不足，可把 `--per_device_eval_batch_size 8` 改小，例如 4、2、1。

## 13. 一键运行入口

本项目提供了统一入口：

```bash
bash docs/evaluation-scripts/run_mmeb_v2_image_eval.sh clip
bash docs/evaluation-scripts/run_mmeb_v2_image_eval.sh siglip2
bash docs/evaluation-scripts/run_mmeb_v2_image_eval.sh qwen3
bash docs/evaluation-scripts/run_mmeb_v2_image_eval.sh all
```

如果脚本不在 `/root/autodl-tmp/mmeb_eval/docs/evaluation-scripts/`，需要调整其中的 `ROOT` 路径。

## 14. 汇总结果

CLIP：

```bash
python docs/evaluation-scripts/summarize_mmeb_v2_image_results.py \
  /root/autodl-tmp/mmeb_eval/results/clip-vit-large-patch14-image \
  --model-name CLIP
```

SigLIP2：

```bash
python docs/evaluation-scripts/summarize_mmeb_v2_image_results.py \
  /root/autodl-tmp/mmeb_eval/results/siglip2-so400m-patch14-384-image \
  --model-name SigLIP2
```

Qwen3：

```bash
python docs/evaluation-scripts/summarize_mmeb_v2_image_results.py \
  /root/autodl-tmp/mmeb_eval/Qwen3-VL-Embedding/results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B \
  --model-name Qwen3-VL-Embedding-8B
```

汇总脚本会输出：

```text
Image CLS
Image QA
Image RET
Image GD
Image Overall
Recall@1
Recall@5
Recall@10
MRR@10
nDCG@10
```

## 15. 评估逻辑

每条样本包含 query、candidates 和 label。评估流程：

```text
query_embedding = normalize(model.encode(query))
candidate_embeddings = normalize(model.encode(candidates))
scores = candidate_embeddings @ query_embedding
ranking = sort(candidates, by=scores, descending=True)
metrics = evaluate(ranking, labels)
```

指标：

| 指标 | 含义 |
|---|---|
| hit@1 / Recall@1 | Top 1 是否命中正确答案 |
| Recall@5 | Top 5 是否包含正确答案 |
| Recall@10 | Top 10 是否包含正确答案 |
| MRR@10 | 正确答案在前 10 的倒数排名均值 |
| nDCG@10 | 前 10 排序质量 |

## 16. 常见问题

### 16.1 Hugging Face 下载慢

使用镜像：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

或者模型使用 ModelScope 下载。

### 16.2 Qwen3 显存不足

降低 batch size：

```bash
--per_device_eval_batch_size 4
```

或使用 80GB 以上显存的 GPU。

### 16.3 Qwen3 官方脚本默认跑 video/visdoc

不要直接用默认 `eval_embedding.sh` 跑全量。为了只跑 image，请使用：

```bash
--dataset_config scripts/evaluation/mmeb_v2/image.yaml
```

### 16.4 CLIP/SigLIP2 和 Qwen3 是否完全同脚本

不是。

- Qwen3 使用官方 `src.evaluation.mmeb_v2.eval_embedding`。
- CLIP/SigLIP2 使用 `eval_clip_siglip_image.py` 适配双塔模型。

但它们使用相同 MMEB-V2 image 任务和相同排序指标，因此可以做业务检索对比。

## 17. 外部来源

| 资源 | 地址 |
|---|---|
| Qwen3-VL-Embedding 官方仓库 | `https://github.com/QwenLM/Qwen3-VL-Embedding` |
| Qwen3-VL-Embedding-8B Hugging Face | `https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B` |
| Qwen3-VL-Embedding-8B ModelScope | `https://modelscope.cn/models/qwen/Qwen3-VL-Embedding-8B` |
| MMEB-V2 数据集 | `https://huggingface.co/datasets/TIGER-Lab/MMEB-V2` |
| MMEB 测试元数据 | `https://huggingface.co/datasets/ziyjiang/MMEB_Test_Instruct` |
| CLIP 模型 | `https://huggingface.co/openai/clip-vit-large-patch14` |
| SigLIP2 模型 | `https://huggingface.co/google/siglip2-so400m-patch14-384` |
