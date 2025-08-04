import openai
import glob
import json
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")
openai.api_key = api_key

# 全工程ブロックを集約
all_blocks = []
for fname in sorted(glob.glob("phase_blocks_*.json")):
    with open(fname, encoding="utf-8") as f:
        blocks = json.load(f)
    # 元ファイル名も持たせる
    for b in blocks:
        b["source_file"] = fname.replace("phase_blocks_", "").replace(".json", "")
        all_blocks.append(b)

# 各ブロックのテキストを集約
def get_block_text(block):
    # 工程ブロックの行区間からtxtを読む
    txtfile = block["source_file"] + ".txt"
    with open(txtfile, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    return "\n".join(lines[block["start_line"]:block["end_line"]+1])

texts = [get_block_text(b) for b in all_blocks]

# 各ブロックをembedding
def get_embeddings(texts):
    # 最大8192トークンまで
    embeddings = []
    batch = []
    for t in texts:
        batch.append(t)
        if len(batch) == 2000:
            response = openai.embeddings.create(model="text-embedding-3-large", input=batch)
            for e in response.data:
                embeddings.append(np.array(e.embedding))
            batch = []
    if batch:
        response = openai.embeddings.create(model="text-embedding-3-large", input=batch)
        for e in response.data:
            embeddings.append(np.array(e.embedding))
    return np.stack(embeddings)

block_embeddings = get_embeddings(texts)

# ユーザの入力をembedding
user_query = input("ご質問はありますか？")
query_emb = openai.embeddings.create(
    model="text-embedding-3-large",
    input=[user_query]
).data[0].embedding
query_emb = np.array(query_emb)

# コサイン類似度で上位N件を抽出
def cosine_sim(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

scores = [cosine_sim(query_emb, e) for e in block_embeddings]
topN = 5 # 参照件数の指定はココ
top_indices = np.argsort(scores)[::-1][:topN]

hit_blocks = [all_blocks[i] for i in top_indices]
hit_texts = [texts[i] for i in top_indices]

# 回答生成用コンテキストを作成し、LLMでまとめる
context = "\n---\n".join(hit_texts)
llm_prompt = f"""
あなたはデジタル工房機器のサポートAIです。

ユーザーからの質問:
「{user_query}」

以下は、現場で実際にあった作業会話例（工程ごと・複数ペア分の抜粋）です。
これらを参考に、質問への横断的なアドバイス・解決策をユーザに提示してください。

【参考会話例】
{context}
"""

response = openai.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "system", "content": "あなたはデジタル工房機器のサポートAIです。"},
        {"role": "user", "content": llm_prompt}
    ],
    #max_tokens=800,
    #temperature=0.3,
)
print("\n=== 回答生成 ===\n")
print(response.choices[0].message.content)
