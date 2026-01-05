# Project Overview - Conversational Drive Navigator

## 概要

**Conversational Drive Navigator** は、町から海辺までのドライブを4人の友人とナビゲートする、シナリオベースの会話型AIアプリケーションです。画像ベースのアバター表示を持ち、将来的には3DアバターやHTML表示にも拡張可能な設計になっています。

### バージョン情報

- **現在のバージョン**: 2.0.0
- **Python**: 3.12+
- **UIフレームワーク**: Gradio 6.0+
- **LLM**: OpenAI GPT-4o-mini
- **設定形式**: YAML (prompts/scenario.yaml)

---

## アーキテクチャ概要

### システム構成図

```
┌─────────────────────────────────────────────────────────────┐
│                    conversation_app.py                      │
│                    (メインアプリケーション)                    │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────────┐  ┌────────────────────┐  ┌──────────────┐
│   renderers/     │  │ scenario_manager   │  │   prompts/   │
│                  │  │                    │  │              │
│ ・base           │  │ ・YAMLサポート     │  │ ・system.txt │
│ ・paper_theater  │  │ ・シーン/ページ管理 │  │ ・scenario   │
│                  │  │ ・遷移ロジック      │  │  .yaml       │
│                  │  │                    │  │              │
└──────────────────┘  └────────────────────┘  └──────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                  ┌───────────────────────┐
                  │   prompts/data/       │
                  │ ・mood_*.png (20枚)   │
                  │ ・bg_*.jpg (背景画像) │
                  └───────────────────────┘
```

---

## ディレクトリ構造

```
claude-test02/
├── conversation_app.py          # メインエントリーポイント
├── scenario_manager.py          # シーン/ページ状態管理（YAMLのみ）
├── yaml_scenario_loader.py      # YAMLパーサー
├── migration_tool.py            # テキスト→YAML変換ツール（旧版用）
│
├── renderers/                   # ディスプレイ抽象化層
│   ├── __init__.py
│   ├── base_renderer.py         # 抽象基底クラス
│   └── paper_theater_renderer.py # HTML/CSS合成レンダラー
│
├── prompts/                     # プロンプトと設定
│   ├── system_prompt.txt        # 技術的指示（開発者管理）
│   ├── scenario.yaml            # YAMLシナリオ定義
│   └── data/                    # 画像リソース
│       ├── mood_basic.png       # ムード画像（20種類）
│       ├── mood_laughing.png
│       ├── ...
│       └── bg_*.jpg             # 背景画像（オプション）
│
├── images/                      # 旧画像ディレクトリ（削除予定）
│
├── .vscode/                     # VSCode設定
│   └── launch.json              # デバッグ設定
│
├── README.md                    # ユーザー向けドキュメント
├── CLAUDE.md                    # 開発者向けガイド
├── CHANGELOG.md                 # 変更履歴
├── LLM_SCRIPT.md                # LLMプロンプト詳細
├── PROJECT_OVERVIEW.md          # 本ドキュメント
│
├── pyproject.toml               # uv依存関係定義
├── requirements.txt             # pip依存関係
├── uv.lock                      # ロックファイル
│
├── run.sh / run.bat             # 起動スクリプト
└── test_scenario.py             # テストスクリプト
```

---

## 主要コンポーネント

### 1. conversation_app.py（メインアプリケーション）

**役割**: アプリケーション全体のオーケストレーション

**主要機能**:
- Gradio UIの構築（チャット、画像表示、ステータス）
- LLM（OpenAI GPT-4o-mini）との通信
- レンダラーとシナリオマネージャーの統合
- イベントハンドリング（メッセージ送信、リセット）

**重要な関数**:
```python
def chat(message, history)               # LLM会話処理
def process_user_message(...)            # ユーザー入力処理
def build_system_prompt(page_data, ...)  # プロンプト構築
def parse_llm_response(response_text)    # LLM応答パース
```

**プログラム的なレンダラー選択**（Line ~25）:
```python
# 現在: Paper Theater Renderer（HTML/CSS合成）
renderer = PaperTheaterRenderer(DEFAULT_PAPER_THEATER_MOODS)

# 旧: Kamishibai Renderer（非推奨）
# renderer = KamishibaiRenderer(DEFAULT_KAMISHIBAI_STATES)

# 将来: 3Dアバター
# renderer = Avatar3DRenderer(config)
```

---

### 2. scenario_manager.py（シナリオ管理）

**役割**: シーン/ページの階層的管理と遷移制御

**主要機能**:
- YAMLシナリオファイル（`prompts/scenario.yaml`）のパース
- シーン → ページの階層構造管理
- LLM制御によるページ遷移
- ページごとのムード制約管理
- 背景画像サポート

**YAMLデータ構造**:
```python
{
  'scene_id': {
    'description': 'シーン説明',
    'scene_prompt': 'シーンレベルプロンプト',
    'start_page': 'page_id',
    'opening_message': 'シーン開始メッセージ',
    'background_image': 'data/bg_scene.jpg',
    'allowed_moods': ['mood1', 'mood2', ...],
    'pages': {
      'page_id': {
        'mood': 'ムード名',
        'opening_message': '冒頭発話',
        'page_prompt': 'ページ指示',
        'background_image': 'data/bg_page.jpg',
        'allowed_moods': ['mood1', ...],
        'transitions': [
          {
            'id': 'cafe',
            'description': '休憩を希望したとき'
          },
          {
            'id': 'shopping',
            'description': '買い物を希望したとき'
          }
        ]
      }
    }
  }
}
```

**主要メソッド**:
```python
def __init__(scenario_file)           # YAMLファイルパス受け取り
def start_scenario(scene_id)          # シナリオ開始
def get_current_page_data()           # 現在ページ取得
def _transition_to(target)            # ページ遷移
def _load_yaml_scenarios()            # YAML読み込み
```

---

### 3. renderers/（レンダラーパッケージ）

#### 3.1 base_renderer.py（抽象基底クラス）

**役割**: すべてのレンダラーが実装すべきインターフェースを定義

**抽象メソッド**:
```python
@abstractmethod
def render(mood_name: str, background_path: Optional[str] = None) -> Any
    """ムード名と背景画像に基づいて表示リソースを返す"""

@abstractmethod
def validate_mood(mood_name: str, allowed_moods: Optional[List[str]]) -> str
    """ムード名を検証し、有効なムードを返す"""

@abstractmethod
def get_default_display() -> Any
    """デフォルト表示リソースを返す"""

@abstractmethod
def get_mood_description_prompt() -> str
    """LLM用のムード説明プロンプトを返す"""

# 後方互換メソッド
def validate_state(...)  # → validate_mood() のエイリアス
def get_state_description_prompt()  # → get_mood_description_prompt() のエイリアス
```

#### 3.2 paper_theater_renderer.py（HTML/CSS合成レンダラー・推奨）

**役割**: HTML/CSSによる背景+ムード画像の合成表示

**特徴**:
- HTML/CSSで画像を重ね合わせ（PIL不要）
- 背景画像とムード画像の2層構造
- `gr.HTML` コンポーネントで表示
- チラつき防止（HTMLのみ更新）
- 20種類のムード画像
- 日本語ムード名（ユーザーカスタマイズ可能）

**ムード設定例**:
```python
DEFAULT_PAPER_THEATER_MOODS = {
    "基本スタイル": "prompts/data/mood_basic.png",
    "笑う": "prompts/data/mood_laughing.png",
    "困る": "prompts/data/mood_troubled.png",
    "運転": "prompts/data/mood_driving.png",
    # ... 全20ムード
}
```

**HTML出力例**:
```html
<div style="position: relative; width: 800px; height: 600px;">
  <!-- 背景画像 -->
  <img src="/prompts/data/bg_cafe.jpg"
       style="position: absolute; width: 100%; height: 100%; object-fit: cover;">
  <!-- ムード画像（中央配置） -->
  <img src="/prompts/data/mood_laughing.png"
       style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);">
</div>
```

---

### 4. prompts/（プロンプトと設定）

#### 4.1 system_prompt.txt（システムプロンプト）

**役割**: LLMへの技術的指示（開発者管理）

**内容**:
- 応答形式（JSON構造）
- ムード使い分けルール
- キャラクター設定
- レンダラームード説明の動的挿入ポイント

**JSON応答形式**:
```json
{
  "text": "ユーザーへの応答メッセージ",
  "mood": "表示するムード名",
  "transition": "次のページID"
}
```

**動的挿入**:
```python
base_system_prompt = base_system_prompt.replace(
    '{RENDERER_MOOD_DESCRIPTION}',
    renderer.get_mood_description_prompt()
)
```

#### 4.2 scenario.yaml（YAMLシナリオ・推奨）

**役割**: YAML形式のシナリオ定義（ユーザー編集可能）

**構造**:
```yaml
base:
  description: str              # アプリケーション説明
  base_prompt: str              # 基本プロンプト
  start_scene: str              # 開始シーン

scenes:
  - scene_id: str
    description: str
    scene_prompt: str           # シーンレベルプロンプト
    start_page: str
    opening_message: str        # シーン開始メッセージ
    background_image: str       # デフォルト背景
    allowed_moods: [str]        # ムード制約

    pages:
      - page_id: str
        description: str
        page_prompt: str        # ページ固有プロンプト（遷移以外の内容を記述）
        opening_message: str    # ページ開始メッセージ
        default_mood: str       # デフォルトムード
        background_image: str   # 背景画像パス
        allowed_moods: [str]    # ページムード制約

        transitions:            # 辞書形式（簡潔）
          target_id: condition  # 遷移先: 自然言語条件
          cafe: 休憩を希望したとき
          shopping: 買い物を希望したとき

configuration:
  mood_images:
    mood_name: str              # ムード画像パス
  background_images:
    bg_name: str                # 背景画像パス
```

**利点**:
- 階層的な設定管理
- 自然言語遷移条件
- シーン/ページレベルのプロンプト
- 背景画像サポート
- YAML検証とエラー報告

---

## データフロー

### 1. アプリケーション起動時

```
1. conversation_app.py 起動
   ↓
2. PaperTheaterRenderer インスタンス作成
   ↓
3. system_prompt.txt 読み込み
   ↓
4. Rendererムード説明を動的挿入
   ↓
5. ScenarioManager インスタンス作成
   ↓
6. YAMLファイルを yaml_scenario_loader.py でパース
   ↓
7. Gradio UI 構築・起動（gr.HTML コンポーネント）
   ↓
8. 初回メッセージ表示（start_scene から開始）
```

### 2. ユーザーメッセージ処理

```
1. ユーザーがメッセージ入力
   ↓
2. process_user_message() 呼び出し
   ↓
3. chat() 関数でLLM呼び出し
   │
   ├─ 現在ページデータ取得（ScenarioManager）
   ├─ システムプロンプト構築
   │  ├─ シーンプロンプト追加
   │  ├─ ページプロンプト追加
   │  ├─ ムード制約情報
   │  └─ 遷移条件フォーマット（自然言語）
   ├─ OpenAI API 呼び出し
   ├─ JSON応答パース（text, mood, transition）
   │
   ↓
4. ページ遷移判定
   │
   └─ 遷移あり → ScenarioManager._transition_to()
   └─ 遷移なし → 現在ページ継続
   ↓
5. ムード検証（Renderer.validate_mood）
   ↓
6. HTML/CSS合成レンダリング
   │
   ├─ 背景画像パス取得（page_data）
   ├─ ムード画像パス取得（mood_config）
   └─ HTMLマークアップ生成
   ↓
7. Gradio UIへ返却
   ├─ チャット履歴更新
   └─ gr.HTML 更新（チラつき防止）
   ↓
8. 画面更新（チャット + HTML表示）
```

### 3. ページ遷移時

```
1. LLMが遷移指示を返す
   {"text": "...", "mood": "...", "transition": "scene:page"}
   ↓
2. ScenarioManager._transition_to("scene:page")
   │
   └─ "scene:page" → シーン間遷移
   └─ "page" → 同一シーン内遷移
   ↓
3. page_just_changed フラグ ON
   ↓
4. 次回 chat() 呼び出し時
   ↓
5. opening_message を返す（LLM呼び出しなし）
   ↓
6. page_just_changed フラグ OFF
   ↓
7. 通常会話再開
```

---

## 主要設計パターン

### 1. Renderer Pattern（レンダラーパターン）

**目的**: 表示方法の抽象化と交換可能性

**利点**:
- 1行のコード変更でレンダラー切り替え可能
- 画像 → 3Dアバター → HTML などへ容易に拡張
- 表示ロジックとビジネスロジックの分離

**実装例**:
```python
# 現在: Paper Theater（HTML/CSS合成）
renderer = PaperTheaterRenderer(DEFAULT_PAPER_THEATER_MOODS)

# 旧: Kamishibai（非推奨）
# renderer = KamishibaiRenderer(DEFAULT_KAMISHIBAI_STATES)

# 将来: 3Dアバター
# renderer = Avatar3DRenderer(animation_config)
```

### 2. YAML Configuration（YAML設定）

**目的**: 階層的で拡張性のあるシナリオ管理

**利点**:
- YAML形式による構造化設定
- シーン/ページレベルのプロンプト
- 自然言語遷移条件（LLM判定）
- 背景画像サポート
- スキーマ検証とエラー報告

### 3. Prompt Separation（プロンプト分離）

**目的**: 技術的指示とコンテンツの分離

**利点**:
- 開発者はシステムプロンプト管理
- ユーザーはYAMLシナリオを自由編集
- 役割分担の明確化

### 4. Scene/Page Hierarchy（シーン/ページ階層）

**目的**: 構造化されたシナリオ管理

**利点**:
- 大規模シナリオの整理
- 自然言語による条件付き遷移
- ページごとの制約（ムード制限、背景画像）
- シーン/ページレベルのコンテキスト管理

---

## 技術スタック

### フロントエンド
- **Gradio 6.0+**: Webインターフェース構築
  - ChatBot コンポーネント（会話履歴）
  - HTML コンポーネント（HTML/CSS画像合成表示）
  - Textbox コンポーネント（入力/ステータス）

### バックエンド
- **Python 3.12+**: メイン言語
- **OpenAI API**: LLM（GPT-4o-mini）
- **PyYAML**: YAML設定パース
- **python-dotenv**: 環境変数管理

### パッケージ管理
- **uv**: 高速パッケージマネージャー
- **pyproject.toml**: プロジェクト定義

### 開発ツール
- **VSCode**: 推奨IDE
- **debugpy**: デバッガー
- **migration_tool.py**: テキスト→YAML変換ツール

---

## 重要な実装詳細

### 1. HTML/CSS画像合成

**手法**: PIL不使用、HTML/CSSによる2層合成

**実装**:
```python
# PaperTheaterRenderer.render()
return f'''
<div style="position: relative; width: 800px; height: 600px;">
  <!-- 背景画像（下層） -->
  <img src="/{background_path}"
       style="position: absolute; width: 100%; height: 100%; object-fit: cover;">
  <!-- ムード画像（上層・中央） -->
  <img src="/{mood_path}"
       style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);">
</div>
'''
```

**利点**:
- 依存関係削減（PIL不要）
- チラつき防止（Gradio HTML直接更新）
- レスポンシブ対応容易
- パフォーマンス向上

### 2. YAML vs テキスト形式

**自動検出**:
```python
# scenario_manager.py
if scenario_file.endswith(('.yaml', '.yml')):
    self.scenarios = self._load_yaml_scenarios()
    self.format = 'yaml'
else:
    self.scenarios = self._load_text_scenarios()
    self.format = 'text'
```

**推奨**: YAMLフォーマット（背景画像、階層プロンプト、遷移条件）

### 3. ムード名の日本語維持

**設計判断**: ユーザーカスタマイズ性のため日本語を維持

**影響範囲**:
- `prompts/scenario.yaml`: ムード名は日本語
- `renderers/paper_theater_renderer.py`: ムード辞書のキーは日本語
- `prompts/data/`: ファイル名は `mood_*.png`（英語）

**英語化された部分**:
- ソースコードの変数名
- ソースコードのコメント
- 技術ドキュメント

### 4. 後方互換性の維持

**レガシーフィールドのエイリアス**:
```python
# yaml_scenario_loader.py
page_data = {
    'mood': default_mood,           # 新フィールド
    'image': default_mood,          # 旧エイリアス
    'opening_message': msg,         # 新フィールド
    'opening_speech': msg,          # 旧エイリアス
    'page_prompt': prompt,          # 新フィールド
    'additional_prompt': prompt,    # 旧エイリアス
}
```

**メソッドエイリアス**:
```python
# base_renderer.py
def validate_state(...):  # 旧メソッド → validate_mood()
def get_state_description_prompt():  # 旧メソッド → get_mood_description_prompt()
```

---

## 拡張ポイント

### 1. 新しいレンダラーの追加

**手順**:
1. `renderers/` に新しいレンダラークラス作成
2. `BaseRenderer` を継承
3. 4つの抽象メソッドを実装
4. `conversation_app.py` の Line ~23 でインスタンス化

**例**:
```python
# renderers/avatar3d_renderer.py
class Avatar3DRenderer(BaseRenderer):
    def render(self, state_name: str) -> str:
        # 3Dモデルファイルパスを返す
        return f"models/{state_name}.glb"

    # 他のメソッドも実装...
```

### 2. 新しいシーンの追加

**手順**（YAML形式）:
1. `prompts/scenario.yaml` 編集
2. `scenes` リストに新しいシーンを追加
3. シーンプロンプト、ページ、遷移条件を定義
4. 必要に応じて背景画像を `prompts/data/` に配置
5. ムード画像は既存の20種類を使用

**例**:
```yaml
scenes:
  - scene_id: new_scene
    description: 新しいシーン
    scene_prompt: シーン固有の指示
    start_page: first_page
    opening_message: ようこそ！
    background_image: prompts/data/bg_new.jpg
    allowed_moods: null
    pages:
      - page_id: first_page
        # ...
```

### 3. LLMモデルの変更

**場所**: `conversation_app.py` Line 152

```python
response = client.chat.completions.create(
    model="gpt-4o-mini",  # ← ここを変更
    messages=[...],
    temperature=0.7,
    max_tokens=500
)
```

---

## 起動とデバッグ

### 起動方法

**コマンドライン**:
```bash
uv run python conversation_app.py
```

**VSCode デバッグ**:
- F5 キー押下
- "Python Debugger: Conversation App" 設定を使用
- ブレークポイント設定可能

### ポート設定

**環境変数**:
```bash
# .env ファイルに設定
GRADIO_SERVER_PORT=7862
```

**デフォルト**: 7862

---

## トラブルシューティング

### 画像が表示されない

**原因**: `images/` ディレクトリのパス問題

**確認**:
```python
# renderers/kamishibai_renderer.py で画像パス確認
print(f"Image path: {image_path}")
```

### シナリオが読み込まれない

**原因**: YAMLまたはテキストファイルのフォーマットエラー

**確認**:
```bash
# YAMLの場合
uv run python -c "from yaml_scenario_loader import YAMLScenarioLoader; YAMLScenarioLoader('prompts/scenario.yaml').load()"

# テキストの場合
uv run python test_scenario.py
```

### LLMがJSON形式で返さない

**原因**: システムプロンプトの指示不足

**対策**:
- `prompts/system_prompt.txt` の JSON例を明確化
- LLMに "mood" フィールドを正しく使用させる

### 背景画像が表示されない

**原因**:
- 画像パスが正しくない
- ファイルが存在しない

**確認**:
```python
# prompts/scenario.yaml の background_image パスを確認
# 例: "prompts/data/bg_cafe.jpg" が実際に存在するか
```

---

## 今後の開発方向

### 短期（Version 2.1）
- [ ] 背景画像の追加と設定
- [ ] YAML設定の洗練化
- [ ] より多くのシナリオ追加
- [ ] エラーハンドリング強化
- [ ] テストカバレッジ向上

### 中期（Version 3.0）
- [ ] 3Dアバターレンダラー実装
- [ ] マルチモーダル対応（音声入力/TTS）
- [ ] セッション永続化
- [ ] 動的背景切り替えアニメーション

### 長期（Version 4.0）
- [ ] マルチユーザー対応
- [ ] カスタムLLM統合（ローカルモデル）
- [ ] プラグインシステム
- [ ] YAML設定のGUIエディタ

---

## ライセンスと貢献

**プロジェクトタイプ**: プライベート開発プロジェクト

**貢献方法**: 現在は単独開発

**ドキュメント**:
- ユーザー向け: `README.md`
- 開発者向け: `CLAUDE.md`
- 変更履歴: `CHANGELOG.md`
- LLM詳細: `LLM_SCRIPT.md`
- 全体像: `PROJECT_OVERVIEW.md`（本ドキュメント）

---

## まとめ

**Conversational Drive Navigator** は、レンダラーパターンとYAML設定を活用した拡張性の高い会話型AIアプリケーションです。HTML/CSS画像合成による現在の実装から、将来的には3Dアバターなど、多様な表示方法に対応できる設計になっています。

**主要な特徴**:
- ✅ プラグイン可能なレンダラーシステム
- ✅ YAML形式の階層的シナリオ管理
- ✅ HTML/CSS画像合成（背景+ムード）
- ✅ 自然言語遷移条件（LLM判定）
- ✅ プロンプトの分離（技術 vs コンテンツ）
- ✅ Gradio 6.0 ベースのモダンUI
- ✅ OpenAI GPT-4o-mini 統合
- ✅ 後方互換性の維持

**Version 2.0 の主要変更点**:
- "state/image" → "mood" への用語変更
- "kamishibai" → "paper theater" への名称変更
- テキスト形式 → YAML形式への移行
- PIL画像合成 → HTML/CSS合成への移行
- 背景画像サポート追加
- シーン/ページレベルプロンプト追加
- 自然言語遷移条件追加

**次のステップ**:
1. [README.md](README.md) でユーザーガイドを確認
2. [CLAUDE.md](CLAUDE.md) で開発ガイドを確認
3. [conversation_app.py](conversation_app.py) でコードを探索
4. [prompts/scenario.yaml](prompts/scenario.yaml) でシナリオをカスタマイズ
5. [migration_tool.py](migration_tool.py) でテキスト→YAML変換
