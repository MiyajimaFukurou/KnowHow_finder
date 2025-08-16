import openai
import glob
import os
import numpy as np
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")
openai.api_key = api_key

CHAT_MODEL = "gpt-4.1"
EMBED_MODEL = "text-embedding-3-large"

GROUP_SIZE = 4   # 何行で1チャンクにするか
MARGIN     = 3   # ヒットしたチャンクの前後何行を追加するか
TOPN       = 5   # 参照するRAG上位チャンク数
BATCH_SIZE = 500 # Embeddingリクエストのバッチ数

# ----- 全ファイルをロード ----------
all_chunks = []      # 各チャンクのテキスト
chunk_meta  = []     # (fname, start_line, end_line, full_lines)

for fname in sorted(glob.glob("2024-10-*.txt")):
    with open(fname, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    n = len(lines)
    i = 0
    while i < n:
        start = i
        end   = min(i + GROUP_SIZE, n)
        text  = "\n".join(lines[start:end])
        if text:  # 空でなければ登録
            all_chunks.append(text)
            chunk_meta.append((fname, start, end-1, lines))
        i += GROUP_SIZE

print(f"総チャンク数: {len(all_chunks)}")

# ----- Embedding ----------
def get_embeddings(texts):
    print("Embedding中...")

    embs = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i+BATCH_SIZE]
        resp = openai.embeddings.create(model=EMBED_MODEL, input=batch)
        for e in resp.data:
            embs.append(np.array(e.embedding))
    return np.stack(embs)

line_embeddings = get_embeddings(all_chunks)

# ----- 回答生成 ----------
def generate_answer(usr_query, context):
    prompt = f"""
あなたはデジタル工房機器のサポートAIです。

質問: 「{usr_query}」

以下は類似する作業会話の一部です。
これを参考に横断的なアドバイスを提示してください。

【参考会話】
{context}
"""

    with open("RAGresult.txt", "w", encoding="utf-8") as f:
        f.write(prompt)
    
    resp = openai.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "あなたはデジタル工房機器のサポートAIです。"},
            {"role": "user", "content": prompt}
        ],
    )
    return resp.choices[0].message.content

# --- メイン処理 ----------
def main():
    while True:
        user_query = input("ご質問はありますか？（終了するには'exit'と入力）：\n")
        if user_query.lower() == 'exit':                                                                                             
            break
        elif not user_query.strip():
            print("質問が入力されていません。")
        else:
            q_emb = openai.embeddings.create(
                model=EMBED_MODEL,
                input=[user_query]
            ).data[0].embedding
            q_emb = np.array(q_emb)

            def cosine_sim(a, b):
                return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

            scores = [cosine_sim(q_emb, e) for e in line_embeddings]
            topN = TOPN
            top_indices = np.argsort(scores)[::-1][:topN]

            # ----- ヒット行 + 前後4行をコンテキストに ----------
            hit_contexts = []
            for idx in top_indices:
                fname, s, e, lines = chunk_meta[idx]
                start = max(0, s - MARGIN)
                end = min(len(lines), e + MARGIN + 1)
                context_block = "\n".join(lines[start:end])
                hit_contexts.append(f"【{fname} 行{s}-{e} 周辺】\n{context_block}")

            context = "\n---\n".join(hit_contexts)

            answer = generate_answer(user_query, context)
            print("\n=== 回答 ===\n")
            print(answer)

if __name__ == "__main__":
    main()
