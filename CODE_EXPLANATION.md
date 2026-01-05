# コード詳細解説

このドキュメントでは、Conversational Drive Navigatorの各モジュールの実装詳細を解説します。

## 目次

1. [メインアプリケーション (conversation_app.py)](#1-メインアプリケーション-conversation_apppy)
2. [会話管理コア (core/)](#2-会話管理コア-core)
   - [ConversationManager](#21-conversationmanager)
   - [TextChatHandler](#22-textchathandler)
   - [VoiceChatHandler](#23-voicechathandler)
   - [TranscriptAnalyzer](#24-transcriptanalyzer)
3. [シナリオ管理 (scenario_manager.py)](#3-シナリオ管理-scenario_managerpy)
4. [YAMLローダー (yaml_scenario_loader.py)](#4-yamlローダー-yaml_scenario_loaderpy)
5. [レンダラー (renderers/)](#5-レンダラー-renderers)
   - [BaseRenderer](#51-baserenderer)
   - [PaperTheaterRenderer](#52-papertheaterrenderer)

---

## 1. メインアプリケーション (conversation_app.py)

### 概要

`conversation_app.py`はアプリケーション全体のエントリーポイントです。Gradio UIの構築、各コンポーネントの初期化、イベントハンドリングを担当します。

### 主要な初期化処理

```python
# Line 44: OpenAI クライアントの初期化
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Line 47-49: レンダラーの選択（プログラマティック選択）
scenario_manager = ScenarioManager('prompts/scenario.yaml')
mood_config = scenario_manager.get_mood_config() or DEFAULT_PAPER_THEATER_MOODS
renderer = PaperTheaterRenderer(mood_config)
```

**重要ポイント**:
- レンダラーは1行の変更で切り替え可能（Line 49）
- YAMLファイルから`mood_config`を読み込み、デフォルト設定も用意

### システムプロンプトの構築

```python
# Line 58-66: システムプロンプトの読み込みと動的構築
base_system_prompt = load_prompt_file('prompts/system_prompt.txt')
if scenario_manager.base_prompt:
    base_system_prompt = f"{base_system_prompt}\n\n{scenario_manager.base_prompt}"

# レンダラー固有のムード説明を注入
base_system_prompt = base_system_prompt.replace(
    '{RENDERER_MOOD_DESCRIPTION}',
    renderer.get_mood_description_prompt()
)
```

**重要ポイント**:
- システムプロンプトは`system_prompt.txt` + YAMLの`base_prompt`の組み合わせ
- `{RENDERER_MOOD_DESCRIPTION}`プレースホルダーにレンダラー固有のムード説明を動的挿入
- これにより、レンダラーを変更してもLLMが正しくムードを選択できる

### 画像パス解決

```python
# Line 73-89: 画像パスの解決関数
def resolve_image_path(path: str) -> str:
    """
    YAML形式のパス（例: "images/page_driving.jpg"）を
    実際のファイルパス（例: "prompts/images/page_driving.jpg"）に変換
    """
    if not path:
        return None

    if path.startswith("images/"):
        return f"prompts/{path}"

    return path
```

**重要ポイント**:
- YAMLでは`images/`で始まる相対パスを使用（ユーザーフレンドリー）
- 実際のファイルは`prompts/images/`に配置
- この関数で両者を橋渡し

### デュアルモード対応の会話処理

```python
# Line 103-142: テキストチャット処理
def chat(message, history):
    """テキストモードでのメッセージ処理"""
    result = conversation_manager.process_text_message(message)

    if result is None:  # ページ遷移直後
        return "", conversation_manager.history, conversation_manager.get_current_display()

    text_response, mood_name, transition = result
    return "", conversation_manager.history, conversation_manager.get_current_display()
```

**重要ポイント**:
- `process_text_message()`が`None`を返す場合、ページ遷移の`opening_message`を表示中
- LLM呼び出しをスキップして効率化

```python
# Line 144-164: 音声チャット処理
def voice_chat(audio: tuple, stream_handler: Stream) -> Generator:
    """音声モードでの処理（Realtime APIストリーミング）"""
    for audio_chunk in conversation_manager.process_voice_audio(audio):
        yield audio_chunk
```

**重要ポイント**:
- Generatorを使用してリアルタイム音声ストリーミング
- `process_voice_audio()`内部でRealtime APIと通信し、音声チャンクを順次yield

### Gradio UI構築

```python
# Line 191-307: Gradio インターフェース構築
with gr.Blocks(...) as demo:
    with gr.Row():
        with gr.Column(scale=1):
            # 左側: 画像表示エリア
            display = gr.HTML(value=initial_display)

        with gr.Column(scale=1):
            # 右側: チャットエリア
            mode_selector = gr.Radio(["Text", "Voice"], value="Text")

            # テキストモードコンポーネント
            with gr.Group(visible=True) as text_group:
                chatbot = gr.Chatbot(...)
                msg = gr.Textbox(...)

            # 音声モードコンポーネント
            with gr.Group(visible=False) as voice_group:
                audio_stream = Stream(...)
                chat_history_display = gr.Chatbot(...)
```

**重要ポイント**:
- 左右2カラムレイアウト（左: 画像、右: チャット）
- テキスト/音声モードでコンポーネントの表示を切り替え
- `Stream`コンポーネント（FastRTC）で音声入出力

### イベントハンドリング

```python
# Line 309-336: イベントハンドラーの接続
# テキスト送信（Enter or ボタン）
msg.submit(chat, [msg, chatbot], [msg, chatbot, display])
send.click(chat, [msg, chatbot], [msg, chatbot, display])

# 音声ストリーミング
audio_stream.stream(voice_chat, ...)

# モード切り替え
mode_selector.change(
    toggle_mode,
    inputs=[mode_selector],
    outputs=[text_group, voice_group]
)

# 会話履歴の定期更新（音声モード用）
demo.load(
    lambda: gr.Timer(active=True, value=1),
    outputs=[update_timer]
)
```

**重要ポイント**:
- テキストモードは同期的な処理（submit/clickイベント）
- 音声モードは非同期ストリーミング（stream イベント）
- 音声モード時は1秒ごとに会話履歴を自動更新（Timer）

---

## 2. 会話管理コア (core/)

### 2.1. ConversationManager

**ファイル**: `core/conversation_manager.py`

#### 概要

テキスト/音声モードの統一状態管理とオーケストレーション。デュアル履歴パターンを実装し、表示用とLLMコンテキスト用の履歴を分離管理します。

#### データ構造

```python
# Line 47-51: 共有状態
self.history = []         # 表示履歴（テキストのみ、チャットUI用）
self.llm_history = []     # LLM履歴（JSONを含む、コンテキスト用）
self.current_mode = "text"  # 現在のモード
self.page_just_changed = False  # ページ遷移フラグ
self.previous_page_location = None  # 前回のページ位置
```

**デュアル履歴パターンの理由**:
- **history**: チャットUIに表示する履歴（ユーザー/アシスタントのテキストのみ）
- **llm_history**: LLMに送るコンテキスト（JSONレスポンス全体を含む）
- LLMはJSON形式で応答するが、ユーザーにはテキスト部分のみ表示したい
- LLMコンテキストには過去のJSON応答を含めることで、一貫性のあるムード選択が可能

#### テキストメッセージ処理

```python
# Line 109-161: テキストメッセージ処理
def process_text_message(self, user_message: str):
    # 1. ページ遷移直後は opening_message を返す
    if self.page_just_changed:
        page_data = self.scenario_manager.get_current_page_data()
        opening_msg = page_data.get('opening_message', ...)

        self.history.append(("", opening_msg))
        self.llm_history.append({"role": "assistant", "content": opening_msg})
        self.page_just_changed = False
        return None  # LLM呼び出しなし

    # 2. ページデータ取得
    page_data = self.scenario_manager.get_current_page_data()

    # 3. TextHandler でLLM処理
    text_response, mood_name, transition, assistant_message = \
        self.text_handler.process_message(user_message, self.llm_history, page_data)

    # 4. 両方の履歴に追加
    self.history.append((user_message, text_response))
    self.llm_history.append({"role": "user", "content": user_message})
    self.llm_history.append({"role": "assistant", "content": assistant_message})

    # 5. ページ遷移処理
    self.handle_page_transition(transition, page_data)

    # 6. ムード検証
    validated_mood = self.renderer.validate_mood(mood_name, ...)

    return text_response, validated_mood, transition
```

**処理フローのポイント**:
1. **遷移直後の最適化**: `page_just_changed`フラグでLLM呼び出しをスキップ
2. **デュアル履歴更新**: `history`にはテキスト、`llm_history`にはJSON全体
3. **遷移処理**: 条件に応じてページ/シーンを切り替え
4. **ムード検証**: レンダラーで許可されたムードのみ使用

#### 音声メッセージ処理

```python
# Line 163-234: 音声メッセージ処理
def process_voice_audio(self, audio: tuple):
    # 1. 現在のページプロンプトを取得
    page_data = self.scenario_manager.get_current_page_data()
    system_instructions = self._build_voice_system_instructions(page_data)

    # 2. VoiceHandler で音声処理（ストリーミング）
    transcripts = None
    for audio_chunk in self.voice_handler.process_audio(audio, system_instructions):
        # Realtime APIから音声チャンクをyield
        if isinstance(audio_chunk, tuple):
            yield audio_chunk
        else:
            transcripts = audio_chunk

    # 3. トランスクリプトを取得
    user_transcript, assistant_transcript = transcripts

    # 4. トランスクリプト分析（ムード/遷移抽出）
    from .transcript_analyzer import analyze_transcript
    mood_name, transition = analyze_transcript(
        self.client,
        user_transcript,
        assistant_transcript,
        page_data
    )

    # 5. 両方の履歴に追加
    self.history.append((user_transcript, assistant_transcript))
    self.llm_history.append({"role": "user", "content": user_transcript})
    self.llm_history.append({"role": "assistant", "content": assistant_transcript})

    # 6. ページ遷移とムード検証
    self.handle_page_transition(transition, page_data)
    validated_mood = self.renderer.validate_mood(mood_name, ...)
```

**音声モード特有の処理**:
1. **ストリーミング**: Realtime APIから音声チャンクを順次yield（低遅延）
2. **トランスクリプトキャプチャ**: Whisperによる自動文字起こし
3. **事後分析**: トランスクリプトをgpt-4o-miniで分析してムード/遷移を抽出
4. **デュアルAPI呼び出し**: Realtime API（音声）+ gpt-4o-mini（分析）

#### ページ遷移処理

```python
# Line 66-93: ページ遷移処理
def handle_page_transition(self, transition: Optional[str], page_data: dict):
    if not transition:
        return False, page_data

    try:
        # シーン間遷移: "scene_id:page_id"
        # 同一シーン内遷移: "page_id"
        self.scenario_manager._transition_to(transition)

        # 遷移フラグON
        self.page_just_changed = True

        # 新しいページデータ取得
        new_page_data = self.scenario_manager.get_current_page_data()

        logger.info(
            "Page transition: %s:%s → %s:%s",
            page_data['scene'], page_data['page'],
            new_page_data['scene'], new_page_data['page']
        )

        return True, new_page_data

    except Exception as e:
        logger.error("Transition failed: %s", e)
        return False, page_data
```

**遷移の仕組み**:
- `transition`: `"scene_id:page_id"`または`"page_id"`
- `_transition_to()`でシナリオマネージャーの状態更新
- `page_just_changed`フラグで次回の`opening_message`表示を指示

---

### 2.2. TextChatHandler

**ファイル**: `core/text_handler.py`

#### 概要

テキストモードのLLM通信とJSON応答パースを担当。システムプロンプトの動的構築、遷移条件のフォーマット、応答の解析を行います。

#### システムプロンプト構築

```python
# Line 55-106: システムプロンプト構築
def build_system_prompt(self, page_data: dict) -> str:
    # 1. ムード制約の取得
    allowed_moods = page_data.get('allowed_moods') or page_data.get('allowed_images')
    if allowed_moods:
        mood_constraint = f"このページでは以下のムードのみ使用可能: {', '.join(allowed_moods)}"
    else:
        mood_constraint = "すべてのムードを使用可能"

    # 2. 遷移条件のフォーマット
    transitions_text = self.format_transitions(page_data.get('transitions', []))

    # 3. プロンプトの取得
    scene_prompt = page_data.get('scene_prompt', '')
    page_prompt = page_data.get('page_prompt', page_data.get('additional_prompt', ''))
    current_mood = page_data.get('mood', page_data.get('image', '基本スタイル'))
    background = page_data.get('background_image', 'なし')

    # 4. 統合プロンプトの生成
    combined_prompt = f"""{self.base_system_prompt}

---
## 現在のシーン/ページ情報
シーン: {page_data['scene']}
ページ: {page_data['page']}
現在のムード: {current_mood}
背景: {background}

## シーンプロンプト
{scene_prompt}

## ページプロンプト
{page_prompt}

## ムード使用制約
{mood_constraint}

## 利用可能な遷移
{transitions_text}

注意: 上記の追加指示は基本ルールに追加されるものです。基本的な応答形式（JSON形式、ムードの使い分けなど）は引き続き守ってください。
"""
    return combined_prompt
```

**プロンプト階層**:
1. **基本プロンプト** (`system_prompt.txt` + YAML `base_prompt`)
2. **シーンプロンプト** (シーンレベルの指示)
3. **ページプロンプト** (ページ固有の指示)
4. **ムード制約** (使用可能なムードリスト)
5. **遷移条件** (自然言語での遷移条件)

#### 遷移条件のフォーマット

```python
# Line 30-53: 遷移条件のフォーマット
def format_transitions(self, transitions: list) -> str:
    if not transitions:
        return "遷移なし（このページに留まります）"

    lines = ["以下の条件に該当する場合、対応する遷移先IDを\"transition\"フィールドに指定してください:\n"]
    for i, trans in enumerate(transitions, 1):
        target_id = trans.get('id', trans.get('transition_id', 'unknown'))
        condition = trans.get('description', trans.get('condition', ''))

        lines.append(f"{i}. \"{target_id}\"")
        if condition:
            lines.append(f"   {condition}\n")

    lines.append("上記に該当しない場合は \"transition\": null を使用してください。")
    return "\n".join(lines)
```

**出力例**:
```
以下の条件に該当する場合、対応する遷移先IDを"transition"フィールドに指定してください:

1. "cafe"
   休憩を希望したとき

2. "shopping"
   買い物を希望したとき

上記に該当しない場合は "transition": null を使用してください。
```

**重要ポイント**:
- 自然言語で遷移条件を記述
- LLMが会話内容から適切な遷移を判断
- 該当しない場合は`null`で現在ページに留まる

#### LLM応答のパース

```python
# Line 108-124: LLM応答のパース
def parse_llm_response(self, response_text: str) -> tuple:
    """
    LLMのJSON応答を解析

    期待形式:
    {
      "text": "ユーザーへの応答",
      "mood": "ムード名",
      "transition": "scene:page" or null
    }
    """
    try:
        data = json.loads(response_text)
        return (
            data.get("text", response_text),
            data.get("mood", data.get("image", "基本スタイル")),  # 後方互換性
            data.get("transition", None)
        )
    except json.JSONDecodeError:
        # JSON形式でない場合はプレーンテキストとして扱う
        return response_text, "基本スタイル", None
```

**エラーハンドリング**:
- JSON解析失敗時はテキスト全体を応答として扱う
- デフォルトムード: "基本スタイル"
- 後方互換性: `"image"`フィールドもサポート

#### LLM API呼び出し

```python
# Line 126-176: メッセージ処理
def process_message(self, message: str, conversation_history: list, page_data: dict):
    # 1. システムプロンプト構築
    system_prompt = self.build_system_prompt(page_data)

    # 2. OpenAI API 呼び出し
    try:
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt}
            ] + conversation_history + [
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=500
        )

        assistant_message = response.choices[0].message.content

        # 3. JSON解析
        text_response, mood_name, transition = self.parse_llm_response(assistant_message)

        logger.debug(
            "RESPONSE: mood=%s, transition=%s: %s",
            mood_name, transition, text_response[:50]
        )

        return text_response, mood_name, transition, assistant_message

    except Exception as e:
        error_message = f"エラーが発生しました: {str(e)}"
        logger.error("LLM API error: %s", e)
        return error_message, "困る", None, error_message
```

**パラメータ**:
- **model**: `gpt-4o-mini`（コスト効率重視）
- **temperature**: 0.7（やや創造的な応答）
- **max_tokens**: 500（応答長の上限）

---

### 2.3. VoiceChatHandler

**ファイル**: `core/voice_handler.py`

#### 概要

OpenAI Realtime APIを使用した音声入出力処理。音声データの前処理、ストリーミング、トランスクリプト取得を担当します。

#### 音声フォーマット定数

```python
# Line 19-20: 音声フォーマット定数
SAMPLE_RATE = 24000  # Realtime API要件: 24kHz
CHUNK_SIZE = 480     # 20ms @ 24000Hz (480 samples)
```

**重要ポイント**:
- Realtime APIは24kHzのPCM16フォーマットを要求
- 20msチャンク = 低遅延ストリーミング

#### 音声前処理

```python
# Line 45-87: 音声前処理
def _preprocess_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    音声データをRealtime API用に前処理:
    1. 2D配列を1Dにflatten
    2. float32をint16に変換
    3. サンプルレートを24kHzにリサンプル
    """
    logger.debug(
        "Audio preprocessing: dtype=%s, shape=%s, rate=%dHz",
        audio_data.dtype, audio_data.shape, sample_rate
    )

    # 1. 2D → 1D変換
    if len(audio_data.shape) == 2:
        logger.debug("Flattening 2D array: %s", audio_data.shape)
        audio_data = audio_data.flatten()

    # 2. float32 → int16変換
    if audio_data.dtype != np.int16:
        audio_data = (audio_data * 32767).astype(np.int16)
        logger.debug("Converted to int16")

    # 3. リサンプリング（必要な場合）
    if sample_rate != self.SAMPLE_RATE:
        target_length = int(len(audio_data) * self.SAMPLE_RATE / sample_rate)
        audio_data = signal.resample(audio_data, target_length).astype(np.int16)
        logger.debug("Resampled %dHz → %dHz", sample_rate, self.SAMPLE_RATE)

    return audio_data
```

**前処理の理由**:
- **2D→1D**: Gradio Streamは2Dステレオを返す場合がある
- **float32→int16**: Gradioはfloat32 [-1.0, 1.0]、Realtime APIはint16 [-32768, 32767]
- **リサンプリング**: Gradioは48kHzを返す場合があるが、Realtime APIは24kHzを要求

#### Realtime APIストリーミング

```python
# Line 89-231: 音声処理メイン関数
def process_audio(self, audio: tuple, system_instructions: str):
    """
    Realtime APIで音声処理（ストリーミング）

    Yields:
        (sample_rate, audio_array): 音声出力チャンク

    Returns:
        (user_transcript, assistant_transcript): トランスクリプト
    """
    sample_rate, audio_data = audio

    # 1. 音声検証
    if len(audio_data) < 100:
        logger.warning("Audio too short: %d samples", len(audio_data))
        yield self._generate_silence(100)
        return "", ""

    # 2. 音声前処理
    audio_24k = self._preprocess_audio(audio_data, sample_rate)

    # 3. トランスクリプト初期化
    user_transcript = ""
    assistant_transcript = ""
    response_count = 0

    # 4. Realtime API接続
    try:
        with self.client.beta.realtime.connect(model="gpt-4o-realtime-preview") as conn:
            # セッション設定
            conn.session.update(session={
                "instructions": system_instructions,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad",  # Server-side Voice Activity Detection
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "input_audio_transcription": {
                    "model": "whisper-1"  # 自動文字起こし
                }
            })

            # 音声データ送信（チャンク単位）
            for i in range(0, len(audio_24k), self.CHUNK_SIZE):
                chunk = audio_24k[i:i+self.CHUNK_SIZE]
                chunk_b64 = base64.b64encode(chunk.tobytes()).decode()
                conn.input_audio_buffer.append(audio=chunk_b64)

            # バッファ確定と応答リクエスト
            conn.input_audio_buffer.commit()
            conn.response.create()

            # イベントストリーム処理
            for event in conn:
                # トランスクリプト取得
                if event.type == "conversation.item.input_audio_transcription.completed":
                    user_transcript = event.transcript
                    logger.info("[USER] %s", user_transcript)

                # 音声応答（ストリーミング）
                elif event.type == "response.audio.delta":
                    audio_chunk = base64.b64decode(event.delta)
                    audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
                    response_count += len(audio_array)
                    yield (self.SAMPLE_RATE, audio_array)  # リアルタイム出力

                # アシスタント トランスクリプト
                elif event.type == "response.audio_transcript.delta":
                    assistant_transcript += event.delta

                elif event.type == "response.audio_transcript.done":
                    logger.info("[ASSISTANT] %s", assistant_transcript)

                # 応答完了
                elif event.type == "response.done":
                    logger.debug("Response complete")
                    if response_count == 0:
                        yield self._generate_silence(100)
                    break

    except Exception as e:
        logger.error("Realtime API error: %s", e)
        yield self._generate_silence(100)
        return "", ""

    return user_transcript, assistant_transcript
```

**処理フロー**:
1. **音声検証**: 短すぎる音声を拒否
2. **前処理**: 24kHz int16に変換
3. **Realtime API接続**: コンテキストマネージャーで自動クリーンアップ
4. **セッション設定**: VAD、Whisper文字起こし有効化
5. **音声送信**: 480サンプル（20ms）チャンク単位
6. **イベント処理**: トランスクリプトと音声を並行取得
7. **ストリーミング**: 音声チャンクを即座にyield（低遅延）

**Server-side VAD (Voice Activity Detection)**:
- **threshold**: 0.5（発話検出の感度）
- **prefix_padding_ms**: 300（発話開始前に含める音声）
- **silence_duration_ms**: 500（この長さの無音で発話終了と判断）

---

### 2.4. TranscriptAnalyzer

**ファイル**: `core/transcript_analyzer.py`

#### 概要

音声トランスクリプトからムードと遷移を抽出する事後分析モジュール。Realtime APIはトランスクリプトのみを返すため、gpt-4o-miniで会話内容を分析してムード/遷移を決定します。

#### 分析プロンプト構築

```python
# Line 11-57: トランスクリプト分析
def analyze_transcript(
    client: OpenAI,
    user_transcript: str,
    assistant_transcript: str,
    page_data: dict
) -> tuple:
    """
    音声トランスクリプトからムードと遷移を抽出

    Returns:
        (mood_name, transition)
    """
    # 1. 許可されたムードリストの取得
    allowed_moods = page_data.get('allowed_moods') or page_data.get('allowed_images')
    if allowed_moods:
        mood_list = ", ".join(allowed_moods)
    else:
        mood_list = "基本スタイル, 話す, 笑う, 驚く, 困る, 泣く, 走る, 寝る, 考える, 指差し, 喜ぶ, 運転, 給油, カフェ, 買い物, 景色, 充電, 地図, 到着, 出発"

    # 2. 利用可能な遷移リストの取得
    transitions = page_data.get('transitions', [])
    if transitions:
        transition_list = "\n".join([
            f"- \"{t.get('id')}\": {t.get('description')}"
            for t in transitions
        ])
    else:
        transition_list = "なし（ページ遷移なし）"

    # 3. 分析プロンプト構築
    analysis_prompt = f"""以下の音声会話トランスクリプトを分析してください。

ユーザー: {user_transcript}
アシスタント: {assistant_transcript}

## タスク
1. アシスタントの応答内容に最も適切なムードを選択
2. 会話の流れから、ページ遷移が必要か判断

## 使用可能なムード
{mood_list}

## 利用可能な遷移
{transition_list}

## 応答形式（JSON）
{{
  "mood": "選択したムード名",
  "transition": "遷移先ID（または null）"
}}
"""
```

**分析の観点**:
- **ムード**: アシスタントの応答内容と感情
- **遷移**: 会話の流れから次のページへの移動が必要か

#### LLM分析実行

```python
    # 4. GPT-4o-mini で分析
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは会話分析の専門家です。JSON形式で応答してください。"},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.3,  # 低めに設定（一貫性重視）
            max_tokens=100
        )

        # 5. JSON解析
        result = json.loads(response.choices[0].message.content)
        mood_name = result.get("mood", "基本スタイル")
        transition = result.get("transition", None)

        logger.info(
            "Transcript analysis: mood=%s, transition=%s",
            mood_name, transition
        )

        return mood_name, transition

    except Exception as e:
        logger.error("Transcript analysis error: %s", e)
        return "基本スタイル", None
```

**パラメータ**:
- **temperature**: 0.3（テキストモードより低く設定し、一貫性重視）
- **max_tokens**: 100（JSON応答は短いため）

**音声モードの2段階API呼び出し**:
1. **Realtime API**: 音声入出力 + トランスクリプト生成（リアルタイム）
2. **gpt-4o-mini**: トランスクリプト分析（事後処理）

この設計により、音声応答の低遅延と正確なムード/遷移判定を両立しています。

---

## 3. シナリオ管理 (scenario_manager.py)

### 概要

シーン/ページの階層的管理、YAML設定の読み込み、ページ遷移制御を担当します。

### 初期化とYAML読み込み

```python
# Line 12-33: 初期化
class ScenarioManager:
    def __init__(self, scenario_file: str):
        """
        シナリオマネージャー初期化

        Args:
            scenario_file: YAMLシナリオファイルのパス
        """
        self.scenario_file = scenario_file
        self.loader = None
        self.start_scene = None
        self.base_prompt = ""
        self.mood_config = {}
        self.background_config = {}

        # YAML形式のみサポート
        if not scenario_file.endswith(('.yaml', '.yml')):
            raise ValueError(f"Only YAML format is supported. Got: {scenario_file}")

        self.scenarios = self._load_yaml_scenarios()
        self.format = 'yaml'

        self.current_scene = None
        self.current_page = None
```

**重要ポイント**:
- YAML形式のみサポート（テキスト形式は非推奨）
- `YAMLScenarioLoader`で解析し、内部形式に変換

### YAML読み込み

```python
# Line 34-44: YAML読み込み
def _load_yaml_scenarios(self) -> Dict[str, Any]:
    """YAML読み込みと設定抽出"""
    from yaml_scenario_loader import YAMLScenarioLoader

    self.loader = YAMLScenarioLoader(self.scenario_file)
    scenarios = self.loader.load()

    # YAML の base/configuration セクションを抽出
    self.base_prompt = self.loader.get_base_prompt()
    self.start_scene = self.loader.get_start_scene()
    self.mood_config = self.loader.get_mood_config()
    self.background_config = self.loader.get_background_config()

    return scenarios
```

**抽出される設定**:
- **base_prompt**: システムプロンプトに追加するベースプロンプト
- **start_scene**: 開始シーンID
- **mood_config**: ムード名→画像パスのマッピング
- **background_config**: 背景名→画像パスのマッピング

### シナリオ開始

```python
# Line 46-68: シナリオ開始
def start_scenario(self, scene_id: Optional[str] = None) -> Dict[str, Any]:
    """
    シナリオ開始

    Args:
        scene_id: 開始シーンID（省略時は base.start_scene を使用）

    Returns:
        現在ページデータ
    """
    target_scene = scene_id or self.start_scene

    if not target_scene:
        raise ValueError("No start scene configured.")

    if target_scene not in self.scenarios:
        raise ValueError(f"Scene not found: {target_scene}")

    scene = self.scenarios[target_scene]
    self.current_scene = target_scene
    self.current_page = scene['start_page']

    return self.get_current_page_data()
```

**開始フロー**:
1. 開始シーンIDを決定（引数 or YAML設定）
2. シーンの存在確認
3. `current_scene`と`current_page`を設定
4. 現在ページデータを返す

### 現在ページデータ取得

```python
# Line 70-106: 現在ページデータ取得
def get_current_page_data(self) -> Dict[str, Any]:
    """
    現在ページの全情報を取得

    Returns:
        ページデータ（新旧フィールド両方を含む）
    """
    if not self.current_scene or not self.current_page:
        raise RuntimeError("Scenario not started. Call start_scenario() first.")

    scene = self.scenarios[self.current_scene]
    page = scene['pages'][self.current_page]

    # シーン/ページ情報を追加
    page_data = page.copy()
    page_data['scene'] = self.current_scene
    page_data['page'] = self.current_page
    page_data['scene_prompt'] = scene.get('scene_prompt', '')

    # ムード制約の継承（ページ → シーン）
    if not page_data.get('allowed_moods') and not page_data.get('allowed_images'):
        page_data['allowed_moods'] = scene.get('allowed_moods')
        page_data['allowed_images'] = scene.get('allowed_moods')

    # 背景画像の継承（ページ → シーン）
    if not page_data.get('background_image'):
        page_data['background_image'] = scene.get('background_image')

    return page_data
```

**データ構造**:
```python
{
    'scene': 'town_start',
    'page': 'departure',
    'mood': '出発',
    'opening_message': '今日はどちらまで？',
    'page_prompt': 'ページ固有の指示',
    'scene_prompt': 'シーン全体の指示',
    'background_image': 'prompts/data/bg_town.jpg',
    'allowed_moods': ['出発', '話す', '指差し'],
    'transitions': [
        {'id': 'cafe', 'description': '休憩を希望したとき'},
        {'id': 'sea_driving', 'description': '海辺に向かうとき'}
    ],
    # 後方互換性フィールド
    'image': '出発',
    'opening_speech': '今日はどちらまで？',
    ...
}
```

### ページ遷移

```python
# Line 108-160: ページ遷移処理
def _transition_to(self, target: str):
    """
    ページ遷移を実行

    Args:
        target: 遷移先（"scene_id:page_id" または "page_id"）

    Raises:
        ValueError: 遷移先が見つからない場合
    """
    # 1. シーン間遷移 vs 同一シーン内遷移を判定
    if ':' in target:
        # シーン間遷移: "scene_id:page_id"
        target_scene, target_page = target.split(':', 1)
    else:
        # 同一シーン内遷移: "page_id"
        target_scene = self.current_scene
        target_page = target

    # 2. 遷移先の検証
    if target_scene not in self.scenarios:
        raise ValueError(f"Scene not found: {target_scene}")

    scene = self.scenarios[target_scene]

    if target_page not in scene['pages']:
        raise ValueError(
            f"Page not found: {target_page} in scene {target_scene}"
        )

    # 3. 状態更新
    self.current_scene = target_scene
    self.current_page = target_page

    logger.info("Transitioned to: %s:%s", target_scene, target_page)
```

**遷移の種類**:
- **シーン間遷移**: `"sea_driving:arrival"` → 別シーンの特定ページへ
- **同一シーン内遷移**: `"cafe"` → 同じシーン内の別ページへ

### 設定取得メソッド

```python
# Line 162-186: 設定取得
def get_mood_config(self) -> Dict[str, str]:
    """ムード設定を取得"""
    return self.mood_config

def get_background_config(self) -> Dict[str, str]:
    """背景設定を取得"""
    return self.background_config

def get_base_prompt(self) -> str:
    """ベースプロンプトを取得"""
    return self.base_prompt

def get_start_scene(self) -> str:
    """開始シーンIDを取得"""
    return self.start_scene
```

---

## 4. YAMLローダー (yaml_scenario_loader.py)

### 概要

YAMLシナリオファイルのパース、スキーマ検証、内部形式への変換を担当します。

### YAML読み込みと検証

```python
# Line 23-48: YAML読み込み
def load(self) -> Dict[str, Any]:
    """
    YAMLファイルを読み込み、検証し、内部形式に変換

    Returns:
        ScenarioManager互換の内部形式

    Raises:
        FileNotFoundError: ファイルが存在しない
        yaml.YAMLError: YAML形式エラー
        ValueError: スキーマ検証エラー
    """
    # 1. ファイル存在確認
    if not os.path.exists(self.yaml_file):
        raise FileNotFoundError(f"YAML scenario file not found: {self.yaml_file}")

    # 2. YAML読み込み
    with open(self.yaml_file, 'r', encoding='utf-8') as f:
        self.raw_data = yaml.safe_load(f)

    # 3. スキーマ検証
    self._validate_schema()

    # 4. 内部形式に変換
    self.scenarios = self._convert_to_internal_format()

    return self.scenarios
```

### スキーマ検証

```python
# Line 50-82: スキーマ検証
def _validate_schema(self):
    """YAMLスキーマの検証"""
    if not isinstance(self.raw_data, dict):
        raise ValueError("YAML root must be a dictionary")

    # 1. base セクション検証
    if 'base' not in self.raw_data:
        raise ValueError("Missing required 'base' section")

    base = self.raw_data['base']
    if 'start_scene' not in base:
        raise ValueError("Missing required 'base.start_scene' field")

    # 2. scenes セクション検証
    if 'scenes' not in self.raw_data:
        raise ValueError("Missing required 'scenes' section")

    scenes = self.raw_data['scenes']
    if not isinstance(scenes, list) or len(scenes) == 0:
        raise ValueError("'scenes' must be a non-empty list")

    # 3. 各シーンの検証
    for i, scene in enumerate(scenes):
        self._validate_scene(scene, i)

    # 4. configuration セクション検証
    if 'configuration' not in self.raw_data:
        raise ValueError("Missing required 'configuration' section")

    config = self.raw_data['configuration']
    if 'mood_images' not in config:
        raise ValueError("Missing required 'configuration.mood_images' field")
```

### シーン検証

```python
# Line 83-98: シーン検証
def _validate_scene(self, scene: Dict, index: int):
    """個別シーンの検証"""
    required_fields = ['scene_id', 'start_page', 'pages']

    # 1. 必須フィールド確認
    for field in required_fields:
        if field not in scene:
            raise ValueError(f"Scene {index}: Missing required field '{field}'")

    # 2. pages リスト検証
    pages = scene['pages']
    if not isinstance(pages, list) or len(pages) == 0:
        raise ValueError(
            f"Scene {index} ('{scene['scene_id']}'): 'pages' must be a non-empty list"
        )

    # 3. 各ページの検証
    for j, page in enumerate(pages):
        self._validate_page(page, scene['scene_id'], j)
```

### ページ検証

```python
# Line 99-108: ページ検証
def _validate_page(self, page: Dict, scene_id: str, index: int):
    """個別ページの検証"""
    required_fields = ['page_id', 'default_mood']

    for field in required_fields:
        if field not in page:
            raise ValueError(
                f"Scene '{scene_id}', Page {index}: Missing required field '{field}'"
            )
```

### 内部形式への変換

```python
# Line 109-175: 内部形式変換
def _convert_to_internal_format(self) -> Dict[str, Any]:
    """YAML形式を内部形式に変換"""
    scenarios = {}

    for scene in self.raw_data['scenes']:
        scene_id = scene['scene_id']

        # 1. ページをdict形式に変換
        pages_dict = {}
        for page in scene['pages']:
            page_id = page['page_id']

            # 2. 遷移形式の変換
            transitions = []
            transitions_data = page.get('transitions', {})

            if isinstance(transitions_data, dict):
                # 新形式: {target: condition}
                for target, condition in transitions_data.items():
                    transitions.append({
                        'id': target,
                        'description': condition,
                        'transition_id': target.replace(':', '_')
                    })
            elif isinstance(transitions_data, list):
                # 旧形式: [{target: ..., condition: ...}]
                for trans in transitions_data:
                    transitions.append({
                        'id': trans.get('target'),
                        'description': trans.get('condition'),
                        'transition_id': trans.get('transition_id', ...)
                    })

            # 3. ページデータ構築
            pages_dict[page_id] = {
                # 新フィールド
                'mood': page['default_mood'],
                'opening_message': page.get('opening_message', ''),
                'page_prompt': page.get('page_prompt', ''),
                'background_image': page.get('background_image'),
                'allowed_moods': page.get('allowed_moods'),
                'transitions': transitions,

                # 後方互換性フィールド
                'image': page['default_mood'],
                'opening_speech': page.get('opening_message', ''),
                'additional_prompt': page.get('page_prompt', ''),
                'allowed_images': page.get('allowed_moods'),
                'available_transitions': transitions
            }

        # 4. シーンデータ構築
        scenarios[scene_id] = {
            'name': scene.get('description', scene_id),
            'description': scene.get('description', ''),
            'start_page': scene['start_page'],
            'scene_prompt': scene.get('scene_prompt', ''),
            'opening_message': scene.get('opening_message', ''),
            'background_image': scene.get('background_image'),
            'allowed_moods': scene.get('allowed_moods'),
            'pages': pages_dict
        }

    return scenarios
```

**遷移形式の変換**:

YAMLの簡潔な形式:
```yaml
transitions:
  cafe: 休憩を希望したとき
  shopping: 買い物を希望したとき
```

内部形式:
```python
[
    {'id': 'cafe', 'description': '休憩を希望したとき', 'transition_id': 'cafe'},
    {'id': 'shopping', 'description': '買い物を希望したとき', 'transition_id': 'shopping'}
]
```

### 設定抽出メソッド

```python
# Line 177-224: 設定抽出
def get_mood_config(self) -> Dict[str, str]:
    """ムード画像設定を抽出"""
    if not self.raw_data:
        raise ValueError("YAML not loaded yet. Call load() first.")

    return self.raw_data['configuration'].get('mood_images', {})

def get_background_config(self) -> Dict[str, str]:
    """背景画像設定を抽出"""
    if not self.raw_data:
        raise ValueError("YAML not loaded yet. Call load() first.")

    return self.raw_data['configuration'].get('background_images', {})

def get_base_prompt(self) -> str:
    """ベースプロンプトを抽出"""
    if not self.raw_data:
        raise ValueError("YAML not loaded yet. Call load() first.")

    return self.raw_data['base'].get('base_prompt', '')

def get_start_scene(self) -> str:
    """開始シーンIDを抽出"""
    if not self.raw_data:
        raise ValueError("YAML not loaded yet. Call load() first.")

    return self.raw_data['base']['start_scene']
```

---

## 5. レンダラー (renderers/)

### 5.1. BaseRenderer

**ファイル**: `renderers/base_renderer.py`

#### 概要

すべてのレンダラーが実装すべき抽象基底クラス。レンダラーパターンのインターフェースを定義します。

#### 抽象メソッド

```python
from abc import ABC, abstractmethod

class BaseRenderer(ABC):
    """レンダラーの抽象基底クラス"""

    @abstractmethod
    def render(self, mood_name: str, background_path: Optional[str] = None) -> Any:
        """
        ムード名と背景パスから表示リソースを生成

        Args:
            mood_name: ムード名（例: "笑う", "困る"）
            background_path: 背景画像パス（オプション）

        Returns:
            表示リソース（HTML文字列、画像パス、3Dモデルパスなど）
        """
        pass

    @abstractmethod
    def validate_mood(self, mood_name: str, allowed_moods: Optional[List[str]]) -> str:
        """
        ムード名を検証し、有効なムード名を返す

        Args:
            mood_name: 検証するムード名
            allowed_moods: 許可されたムードリスト（None = 全て許可）

        Returns:
            有効なムード名（無効な場合はデフォルトムード）
        """
        pass

    @abstractmethod
    def get_default_display() -> Any:
        """
        デフォルト表示リソースを返す

        Returns:
            デフォルト表示リソース
        """
        pass

    @abstractmethod
    def get_mood_description_prompt() -> str:
        """
        LLM用のムード説明プロンプトを返す

        Returns:
            ムードの使い分けを説明するテキスト
        """
        pass
```

#### 後方互換性メソッド

```python
    # 後方互換性のためのエイリアス
    def validate_state(self, state_name: str, allowed_states: Optional[List[str]]) -> str:
        """旧メソッド名 → validate_mood() のエイリアス"""
        return self.validate_mood(state_name, allowed_states)

    def get_state_description_prompt(self) -> str:
        """旧メソッド名 → get_mood_description_prompt() のエイリアス"""
        return self.get_mood_description_prompt()
```

---

### 5.2. PaperTheaterRenderer

**ファイル**: `renderers/paper_theater_renderer.py`

#### 概要

HTML/CSSによる画像合成レンダラー。背景画像とムード画像を2層構造で表示します。

#### ムード説明プロンプト

```python
# Line 17-43: ムード説明
def get_mood_description_prompt(self) -> str:
    """LLM用のムード使い分けガイド"""
    return """## ムードの使い分け
- 基本スタイル: 通常の会話、待機中
- 話す: 説明やアドバイスをするとき
- 笑う: 楽しい提案、ポジティブな反応
- 驚く: 予想外の質問や発見
- 困る: 難しい質問、判断に迷うとき
- 泣く: 残念なニュース（渋滞など）
- 走る: 急いでいるとき、スピード感のある話題
- 寝る: 休憩を提案するとき
- 考える: ルートを検討中
- 指差し: 方向を示すとき、案内
- 喜ぶ: 目的地到着、良いニュース
- 運転: 運転に関するアドバイス
- 給油: ガソリンスタンドの案内
- カフェ: カフェ・休憩の提案
- 買い物: お土産屋さんの案内
- 景色: 景色の良い場所の紹介
- 充電: 充電スポットの案内
- 地図: ルート全体の説明
- 到着: 目的地到着時
- 出発: 出発時、ルート開始時

会話の文脈に合わせて最も適切なムードを選択してください。"""
```

**重要ポイント**:
- このテキストが`system_prompt.txt`の`{RENDERER_MOOD_DESCRIPTION}`に挿入される
- LLMはこの説明を見て適切なムードを選択

#### HTML/CSS画像合成

```python
# Line 45-82: レンダリング
def render(self, mood_name: str, background_path: Optional[str] = None) -> str:
    """
    HTML/CSSで背景+ムード画像を合成

    Args:
        mood_name: 日本語ムード名
        background_path: 背景画像パス

    Returns:
        HTML文字列（gr.HTML用）
    """
    # 1. ムード画像パス取得
    mood_image_path = self.mood_config.get(
        mood_name,
        self.mood_config[self.default_mood]
    )

    # 2. パス解決（images/ → prompts/images/）
    if mood_image_path.startswith("images/"):
        mood_image_path = f"prompts/{mood_image_path}"

    # 3. 背景なしの場合
    if not background_path:
        return f'''
<div style="position: relative; width: 800px; height: 600px; margin: 0 auto; display: flex; justify-content: center; align-items: center; background-color: #f0f0f0;">
    <img src="/gradio_api/file={mood_image_path}" style="max-width: 100%; max-height: 100%; object-fit: contain;">
</div>
'''

    # 4. 背景+ムード画像の2層合成
    return f'''
<div style="position: relative; width: 800px; height: 600px; margin: 0 auto; overflow: hidden;">
    <!-- 背景画像（下層・全体を覆う） -->
    <img src="/gradio_api/file={background_path}"
         style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover;">

    <!-- ムード画像（上層・右下配置） -->
    <img src="/gradio_api/file={mood_image_path}"
         style="position: absolute; right: 20px; bottom: 20px; max-width: 40%; max-height: 40%; object-fit: contain;">
</div>
'''
```

**CSS合成の利点**:
- **PIL不要**: 依存関係削減
- **チラつき防止**: Gradio gr.HTMLで直接更新
- **レスポンシブ**: ブラウザが自動調整
- **パフォーマンス**: サーバー側の画像処理不要

**レイアウト**:
```
┌────────────────────────────────┐
│                                │
│    背景画像（全体）            │
│                                │
│                                │
│                    ┌──────┐    │
│                    │ムード│    │
│                    │画像  │    │
│                    └──────┘    │
└────────────────────────────────┘
```

#### デフォルトムード設定

```python
# Line 85-108: デフォルトムード設定
DEFAULT_PAPER_THEATER_MOODS = {
    "基本スタイル": "images/basic.png",
    "話す": "images/talking.png",
    "笑う": "images/laughing.png",
    "驚く": "images/surprised.png",
    "困る": "images/troubled.png",
    "泣く": "images/crying.png",
    "走る": "images/running.png",
    "寝る": "images/sleeping.png",
    "考える": "images/thinking.png",
    "指差し": "images/pointing.png",
    "喜ぶ": "images/happy.png",
    "運転": "images/driving.png",
    "給油": "images/refueling.png",
    "カフェ": "images/cafe.png",
    "買い物": "images/shopping.png",
    "景色": "images/scenery.png",
    "充電": "images/charging.png",
    "地図": "images/map.png",
    "到着": "images/arrival.png",
    "出発": "images/departure.png"
}
```

**ファイル配置**:
- YAMLでは`images/basic.png`と記述
- 実際のファイルは`prompts/images/basic.png`に配置
- `render()`内で自動的にパス解決

---

## まとめ

### コードの全体的な特徴

1. **モジュール分離**: 各モジュールが単一責任を持つ（SRP）
2. **後方互換性**: 旧フィールド名/メソッド名をエイリアスでサポート
3. **エラーハンドリング**: 適切なログ出力と例外処理
4. **型ヒント**: 関数シグネチャに型情報を含む
5. **ドキュメント**: docstringによる詳細な説明

### 重要な設計パターン

1. **レンダラーパターン**: 表示方法の抽象化と交換可能性
2. **デュアル履歴パターン**: 表示用とLLMコンテキスト用の履歴分離
3. **プロンプト階層**: ベース → シーン → ページの3層構造
4. **YAML駆動設定**: コードを変更せずにシナリオを編集可能

### パフォーマンス最適化

1. **ページ遷移時のLLMスキップ**: `page_just_changed`フラグ
2. **HTML/CSS合成**: サーバー側の画像処理を回避
3. **音声ストリーミング**: チャンク単位のリアルタイム出力
4. **効率的なモデル選択**: gpt-4o-mini使用でコスト削減

### 拡張性

1. **新しいレンダラー追加**: `BaseRenderer`を継承して実装
2. **新しいシーン追加**: YAMLファイル編集のみ
3. **新しいムード追加**: YAML設定と画像ファイル追加のみ
4. **LLMモデル変更**: 1行の変更で切り替え可能

このコードベースは、拡張性と保守性を重視した設計になっており、将来的な機能追加や変更に柔軟に対応できます。
