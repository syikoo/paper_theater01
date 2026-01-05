"""
Base renderer abstract class for display methods.
Defines the interface that all renderer implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseRenderer(ABC):
    """
    Abstract base class for rendering conversation responses.

    Subclasses implement specific display methods (images, 3D avatars, HTML, etc.)
    while maintaining a consistent interface with the conversation system.
    """

    def __init__(self, mood_config: Dict[str, str]):
        """
        Initialize renderer with mood configuration.

        Args:
            mood_config: Dictionary mapping Japanese mood names to display resources
                        (e.g., {"基本スタイル": "prompts/data/mood_basic.png"})
        """
        self.mood_config = mood_config
        # Legacy alias for backward compatibility
        self.state_config = mood_config
        self.default_mood = "基本スタイル"
        # Legacy alias for backward compatibility
        self.default_state = "基本スタイル"

    @abstractmethod
    def get_mood_description_prompt(self) -> str:
        """
        Returns a prompt fragment describing available moods and their usage.
        This is injected into the system prompt to guide LLM mood selection.

        Returns:
            String describing moods (e.g., "基本スタイル: normal conversation...")
        """
        pass

    # Legacy alias for backward compatibility
    def get_state_description_prompt(self) -> str:
        """Legacy method. Use get_mood_description_prompt() instead."""
        return self.get_mood_description_prompt()

    @abstractmethod
    def render(self, mood_name: str, background_path: Optional[str] = None) -> Any:
        """
        Render the display for a given mood name, optionally with background.

        Args:
            mood_name: Japanese mood name (e.g., "笑う", "困る")
            background_path: Optional background image path for compositing

        Returns:
            Display resource (file path, HTML string, 3D model data, etc.)
        """
        pass

    def get_default_display(self) -> Any:
        """
        Returns the default display resource.

        Returns:
            Default display resource
        """
        return self.render(self.default_mood)

    def validate_mood(self, mood_name: str, allowed_moods: Optional[list] = None) -> str:
        """
        Validate mood name against allowed moods.

        Args:
            mood_name: Mood name to validate
            allowed_moods: Optional list of allowed moods for current page

        Returns:
            Valid mood name (original or default if invalid)
        """
        # Check if mood exists in configuration
        if mood_name not in self.mood_config:
            return self.default_mood

        # Check against allowed moods if specified
        if allowed_moods and mood_name not in allowed_moods:
            return self.default_mood

        return mood_name

    # Legacy alias for backward compatibility
    def validate_state(self, state_name: str, allowed_states: Optional[list] = None) -> str:
        """Legacy method. Use validate_mood() instead."""
        return self.validate_mood(state_name, allowed_states)
