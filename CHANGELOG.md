# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2025-12-30

### 🔄 Major Refactoring - Display Method Abstraction

This release introduces a major architectural refactoring to abstract display methods, enabling future extensions to 3D avatars, HTML content, and other visualization approaches.

### Added

- **Renderer Architecture**
  - `renderers/base_renderer.py`: Abstract base class for all display methods
  - `renderers/kamishibai_renderer.py`: Image-based renderer (current implementation)
  - `renderers/__init__.py`: Renderer package initialization
  - Pluggable renderer system - switch display methods by changing one line of code

- **Prompt Separation**
  - `prompts/system_prompt.txt`: Technical system prompt (developer-managed)
  - `prompts/user_scenario.txt`: User scenario definitions (user-editable)
  - Clear separation between technical instructions and content

### Changed

- **File Renaming**
  - `kamishibai_chat.py` → `conversation_app.py`: More generic name reflecting multi-renderer support
  - All source code variable names and comments changed from Japanese to English
  - Response state names remain in Japanese for user customization

- **Architecture Improvements**
  - Scenario manager now parses text files instead of YAML
  - System prompt dynamically injected with renderer-specific state descriptions
  - State validation delegated to renderer classes
  - Cleaner separation of concerns

- **Variable Naming**
  - `KAMISHIBAI_IMAGES` → Moved to `DEFAULT_KAMISHIBAI_STATES` in renderer
  - `current_scenario_started` → `scenario_started`
  - `kamishibai_image` → `display_component`
  - `parse_response()` → `parse_llm_response()`
  - `user_message()` → `process_user_message()`

### Removed

- `scenarios.yaml`: Content migrated to `prompts/user_scenario.txt`
- Direct image dictionary references in main application
- Hard-coded image usage rules from main code

### Migration Guide

**For Users:**
1. Scenarios are now defined in `prompts/user_scenario.txt` (text format)
2. Edit user scenarios directly in the text file - no YAML knowledge required
3. Response state names remain in Japanese and fully customizable

**For Developers:**
1. Import from new locations:
   ```python
   from renderers import KamishibaiRenderer, DEFAULT_KAMISHIBAI_STATES
   ```
2. Switch renderers programmatically:
   ```python
   # In conversation_app.py line ~23
   renderer = KamishibaiRenderer(DEFAULT_KAMISHIBAI_STATES)
   # Or in the future:
   # renderer = Avatar3DRenderer(config)
   ```
3. Update imports if using scenario_manager directly

### Technical Details

- Renderer pattern enables future 3D avatar, HTML, or other display methods
- Text-based scenario format more accessible to non-technical users
- System prompt and user content clearly separated
- State names (Japanese) independent of display implementation
- All existing images and scenarios preserved

### Breaking Changes

⚠️ **File Structure Changed**
- `kamishibai_chat.py` no longer exists - use `conversation_app.py`
- `scenarios.yaml` removed - migrate to `prompts/user_scenario.txt`

⚠️ **Import Changes**
- Renderer classes must be imported from `renderers` package
- ScenarioManager constructor now expects text file path

### Future Extensions

This refactoring enables:
- 3D avatar renderers with animation support
- HTML/CSS-based dynamic content rendering
- Multiple renderers per application
- Custom renderer implementations

---

## [1.0.0] - 2025-12-29

### シーン・ページベースのプロンプト構造の実装

**新機能:**
- シーン/ページベースの階層的なシナリオ管理システムを実装
- YAMLファイルでシナリオを定義できるようになりました

**実装内容:**

1. **ScenarioManager クラス** ([scenario_manager.py](scenario_manager.py))
   - YAMLファイルからシナリオを読み込み
   - シーン/ページの遷移を管理
   - 条件付き遷移をサポート

2. **シナリオ定義ファイル** ([scenarios.yaml](scenarios.yaml))
   - 3つのシーン: `town_start`（町中出発）, `gas_station`（給油）, `beach_arrival`（海辺到着）
   - 各シーンに複数のページ（挨拶、運転、カフェ、買い物、景色、充電、給油など）
   - ページごとに固有の画像、冒頭テキスト、追加プロンプトを定義

3. **プロンプト構造の改善**
   - **基本プロンプトは維持**: 既存の`SYSTEM_PROMPT`を常に使用
   - **追加プロンプト方式**: ページごとの`additional_prompt`を基本プロンプトに付与
   - **画像制約機能**: `allowed_images`でページごとに使用可能な画像を制限可能
   - **冒頭発話**: ページ遷移時はLLMが固定テキストで先に話す

4. **ページ遷移の仕組み**
   ```yaml
   transitions:
     - condition: "user_mentions:給油|ガソリン"
       next: "gas_station:refueling"  # シーン間遷移
     - condition: "user_mentions:カフェ|休憩"
       next: "cafe"  # 同一シーン内遷移
     - condition: "default"
       next: "driving"  # デフォルト遷移
   ```

5. **画像制約の例**
   ```yaml
   # すべての画像を使用可能
   allowed_images: null

   # 特定の画像のみ使用可能
   allowed_images: ["運転", "話す", "笑う", "指差し"]
   ```

**技術詳細:**

- **PyYAML**: シナリオ定義の読み込みに使用
- **動作フロー**:
  1. ユーザー入力を受け取る
  2. 遷移条件をチェック（キーワードマッチング）
  3. 遷移する場合: ページの`opening_speech`を表示（LLM呼び出しなし）
  4. 遷移しない場合: 通常通りLLMを呼び出し（基本プロンプト + 追加プロンプト）
  5. LLMの応答から画像を選択し、制約をチェック

**メリット:**

- ✅ **柔軟性**: YAMLで簡単にシナリオ編集
- ✅ **保守性**: プログラムとシナリオの分離
- ✅ **拡張性**: 新しいシーン/ページを簡単に追加
- ✅ **制御性**: 明確なページ遷移ルール、画像制約
- ✅ **基本動作の維持**: 既存の基本プロンプトを壊さない

**追加したファイル:**
- [scenario_manager.py](scenario_manager.py): シナリオ管理クラス
- [scenarios.yaml](scenarios.yaml): シナリオ定義ファイル
- [test_scenario.py](test_scenario.py): シナリオシステムのテストスクリプト

**修正したファイル:**
- [kamishibai_chat.py](kamishibai_chat.py): ScenarioManager統合
  - `build_system_prompt()`: 基本プロンプト + 追加プロンプトを組み合わせ
  - `get_opening_message()`: ページ遷移時の冒頭メッセージ生成
  - `chat()`: シナリオベースの会話処理
  - `reset_conversation()`: シナリオ状態もリセット
- [pyproject.toml](pyproject.toml): PyYAML依存関係を追加

---

## 2025-12-30 (Earlier)

### 画像が消える問題の修正

**問題:**
- ユーザーがメッセージを送信（Enterキー押下）後、LLMの応答が返るまでの間、画像が非表示になる

**原因:**
- Gradioのイベント処理中に、画像コンポーネントの値が一時的にクリアされる
- 単純に画像パスを返すだけでは、Gradioが値の更新を正しく処理しない

**解決策:**
`gr.update()`を使用して、明示的に画像の値を更新するようGradioに指示

**修正内容:**

```python
# 修正前
def user_message(user_msg, history, current_image):
    # ...
    return history, "", new_image

# 修正後
def user_message(user_msg, history, current_image):
    # ...
    return history, "", gr.update(value=new_image)
```

**効果:**
- ✅ Enter キー押下後も画像が表示され続ける
- ✅ LLM応答待ち中も現在の画像を保持
- ✅ 応答が返ってきたら新しい画像に切り替わる（または現在の画像を継続）

### 修正したファイル

- `kamishibai_chat.py`
  - `user_message()` 関数: `gr.update(value=new_image)` を使用
  - `reset_conversation()` 関数: `gr.update(value=KAMISHIBAI_IMAGES["基本スタイル"])` を使用

### 技術詳細

Gradio 6.0+ では、コンポーネントの値を更新する際に `gr.update()` を使用することで、UIの更新を明示的に制御できます。

```python
# 画像を更新する正しい方法
return gr.update(value=new_image_path)

# または、複数のプロパティを更新
return gr.update(value=new_image_path, visible=True)
```

これにより、Gradioは以下を保証します:
1. 現在の値を保持
2. 新しい値への明示的な更新
3. UIの再レンダリング時の一貫性

### プロジェクト整理

開発用ドキュメントを削除し、最終版をシンプルに:

**削除したファイル:**
- DEBUG_SETUP.md
- DEBUGGER_QUICKSTART.md
- FINAL_SUMMARY.md
- GRADIO6_MIGRATION.md
- IMAGE_SWITCHING.md
- VERIFICATION.md
- test_debug.py

**残したドキュメント:**
- README.md（メインドキュメント、簡略化）
- CLAUDE.md（プロジェクト概要）
- LLM_SCRIPT.md（LLMプロンプト詳細）
