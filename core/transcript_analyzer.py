"""
Transcript analyzer - converts voice transcripts to structured JSON format.

This module re-analyzes voice conversation transcripts using gpt-4o-mini
to extract mood and transition information, matching the format used by
text mode for unified processing.
"""

import json
import logging
from typing import Optional
from openai import OpenAI


logger = logging.getLogger(__name__)


def format_transitions_for_analysis(transitions: list) -> str:
    """
    Format transitions for analysis prompt.

    Args:
        transitions: List of transition dicts with 'id', 'description'

    Returns:
        Formatted transition text
    """
    if not transitions:
        return "遷移なし"

    lines = []
    for i, trans in enumerate(transitions, 1):
        target_id = trans.get('id', trans.get('transition_id', 'unknown'))
        condition = trans.get('description', trans.get('condition', ''))
        lines.append(f"{i}. \"{target_id}\": {condition}")

    return "\n".join(lines)


def analyze_transcript(
    client: OpenAI,
    user_transcript: str,
    assistant_transcript: str,
    page_data: dict,
    allowed_moods: Optional[list] = None
) -> dict:
    """
    Re-analyze voice conversation to extract mood and transition.

    This function makes an additional API call to gpt-4o-mini to retrospectively
    analyze the voice conversation and determine what mood and transition would
    be appropriate based on the page context.

    Args:
        client: OpenAI client instance
        user_transcript: User's spoken words (from Whisper)
        assistant_transcript: AI's spoken response (from Realtime API)
        page_data: Current scenario page context
        allowed_moods: List of allowed mood names for this page

    Returns:
        dict: {
            "mood": str,
            "transition": str or None
        }
    """
    # Get page constraints
    page_allowed_moods = allowed_moods or page_data.get('allowed_moods') or page_data.get('allowed_images')
    transitions = page_data.get('transitions', [])

    # Build mood constraint text
    if page_allowed_moods:
        mood_constraint = f"以下のムードのみ使用可能: {', '.join(page_allowed_moods)}"
    else:
        mood_constraint = "すべてのムードを使用可能"

    # Format transitions
    transitions_text = format_transitions_for_analysis(transitions)

    # Build analysis prompt
    analysis_prompt = f"""
以下の音声会話の内容を分析し、適切なムードと遷移を判定してください。

## 現在のページ情報
シーン: {page_data.get('scene', 'unknown')}
ページ: {page_data.get('page', 'unknown')}

## ムード使用制約
{mood_constraint}

## 利用可能な遷移
{transitions_text}

## 会話内容
ユーザー: {user_transcript}
アシスタント: {assistant_transcript}

## 判定指示
1. アシスタントの応答内容から、最も適切なムード（表情）を選択してください
2. 会話の流れから、ページ遷移が必要かどうかを判断してください
3. 遷移が不要な場合は transition に null を設定してください

## 出力形式
以下のJSON形式で応答してください（JSONのみ、説明不要）：
{{
  "mood": "ムード名",
  "transition": "遷移先ID" または null
}}
"""

    logger.debug("=== Transcript Analysis Prompt ===\n%s", analysis_prompt)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.3,  # Low temperature for consistent analysis
            max_tokens=150
        )

        response_text = response.choices[0].message.content.strip()
        logger.debug("Analysis response: %s", response_text)

        # Parse JSON response
        try:
            result = json.loads(response_text)
            mood = result.get("mood", "基本スタイル")
            transition = result.get("transition", None)

            logger.info(
                "Transcript analysis: mood=%s, transition=%s",
                mood,
                transition
            )

            return {
                "mood": mood,
                "transition": transition
            }

        except json.JSONDecodeError as e:
            logger.error("Failed to parse analysis JSON: %s", e)
            return {
                "mood": "基本スタイル",
                "transition": None
            }

    except Exception as e:
        logger.error("Transcript analysis error: %s", e)
        return {
            "mood": "基本スタイル",
            "transition": None
        }
