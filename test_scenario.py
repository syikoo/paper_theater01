"""
シナリオマネージャーの基本的なテスト
"""

from scenario_manager import ScenarioManager


def test_scenario_loading():
    """YAMLシナリオの読み込みと遷移テスト"""
    print("Testing scenario loading...")

    try:
        manager = ScenarioManager('prompts/scenario.yaml')
        start_scene = manager.get_start_scene()
        print(f"[OK] ScenarioManager initialized. Start scene: {start_scene}")

        # YAMLのbase.start_sceneを利用して開始
        page_data = manager.start_scenario()
        print(f"[OK] Started scenario: {page_data['scene']}/{page_data['page']}")
        print(f"     Mood: {page_data['mood']}")
        print(f"     Opening: {page_data['opening_message'][:50]}...")

        mood_config = manager.get_mood_config()
        print(f"[OK] Loaded {len(mood_config)} moods from configuration.mood_images")

        # ページ遷移テスト（LLMのtransition指定を模擬）
        print("\nTesting page transitions...")

        result = manager._transition_to("driving")
        print(f"[OK] Transition to: {result['scene']}/{result['page']}")

        result = manager._transition_to("gas_station:refueling")
        print(f"[OK] Transition to: {result['scene']}/{result['page']}")

        result = manager._transition_to("town_start:driving")
        print(f"[OK] Transition back to: {result['scene']}/{result['page']}")

        print("\n[OK] All tests passed!")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_scenario_loading()
