"""
Scenario management module.
Manages scene/page-based prompt structure.
"""

from typing import Dict, Any, Optional


class ScenarioManager:
    """Manages scenario loading and page transitions."""

    def __init__(self, scenario_file: str):
        """
        Args:
            scenario_file: Path to YAML scenario definition file
        """
        self.scenario_file = scenario_file
        self.loader = None
        self.start_scene: Optional[str] = None
        self.base_prompt: str = ""
        self.mood_config: Dict[str, str] = {}
        self.background_config: Dict[str, str] = {}

        # Load YAML scenarios
        if not scenario_file.endswith(('.yaml', '.yml')):
            raise ValueError(f"Only YAML format is supported. Got: {scenario_file}")

        self.scenarios = self._load_yaml_scenarios()
        self.format = 'yaml'

        self.current_scene = None
        self.current_page = None

    def _load_yaml_scenarios(self) -> Dict[str, Any]:
        """Load scenarios from YAML file and capture base/config sections."""
        from yaml_scenario_loader import YAMLScenarioLoader

        self.loader = YAMLScenarioLoader(self.scenario_file)
        scenarios = self.loader.load()
        self.base_prompt = self.loader.get_base_prompt()
        self.start_scene = self.loader.get_start_scene()
        self.mood_config = self.loader.get_mood_config()
        self.background_config = self.loader.get_background_config()
        return scenarios

    def start_scenario(self, scene_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a scenario.

        Args:
            scene_id: Scene ID to start. If omitted, uses base.start_scene from YAML.

        Returns:
            Current page data
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

    def get_current_page_data(self) -> Dict[str, Any]:
        """
        Get current page information.

        Returns:
            Page data with all fields (new and legacy)
        """
        if not self.current_scene or not self.current_page:
            raise RuntimeError("Scenario not started. Call start_scenario() first.")

        scene = self.scenarios[self.current_scene]
        page = scene['pages'][self.current_page]

        return {
            'scene': self.current_scene,
            'page': self.current_page,
            # New fields
            'mood': page.get('mood', page.get('image', '基本スタイル')),
            'opening_message': page.get('opening_message', page.get('opening_speech', '')),
            'page_prompt': page.get('page_prompt', page.get('additional_prompt', '')),
            'scene_prompt': scene.get('scene_prompt', ''),
            'background_image': page.get('background_image'),
            'allowed_moods': page.get('allowed_moods', page.get('allowed_images')),
            'transitions': page.get('transitions', page.get('available_transitions', [])),
            # Legacy fields for backward compatibility
            'image': page.get('image', page.get('mood', '基本スタイル')),
            'opening_speech': page.get('opening_speech', page.get('opening_message', '')),
            'additional_prompt': page.get('additional_prompt', page.get('page_prompt', '')),
            'allowed_images': page.get('allowed_images', page.get('allowed_moods')),
            'available_transitions': page.get('available_transitions', page.get('transitions', []))
        }

    def _transition_to(self, next_location: str) -> Dict[str, Any]:
        """
        Transition to specified location.

        Args:
            next_location: Destination ("page_2" or "scene_B:page_1" format)

        Returns:
            Destination page data
        """
        if ':' in next_location:
            # Cross-scene transition: "scene_B:page_1"
            scene_id, page_id = next_location.split(':', 1)
            self.current_scene = scene_id
            self.current_page = page_id
        else:
            # Same-scene transition: "page_2"
            self.current_page = next_location

        return self.get_current_page_data()

    def get_start_scene(self) -> Optional[str]:
        """Return configured default start scene from YAML."""
        return self.start_scene

    def get_mood_config(self) -> Dict[str, str]:
        """Return mood image configuration from YAML."""
        return self.mood_config
