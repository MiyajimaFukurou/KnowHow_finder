import openai
import re
import json
import os
import glob
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
api_key = os.getenv("API_KEY")
openai.api_key = api_key
base_txt = "2024-10-02_13_11_31.txt" # タグ分けのベースになるtxtファイル

with open(base_txt, encoding="utf-8") as f:
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

- 工程名は端的な日本語で自由につけてOKです。

{user_prompt}

【会話データ】
{line_txt}
"""
    return base

user_prompt = ""

# --- ここから、全ファイルのタグ付け処理 ---------
def add_tag_all():
    # 1. phase_tags.txtを読み込む
    with open("phase_tags.txt", encoding="utf-8") as f:
        fixed_tags = [l.strip() for l in f if l.strip()]

    tag_list_str = "・" + "\n・".join(fixed_tags)
    tag_instr = f"これは「phase_tags.txt」です。記載されているタグのみを使い、タグ付けしてください。ここに記載されているタグは遵守し、追記・削除は絶対に行わないでください:\n{tag_list_str}"

    # --- base_txtの区間数を取得 ---
    base_blocks_path = f"phase_blocks_{base_txt}.json"
    with open(base_blocks_path, encoding="utf-8") as f:
        base_blocks = json.load(f)
    base_block_count = len(base_blocks)

    # 2. 他の2024-10-*.txtについてもphase_tag.txtをベースにタグ分け
    txt_files = sorted(glob.glob("2024-10-*.txt"))

    for fname in txt_files:
        if fname == base_txt: # 1件目はすでに処理済みなので省略
            continue
        with open(fname, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        line_txt = "\n".join([f"{i}: {line}" for i, line in enumerate(lines)])

        for attempt in range(3):  # 最大3回試行
            prompt = f"""
以下は作業実践中の会話書き起こしです。
会話全体を俯瞰し、「どこからどこまでが同じ“作業工程（フェーズ）”なのか」を抽出し、
工程ごとにタグ名をつけて、区切り・対応範囲を明示してください。

【出力フォーマット例】
1. 0行目～12行目：TAG1
2. 13行目～41行目：TAG2
3. 42行目～100行目：TAG3
...

- タグ名は「phase_tags.txtに記載のもののみ」を必ず使ってください。他の表記は禁止です。
- タグ数は必ず{base_block_count}個にしてください。
{tag_instr}

【会話データ】
{line_txt}
"""
            # 3. 同様にタグ付け処理
            response = openai.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "あなたは作業会話の工程分析エキスパートです。"},
                    {"role": "user", "content": prompt}
                ],
                #max_tokens=2000,
                #temperature=0,
            )
            output = response.choices[0].message.content
            print(f"\n==== {fname} のタグ付け結果 ====")
            print(output)

            blocks = []
            for m in re.finditer(r"(\d+)[行目～]*(\d+)行目：(.+)", output):
                start = int(m.group(1))
                end = int(m.group(2))
                tag = m.group(3).strip()
                blocks.append({"start_line": start, "end_line": end, "tag": tag})

            if len(blocks) == base_block_count:
                outname = f"phase_blocks_{os.path.splitext(fname)[0]}.json"
                with open(outname, "w", encoding="utf-8") as f:
                    json.dump(blocks, f, ensure_ascii=False, indent=2)
                print(f"{outname} に保存しました")
                break
            else:
                print(f"タグ付け結果の工程数が不正です。再試行します... (期待: {base_block_count}, 実際: {len(blocks)})")
        else:
            print(f"3回試行しても工程数が一致しませんでした。Something Went Wrong ってやつです。: {fname}")
# ---------------------------------------

while True:
    prompt = make_prompt(user_prompt)
    response = openai.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "あなたは作業会話の工程分析エキスパートです。"},
            {"role": "user", "content": prompt}
        ],
        #max_tokens=2000,
        #temperature=0,
    )
    output = response.choices[0].message.content
    print(output)

    blocks = []
    for m in re.finditer(r"(\d+)[行目～]*(\d+)行目：(.+)", output):
        start = int(m.group(1))
        end = int(m.group(2))
        tag = m.group(3).strip()
        blocks.append({"start_line": start, "end_line": end, "tag": tag})

    tags = sorted({b["tag"] for b in blocks})
    print("\n=== 以下のようにタグ分けしました ===")
    for t in tags:
        print(t)
    print("======================\n")

    yn = input("このタグ分けで問題ないですか？ [Y/N]: ").strip().lower()
    if yn == "y":
        # jsonに保存
        outname = f"phase_blocks_{base_txt}.json"
        with open(outname, "w", encoding="utf-8") as f:
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
        print("他のファイルについても、同様にタグ分けを行います")
        add_tag_all()
        print("全ファイルのタグ分けが完了しました")
        break
    else:
        # ユーザーから追加指示を受けて再試行
        add = input("プロンプトに追加する指示（例：『大まかに分類してください』など）: ").strip()
        user_prompt = add
        print("改めてタグ分け中です...\n")