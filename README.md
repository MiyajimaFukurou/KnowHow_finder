## 作業会話ノウハウ抽出エージェント

「複数ペアの作業会話データ」からノウハウを抽出し、これをもとに質問に答えるエージェントです。  
作業会話だからこそ得られる、明示的・非明示的ノウハウ、作業の流れ、陥りやすいポイントなどを、生成AIによる俯瞰的観察により発見・提示することを目指します。

---

### 概要

- **add_tag.py** … 作業会話の書き起こしデータに工程（フェーズ）タグを一貫して付与
- **tag2knowhow.py** … ユーザ質問 → 工程タグ推定 → 該当工程の全ペア分会話を要約してノウハウ提示
- **RAG2knowhow.py** … RAGを用いたノウハウ提示
- **tools** … トークン長チェックなど補助スクリプト
- **experiments** … 実験的コード群

---

### ディレクトリ構成

```plaintext
.
├── add_tag.py
├── tag2knowhow.py
├── RAG2knowhow.py
├── tools/
│   └── tokenChecker.py
├── experiments/
│   └── RAG_butTokenOver.py
├── .gitignore
```
---

### 使い方
1. **前準備**  
   - add_tag.pyで会話データを工程ごとにタグ付け  
   → phase_blocks_*.jsonとphase_tags.txtが生成されます
3. **回答生成**  
   - tag2knowhow.py  
   → 質問から工程タグを推定し、その工程の全ペア分会話を横断的に見ることで、ノウハウを提示します
   - RAG2knowhow.py  
   → RAGによる類似状況の検索から、ノウハウを提示します
