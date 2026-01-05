"""
Conversational avatar application with pluggable display renderers.
Main application orchestrating LLM, scenario management, and UI.
"""

import gradio as gr
import json
import os
import logging
from pathlib import Path
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
from scenario_manager import ScenarioManager
from renderers import PaperTheaterRenderer, DEFAULT_PAPER_THEATER_MOODS

# Load environment variables
load_dotenv()

# Logging level can be controlled via environment variable LOG_LEVEL (e.g., INFO, DEBUG)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='[%(levelname)s] %(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)
# Ensure module logger follows configured level
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# Set static paths for Gradio to serve images
gr.set_static_paths(paths=[
    Path.cwd() / "images",
    Path.cwd() / "prompts" / "images",
    Path.cwd() / "prompts" / "data"
])

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === PROGRAMMATIC RENDERER SELECTION ===
# Developer chooses renderer implementation here
# To switch display methods, instantiate a different renderer class:
# - renderer = PaperTheaterRenderer(DEFAULT_PAPER_THEATER_MOODS)  # HTML/CSS-based with background support
# - renderer = Avatar3DRenderer(mood_config)                      # Future: 3D avatars
scenario_manager = ScenarioManager('prompts/scenario.yaml')
mood_config = scenario_manager.get_mood_config() or DEFAULT_PAPER_THEATER_MOODS
renderer = PaperTheaterRenderer(mood_config)

# Load prompts from files
def load_prompt_file(filepath: str) -> str:
    """Load prompt content from text file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

# Load and prepare system prompt
base_system_prompt = load_prompt_file('prompts/system_prompt.txt')
# Append base prompt from YAML if provided
if scenario_manager.base_prompt:
    base_system_prompt = f"{base_system_prompt}\n\n{scenario_manager.base_prompt}"

# Inject renderer mood descriptions
base_system_prompt = base_system_prompt.replace(
    '{RENDERER_MOOD_DESCRIPTION}',
    renderer.get_mood_description_prompt()
)

# Conversation state
conversation_history = []
scenario_started = False
page_just_changed = False
previous_page_location = None


def resolve_image_path(path: str) -> str:
    """
    Resolve image path from YAML format to actual file path.

    Args:
        path: Path from YAML (e.g., "images/page_driving.jpg")

    Returns:
        Resolved path (e.g., "prompts/images/page_driving.jpg")
    """
    if not path:
        return None

    # If path starts with "images/", prepend "prompts/"
    if path.startswith("images/"):
        return f"prompts/{path}"

    # Otherwise return as-is (already has full path like "prompts/images/...")
    return path


def resolve_move_target(target: str) -> Optional[str]:
    """
    Resolve /move target to a transition string usable by ScenarioManager.

    Args:
        target: Page ID or "scene_id:page_id"

    Returns:
        Transition string or None if not found/ambiguous
    """
    if not target:
        return None

    # Explicit scene/page provided
    if ":" in target:
        return target

    # Prefer current scene match
    if scenario_manager.current_scene in scenario_manager.scenarios:
        scene = scenario_manager.scenarios[scenario_manager.current_scene]
        if target in scene.get('pages', {}):
            return target

    # Search across scenes
    matches = []
    for scene_id, scene in scenario_manager.scenarios.items():
        if target in scene.get('pages', {}):
            matches.append(f"{scene_id}:{target}")

    if len(matches) == 1:
        return matches[0]

    return None


def format_transitions(transitions: list) -> str:
    """
    Format transitions for system prompt.

    Args:
        transitions: List of transition dicts with 'id', 'description'

    Returns:
        Formatted transition text for prompt
    """
    if not transitions:
        return "遷移なし（このページに留まります）"

    lines = ["以下の条件に該当する場合、対応する遷移先IDを\"transition\"フィールドに指定してください:\n"]
    for i, trans in enumerate(transitions, 1):
        # Use 'id' as the transition target (simplified format)
        target_id = trans.get('id', trans.get('transition_id', 'unknown'))
        condition = trans.get('description', trans.get('condition', ''))

        lines.append(f"{i}. \"{target_id}\"")
        if condition:
            lines.append(f"   {condition}\n")

    lines.append("上記に該当しない場合は \"transition\": null を使用してください。")
    return "\n".join(lines)


def build_system_prompt(page_data: dict, base_prompt: str) -> str:
    """
    Combine page data with base system prompt.

    Args:
        page_data: Current page data
        base_prompt: Base system prompt

    Returns:
        Combined system prompt
    """
    # Mood constraints (support both new 'allowed_moods' and legacy 'allowed_images')
    allowed_moods = page_data.get('allowed_moods') or page_data.get('allowed_images')
    if allowed_moods:
        mood_constraint = f"このページでは以下のムードのみ使用可能: {', '.join(allowed_moods)}"
    else:
        mood_constraint = "すべてのムードを使用可能"

    # Format transitions
    transitions_text = format_transitions(page_data.get('transitions', []))

    # Get prompts (support both new and legacy field names)
    scene_prompt = page_data.get('scene_prompt', '')
    page_prompt = page_data.get('page_prompt', page_data.get('additional_prompt', ''))
    current_mood = page_data.get('mood', page_data.get('image', '基本スタイル'))
    background = page_data.get('background_image', 'なし')

    # Combine with page-specific instructions
    combined_prompt = f"""{base_prompt}

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
    logger.debug("=== System Prompt ===\n%s", combined_prompt)
    return combined_prompt


def get_opening_message(page_data: dict) -> dict:
    """
    Generate opening message for page transitions.

    Args:
        page_data: Current page data

    Returns:
        dict: Contains text and mood name
    """
    return {
        "text": page_data.get('opening_message', page_data.get('opening_speech', '')),
        "mood": page_data.get('mood', page_data.get('image', '基本スタイル'))
    }


def parse_llm_response(response_text: str) -> tuple:
    """
    Extract JSON from LLM response and parse it.

    Returns:
        tuple: (text, mood_name, transition)
    """
    try:
        data = json.loads(response_text)
        return (
            data.get("text", response_text),
            data.get("mood", data.get("image", "基本スタイル")),  # Support both 'mood' and legacy 'image'
            data.get("transition", None)
        )
    except json.JSONDecodeError:
        # Not JSON format, treat as plain text
        return response_text, "基本スタイル", None


def chat(message: str, history: list):
    """
    Main chat processing function (scenario-based with LLM transition detection).
    Returns: (text_response, html_output)
    """
    global conversation_history, scenario_started, scenario_manager, page_just_changed

    # Get current page data
    page_data = scenario_manager.get_current_page_data()

    # If page just changed, return opening message
    if page_just_changed:
        opening = get_opening_message(page_data)
        page_just_changed = False

        conversation_history.append({"role": "assistant", "content": opening['text']})

        # Render display using HTML/CSS renderer
        # Resolve background image path (images/ -> prompts/images/)
        background_path = resolve_image_path(page_data.get('background_image'))
        logger.info("PAGE CHANGED: %s/%s - mood=%s", page_data['scene'], page_data['page'], opening['mood'])
        logger.debug("  Background (YAML): %s", page_data.get('background_image'))
        logger.debug("  Background (resolved): %s", background_path)
        html_output = renderer.render(
            opening['mood'],
            background_path=background_path
        )

        return opening['text'], html_output

    # Normal conversation flow
    conversation_history.append({"role": "user", "content": message})

    # Build system prompt
    system_prompt = build_system_prompt(page_data, base_system_prompt)

    # Call OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt}
            ] + conversation_history,
            temperature=0.7,
            max_tokens=500
        )

        assistant_message = response.choices[0].message.content

        # Parse response (includes transition field)
        text_response, mood_name, transition = parse_llm_response(assistant_message)
        logger.debug("RESPONSE: mood=%s, transition=%s: %s", mood_name, transition, text_response[:50])

        conversation_history.append({"role": "assistant", "content": assistant_message})

        # Handle page transition if LLM indicated
        if transition:
            try:
                # Remember current location for possible undo
                global previous_page_location
                previous_page_location = (page_data['scene'], page_data['page'])

                next_page_data = scenario_manager._transition_to(transition)
                page_just_changed = True
                logger.info("TRANSITION: %s -> %s/%s", transition, next_page_data['scene'], next_page_data['page'])
                # Use the updated page data for rendering so background changes immediately
                page_data = next_page_data
            except Exception as e:
                logger.error("TRANSITION ERROR: %s", e)

        # Validate mood against page constraints
        allowed_moods = page_data.get('allowed_moods', page_data.get('allowed_images'))
        validated_mood = renderer.validate_mood(mood_name, allowed_moods)

        if validated_mood != mood_name:
            logger.debug("MOOD VALIDATION: %s -> %s", mood_name, validated_mood)

        # Render HTML display with background
        # Resolve background image path (images/ -> prompts/images/)
        background_path = resolve_image_path(page_data.get('background_image'))
        logger.debug("RENDER: %s/%s - mood=%s", page_data['scene'], page_data['page'], validated_mood)
        logger.debug("  Background (YAML): %s", page_data.get('background_image'))
        logger.debug("  Background (resolved): %s", background_path)
        html_output = renderer.render(
            validated_mood,
            background_path=background_path
        )

        return text_response, html_output

    except Exception as e:
        error_message = f"エラーが発生しました: {str(e)}"
        background_path = resolve_image_path(page_data.get('background_image'))
        return error_message, renderer.render("困る", background_path=background_path)


def reset_conversation():
    """Reset conversation history and scenario state."""
    global conversation_history, scenario_started, page_just_changed, previous_page_location
    conversation_history = []
    scenario_started = False
    page_just_changed = False
    previous_page_location = None
    return None, renderer.get_default_display(), "Scene: - | Page: - | Mood: -"


def undo_last_page(history: list, current_display: str):
    """
    Revert to the previous page location if available.

    Args:
        history: Current chat history (unchanged)
        current_display: Current HTML (unused, kept for signature compatibility)
    """
    global previous_page_location, page_just_changed

    if not previous_page_location:
        status = get_status_text()
        return history, current_display, status

    # Restore previous scene/page
    scene_id, page_id = previous_page_location
    scenario_manager.current_scene = scene_id
    scenario_manager.current_page = page_id

    page_data = scenario_manager.get_current_page_data()
    page_just_changed = True  # ensure next chat treats it as fresh page

    background_path = resolve_image_path(page_data.get('background_image'))
    html_output = renderer.render(page_data.get('mood', '基本スタイル'), background_path=background_path)
    status = get_status_text()

    # Clear previous location after use to prevent repeated toggling
    previous_page_location = None

    return history, html_output, status


# === Gradio UI ===
# Custom CSS to prevent HTML component from graying out during processing
custom_css = """
/* Prevent HTML avatar display from graying out during LLM processing */
.gradio-html {
    opacity: 1 !important;
}

.gradio-html[disabled] {
    opacity: 1 !important;
    filter: none !important;
    pointer-events: auto !important;
}

/* Alternative: Target by data attribute if above doesn't work */
[data-testid="html"] {
    opacity: 1 !important;
}

[data-testid="html"][disabled] {
    opacity: 1 !important;
    filter: none !important;
}

/* Stronger override: never dim elements marked with .no-dim */
.no-dim, .no-dim * {
    opacity: 1 !important;
    filter: none !important;
    pointer-events: auto !important;
}

/* Cover Gradio queue states */
.no-dim.pending, .no-dim.generating, .no-dim.loading {
    opacity: 1 !important;
    filter: none !important;
}

/* Parent containers that get disabled */
fieldset:has(.no-dim) {
    opacity: 1 !important;
    filter: none !important;
    pointer-events: auto !important;
}
"""

with gr.Blocks(title="Conversational Drive Navigator", css=custom_css) as demo:
    gr.Markdown("# 🚗 Conversational Drive Navigator")
    gr.Markdown("Navigate a drive from the city to the seaside with 4 friends! Guides gas, cafe, and souvenir spots.")

    with gr.Row():
        # Left: Display area (HTML/CSS rendered output) - 2/3 width
        with gr.Column(scale=2):
            display_component = gr.HTML(
                value=renderer.get_default_display(),
                label="Avatar Display",
                elem_classes=["no-dim"]
            )

            # Status line under the display
            status_line = gr.Textbox(
                label="Status",
                value="Scene: - | Page: - | Mood: -",
                interactive=False,
                show_label=True,
                lines=3,
                max_lines=3
            )

        # Right: Chat interface - 1/3 width
        with gr.Column(scale=1):
            chatbot = gr.Chatbot(label="Conversation", height=500)

            with gr.Row():
                msg = gr.Textbox(
                    label="Enter message",
                    placeholder="Example: Tell me the route to the beach!",
                    scale=4
                )
                send_btn = gr.Button("Send", scale=1, variant="primary")

            with gr.Row():
                undo_btn = gr.Button("Undo Last Page", variant="secondary")
                clear_btn = gr.Button("Reset Conversation", variant="secondary")

            gr.Markdown("### 💡 Try these")
            gr.Markdown("""
            - "Tell me the recommended route to the beach"
            - "I want to refuel on the way"
            - "I'd like to take a break at a cafe"
            - "Are there charging spots?"
            - "I want to buy souvenirs!"
            """)

    # Helper function to get status text
    def get_status_text() -> str:
        """Return current scene, page, mood name, and image paths."""
        page_data = scenario_manager.get_current_page_data()
        scene = page_data.get('scene', '-')
        page = page_data.get('page', '-')
        mood = page_data.get('mood', page_data.get('image', '-'))

        # Get image paths
        background_yaml = page_data.get('background_image', 'none')
        background_resolved = resolve_image_path(background_yaml) if background_yaml and background_yaml != 'none' else 'none'

        # Get mood image path from renderer
        mood_image = renderer.mood_config.get(mood, renderer.mood_config.get(renderer.default_mood, '-'))

        return f"""Scene: {scene} | Page: {page} | Mood: {mood}
Background: {background_yaml} → {background_resolved}
Mood Image: {mood_image}"""

    # Initial load handler
    def load_initial_message():
        """Display greeting from LLM on initial load."""
        global scenario_started, scenario_manager, page_just_changed, conversation_history

        if not scenario_started:
            page_data = scenario_manager.start_scenario()
            scenario_started = True

            opening = get_opening_message(page_data)
            conversation_history.append({"role": "assistant", "content": opening['text']})

            # Render HTML with background
            # Resolve background image path (images/ -> prompts/images/)
            background_path = resolve_image_path(page_data.get('background_image'))
            html_output = renderer.render(
                opening['mood'],
                background_path=background_path
            )
            history = [{"role": "assistant", "content": opening['text']}]
            status = get_status_text()

            return history, html_output, status

        return [], renderer.get_default_display(), "Scene: - | Page: - | Mood: -"

    # Event handlers
    def process_user_message(user_msg: str, history: list, current_display):
        """Process user message."""
        if not user_msg.strip():
            status = get_status_text()
            return history, "", current_display, status

        history = history or []

        # Special command handling (slash commands)
        if user_msg.strip().startswith("/"):
            parts = user_msg.strip().split()
            command = parts[0].lower()
            args = parts[1:]

            if command == "/move":
                if not args:
                    response_text = "移動先を指定してください。例: /move arrival"
                    history.append({"role": "user", "content": user_msg})
                    history.append({"role": "assistant", "content": response_text})
                    status = get_status_text()
                    return history, "", current_display, status

                target = args[0]
                transition = resolve_move_target(target)
                if not transition:
                    response_text = f"移動先が見つかりません: {target}"
                    history.append({"role": "user", "content": user_msg})
                    history.append({"role": "assistant", "content": response_text})
                    status = get_status_text()
                    return history, "", current_display, status

                # Remember current location for undo
                global previous_page_location, page_just_changed
                if scenario_manager.current_scene and scenario_manager.current_page:
                    previous_page_location = (scenario_manager.current_scene, scenario_manager.current_page)

                next_page_data = scenario_manager._transition_to(transition)
                page_just_changed = True

                opening = get_opening_message(next_page_data)
                background_path = resolve_image_path(next_page_data.get('background_image'))
                html_output = renderer.render(opening['mood'], background_path=background_path)

                # Record assistant opening in conversation history (skip slash command)
                conversation_history.append({"role": "assistant", "content": opening['text']})

                response_text = opening['text'] or f"移動しました: {next_page_data['scene']}/{next_page_data['page']}"
                history.append({"role": "user", "content": user_msg})
                history.append({"role": "assistant", "content": response_text})

                status = get_status_text()
                return history, "", html_output, status

            # Unknown command
            response_text = f"不明なコマンドです: {command}"
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": response_text})
            status = get_status_text()
            return history, "", current_display, status

        # Get response from chat function (returns text_response, html_output)
        response_text, html_output = chat(user_msg, history)

        # Add to history (Gradio 6.0 format)
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": response_text})

        # Update HTML display - always use html_output
        status = get_status_text()

        return history, "", html_output, status

    # Button click handlers
    send_btn.click(
        process_user_message,
        inputs=[msg, chatbot, display_component],
        outputs=[chatbot, msg, display_component, status_line]
    )

    msg.submit(
        process_user_message,
        inputs=[msg, chatbot, display_component],
        outputs=[chatbot, msg, display_component, status_line]
    )

    clear_btn.click(
        reset_conversation,
        outputs=[chatbot, display_component, status_line]
    )

    undo_btn.click(
        undo_last_page,
        inputs=[chatbot, display_component],
        outputs=[chatbot, display_component, status_line]
    )

    demo.load(
        load_initial_message,
        outputs=[chatbot, display_component, status_line]
    )


# Application startup
if __name__ == "__main__":
    port = int(os.getenv("GRADIO_SERVER_PORT", "7862"))

    demo.launch(
        share=False,
        server_name="127.0.0.1",
        server_port=port,
        theme=gr.themes.Soft(),
        allowed_paths=["images", "prompts/images", "prompts/data"]
    )
