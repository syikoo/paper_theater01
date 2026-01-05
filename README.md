# Conversational Drive Navigator

町中から海辺までのドライブを、シーン/ページ構成のシナリオで案内する対話アプリです。Gradio UIと紙芝居スタイルのレンダラーで、応答に合わせてムード画像と背景を切り替えます。

**Version 2.1.0**: テキストチャットと音声チャットの両方に対応したデュアルモードアプリケーションです。

## 主な特徴
- **デュアルモード対応**: テキスト入力と音声入力を切り替え可能
- **音声対話**: OpenAI Realtime APIによる自然な音声会話
- **自動文字起こし**: 音声会話の内容がチャット履歴に表示
- **インテリジェント分析**: 音声トランスクリプトからムードと遷移を自動検出
- `prompts/scenario.yaml` で定義したシーン/ページ・遷移に沿った会話進行
- YAMLの `configuration.mood_images` をそのまま使うムードレンダリング
- `base.start_scene` で開始シーンを設定可能（デフォルト: `town_start`）
- 背景画像の合成表示（YAML内 `background_image` を自動解決）
- Gradio 5 UI（左に表示、右にチャット）、OpenAI GPT-4o-mini + Realtime API連携

## セットアップ

### 必要要件
- **Python 3.10以上**（FastRTC要件）
- **OpenAI API キー**（GPT-4o-mini + Realtime API）
- **マイク**（音声モード使用時）

### インストール手順

1) uvが未インストールの場合は導入
   - Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`

2) 依存パッケージのインストール
   ```bash
   uv sync
   ```

   **注意**: 初回起動時、音声機能のVADモデル（約3MB）が自動ダウンロードされます。

3) 環境変数の設定
   `.env.example` を `.env` にコピーし、`OPENAI_API_KEY` を設定してください。

## 実行方法

### アプリケーション起動
```bash
uv run python conversation_app.py
# または
./run.sh        # macOS/Linux
run.bat         # Windows
```

デフォルトで `http://127.0.0.1:7862` で起動します。

### ポート変更
```bash
GRADIO_SERVER_PORT=7861 uv run python conversation_app.py
```

## 使い方

### テキストモード（デフォルト）
1. アプリを起動すると、デフォルトで「Text」モードが選択されています
2. 下部のテキストボックスにメッセージを入力
3. 「Send」ボタンをクリック、またはEnterキーを押す
4. AIの応答がチャット履歴に表示され、左側の画像が変化します

### 音声モード
1. 画面右上の「Voice」ラジオボタンをクリックしてモードを切り替え
2. ブラウザのマイク許可を求められたら「許可」をクリック
3. オレンジ色のアニメーションが表示されます
4. マイクに向かって話しかける
5. 発話が終わると自動的にAIが音声で応答します
6. 会話内容（文字起こし）が自動的にチャット履歴に追加されます
7. 左側の画像は会話内容に応じて自動的に変化します

### モード切り替え
- いつでも「Text」と「Voice」を切り替え可能
- 会話履歴は両モード間で共有されます
- テキストモードの会話と音声モードの会話が混在できます

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

- 基本機能テスト（テキストモード）:
  ```bash
  uv run python test_basic_functionality.py
  ```

- JSON分離テスト（表示履歴にJSONが含まれないことを確認）:
  ```bash
  uv run python test_json_display.py
  ```

## トラブルシューティング

### 共通の問題
- **画像が出ない**: `configuration.mood_images` のパスと `prompts/images/` のファイル名が一致しているか確認してください。
- **APIキーエラー**: `.env` の `OPENAI_API_KEY` が有効か確認してください。
- **Python バージョンエラー**: Python 3.10以上がインストールされているか確認してください。

### 音声モード固有の問題

#### マイクが使えない
- ブラウザの設定でマイク権限が許可されているか確認
- 別のアプリケーションがマイクを使用していないか確認
- ブラウザを再起動して再度許可

#### 音声が聞こえない
- デバイスのスピーカー設定を確認
- ブラウザの音量設定を確認
- 別のタブで音声が再生されていないか確認

#### VADモデルのダウンロードエラー
- インターネット接続を確認
- 初回起動時は約3MBのモデルファイルがダウンロードされます
- 以降はキャッシュが使用されます

#### オレンジのアニメーションが画面全体を覆う
- CSSの問題の可能性があります
- ブラウザのキャッシュをクリアして再読み込み
- 別のブラウザで試してみてください

#### 音声モードに切り替わらない
- ページを再読み込みしてください
- ブラウザのコンソールでエラーを確認
- FastRTC依存関係が正しくインストールされているか確認: `uv sync --force`

#### 文字起こしがチャットに表示されない
- 1秒ごとの自動更新を待ってください
- ページを手動で再読み込み
- ブラウザのコンソールでエラーログを確認

## コスト情報

### API使用料金の目安
- **テキストモード**: 約$0.0001/メッセージ（gpt-4o-mini）
- **音声モード**: 約$0.06/分（Realtime API） + 約$0.0001/メッセージ（トランスクリプト分析）

音声モードは2回のAPI呼び出しを行います:
1. Realtime API: 音声入出力とトランスクリプト生成
2. gpt-4o-mini: トランスクリプトからムード/遷移を抽出

## 詳細ドキュメント

- **[VOICE_MODE_README.md](VOICE_MODE_README.md)**: 音声モードの詳細仕様
- **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)**: プロジェクト全体のアーキテクチャ
- **[AGENTS.md](AGENTS.md)**: 開発者向けガイド
- **[CHANGELOG.md](CHANGELOG.md)**: バージョン履歴
