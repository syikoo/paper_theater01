"""
Paper Theater (kamishibai) renderer implementation using HTML/CSS compositing.
Uses static images for moods with background image support via HTML layering.
"""

import os
from typing import Optional
from .base_renderer import BaseRenderer


class PaperTheaterRenderer(BaseRenderer):
    """
    Renderer that displays mood images layered over background images using HTML/CSS.
    This is the new implementation replacing KamishibaiRenderer with background support.
    """

    def get_mood_description_prompt(self) -> str:
        """
        Returns description of mood images for system prompt.
        """
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

    def render(self, mood_name: str, background_path: Optional[str] = None) -> str:
        """
        Returns HTML markup with background and mood images composited using CSS.

        Args:
            mood_name: Japanese mood name
            background_path: Optional background image path

        Returns:
            HTML string for display in Gradio gr.HTML component
        """
        # Get mood image path
        mood_image_path = self.mood_config.get(mood_name, self.mood_config[self.default_mood])

        # Resolve mood image path (images/ -> prompts/images/)
        if mood_image_path.startswith("images/"):
            mood_image_path = f"prompts/{mood_image_path}"

        # If no background, display mood image only
        if not background_path:
            return f'''
<div style="position: relative; width: 800px; height: 600px; margin: 0 auto; display: flex; justify-content: center; align-items: center; background-color: #f0f0f0;">
    <img src="/gradio_api/file={mood_image_path}" style="max-width: 100%; max-height: 100%; object-fit: contain;">
</div>
'''

        # Composite background + mood image using CSS positioning
        return f'''
<div style="position: relative; width: 800px; height: 600px; margin: 0 auto; overflow: hidden;">
    <!-- Background image -->
    <img src="/gradio_api/file={background_path}"
         style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover;">

    <!-- Mood image (bottom-right overlay) -->
    <img src="/gradio_api/file={mood_image_path}"
         style="position: absolute; right: 20px; bottom: 20px; max-width: 40%; max-height: 40%; object-fit: contain;">
</div>
'''


# Default mood configuration for paper theater renderer
# Maps Japanese mood names to image file paths
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
