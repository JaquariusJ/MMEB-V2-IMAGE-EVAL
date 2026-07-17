# MMEB-V2 Image 评估 - 交接文件

> 写于 2026-07-16 服务器关机前。明天新 agent 读此文件继续执行未完成任务。

## 1. 背景与目标

评估 CLIP、SigLIP2、Qwen3-VL-Embedding-8B 三个模型在 MMEB-V2 image-only(36 个任务)上的表现,
验证能复现历史报告(`mmeb-v2-image-model-evaluation-report.md`,2026-05-28),并跑完全部三模型对比。

报告里历史结果(hit@1 × 100):

| Model | Overall | CLS | QA | RET | GD |
|---|---:|---:|---:|---:|---:|
| CLIP | 41.6 | 55.3 | 10.5 | 52.2 | 53.3 |
| SigLIP2 | 39.4 | 55.4 | 9.1 | 43.8 | 62.1 |
| Qwen3 | 80.1 | 74.2 | 81.1 | 80.1 | 92.3 |

RET 扩展指标见报告 6.2 节(CLIP: R@1 52.2 / R@5 74.3 / R@10 81.3 / MRR@10 61.8 / nDCG@10 66.5)。

## 2. 服务器信息

- **SSH**: `ssh -p 38038 root@connect.bjb1.seetacloud.com`
- **密码**: `Xk24PVg+bysp`
- **GPU**: NVIDIA RTX PRO 6000 Blackwell, 96GB 显存
- **工作目录**: `/root/autodl-tmp/mmeb_eval`
- **Python**: `/root/miniconda3/bin/python`(3.12,torch 2.8.0+cu128,transformers 5.14.1,datasets 5.0.0)
- **磁盘**: `/root/autodl-tmp` 约 79GB

⚠️ 密码已在对话中暴露,任务跑完后建议在 autodl 控制台改密码。

### 连接方法(无 sshpass,用 paramiko)

本地是 Windows,没有 sshpass。用 paramiko 脚本连接(密码走环境变量)。若 `C:\Users\Administrator\AppData\Local\Temp\ssh_run.py` 还在可直接用;否则重建:

```python
# ssh_run.py —— 执行远程命令
import os, sys, shlex, paramiko
HOST="connect.bjb1.seetacloud.com"; PORT=38038; USER="root"
cmd = sys.argv[1] if len(sys.argv)>1 else "echo ok"
passwd = os.environ.get("SSH_PASS") or sys.exit("set SSH_PASS")
full = f"bash -lc {shlex.quote(cmd)}"
c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=PORT, username=USER, password=passwd, timeout=30, banner_timeout=30, auth_timeout=30)
si, so, se = c.exec_command(full, timeout=int(os.environ.get("SSH_TIMEOUT","120")))
sys.stdout.write(so.read().decode("utf-8","replace")); sys.stderr.write(se.read().decode("utf-8","replace"))
sys.exit(so.channel.recv_exit_status())
```

用法: `SSH_PASS='Xk24PVg+bysp' python ssh_run.py '远程命令'`

⚠️ 注意:`pkill -f xxx` 若模式出现在 ssh_run 的命令字符串里会误杀自身 shell,用 `pkill -f "python /path/to/script.py"` 这种精确模式,或写脚本文件执行。

## 3. 当前进度(关机前)

### ✅ 已完成
- **依赖**:transformers/datasets/accelerate/qwen-vl-utils 等已装(pip 升级到 26.1.2 修复了 resolvelib bug)
- **数据**:MMEB-V2 image 数据已下载+解压,`/root/autodl-tmp/mmeb_eval/data/image-tasks/MMEB/`(36 个 task 目录)
- **模型**:CLIP、SigLIP2、Qwen3-8B 全部下载到 `models/`
- **Qwen3 官方仓库**:已 clone 到 `Qwen3-VL-Embedding/`,image-tasks 软链接已建(`data/evaluation/mmeb_v2/image-tasks -> /root/autodl-tmp/mmeb_eval/data/image-tasks/MMEB`)
- **CLIP 评估**:✅ 完成,结果与历史报告**完全匹配**(Overall 41.6,CLS 55.3,QA 10.5,RET 52.2,GD 53.3,RET 扩展指标全匹配,逐任务全匹配)。结果在 `results/clip-vit-large-patch14-image/`
- **代码同步**:一站式脚本已写好并 push 到远程分支 `feat/one-stop-eval-scripts`(本地 `evaluation-scripts/` 含 run_all.sh、lib/eval_custom_retrieval.py、example_embedding_server.py 等)

### ⏳ 进行中/未完成(关机中断)
- **SigLIP2 评估**:✅ **已完成,与历史报告完全匹配**(Overall 39.4,CLS 55.4,QA 9.1,RET 43.8,GD 62.1,RET 扩展全匹配)。结果在 `results/siglip2-so400m-patch14-384-image/`(36 个 `*_score.json`)
- **Qwen3 评估**:❌ 未开始(关机打断,明天跑)
- **汇总对比**:Qwen3 跑完后用 `summarize_mmeb_v2_image_results.py` 算指标,和报告对比

## 4. 明天继续执行的步骤

### 步骤 1:连服务器,确认状态
```bash
SSH_PASS='Xk24PVg+bysp' python ssh_run.py 'cd /root/autodl-tmp/mmeb_eval; \
  echo "siglip done:"; cat siglip_eval.done 2>/dev/null || echo "not done"; \
  echo "siglip scores:"; ls results/siglip2-so400m-patch14-384-image/*_score.json 2>/dev/null | wc -l; \
  echo "qwen3 done:"; cat qwen3_eval.done 2>/dev/null || echo "not done"; \
  nvidia-smi --query-gpu=name,memory.used --format=csv'
```

连服务器 -> 跑 Qwen3(run_qwen3.sh, batch 16) -> gather + summarize -> 和报告对比 -> 汇报 Qwen3 匹配情况。(CLIP、SigLIP2 已完成且与报告完全匹配,只剩 Qwen3)
`eval_clip_siglip_image.py` 会跳过已有 `*_score.json` 的任务,直接重跑即可只补剩下的:
```bash
SSH_PASS='Xk24PVg+bysp' python ssh_run.py 'cd /root/autodl-tmp/mmeb_eval; \
  nohup bash -c "bash run_siglip.sh; echo EXIT=\$? > siglip_eval.done" > siglip_eval.log 2>&1 & echo "pid $!"'
```
等完成后验证:
```bash
SSH_PASS='Xk24PVg+bysp' python ssh_run.py 'cd /root/autodl-tmp/mmeb_eval/evaluation-scripts; \
  python summarize_mmeb_v2_image_results.py /root/autodl-tmp/mmeb_eval/results/siglip2-so400m-patch14-384-image --model-name SigLIP2'
```
对比报告:Overall 39.4 / CLS 55.4 / QA 9.1 / RET 43.8 / GD 62.1。

### 步骤 3:跑 Qwen3(batch 16)
```bash
SSH_PASS='Xk24PVg+bysp' python ssh_run.py 'cd /root/autodl-tmp/mmeb_eval; \
  nohup bash -c "bash run_qwen3.sh; echo EXIT=\$? > qwen3_eval.done" > qwen3_eval.log 2>&1 & echo "pid $!"'
```
Qwen3 约 30-60 分钟。等 `qwen3_eval.done` 出现。注意 Qwen3 评估用的是官方 `src.evaluation.mmeb_v2.eval_embedding`,输出在 `Qwen3-VL-Embedding/results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B/image/`,需先 `gather_results` 再 summarize:
```bash
SSH_PASS='Xk24PVg+bysp' python ssh_run.py 'cd /root/autodl-tmp/mmeb_eval/Qwen3-VL-Embedding && \
  python -m src.evaluation.mmeb_v2.gather_results results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B \
    --output_dir results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B && \
  cd /root/autodl-tmp/mmeb_eval/evaluation-scripts && \
  python summarize_mmeb_v2_image_results.py \
    /root/autodl-tmp/mmeb_eval/Qwen3-VL-Embedding/results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B --model-name Qwen3'
```
对比报告:Overall 80.1 / CLS 74.2 / QA 81.1 / RET 80.1 / GD 92.3。

### 步骤 4:出对比报告
三个模型都跑完后,把 summarize 输出和报告 6.1/6.2 节逐项对比,汇报匹配情况(预期 0.1-0.3 小差异属正常)。

## 5. 关键路径(服务器)

```
/root/autodl-tmp/mmeb_eval/
├── evaluation-scripts/          # 评估脚本(旧版,但 run_clip/siglip/qwen3.sh 逻辑同新版)
├── data/image-tasks/MMEB/       # 36 个 task 图片目录(image_root)
├── models/{clip-vit-large-patch14, siglip2-so400m-patch14-384, Qwen3-VL-Embedding-8B}/
├── results/clip-vit-large-patch14-image/        # ✅ CLIP 结果(36 score.json + summary.json)
├── results/siglip2-so400m-patch14-384-image/    # SigLIP2 结果(33/36)
├── Qwen3-VL-Embedding/          # 官方仓库,results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B/ 为 Qwen3 输出
├── cache/                       # HF cache
└── run_clip.sh / run_siglip.sh / run_qwen3.sh   # 单模型评估脚本
```

## 6. 注意事项(踩过的坑)

1. **hf-xet 401**:huggingface_hub 1.x 自带 hf-xet,下大文件走 xet 协议连 cas-server.xethub.hf.co 会 401。解决:`pip uninstall -y hf-xet` 或设 `HF_HUB_DISABLE_XET=1`。已卸载,但 pip install transformers 可能带回来,留意。
2. **数据下载**:MMEB-V2 image 数据是单个 `image-tasks/mmeb_v1.tar.gz`(6.7GB)。**不要用 snapshot_download**(卡),用 `lib/multi_dl.py` 多连接下载(已下完解压)。
3. **pip resolvelib bug**:某包 version=None 导致 pip install 失败。升级 pip(`pip install --upgrade pip` 到 26.x)已修复。
4. **Qwen3 评估**:用官方仓库 `src.evaluation.mmeb_v2.eval_embedding`,attn=sdpa(免 flash-attn),bf16。image-tasks 软链接已建。transformers 5.14.1 较新,若 Qwen3 模型加载报错可能需调试(报告时用的是 5.9.0)。
5. **eval_clip_siglip_image.py 支持断点**:已有 `*_score.json` 的任务会跳过,重跑只补缺失的。
6. **Qwen3 eval_embedding 也支持断点**:已有 `{task}_qry`/`{task}_tgt` embedding 会跳过。
7. **CLIP 模型偏大(7G)**:因为仓库含 pytorch_model.bin + model.safetensors 两份,不影响加载(EXIT=0,结果正确)。

## 7. 代码改动(已 push)

远程分支 `feat/one-stop-eval-scripts`(未合并 main),含一站式脚本:
- `run_all.sh`(自动下载+评估+汇总)
- `lib/eval_custom_retrieval.py`(自定义数据评估,支持 clip/siglip/qwen3/remote)
- `example_embedding_server.py`(FastAPI embedding 服务,远程评估)
- `eval_clip_siglip_image.py` 加 `--kind remote --endpoint` 分支

服务器上跑评估用的是旧版脚本(逻辑一致),无需更新即可继续跑完。跑完后若想让服务器也有最新一站式脚本,可把本地 `evaluation-scripts/` 重新上传。

PR 链接:https://github.com/JaquariusJ/MMEB-V2-IMAGE-EVAL/pull/new/feat/one-stop-eval-scripts

### 步骤 5:更新 report 目录
Qwen3 跑完后,下载 qwen3 summary 到本地:
```bash
SSH_PASS='Xk24PVg+bysp' python ssh_run.py 'cat /root/autodl-tmp/mmeb_eval/Qwen3-VL-Embedding/results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B/summary.tsv 2>/dev/null; echo; ls /root/autodl-tmp/mmeb_eval/Qwen3-VL-Embedding/results/evaluation/mmeb_v2/Qwen3-VL-Embedding-8B/image/*_score.json 2>/dev/null | head'
```
然后更新 `report/2026-07-16/REPORT.md` 第 1/2/3/4 节填入 Qwen3 结果(基准 Overall 80.1),并补充 `qwen3_summary.json`。

## 8. 一句话总结明天要做的

连服务器 -> 跑 Qwen3(run_qwen3.sh, batch 16) -> gather + summarize -> 和报告对比 -> 汇报 Qwen3 匹配情况。(CLIP、SigLIP2 已完成且与报告完全匹配,只剩 Qwen3)
