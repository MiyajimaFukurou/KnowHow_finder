from sentence_transformers import SentenceTransformer, util
from rank_bm25 import BM25Okapi
import numpy as np
import tiktoken
from typing import List, Dict, Tuple

ENC = tiktoken.get_encoding("cl100k_base")  # ざっくりトークン見積もり

def count_tokens(text: str) -> int:
    return len(ENC.encode(text))

def smart_trim(text: str, max_tokens: int) -> str:
    toks = ENC.encode(text)
    if len(toks) <= max_tokens:
        return text
    return ENC.decode(toks[:max_tokens])

# --- 1) チャンク化（行ごと） -----------
def make_microchunks(
    lines: List[str],
    doc_id: str,
    chunk_tokens: int = 300,
    overlap_tokens: int = 80,
    min_tokens: int = 30
) -> List[Dict]:
    """
    行単位の会話を、約300トークンのマイクロチャンクに分割（80トークン重なり）。
    戻り値: [{doc_id, chunk_idx, text, start_line, end_line}]
    """
    chunks = []
    buf = []
    buf_start = 0
    i = 0
    # 発話境界を尊重して積む
    while i < len(lines):
        if not buf:
            buf_start = i
        buf.append(lines[i])
        cur_text = "\n".join(buf)
        if count_tokens(cur_text) >= chunk_tokens:
            # 閾値超えたら確定
            start_line = buf_start
            end_line = i
            text = cur_text
            # 小さすぎる断片は少し先まで伸ばす
            if count_tokens(text) < min_tokens and i + 1 < len(lines):
                i += 1
                buf.append(lines[i])
                text = "\n".join(buf)
                end_line = i

            chunks.append({
                "doc_id": doc_id,
                "chunk_idx": len(chunks),
                "text": text,
                "start_line": start_line,
                "end_line": end_line
            })
            # オーバーラップ再構築
            # 現在のbuf末尾から overlap_tokens 程度を残す
            tail = []
            # 末尾から逆に足して overlap_tokens を超えるまで保持
            for rev in range(len(buf)-1, -1, -1):
                tmp = "\n".join([lines for lines in buf[rev:]])
                if count_tokens(tmp) >= overlap_tokens:
                    tail = buf[rev:]
                    break
            buf = tail[:]  # overlap分を次バッファの先頭に
            buf_start = max(end_line - (len(buf)-1), 0)
        i += 1

    # 残り
    if buf:
        chunks.append({
            "doc_id": doc_id,
            "chunk_idx": len(chunks),
            "text": "\n".join(buf),
            "start_line": buf_start,
            "end_line": len(lines)-1
        })
    return chunks

# --- 2) インデックス構築 ---------------
class HybridIndex:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.chunks: List[Dict] = []
        self.dense = None
        self.bm25 = None

    def build(self, chunks: List[Dict]):
        self.chunks = chunks
        corpus = [c["text"] for c in chunks]
        # Dense
        self.dense = self.model.encode(
            corpus, batch_size=64, convert_to_numpy=True, show_progress_bar=True
        )
        # BM25（超簡易トークナイズ）
        tokenized = [c["text"].split() for c in chunks]
        self.bm25 = BM25Okapi(tokenized)

    def hybrid_search(self, query: str, top_k: int = 30, alpha: float = 0.6) -> List[Tuple[Dict, float]]:
        # BM25
        bm25_scores = self.bm25.get_scores(query.split())
        # Dense
        qv = self.model.encode([query], convert_to_numpy=True)[0]
        dense_scores = util.cos_sim(qv, self.dense).cpu().numpy().ravel()
        # 0-1正規化
        b = (bm25_scores - bm25_scores.min()) / (bm25_scores.ptp() + 1e-9)
        d = (dense_scores - dense_scores.min()) / (dense_scores.ptp() + 1e-9)
        score = alpha * d + (1 - alpha) * b
        idx = np.argsort(score)[::-1][:top_k]
        return [(self.chunks[i], float(score[i])) for i in idx]

# --- 3) 近傍拡張 ----------
def stitch_neighbors(
    hits: List[Tuple[Dict, float]],
    all_chunks: List[Dict],
    window: int = 1,
    max_tokens_per_stitch: int = 1000
) -> List[Dict]:
    """
    ヒットしたチャンクの前後windowチャンクを連結して“塊”を作る。
    同一doc_idでchunk_idxが近いものをまとめる。
    """
    # 索引: doc_id -> idx -> chunk
    by_doc = {}
    for c in all_chunks:
        by_doc.setdefault(c["doc_id"], {})[c["chunk_idx"]] = c

    stitched = []
    seen = set()

    for chunk, _score in hits:
        doc = chunk["doc_id"]
        idx = chunk["chunk_idx"]
        key = (doc, idx)
        if key in seen:
            continue
        # 窓を確定
        start = idx - window
        end = idx + window
        parts = []
        for k in range(start, end + 1):
            if k in by_doc.get(doc, {}):
                parts.append(by_doc[doc][k])

        if not parts:
            continue

        parts = sorted(parts, key=lambda x: x["chunk_idx"])
        text = "\n".join([p["text"] for p in parts])
        text = smart_trim(text, max_tokens=max_tokens_per_stitch)

        stitched.append({
            "doc_id": doc,
            "start_chunk": parts[0]["chunk_idx"],
            "end_chunk": parts[-1]["chunk_idx"],
            "start_line": parts[0]["start_line"],
            "end_line": parts[-1]["end_line"],
            "text": text
        })
        for p in parts:
            seen.add((doc, p["chunk_idx"]))

    return stitched
