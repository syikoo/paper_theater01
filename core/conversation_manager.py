"""
Conversation manager - orchestrates text/voice handlers and manages unified state.
"""

import logging
from typing import Generator, Optional, Tuple
from openai import OpenAI
from .text_handler import TextChatHandler
from .voice_handler import VoiceChatHandler
from .transcript_analyzer import analyze_transcript


logger = logging.getLogger(__name__)


class ConversationManager:
    """Unified conversation manager for both text and voice modes."""

    def __init__(
        self,
        client: OpenAI,
        text_handler: TextChatHandler,
        voice_handler: VoiceChatHandler,
        scenario_manager,
        renderer,
        resolve_image_path_func
    ):
        """
        Initialize conversation manager.

        Args:
            client: OpenAI client instance
            text_handler: TextChatHandler instance
            voice_handler: VoiceChatHandler instance
            scenario_manager: ScenarioManager instance
            renderer: Display renderer instance
            resolve_image_path_func: Function to resolve image paths
        """
        self.client = client
        self.text_handler = text_handler
        self.voice_handler = voice_handler
        self.scenario_manager = scenario_manager
        self.renderer = renderer
        self.resolve_image_path = resolve_image_path_func

        # Shared state
        self.history = []  # Display history (text only, for chatbot)
        self.llm_history = []  # Internal history (with JSON, for LLM context)
        self.current_mode = "text"  # "text" or "voice"
        self.page_just_changed = False
        self.previous_page_location = None

    def get_current_display(self) -> str:
        """
        Get HTML for current mood/background.

        Returns:
            HTML string for display component
        """
        page_data = self.scenario_manager.get_current_page_data()
        mood = page_data.get('mood', page_data.get('image', '基本スタイル'))
        background_path = self.resolve_image_path(page_data.get('background_image'))

        return self.renderer.render(mood, background_path=background_path)

    def handle_page_transition(self, transition: Optional[str], page_data: dict) -> Tuple[bool, dict]:
        """
        Handle page transition if indicated.

        Args:
            transition: Transition target ID or None
            page_data: Current page data

        Returns:
            Tuple of (transition_occurred, new_page_data)
        """
        if not transition:
            return False, page_data

        try:
            # Save current location for undo
            self.previous_page_location = (page_data['scene'], page_data['page'])

            # Execute transition
            next_page_data = self.scenario_manager._transition_to(transition)
            self.page_just_changed = True

            logger.info(
                "TRANSITION: %s -> %s/%s",
                transition,
                next_page_data['scene'],
                next_page_data['page']
            )

            return True, next_page_data

        except Exception as e:
            logger.error("TRANSITION ERROR: %s", e)
            return False, page_data

    def process_text_message(
        self,
        message: str
    ) -> Tuple[str, str]:
        """
        Process text message through text handler.

        Args:
            message: User message

        Returns:
            Tuple of (text_response, html_output)
        """
        # Get current page data
        page_data = self.scenario_manager.get_current_page_data()

        # Handle page just changed (opening message)
        if self.page_just_changed:
            opening_text = page_data.get('opening_message', page_data.get('opening_speech', ''))
            opening_mood = page_data.get('mood', page_data.get('image', '基本スタイル'))

            self.page_just_changed = False
            self.history.append({"role": "assistant", "content": opening_text})
            self.llm_history.append({"role": "assistant", "content": opening_text})

            # Render display
            background_path = self.resolve_image_path(page_data.get('background_image'))
            html_output = self.renderer.render(opening_mood, background_path=background_path)

            logger.info(
                "PAGE CHANGED: %s/%s - mood=%s",
                page_data['scene'],
                page_data['page'],
                opening_mood
            )

            return opening_text, html_output

        # Process message through text handler (use LLM history with JSON for context)
        text_response, mood_name, transition, assistant_message = self.text_handler.process_message(
            message,
            self.llm_history,
            page_data
        )

        # Add to both histories
        # LLM history: includes JSON for model context
        self.llm_history.append({"role": "user", "content": message})
        self.llm_history.append({"role": "assistant", "content": assistant_message})

        # Display history: text only for chatbot
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": text_response})

        # Handle transition
        transition_occurred, page_data = self.handle_page_transition(transition, page_data)

        # Validate mood against page constraints
        allowed_moods = page_data.get('allowed_moods', page_data.get('allowed_images'))
        validated_mood = self.renderer.validate_mood(mood_name, allowed_moods)

        if validated_mood != mood_name:
            logger.debug("MOOD VALIDATION: %s -> %s", mood_name, validated_mood)

        # Render display
        background_path = self.resolve_image_path(page_data.get('background_image'))
        html_output = self.renderer.render(validated_mood, background_path=background_path)

        logger.debug(
            "RENDER: %s/%s - mood=%s",
            page_data['scene'],
            page_data['page'],
            validated_mood
        )

        return text_response, html_output

    def process_voice_audio(
        self,
        audio: Tuple[int, "np.ndarray"]
    ) -> Generator[Tuple[int, "np.ndarray"], None, None]:
        """
        Process voice audio through voice handler and transcript analyzer.

        This is a generator that yields audio chunks for streaming output,
        and also updates the conversation history with analyzed transcripts.

        Args:
            audio: Tuple of (sample_rate, audio_data)

        Yields:
            Tuple of (sample_rate, audio_array) for Gradio Stream output
        """
        # Get current page data for context
        page_data = self.scenario_manager.get_current_page_data()

        # Build system instructions for Realtime API
        scene_prompt = page_data.get('scene_prompt', '')
        page_prompt = page_data.get('page_prompt', page_data.get('additional_prompt', ''))

        system_instructions = f"""あなたは親切なドライブナビゲーターです。
簡潔に日本語で応答してください。

現在のシーン: {page_data['scene']}
現在のページ: {page_data['page']}

{scene_prompt}

{page_prompt}
"""

        logger.info("Processing voice audio for page: %s/%s", page_data['scene'], page_data['page'])

        # Process audio through voice handler (streaming)
        user_transcript = ""
        assistant_transcript = ""

        for audio_chunk in self.voice_handler.process_audio(audio, system_instructions):
            # Stream audio output
            yield audio_chunk

            # Capture return value (transcripts) at the end
            if hasattr(audio_chunk, '__iter__'):
                sample_rate, audio_array = audio_chunk
            else:
                # This is the return value with transcripts
                user_transcript, assistant_transcript = audio_chunk

        # After audio streaming completes, analyze transcripts
        if user_transcript or assistant_transcript:
            logger.info("Analyzing transcripts: user=%s, assistant=%s", user_transcript[:50], assistant_transcript[:50])

            # Analyze transcript to extract mood/transition
            analysis = analyze_transcript(
                self.client,
                user_transcript,
                assistant_transcript,
                page_data,
                allowed_moods=page_data.get('allowed_moods', page_data.get('allowed_images'))
            )

            mood = analysis.get("mood", "基本スタイル")
            transition = analysis.get("transition", None)

            logger.info("Transcript analysis result: mood=%s, transition=%s", mood, transition)

            # Add to both histories (voice mode: no JSON, just text)
            if user_transcript:
                self.history.append({"role": "user", "content": user_transcript})
                self.llm_history.append({"role": "user", "content": user_transcript})
            if assistant_transcript:
                self.history.append({"role": "assistant", "content": assistant_transcript})
                self.llm_history.append({"role": "assistant", "content": assistant_transcript})

            # Handle transition
            transition_occurred, page_data = self.handle_page_transition(transition, page_data)

            # Note: Display update will be handled by the UI's timer-based refresh
            # which calls get_current_display()

    def reset_conversation(self):
        """Reset conversation history and scenario state."""
        self.history = []
        self.llm_history = []
        self.page_just_changed = False
        self.previous_page_location = None
        logger.info("Conversation reset")

    def undo_last_page(self) -> bool:
        """
        Revert to the previous page location if available.

        Returns:
            bool: True if undo was successful, False otherwise
        """
        if not self.previous_page_location:
            return False

        # Restore previous scene/page
        scene_id, page_id = self.previous_page_location
        self.scenario_manager.current_scene = scene_id
        self.scenario_manager.current_page = page_id

        self.page_just_changed = True  # Ensure next chat treats it as fresh page

        # Clear previous location after use to prevent repeated toggling
        self.previous_page_location = None

        logger.info("Undone to page: %s/%s", scene_id, page_id)
        return True
