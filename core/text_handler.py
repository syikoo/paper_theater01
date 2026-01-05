"""
Text chat handler - manages LLM text conversations with scenario integration.
"""

import json
import logging
from typing import Optional
from openai import OpenAI


logger = logging.getLogger(__name__)


class TextChatHandler:
    """Handles text-based chat interactions with scenario/mood/transition logic."""

    def __init__(self, client: OpenAI, scenario_manager, base_system_prompt: str):
        """
        Initialize text chat handler.

        Args:
            client: OpenAI client instance
            scenario_manager: ScenarioManager instance
            base_system_prompt: Base system prompt template
        """
        self.client = client
        self.scenario_manager = scenario_manager
        self.base_system_prompt = base_system_prompt

    def format_transitions(self, transitions: list) -> str:
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
            target_id = trans.get('id', trans.get('transition_id', 'unknown'))
            condition = trans.get('description', trans.get('condition', ''))

            lines.append(f"{i}. \"{target_id}\"")
            if condition:
                lines.append(f"   {condition}\n")

        lines.append("上記に該当しない場合は \"transition\": null を使用してください。")
        return "\n".join(lines)

    def build_system_prompt(self, page_data: dict) -> str:
        """
        Combine page data with base system prompt.

        Args:
            page_data: Current page data

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
        transitions_text = self.format_transitions(page_data.get('transitions', []))

        # Get prompts (support both new and legacy field names)
        scene_prompt = page_data.get('scene_prompt', '')
        page_prompt = page_data.get('page_prompt', page_data.get('additional_prompt', ''))
        current_mood = page_data.get('mood', page_data.get('image', '基本スタイル'))
        background = page_data.get('background_image', 'なし')

        # Combine with page-specific instructions
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
        logger.debug("=== System Prompt ===\n%s", combined_prompt)
        return combined_prompt

    def parse_llm_response(self, response_text: str) -> tuple:
        """
        Extract JSON from LLM response and parse it.

        Returns:
            tuple: (text, mood_name, transition)
        """
        try:
            data = json.loads(response_text)
            return (
                data.get("text", response_text),
                data.get("mood", data.get("image", "基本スタイル")),
                data.get("transition", None)
            )
        except json.JSONDecodeError:
            # Not JSON format, treat as plain text
            return response_text, "基本スタイル", None

    def process_message(
        self,
        message: str,
        conversation_history: list,
        page_data: dict
    ) -> tuple:
        """
        Process text message through LLM.

        Args:
            message: User message
            conversation_history: Full conversation history
            page_data: Current page data from scenario manager

        Returns:
            tuple: (text_response, mood_name, transition)
        """
        # Build system prompt
        system_prompt = self.build_system_prompt(page_data)

        # Call OpenAI API
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

            # Parse response (includes transition field)
            text_response, mood_name, transition = self.parse_llm_response(assistant_message)
            logger.debug(
                "RESPONSE: mood=%s, transition=%s: %s",
                mood_name,
                transition,
                text_response[:50]
            )

            return text_response, mood_name, transition, assistant_message

        except Exception as e:
            error_message = f"エラーが発生しました: {str(e)}"
            logger.error("LLM API error: %s", e)
            return error_message, "困る", None, error_message
