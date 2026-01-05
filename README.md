# Conversational Drive Navigator

町中から海辺までのドライブを、シーン/ページ構成のシナリオで案内する対話アプリです。Gradio UIと紙芝居スタイルのレンダラーで、応答に合わせてムード画像と背景を切り替えます。

## 主な特徴
- `prompts/scenario.yaml` で定義したシーン/ページ・遷移に沿った会話進行
- YAMLの `configuration.mood_images` をそのまま使うムードレンダリング
- `base.start_scene` で開始シーンを設定可能（デフォルト: `town_start`）
- 背景画像の合成表示（YAML内 `background_image` を自動解決）
- Gradio 6 UI（左に表示、右にチャット）、OpenAI GPT-4o-mini連携

## セットアップ
1) uvが未インストールの場合は導入  
   - Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`  
   - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`

2) 依存パッケージのインストール  
   ```bash
   uv sync
   ```

3) 環境変数の設定  
   `.env.example` を `.env` にコピーし、`OPENAI_API_KEY` を設定してください。

## 実行方法
- Gradioアプリ起動:
  ```bash
  uv run python conversation_app.py
  # または
  ./run.sh        # macOS/Linux
  run.bat         # Windows
  ```
- ポート変更: `GRADIO_SERVER_PORT=7861 uv run python conversation_app.py`

## シナリオとアセット
- シナリオ定義: `prompts/scenario.yaml`
  - `base.start_scene`: アプリが起動時に読む開始シーン
  - `configuration.mood_images`: ムード名→画像パス。`images/` で始まるパスは自動的に `prompts/images/` に解決されます。
  - `background_image`: `images/page_*.jpg` などを指定すると背景として合成表示
- 画像配置例:
  ```
  prompts/
    images/
      basic.png, talking.png, ...  # ムード画像
      page_departure.jpg, ...      # 背景画像
  ```
- シナリオの追加・編集: `scenes` 配下にシーンとページを追加し、`transitions` で遷移IDを指定します。LLM応答の `transition` フィールドにこのIDを返すと画面が遷移します。

## テスト
- シナリオ読込と遷移の簡易チェック:
  ```bash
  uv run python test_scenario.py
  ```

## トラブルシューティング
- 画像が出ない: `configuration.mood_images` のパスと `prompts/images/` のファイル名が一致しているか確認してください。
- APIキーエラー: `.env` の `OPENAI_API_KEY` が有効か確認してください。
