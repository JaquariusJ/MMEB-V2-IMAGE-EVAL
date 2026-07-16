import argparse
import json
import math
import os
import re
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import yaml
from datasets import load_dataset
from PIL import Image, ImageFile
from tqdm import tqdm
from transformers import AutoModel, AutoProcessor, CLIPModel, CLIPProcessor

ImageFile.LOAD_TRUNCATED_IMAGES = True

def as_embedding_tensor(out, side):
    if torch.is_tensor(out):
        return out
    for name in ([f'{side}_embeds', 'pooler_output'] if side in ('text','image') else ['pooler_output']):
        val = getattr(out, name, None)
        if val is not None:
            return val
    if isinstance(out, (tuple, list)) and out:
        return out[0]
    raise RuntimeError(f'Cannot find {side} embeddings in output type {type(out)}')


TASK_GROUPS = {
    'CLS': {'ImageNet-1K','N24News','HatefulMemes','VOC2007','SUN397','Place365','ImageNet-A','ImageNet-R','ObjectNet','Country211'},
    'QA': {'OK-VQA','A-OKVQA','DocVQA','InfographicsVQA','ChartQA','Visual7W','ScienceQA','VizWiz','GQA','TextVQA'},
    'RET': {'MSCOCO_i2t','VisualNews_i2t','VisDial','MSCOCO_t2i','VisualNews_t2i','WebQA','EDIS','Wiki-SS-NQ','CIRR','NIGHTS','OVEN','FashionIQ'},
    'VG': {'MSCOCO','RefCOCO','RefCOCO-Matching','Visual7W-Pointing'},
}

def group_for(name):
    for g, names in TASK_GROUPS.items():
        if name in names:
            return g
    return 'OTHER'

def clean_text(*parts):
    text = ' '.join([p for p in parts if isinstance(p, str) and p.strip()])
    text = text.replace('<|image_1|>', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def as_list(x):
    return x if isinstance(x, list) else [x]

def item_id(text, image, parser=None):
    if parser == 'image_i2i_vg':
        return f'{image}:{text}'
    if image:
        return image
    return text

def build_examples(row, parser):
    q_text = clean_text(row.get('qry_text', ''))
    q_img = row.get('qry_img_path') or ''
    tgt_texts = as_list(row.get('tgt_text', []))
    tgt_imgs = as_list(row.get('tgt_img_path', []))
    if not tgt_imgs or tgt_imgs == ['']:
        tgt_imgs = [''] * len(tgt_texts)
    if not tgt_texts or tgt_texts == ['']:
        tgt_texts = [''] * len(tgt_imgs)
    n = max(len(tgt_texts), len(tgt_imgs))
    if len(tgt_texts) < n:
        tgt_texts = tgt_texts + [''] * (n - len(tgt_texts))
    if len(tgt_imgs) < n:
        tgt_imgs = tgt_imgs + [''] * (n - len(tgt_imgs))

    # CLIP-like models cannot consume an instruction plus image as a fused sequence.
    # Use the natural query/candidate content; average image and text embeddings only when both carry content.
    query = {'text': q_text, 'image': q_img}
    raw_cands = [{'text': clean_text(t), 'image': im or ''} for t, im in zip(tgt_texts, tgt_imgs)]
    first_valid = next((c for c in raw_cands if c['text'] or c['image']), None)
    cands = [c for c in raw_cands if c['text'] or c['image']]
    if first_valid is None or not cands:
        raise RuntimeError('No valid candidates after filtering empty text/image entries')
    labels = [item_id(first_valid['text'], first_valid['image'], parser)]
    cand_ids = [item_id(c['text'], c['image'], parser) for c in cands]
    return query, cands, cand_ids, labels

def hit_at(pred, labels, k):
    return 1.0 if set(pred[:k]).intersection(labels) else 0.0

def recall_at(pred, labels, k):
    return len(set(pred[:k]).intersection(labels)) / max(1, len(labels))

def precision_at(pred, labels, k):
    return len(set(pred[:k]).intersection(labels)) / k

def mrr_at(pred, labels, k):
    s = set(labels)
    for i, p in enumerate(pred[:k]):
        if p in s:
            return 1.0 / (i + 1)
    return 0.0

def ndcg_at(pred, labels, k):
    s = set(labels)
    dcg = 0.0
    for i, p in enumerate(pred[:k]):
        if p in s:
            dcg += 1.0 / math.log2(i + 2)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(s), k)))
    return dcg / ideal if ideal else 0.0

def evaluate_rankings(rankings):
    ks = [1, 5, 10]
    out = {}
    for k in ks:
        out[f'hit@{k}'] = float(np.mean([hit_at(p, l, k) for p, l in rankings]))
        out[f'recall@{k}'] = float(np.mean([recall_at(p, l, k) for p, l in rankings]))
        out[f'precision@{k}'] = float(np.mean([precision_at(p, l, k) for p, l in rankings]))
        out[f'mrr@{k}'] = float(np.mean([mrr_at(p, l, k) for p, l in rankings]))
        out[f'ndcg@{k}'] = float(np.mean([ndcg_at(p, l, k) for p, l in rankings]))
    return out

class ClipLike:
    def __init__(self, model_id, kind, batch_size):
        self.model_id = model_id
        self.kind = kind
        self.batch_size = batch_size
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        if kind == 'clip':
            self.processor = CLIPProcessor.from_pretrained(model_id)
            self.model = CLIPModel.from_pretrained(model_id).to(self.device).eval()
        else:
            self.processor = AutoProcessor.from_pretrained(model_id)
            self.model = AutoModel.from_pretrained(model_id).to(self.device).eval()
        self.text_cache = {}
        self.image_cache = {}
        self.item_cache = {}

    @torch.no_grad()
    def encode_texts(self, texts):
        result = {}
        pending = [t for t in texts if t and t not in self.text_cache]
        for i in tqdm(range(0, len(pending), self.batch_size), desc='text batches', leave=False, disable=True):
            batch = pending[i:i+self.batch_size]
            inputs = self.processor(text=batch, padding=('max_length' if self.kind == 'siglip' else True), truncation=True, return_tensors='pt').to(self.device)
            if hasattr(self.model, 'get_text_features'):
                out = self.model.get_text_features(**inputs)
                emb = as_embedding_tensor(out, 'text')
            else:
                out = self.model(**inputs)
                emb = as_embedding_tensor(out, 'text')
            emb = F.normalize(emb.float(), dim=-1).cpu().numpy()
            for t, e in zip(batch, emb):
                self.text_cache[t] = e
        for t in texts:
            if t:
                result[t] = self.text_cache[t]
        return result

    @torch.no_grad()
    def encode_images(self, paths):
        result = {}
        pending = [p for p in paths if p and p not in self.image_cache]
        for i in tqdm(range(0, len(pending), self.batch_size), desc='image batches', leave=False, disable=True):
            batch_paths = pending[i:i+self.batch_size]
            imgs = []
            valid = []
            for p in batch_paths:
                try:
                    imgs.append(Image.open(p).convert('RGB'))
                    valid.append(p)
                except Exception as e:
                    print(f'[WARN] failed image {p}: {e}')
            if not imgs:
                continue
            inputs = self.processor(images=imgs, return_tensors='pt').to(self.device)
            if hasattr(self.model, 'get_image_features'):
                out = self.model.get_image_features(**inputs)
                emb = as_embedding_tensor(out, 'image')
            else:
                out = self.model(**inputs)
                emb = as_embedding_tensor(out, 'image')
            emb = F.normalize(emb.float(), dim=-1).cpu().numpy()
            for p, e in zip(valid, emb):
                self.image_cache[p] = e
        for p in paths:
            if p and p in self.image_cache:
                result[p] = self.image_cache[p]
        return result

    def prepare(self, items, image_root):
        texts, images = set(), set()
        normalized = []
        for it in items:
            text = it.get('text') or ''
            image = it.get('image') or ''
            full_image = str(Path(image_root) / image) if image else ''
            normalized.append((text, full_image))
            if text:
                texts.add(text)
            if full_image:
                images.add(full_image)
        self.encode_texts(sorted(texts))
        self.encode_images(sorted(images))
        vecs = []
        for text, full_image in normalized:
            key = (text, full_image)
            if key not in self.item_cache:
                parts = []
                if text:
                    parts.append(self.text_cache[text])
                if full_image:
                    parts.append(self.image_cache[full_image])
                if not parts:
                    raise RuntimeError('Empty item without text or image')
                v = np.mean(np.stack(parts), axis=0)
                v = v / max(np.linalg.norm(v), 1e-12)
                self.item_cache[key] = v.astype('float32')
            vecs.append(self.item_cache[key])
        return np.stack(vecs)

def eval_dataset(model, task_name, parser, image_root, output_dir):
    ds = load_dataset('ziyjiang/MMEB_Test_Instruct', task_name, split='test')
    rankings = []
    preds_path = Path(output_dir) / f'{task_name}_pred.jsonl'
    score_path = Path(output_dir) / f'{task_name}_score.json'
    with preds_path.open('w') as pf:
        for row in tqdm(ds, desc=task_name):
            query, cands, cand_ids, labels = build_examples(row, parser)
            qv = model.prepare([query], image_root)[0]
            cv = model.prepare(cands, image_root)
            scores = cv @ qv
            order = np.argsort(-scores)
            pred = [cand_ids[i] for i in order]
            rankings.append((pred, labels))
            pf.write(json.dumps({'prediction': pred, 'label': labels}, ensure_ascii=False) + '\n')
    scores = evaluate_rankings(rankings)
    scores['num_data'] = len(rankings)
    score_path.write_text(json.dumps(scores, indent=2), encoding='utf-8')
    return scores

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model-id', required=True)
    ap.add_argument('--kind', choices=['clip','siglip'], required=True)
    ap.add_argument('--dataset-config', default='experiments/public/eval/image.yaml')
    ap.add_argument('--image-root', default='/root/mmeb_eval/data/image-tasks/MMEB')
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--batch-size', type=int, default=64)
    ap.add_argument('--tasks', default='')
    args = ap.parse_args()
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    cfg = yaml.safe_load(open(args.dataset_config))
    tasks = [t.strip() for t in args.tasks.split(',') if t.strip()] or list(cfg.keys())
    model = ClipLike(args.model_id, args.kind, args.batch_size)
    all_scores = {}
    for task in tasks:
        parser = cfg[task]['dataset_parser']
        print(f'\n=== {task} ({parser}) ===')
        score_file = Path(args.output_dir) / f'{task}_score.json'
        if score_file.exists():
            all_scores[task] = json.loads(score_file.read_text(encoding='utf-8'))
            print(f'{task} loaded existing score')
        else:
            all_scores[task] = eval_dataset(model, task, parser, args.image_root, args.output_dir)
            print(task, all_scores[task])
        torch.cuda.empty_cache()
    summary = {'model': args.model_id, 'tasks': all_scores}
    for group in ['CLS','QA','RET','VG']:
        vals = [s['ndcg@10'] for t, s in all_scores.items() if group_for(t) == group]
        if vals:
            summary[f'{group}_ndcg@10_avg'] = float(np.mean(vals))
    vals = [s['ndcg@10'] for s in all_scores.values()]
    summary['image_ndcg@10_avg'] = float(np.mean(vals)) if vals else None
    vals = [s['hit@1'] for s in all_scores.values()]
    summary['image_hit@1_avg'] = float(np.mean(vals)) if vals else None
    Path(args.output_dir, 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('\nSUMMARY')
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
