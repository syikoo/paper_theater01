"""
Conversational avatar application with pluggable display renderers.
Main application orchestrating LLM, scenario management, and UI.
Supports both text and voice chat modes.
"""

import gradio as gr
import os
import logging
from pathlib import Path
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
from fastrtc import Stream, ReplyOnPause

# Import core handlers
from core import TextChatHandler, VoiceChatHandler, ConversationManager
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
if scenario_manager.base_prompt:
    base_system_prompt = f"{base_system_prompt}\n\n{scenario_manager.base_prompt}"

# Inject renderer mood descriptions
base_system_prompt = base_system_prompt.replace(
    '{RENDERER_MOOD_DESCRIPTION}',
    renderer.get_mood_description_prompt()
)

# Initialize handlers
text_handler = TextChatHandler(client, scenario_manager, base_system_prompt)
voice_handler = VoiceChatHandler(client)


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

    if path.startswith("images/"):
        return f"prompts/{path}"

    return path


# Initialize conversation manager
conversation_manager = ConversationManager(
    client=client,
    text_handler=text_handler,
    voice_handler=voice_handler,
    scenario_manager=scenario_manager,
    renderer=renderer,
    resolve_image_path_func=resolve_image_path
)

# Scenario state
scenario_started = False


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


def chat(message: str, history: list):
    """
    Main text chat processing function.
    Returns: (text_response, html_output)
    """
    return conversation_manager.process_text_message(message)


def voice_chat(audio: tuple):
    """
    Voice chat handler for Gradio Stream.
    Yields audio chunks for streaming output.
    """
    return conversation_manager.process_voice_audio(audio)


def reset_conversation():
    """Reset conversation history and scenario state."""
    global scenario_started
    conversation_manager.reset_conversation()
    scenario_started = False
    return None, renderer.get_default_display(), "Scene: - | Page: - | Mood: -"


def undo_last_page(history: list, current_display: str):
    """
    Revert to the previous page location if available.

    Args:
        history: Current chat history (unchanged)
        current_display: Current HTML (unused, kept for signature compatibility)
    """
    success = conversation_manager.undo_last_page()

    if success:
        page_data = scenario_manager.get_current_page_data()
        background_path = resolve_image_path(page_data.get('background_image'))
        html_output = renderer.render(
            page_data.get('mood', '基本スタイル'),
            background_path=background_path
        )
        status = get_status_text()
        return history, html_output, status

    # No undo available
    status = get_status_text()
    return history, current_display, status


# === Gradio UI ===
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

[data-testid="html"] {
    opacity: 1 !important;
}

[data-testid="html"][disabled] {
    opacity: 1 !important;
    filter: none !important;
}

.no-dim, .no-dim * {
    opacity: 1 !important;
    filter: none !important;
    pointer-events: auto !important;
}

.no-dim.pending, .no-dim.generating, .no-dim.loading {
    opacity: 1 !important;
    filter: none !important;
}

fieldset:has(.no-dim) {
    opacity: 1 !important;
    filter: none !important;
    pointer-events: auto !important;
}

/* Fix FastRTC Stream component to stay within right column */
.fastrtc-container {
    position: relative !important;
    width: 100% !important;
    height: auto !important;
    max-width: 100% !important;
}

/* Prevent Stream from creating fullscreen overlay */
.fastrtc-container canvas,
.fastrtc-container video {
    position: relative !important;
    width: 100% !important;
    max-width: 100% !important;
    height: auto !important;
}

/* Keep mode toggle and controls accessible during voice mode */
.radio-group {
    position: relative !important;
    z-index: 1000 !important;
}

/* Voice stream container - constrain within right column */
.voice-stream-container {
    position: relative !important;
    width: 100% !important;
    max-width: 100% !important;
    height: 300px !important;
    max-height: 300px !important;
    overflow: hidden !important;
    contain: layout size style !important;
}

/* Prevent any fullscreen overlays from Stream component */
.voice-stream-container * {
    position: relative !important;
    max-width: 100% !important;
}

/* Override any absolute/fixed positioning in Stream */
.voice-stream-container [style*="position: absolute"],
.voice-stream-container [style*="position: fixed"] {
    position: relative !important;
}

/* Chat column should contain its children */
.chat-column {
    position: relative !important;
    overflow: visible !important;
    contain: layout !important;
}

/* Ensure left column (display area) is not affected */
.chat-column ~ * {
    position: relative !important;
    z-index: 1 !important;
}
"""

with gr.Blocks(title="Conversational Drive Navigator", css=custom_css) as demo:
    gr.Markdown("# 🚗 Conversational Drive Navigator")
    gr.Markdown("Navigate a drive from the city to the seaside with 4 friends! Text & Voice modes supported.")

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
        with gr.Column(scale=1, elem_classes=["chat-column"]):
            # Mode toggle
            mode_toggle = gr.Radio(
                choices=["Text", "Voice"],
                value="Text",
                label="Chat Mode",
                interactive=True,
                elem_classes=["radio-group"]
            )

            chatbot = gr.Chatbot(label="Conversation", height=500, type="messages", allow_tags=False)

            # Text mode components
            with gr.Group() as text_group:
                msg = gr.Textbox(
                    label="Enter message",
                    placeholder="Example: Tell me the route to the beach!",
                    scale=4
                )
                send_btn = gr.Button("Send", variant="primary")

            # Voice mode components
            with gr.Group(visible=False, elem_classes=["voice-stream-container"]) as voice_group:
                gr.Markdown("🎤 **Voice Mode**")
                gr.Markdown("Speak into your microphone. AI will respond with voice.")
                voice_stream = Stream(
                    handler=ReplyOnPause(voice_chat),
                    modality="audio",
                    mode="send-receive"
                )

            # Control buttons
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

        background_yaml = page_data.get('background_image', 'none')
        background_resolved = resolve_image_path(background_yaml) if background_yaml and background_yaml != 'none' else 'none'

        mood_image = renderer.mood_config.get(mood, renderer.mood_config.get(renderer.default_mood, '-'))

        return f"""Scene: {scene} | Page: {page} | Mood: {mood}
Background: {background_yaml} → {background_resolved}
Mood Image: {mood_image}"""

    # Initial load handler
    def load_initial_message():
        """Display greeting from LLM on initial load."""
        global scenario_started

        if not scenario_started:
            page_data = scenario_manager.start_scenario()
            scenario_started = True

            opening_text = page_data.get('opening_message', page_data.get('opening_speech', ''))
            opening_mood = page_data.get('mood', page_data.get('image', '基本スタイル'))

            conversation_manager.history.append({"role": "assistant", "content": opening_text})

            background_path = resolve_image_path(page_data.get('background_image'))
            html_output = renderer.render(opening_mood, background_path=background_path)

            history = [{"role": "assistant", "content": opening_text}]
            status = get_status_text()

            return history, html_output, status

        return [], renderer.get_default_display(), "Scene: - | Page: - | Mood: -"

    # Mode toggle handler
    def toggle_mode(mode):
        """Show/hide components based on mode."""
        is_text = (mode == "Text")
        conversation_manager.current_mode = "text" if is_text else "voice"

        return (
            gr.update(visible=is_text),   # text_group
            gr.update(visible=not is_text) # voice_group
        )

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
                if scenario_manager.current_scene and scenario_manager.current_page:
                    conversation_manager.previous_page_location = (
                        scenario_manager.current_scene,
                        scenario_manager.current_page
                    )

                next_page_data = scenario_manager._transition_to(transition)
                conversation_manager.page_just_changed = True

                opening_text = next_page_data.get('opening_message', next_page_data.get('opening_speech', ''))
                opening_mood = next_page_data.get('mood', next_page_data.get('image', '基本スタイル'))
                background_path = resolve_image_path(next_page_data.get('background_image'))
                html_output = renderer.render(opening_mood, background_path=background_path)

                conversation_manager.history.append({"role": "assistant", "content": opening_text})

                response_text = opening_text or f"移動しました: {next_page_data['scene']}/{next_page_data['page']}"
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

        # Get response from chat function
        response_text, html_output = chat(user_msg, history)

        # Add to history
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": response_text})

        status = get_status_text()
        return history, "", html_output, status

    # Refresh history for voice mode updates
    def get_conversation_history():
        """Get current conversation history for chatbot display."""
        return conversation_manager.history.copy()

    # Mode toggle event
    mode_toggle.change(
        fn=toggle_mode,
        inputs=[mode_toggle],
        outputs=[text_group, voice_group]
    )

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

    # Timer for history refresh (updates chatbot with voice transcripts)
    refresh_timer = gr.Timer(value=1)  # 1 second interval
    refresh_timer.tick(
        fn=get_conversation_history,
        outputs=[chatbot]
    )


# Application startup
if __name__ == "__main__":
    port = int(os.getenv("GRADIO_SERVER_PORT", "7862"))

    demo.launch(
        share=False,
        server_name="127.0.0.1",
        server_port=port,
        allowed_paths=["images", "prompts/images", "prompts/data"]
    )
