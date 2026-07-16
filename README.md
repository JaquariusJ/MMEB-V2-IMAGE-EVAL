# MMEB-V2 Image Model Evaluation

独立的 MMEB-V2 image-only 模型对比项目。它评估 CLIP、SigLIP2 和
Qwen3-VL-Embedding-8B 在图像分类、视觉问答、检索及 grounding 任务上的表现。

## 内容

- `docs/evaluation-scripts/`：评测、结果汇总与复现脚本；其中包含 Qwen3 官方评测代码摘录。
- `docs/mmeb-v2-image-model-evaluation-report.md`：已有的对比报告。
- `docs/assets/`：报告配图。

## 在 GPU 服务器运行

完整环境准备见
[`docs/evaluation-scripts/MMEB_V2_IMAGE_REPRODUCE_GUIDE.md`](docs/evaluation-scripts/MMEB_V2_IMAGE_REPRODUCE_GUIDE.md)。
默认服务器工作目录是 `/root/autodl-tmp/mmeb_eval`；上传或克隆本项目后，确保
`docs/evaluation-scripts/run_mmeb_v2_image_eval.sh` 中的 `ROOT` 与 `PY` 和实际环境一致。

```bash
# 在服务器的评测工作目录运行
bash docs/evaluation-scripts/run_mmeb_v2_image_eval.sh clip
bash docs/evaluation-scripts/run_mmeb_v2_image_eval.sh siglip2
bash docs/evaluation-scripts/run_mmeb_v2_image_eval.sh qwen3
```

评测会下载模型和数据；不要把本地缓存、权重或输出结果提交到版本库。

## 说明

该项目只保留评测代码与报告，不含 MMEB-V2 数据集、模型权重、Qwen3 官方完整仓库或任何运行结果。
它们需要在目标 GPU 服务器上按复现手册下载和生成。
