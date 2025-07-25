import openai
import re
import json
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
api_key = os.getenv("API_KEY")
openai.api_key = api_key

with open("2024-10-02_13_11_31.txt", encoding="utf-8") as f:
    lines = [l.strip() for l in f if l.strip()]

# 行番号付きでLLMに渡す用のテキスト作成
line_txt = "\n".join([f"{i}: {line}" for i, line in enumerate(lines)])

def make_prompt(user_prompt=""):
    base = f"""
以下は作業実践中の会話書き起こしです。
会話全体を俯瞰し、「どこからどこまでが同じ“作業工程（フェーズ）”なのか」を抽出し、工程ごとにタグ名をつけて、区切り・対応範囲を明示してください。

【出力フォーマット例】
1. 0行目～12行目：事前準備
2. 13行目～41行目：3Dプリンター準備
3. 42行目～100行目：印刷作業
...

- 同じ意味の工程・フェーズは必ず同じ表記でタグ付けしてください。
- 工程名は端的な日本語で自由につけてOKです。

{user_prompt}

【会話データ】
{line_txt}
"""
    return base

user_prompt = ""

while True:
    prompt = make_prompt(user_prompt)
    response = openai.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "あなたは現場会話の工程分析エキスパートです。"},
            {"role": "user", "content": prompt}
        ],
        #max_tokens=2000,
        #temperature=0,
    )
    output = response.choices[0].message.content
    print(output)

    # タグ抽出（ざっくりパターン：XX行目～YY行目：タグ名）
    blocks = []
    for m in re.finditer(r"(\d+)[行目～]*(\d+)行目：(.+)", output):
        start = int(m.group(1))
        end = int(m.group(2))
        tag = m.group(3).strip()
        blocks.append({"start_line": start, "end_line": end, "tag": tag})

    # タグ分け結果を提示
    tags = sorted({b["tag"] for b in blocks})
    print("\n=== 以下のようにタグ分けしました ===")
    for t in tags:
        print(t)
    print("======================\n")

    yn = input("このタグ分けで問題ないですか？ [Y/N]: ").strip().lower()
    if yn == "y":
        # jsonに保存
        with open("phase_blocks.json", "w", encoding="utf-8") as f:
            json.dump(blocks, f, ensure_ascii=False, indent=2)
        # .txtに保存（出現順に書かれるよう処理）
        tags_in_order = []
        for b in blocks:
            t = b["tag"]
            if t not in tags_in_order:
                tags_in_order.append(t)
        with open("phase_tags.txt", "w", encoding="utf-8") as f:
            for t in tags_in_order:
                f.write(t + "\n")
        print("保存しました。")
        break
    else:
        # ユーザーから追加指示を受けて再プロンプト
        add = input("プロンプトに追加する指示（例：『大まかに分類してください』など）: ").strip()
        user_prompt = add
        print("改めてタグ分け中です...\n")