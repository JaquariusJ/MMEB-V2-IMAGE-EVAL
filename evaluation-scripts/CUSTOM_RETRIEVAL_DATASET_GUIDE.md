# 自定义文搜图 / 以图搜图数据集与评分指南

本文档说明如何准备自己的业务数据集和 label，用于评估 CLIP、SigLIP2、Qwen3-VL-Embedding 等多模态 embedding 模型在文搜图、以图搜图场景中的效果。

## 1. 适用场景

本文档覆盖两类最常见业务检索：

| 场景 | 输入 | 检索目标 |
|---|---|---|
| 文搜图 Text-to-Image | 文本 query | 图片库 |
| 以图搜图 Image-to-Image | 图片 query | 图片库 |

也可以扩展到图文混合检索：

```text
图片 query + 文本条件 -> 图片库
```

例如：

```text
上传一张鞋图 + “找同款黑色”
上传一张票据 + “找招商银行相关账单”
```

## 2. 推荐数据格式

建议把评估集拆成 3 个文件：

```text
queries.jsonl
corpus.jsonl
qrels.jsonl
```

含义：

| 文件 | 作用 |
|---|---|
| `queries.jsonl` | 查询集合，每一行是一个 query |
| `corpus.jsonl` | 候选库，每一行是一个候选图片或候选文档 |
| `qrels.jsonl` | label 文件，记录 query 和正确候选之间的相关性 |

这种格式接近信息检索领域常用的 qrels 格式，后续可以方便地计算 `Recall@K`、`MRR@K`、`nDCG@K`。

## 3. 文搜图数据准备

目标：

```text
输入一段文字 query，从图片库里找正确图片。
```

### 3.1 queries.jsonl

```jsonl
{"query_id":"q001","text":"红色连衣裙","image":null}
{"query_id":"q002","text":"黑色运动鞋，白色鞋底","image":null}
{"query_id":"q003","text":"招商银行 2024 年 5 月账单截图","image":null}
```

字段说明：

| 字段 | 是否必填 | 含义 |
|---|---|---|
| `query_id` | 是 | query 唯一 ID |
| `text` | 是 | 文本查询 |
| `image` | 否 | 文搜图场景可为 `null` |

### 3.2 corpus.jsonl

```jsonl
{"doc_id":"img001","text":"红色连衣裙 夏季 女装","image":"images/img001.jpg"}
{"doc_id":"img002","text":"黑色运动鞋 白色鞋底","image":"images/img002.jpg"}
{"doc_id":"img003","text":"蓝色牛仔裤","image":"images/img003.jpg"}
```

字段说明：

| 字段 | 是否必填 | 含义 |
|---|---|---|
| `doc_id` | 是 | 候选图片唯一 ID |
| `text` | 否 | 候选图片的标题、描述、OCR 文本或商品属性 |
| `image` | 是 | 候选图片路径 |

### 3.3 qrels.jsonl

```jsonl
{"query_id":"q001","doc_id":"img001","score":3}
{"query_id":"q002","doc_id":"img002","score":3}
{"query_id":"q003","doc_id":"img010","score":3}
```

含义：

```text
q001 的正确答案是 img001
q002 的正确答案是 img002
q003 的正确答案是 img010
```

如果一个 query 有多个正确图片，可以写多行：

```jsonl
{"query_id":"q001","doc_id":"img001","score":3}
{"query_id":"q001","doc_id":"img007","score":2}
{"query_id":"q001","doc_id":"img009","score":1}
```

## 4. 以图搜图数据准备

目标：

```text
输入一张图片 query，从图库里找相似、同款或相关图片。
```

### 4.1 queries.jsonl

```jsonl
{"query_id":"q001","text":null,"image":"queries/q001.jpg"}
{"query_id":"q002","text":null,"image":"queries/q002.jpg"}
{"query_id":"q003","text":null,"image":"queries/q003.jpg"}
```

字段说明：

| 字段 | 是否必填 | 含义 |
|---|---|---|
| `query_id` | 是 | query 唯一 ID |
| `text` | 否 | 纯以图搜图可为 `null` |
| `image` | 是 | query 图片路径 |

### 4.2 corpus.jsonl

```jsonl
{"doc_id":"img001","text":"红色连衣裙 正面图","image":"images/img001.jpg"}
{"doc_id":"img002","text":"红色连衣裙 侧面图","image":"images/img002.jpg"}
{"doc_id":"img003","text":"黑色运动鞋","image":"images/img003.jpg"}
```

### 4.3 qrels.jsonl

```jsonl
{"query_id":"q001","doc_id":"img001","score":3}
{"query_id":"q001","doc_id":"img002","score":2}
{"query_id":"q002","doc_id":"img003","score":3}
```

含义：

```text
q001 与 img001 完全同款
q001 与 img002 高度相似
q002 与 img003 完全同款
```

## 5. label 标注建议

最简单的 label 是二值：

| score | 含义 |
|---:|---|
| 1 | 正确 / 相关 |
| 未写入 qrels | 不相关 |

更推荐的多级相关性：

| score | 含义 | 示例 |
|---:|---|---|
| 3 | 完全正确 / 完全同款 | 同一个商品、同一个票据、同一个文档页面 |
| 2 | 高度相关 / 可接受 | 同款不同角度、同系列商品、同一账单类型 |
| 1 | 弱相关 | 类目相同但不是目标结果 |
| 0 | 不相关 | 通常不用写入 `qrels.jsonl` |

建议第一版先做二值 label：

```text
score = 1：正确
没写：不正确
```

等模型初筛完成后，再对重点样本补 `score=1/2/3`，用于计算更稳定的 `nDCG@10`。

## 6. 目录结构建议

推荐结构：

```text
/root/my_eval_data/
├── queries.jsonl
├── corpus.jsonl
├── qrels.jsonl
├── queries/
│   ├── q001.jpg
│   ├── q002.jpg
│   └── q003.jpg
└── images/
    ├── img001.jpg
    ├── img002.jpg
    └── img003.jpg
```

JSONL 中图片路径建议使用相对路径：

```json
{"doc_id":"img001","image":"images/img001.jpg"}
```

评估时通过 `--data-root /root/my_eval_data` 拼成完整路径。

## 7. 数据量建议

| 阶段 | Query 数 | Corpus 图片数 | 用途 |
|---|---:|---:|---|
| 小样验证 | 100-300 | 1k-5k | 快速判断模型方向 |
| 正式评估 | 1k-5k | 1万-10万 | 比较模型稳定性 |
| 上线前评估 | 5k+ | 接近真实图库 | 更接近线上真实效果 |

每个 query 建议至少有：

```text
1-5 个正样本
```

负样本通常不需要人工逐个标注。只要候选在 `corpus.jsonl` 中，但没有写入 `qrels.jsonl`，就默认视为负样本。

## 8. 评分指标

建议计算：

| 指标 | 是否建议 | 含义 |
|---|---|---|
| Recall@1 | 必须 | 第一名是否命中正确结果 |
| Recall@5 | 必须 | 前 5 是否包含正确结果 |
| Recall@10 | 必须 | 前 10 是否包含正确结果 |
| MRR@10 | 建议 | 正确结果越靠前分越高 |
| nDCG@10 | 建议 | 支持多级相关性 label，衡量排序质量 |
| Precision@K | 可选 | 前 K 个结果中相关结果占比 |
| latency | 建议 | 单条 query 检索耗时 |

## 9. 评估流程

统一流程：

```text
1. 读取 queries.jsonl
2. 读取 corpus.jsonl
3. 读取 qrels.jsonl
4. 编码 query embedding
5. 编码 corpus embedding
6. 计算 query 与 corpus 的相似度
7. 对每个 query 按相似度排序
8. 对比 qrels，计算 Recall@K、MRR@10、nDCG@10
```

核心伪代码：

```text
query_embedding = normalize(model.encode(query))
corpus_embeddings = normalize(model.encode(corpus))
scores = corpus_embeddings @ query_embedding
ranking = sort(corpus, by=scores, descending=True)
metrics = evaluate(ranking, qrels[query_id])
```

## 10. 跑分命令示例

如果后续实现通用脚本 `eval_custom_retrieval.py`，建议命令如下。

### 10.1 CLIP

```bash
python eval_custom_retrieval.py \
  --model-id openai/clip-vit-large-patch14 \
  --kind clip \
  --data-root /root/my_eval_data \
  --queries queries.jsonl \
  --corpus corpus.jsonl \
  --qrels qrels.jsonl \
  --output-dir /root/my_eval_results/clip
```

### 10.2 SigLIP2

```bash
python eval_custom_retrieval.py \
  --model-id google/siglip2-so400m-patch14-384 \
  --kind siglip \
  --data-root /root/my_eval_data \
  --queries queries.jsonl \
  --corpus corpus.jsonl \
  --qrels qrels.jsonl \
  --output-dir /root/my_eval_results/siglip2
```

### 10.3 Qwen3-VL-Embedding-8B

```bash
python eval_custom_retrieval.py \
  --model-id /root/autodl-tmp/mmeb_eval/models/Qwen3-VL-Embedding-8B \
  --kind qwen3 \
  --data-root /root/my_eval_data \
  --queries queries.jsonl \
  --corpus corpus.jsonl \
  --qrels qrels.jsonl \
  --output-dir /root/my_eval_results/qwen3
```

## 11. 输出结果建议

建议输出一个汇总文件：

```text
summary.json
```

示例：

```json
{
  "recall@1": 0.72,
  "recall@5": 0.91,
  "recall@10": 0.95,
  "mrr@10": 0.81,
  "ndcg@10": 0.84,
  "num_queries": 1000,
  "num_corpus": 50000
}
```

同时输出每条 query 的排序结果：

```text
predictions.jsonl
```

示例：

```jsonl
{"query_id":"q001","prediction":["img001","img008","img020"],"label":["img001","img007"]}
{"query_id":"q002","prediction":["img003","img018","img088"],"label":["img003"]}
```

## 12. 实操建议

第一版不要追求很复杂的 label。推荐先准备：

```text
100-300 个 query
1000-5000 张候选图片
每个 query 标 1-3 个正样本
score 全部先写 1
```

先跑：

```text
Recall@1
Recall@5
Recall@10
MRR@10
```

等确认模型方向后，再扩大数据规模，并补充 `score=1/2/3` 多级相关性，用于计算 `nDCG@10`。

