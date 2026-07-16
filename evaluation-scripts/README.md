# MMEB-V2 Image Evaluation Scripts

这些脚本用于复现报告中的 MMEB-V2 image-only 评估。

完整从零复现步骤见：

```text
MMEB_V2_IMAGE_REPRODUCE_GUIDE.md
```

## 文件说明

| 文件 | 说明 |
|---|---|
| `eval_clip_siglip_image.py` | CLIP / SigLIP2 的实际评估脚本，负责加载 MMEB-V2 image 任务、编码 embedding、排序并输出 `*_score.json` / `*_pred.jsonl` |
| `run_mmeb_v2_image_eval.sh` | 默认新机器路径下的运行入口，可分别运行 `clip`、`siglip2`、`qwen3` 或 `all` |
| `summarize_mmeb_v2_image_results.py` | 从结果目录读取 `*_score.json`，汇总官方 image 指标和业务检索扩展指标 |
| `qwen3-official/` | Qwen3 官方 MMEB-V2 评估入口文件和 image 配置摘录 |
| `requirements-qwen3.txt` | Qwen3 官方评估所需主要依赖 |
| `requirements-clip-siglip.txt` | CLIP/SigLIP2 baseline 评估所需主要依赖 |
| `MMEB_V2_IMAGE_REPRODUCE_GUIDE.md` | 从服务器准备到结果汇总的完整操作手册 |
| `CUSTOM_RETRIEVAL_DATASET_GUIDE.md` | 自定义文搜图/以图搜图数据集和 label 准备指南 |

## Qwen3 官方评估脚本说明

Qwen3 的实际评估入口不是单个独立脚本，而是官方仓库里的 Python module：

```text
src/evaluation/mmeb_v2/eval_embedding.py
```

本目录已复制关键文件：

```text
qwen3-official/src/evaluation/mmeb_v2/eval_embedding.py
qwen3-official/src/evaluation/mmeb_v2/gather_results.py
qwen3-official/scripts/evaluation/mmeb_v2/image.yaml
qwen3-official/scripts/evaluation/mmeb_v2/eval_embedding.sh
```

注意：这些文件依赖完整的 `Qwen3-VL-Embedding` 官方仓库环境，不能只拿这几个文件单独运行。实际运行时应在官方仓库根目录执行：

```bash
cd /root/autodl-tmp/mmeb_eval/Qwen3-VL-Embedding

/root/miniconda3/bin/python -m src.evaluation.mmeb_v2.eval_embedding ...
```

`results/evaluation/mmeb_v2` 不是外部下载地址，而是官方仓库内的相对输出目录。完整结果目录示例：

```text
/root/autodl-tmp/mmeb_eval/Qwen3-VL-Embedding/results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B
```

## 运行方式

```bash
cd /root/autodl-tmp/mmeb_eval

# 跑 CLIP
bash docs/evaluation-scripts/run_mmeb_v2_image_eval.sh clip

# 跑 SigLIP2
bash docs/evaluation-scripts/run_mmeb_v2_image_eval.sh siglip2

# 跑 Qwen3
bash docs/evaluation-scripts/run_mmeb_v2_image_eval.sh qwen3
```

如果是在远程机器的 `$ROOT/VLM2Vec` 目录运行 CLIP/SigLIP2，需要把 `eval_clip_siglip_image.py` 放到该目录下，或调整 `run_mmeb_v2_image_eval.sh` 中的路径。

## 汇总结果

```bash
python docs/evaluation-scripts/summarize_mmeb_v2_image_results.py \
  /root/autodl-tmp/mmeb_eval/results/clip-vit-large-patch14-image \
  --model-name CLIP
```

Qwen3 官方结果目录通常是：

```text
/root/autodl-tmp/mmeb_eval/Qwen3-VL-Embedding/results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B
```

可以这样汇总：

```bash
python docs/evaluation-scripts/summarize_mmeb_v2_image_results.py \
  /root/autodl-tmp/mmeb_eval/Qwen3-VL-Embedding/results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B \
  --model-name Qwen3-VL-Embedding-8B
```
