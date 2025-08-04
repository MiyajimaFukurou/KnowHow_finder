<h2>作業会話ノウハウ抽出エージェント</h2>

<div class="section">
  <p>
    「複数ペアの作業会話データ」からノウハウを抽出し、これをもとに質問に答えるエージェントです。<br>
    作業会話だからこそ得られる、明示的・非明示的ノウハウ、作業の流れ、陥りやすいポイントなどを、生成AIによる俯瞰的観察により発見・提示することを目指します。
  </p>
</div>

<div class="section">
  <h3>概要</h3>
  <ul>
    <li><b>add_tag.py</b> … 作業会話の書き起こしデータに工程（フェーズ）タグを一貫して付与</li>
    <li><b>tag2knowhow.py</b> … ユーザ質問→工程タグ推定→該当工程の全ペア分会話を要約して回答生成</li>
    <li><b>tools/tokenChecker.py</b> … トークン長チェックなど補助スクリプト</li>
    <li><b>experiments/RAG_butTokenOver.py</b> … embedding token超過で断念したRAG実験用コード</li>
  </ul>
</div>

<div class="section">
  <h3>ディレクトリ構成</h3>
  <pre class="dir-structure">
.
├── add_tag.py
├── tag2knowhow.py
├── tools/
│   └── tokenChecker.py
├── experiments/
│   └── RAG_butTokenOver.py
├── .gitignore
  </pre>
</div>

<div class="section">
  <h3>使い方</h3>
  <ol>
    <li>
      <b>add_tag.py</b>で会話データを工程ごとにタグ付け<br>
      → <code>phase_blocks_*.json</code>と<code>phase_tags.txt</code>が生成されます
    </li>
    <li>
      <b>tag2knowhow.py</b>で質問を入力<br>
      → 質問から工程タグを推定し、その工程の全ペア分会話を横断的に見ることで、ノウハウを提示します
    </li>
  </ol>
</div>
