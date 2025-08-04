import glob
import json
import tiktoken
import pandas as pd

MODEL_NAME = "text-embedding-3-large"
enc = tiktoken.encoding_for_model(MODEL_NAME)

def count_tokens(text):
    return len(enc.encode(text))

def get_block_text(block):
    txtfile = block["source_file"] + ".txt"
    with open(txtfile, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    return "\n".join(lines[block["start_line"]:block["end_line"]+1])

# 全工程ブロックを集める
all_blocks = []
for fname in sorted(glob.glob("phase_blocks_*.json")):
    with open(fname, encoding="utf-8") as f:
        blocks = json.load(f)
    for b in blocks:
        b["source_file"] = fname.replace("phase_blocks_", "").replace(".json", "")
        all_blocks.append(b)

# トークン数計算
token_report = []
for idx, block in enumerate(all_blocks):
    txt = get_block_text(block)
    n_tok = count_tokens(txt)
    token_report.append({
        "block_id": idx,
        "source_file": block["source_file"],
        "tag": block["tag"],
        "start_line": block["start_line"],
        "end_line": block["end_line"],
        "char_len": len(txt),
        "token_len": n_tok,
    })

# トークン数順にソートして上位を出力
token_report = sorted(token_report, key=lambda x: -x["token_len"])

print("トークン数が多い順にTOP10：")
for b in token_report[:10]:
    print(f"{b['source_file']} [{b['tag']}]: {b['start_line']}-{b['end_line']} chars={b['char_len']} tokens={b['token_len']}")

# 全ブロックの最大値も出力
max_block = token_report[0]
print(f"\n最大トークン数ブロック:\n{max_block}")

# CSV保存
df = pd.DataFrame(token_report)
df.to_csv("block_token_report.csv", index=False, encoding="utf-8-sig")
print("\nblock_token_report.csvに詳細レポート出力済み")
