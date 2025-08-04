import openai
import json
import glob
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")
openai.api_key = api_key

# phase_tags.txtのタグ読み込み
with open("phase_tags.txt", encoding="utf-8") as f:
    phase_tags = [l.strip() for l in f if l.strip()]

# --- 作業工程タグ推定関数 ----------
def tag_estimate(question):
    """
    ユーザーの質問に対して、phase_tags.txtのタグから最も適切なものを選ぶ
    """

    # タグ一覧を整形
    tag_list_str = "・" + "\n・".join(phase_tags)
    prompt = f"""
あなたは現場作業の工程分析エージェントです。

以下はユーザーからの質問です。この内容が「どの作業工程（phase_tags.txtのタグ）」に該当するか、一つだけ選んで日本語のタグ名のみ答えてください。

[タグ一覧]{tag_list_str}

[ユーザーの質問]「{question}」

出力形式：タグ名のみ1行で（例：「3Dプリンター準備」）
"""

    response = openai.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": "あなたはデジタル工房機器作業の工程分析エージェントです。"},
            {"role": "user", "content": prompt}
        ],
        #max_tokens=20,
        #temperature=0,
    )
    phase = response.choices[0].message.content.strip()
    return phase
# --- ここまで作業工程タグ推定関数 ----------

# --- タグ -> ブロック取得関数 ----------
def tag2block(tag):
    """
    全 phase_blocks_*.json を走査し、該当タグのブロックを集める
    """
    blocks = []
    for fname in sorted(glob.glob("phase_blocks_*.json")):
        with open(fname, encoding="utf-8") as f:
            block_list = json.load(f)
        for b in block_list:
            if b["tag"] == tag:
                b["source_file"] = fname.replace("phase_blocks_", "").replace(".json", "")
                blocks.append(b)
    return blocks
# --- ここまでタグ -> ブロック取得関数 ----------

# --- ブロック -> テキスト関数 ----------
def block2text(block):
    """
    ブロックのテキストを抽出（元txtファイルから抜粋）
    """
    txtfile = block["source_file"] + ".txt"
    with open(txtfile, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    return "\n".join(lines[block["start_line"]:block["end_line"]+1])
# --- ここまでブロック -> テキスト関数 ----------

# --- 回答生成関数 ----------
def generate_answer(question):
    """
    質問→タグ推定→該当工程の全9ペアの会話ブロックを集めて回答生成
    """
    tag = tag_estimate(question)
    print(f"\n推定されたタグ：{tag}\n")

    blocks = tag2block(tag)
    if not blocks:
        print("該当タグの会話データが見つかりませんでした。")
        return

    # すべての該当ブロックのテキストを連結
    context_blocks = []
    for b in blocks:
        block_txt = block2text(b)
        context_blocks.append(f"【{b['source_file']}】\n{block_txt}")
    context = "\n\n---\n\n".join(context_blocks)

    prompt = f"""
あなたは現場作業のノウハウサポートAIです。

ユーザーからの質問：
「{question}」

以下は9ペア分の、同じ工程（タグ: {tag}）での実際の作業会話の抜粋です。
これらを参考にして、ユーザーの質問に対しアドバイスしてください。作業会話からわかる、今後起こりうる問題について、先回りして示すなどしてもかまいません。

【参考作業会話】
{context}
"""
    with open("prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)

    response = openai.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "あなたはデジタル工房機器作業のノウハウを伝えるサポートAIです。"},
            {"role": "user", "content": prompt}
        ],
        #max_tokens=800,
        #temperature=0.3,
    )
    return response.choices[0].message.content
# --- ここまで回答生成関数 ----------

# --- メイン処理 ----------
def main():
    while True:
        question = input("ご質問はありますか？（終了するには'exit'と入力）：\n")
        if question.lower() == 'exit':                                                                                             
            break
        elif not question.strip():
            print("質問が入力されていません。")
        else:
            answer = generate_answer(question)
            print("\n=== 回答 ===\n")
            print(answer)

if __name__ == "__main__":
    main()