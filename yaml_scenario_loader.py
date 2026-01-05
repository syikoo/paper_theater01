"""
YAML scenario loader and validator.
Loads YAML-based scenario files and converts them to internal data structures.
"""

import yaml
import os
from typing import Dict, Any, List, Optional


class YAMLScenarioLoader:
    """Loads and validates YAML scenario files."""

    def __init__(self, yaml_file: str):
        """
        Args:
            yaml_file: Path to YAML scenario file
        """
        self.yaml_file = yaml_file
        self.raw_data = None
        self.scenarios = {}

    def load(self) -> Dict[str, Any]:
        """
        Load and parse YAML scenario file.

        Returns:
            Dict of scenarios in internal format compatible with ScenarioManager

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            yaml.YAMLError: If YAML is malformed
            ValueError: If schema validation fails
        """
        if not os.path.exists(self.yaml_file):
            raise FileNotFoundError(f"YAML scenario file not found: {self.yaml_file}")

        # Load YAML
        with open(self.yaml_file, 'r', encoding='utf-8') as f:
            self.raw_data = yaml.safe_load(f)

        # Validate schema
        self._validate_schema()

        # Convert to internal format
        self.scenarios = self._convert_to_internal_format()

        return self.scenarios

    def _validate_schema(self):
        """Validate YAML schema has required fields."""
        if not isinstance(self.raw_data, dict):
            raise ValueError("YAML root must be a dictionary")

        # Validate base section
        if 'base' not in self.raw_data:
            raise ValueError("Missing required 'base' section")

        base = self.raw_data['base']
        if 'start_scene' not in base:
            raise ValueError("Missing required 'base.start_scene' field")

        # Validate scenes section
        if 'scenes' not in self.raw_data:
            raise ValueError("Missing required 'scenes' section")

        scenes = self.raw_data['scenes']
        if not isinstance(scenes, list) or len(scenes) == 0:
            raise ValueError("'scenes' must be a non-empty list")

        # Validate each scene
        for i, scene in enumerate(scenes):
            self._validate_scene(scene, i)

        # Validate configuration section
        if 'configuration' not in self.raw_data:
            raise ValueError("Missing required 'configuration' section")

        config = self.raw_data['configuration']
        if 'mood_images' not in config:
            raise ValueError("Missing required 'configuration.mood_images' field")

    def _validate_scene(self, scene: Dict, index: int):
        """Validate a single scene."""
        required_fields = ['scene_id', 'start_page', 'pages']

        for field in required_fields:
            if field not in scene:
                raise ValueError(f"Scene {index}: Missing required field '{field}'")

        # Validate pages
        pages = scene['pages']
        if not isinstance(pages, list) or len(pages) == 0:
            raise ValueError(f"Scene {index} ('{scene['scene_id']}'): 'pages' must be a non-empty list")

        for j, page in enumerate(pages):
            self._validate_page(page, scene['scene_id'], j)

    def _validate_page(self, page: Dict, scene_id: str, index: int):
        """Validate a single page."""
        required_fields = ['page_id', 'default_mood']

        for field in required_fields:
            if field not in page:
                raise ValueError(
                    f"Scene '{scene_id}', Page {index}: Missing required field '{field}'"
                )

    def _convert_to_internal_format(self) -> Dict[str, Any]:
        """
        Convert YAML data to internal scenario format.

        Returns:
            Dict compatible with ScenarioManager's existing structure
        """
        scenarios = {}

        for scene in self.raw_data['scenes']:
            scene_id = scene['scene_id']

            # Convert pages to dict format
            pages_dict = {}
            for page in scene['pages']:
                page_id = page['page_id']

                # Convert transitions format (dict: {target: condition})
                transitions = []
                transitions_data = page.get('transitions', {})

                if isinstance(transitions_data, dict):
                    # New format: {target: condition}
                    for target, condition in transitions_data.items():
                        transitions.append({
                            'id': target,
                            'description': condition,
                            'transition_id': target.replace(':', '_')
                        })
                elif isinstance(transitions_data, list):
                    # Legacy format: [{target: ..., condition: ...}]
                    for trans in transitions_data:
                        transitions.append({
                            'id': trans.get('target'),
                            'description': trans.get('condition'),
                            'transition_id': trans.get('transition_id', trans.get('target', '').replace(':', '_'))
                        })

                # Build page data in internal format
                pages_dict[page_id] = {
                    'mood': page['default_mood'],  # NEW: 'mood' instead of 'image'
                    'opening_message': page.get('opening_message', ''),  # NEW: renamed from 'opening_speech'
                    'page_prompt': page.get('page_prompt', ''),  # NEW: separate page prompt
                    'background_image': page.get('background_image'),  # NEW: background support
                    'allowed_moods': page.get('allowed_moods'),  # NEW: renamed from 'allowed_images'
                    'transitions': transitions,  # NEW: enhanced transition format
                    # Legacy fields for compatibility
                    'image': page['default_mood'],
                    'opening_speech': page.get('opening_message', ''),
                    'additional_prompt': page.get('page_prompt', ''),
                    'allowed_images': page.get('allowed_moods'),
                    'available_transitions': transitions
                }

            # Build scene data
            scenarios[scene_id] = {
                'name': scene.get('description', scene_id),
                'description': scene.get('description', ''),
                'start_page': scene['start_page'],
                'scene_prompt': scene.get('scene_prompt', ''),  # NEW: scene-level prompt
                'opening_message': scene.get('opening_message', ''),  # NEW: scene opening message
                'background_image': scene.get('background_image'),  # NEW: scene default background
                'allowed_moods': scene.get('allowed_moods'),  # NEW: scene-level mood constraints
                'pages': pages_dict
            }

        return scenarios

    def get_mood_config(self) -> Dict[str, str]:
        """
        Extract mood image configuration.

        Returns:
            Dict mapping mood names to image paths
        """
        if not self.raw_data:
            raise ValueError("YAML not loaded yet. Call load() first.")

        return self.raw_data['configuration'].get('mood_images', {})

    def get_background_config(self) -> Dict[str, str]:
        """
        Extract background image configuration.

        Returns:
            Dict mapping background names to image paths
        """
        if not self.raw_data:
            raise ValueError("YAML not loaded yet. Call load() first.")

        return self.raw_data['configuration'].get('background_images', {})

    def get_base_prompt(self) -> str:
        """
        Extract base prompt to combine with system_prompt.txt.

        Returns:
            Base prompt string
        """
        if not self.raw_data:
            raise ValueError("YAML not loaded yet. Call load() first.")

        return self.raw_data['base'].get('base_prompt', '')

    def get_start_scene(self) -> str:
        """
        Get the starting scene ID.

        Returns:
            Scene ID to start with
        """
        if not self.raw_data:
            raise ValueError("YAML not loaded yet. Call load() first.")

        return self.raw_data['base']['start_scene']
