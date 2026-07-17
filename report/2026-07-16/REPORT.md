# MMEB-V2 Image 评估报告(2026-07-16)

- 运行日期:2026-07-16
- 评估范围:MMEB-V2 image-only,36 个任务(CLS 10 / QA 10 / RET 12 / GD 4)
- GPU:NVIDIA RTX PRO 6000 Blackwell,96GB 显存
- 环境:torch 2.8.0+cu128,transformers 5.14.1,datasets 5.0.0
- 对比基准:`../2026-05-28/`(历史报告)
- 评估脚本:`../../evaluation-scripts/`(run_clip.sh / run_siglip.sh / summarize_mmeb_v2_image_results.py)

## 1. 官方主指标(hit@1 × 100)

| Model | Image CLS | Image QA | Image RET | Image GD | Image Overall |
|---|---:|---:|---:|---:|---:|
| CLIP `openai/clip-vit-large-patch14` | 55.3 | 10.5 | 52.2 | 53.3 | 41.6 |
| SigLIP2 `google/siglip2-so400m-patch14-384` | 55.4 | 9.1 | 43.8 | 62.1 | 39.4 |
| Qwen3-VL-Embedding-8B | — | — | — | — | 待跑(关机中断) |

## 2. Image RET 扩展指标(12 检索任务,百分制)

| Model | Recall@1 | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---:|---:|---:|---:|---:|
| CLIP | 52.2 | 74.3 | 81.2 | 61.8 | 66.5 |
| SigLIP2 | 43.8 | 66.0 | 73.2 | 53.5 | 58.2 |
| Qwen3 | — | — | — | — | 待跑 |

## 3. 与历史报告(2026-05-28)对比

CLIP 和 SigLIP2 的全部指标与历史报告**完全一致**,复现成功(差异 0.1 以内属四舍五入)。

| Model | 指标 | 本次 07-16 | 历史 05-28 | 匹配 |
|---|---|---:|---:|---|
| CLIP | Overall | 41.6 | 41.6 | ✓ |
| CLIP | CLS / QA / RET / GD | 55.3 / 10.5 / 52.2 / 53.3 | 55.3 / 10.5 / 52.2 / 53.3 | ✓ |
| CLIP | R@1 / R@5 / R@10 | 52.2 / 74.3 / 81.2 | 52.2 / 74.3 / 81.3 | ✓ |
| CLIP | MRR@10 / nDCG@10 | 61.8 / 66.5 | 61.8 / 66.5 | ✓ |
| SigLIP2 | Overall | 39.4 | 39.4 | ✓ |
| SigLIP2 | CLS / QA / RET / GD | 55.4 / 9.1 / 43.8 / 62.1 | 55.4 / 9.1 / 43.8 / 62.1 | ✓ |
| SigLIP2 | R@1 / R@5 / R@10 | 43.8 / 66.0 / 73.2 | 43.8 / 66.0 / 73.2 | ✓ |
| SigLIP2 | MRR@10 / nDCG@10 | 53.5 / 58.2 | 53.5 / 58.2 | ✓ |

## 4. 完成状态

- ✅ **CLIP**:完成,与历史报告完全匹配
- ✅ **SigLIP2**:完成,与历史报告完全匹配
- ⏳ **Qwen3-VL-Embedding-8B**:未跑完(服务器关机中断),待补。历史报告基准 Overall = 80.1

## 5. 结果文件

- `clip_summary.json`:CLIP 36 任务逐任务指标(hit@1/5/10、recall、mrr、ndcg)
- `siglip_summary.json`:SigLIP2 36 任务逐任务指标
- Qwen3 跑完后补充 `qwen3_summary.json` 并更新本报告第 1/2/3/4 节

## 6. 复现命令

```bash
# 一键(下次换服务器)
bash evaluation-scripts/run_all.sh --models clip,siglip2,qwen3

# 单模型
bash evaluation-scripts/run_clip.sh
bash evaluation-scripts/run_siglip.sh
bash evaluation-scripts/run_qwen3.sh

# 汇总
python evaluation-scripts/summarize_mmeb_v2_image_results.py <result_dir> --model-name <name>
```
