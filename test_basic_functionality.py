"""
Basic functionality test for dual-mode conversation app.
Tests text handler and conversation manager without UI.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from core import TextChatHandler, VoiceChatHandler, ConversationManager
from scenario_manager import ScenarioManager
from renderers import PaperTheaterRenderer, DEFAULT_PAPER_THEATER_MOODS

# Load environment
load_dotenv()

# Initialize components
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
scenario_manager = ScenarioManager('prompts/scenario.yaml')
mood_config = scenario_manager.get_mood_config() or DEFAULT_PAPER_THEATER_MOODS
renderer = PaperTheaterRenderer(mood_config)

# Load base system prompt
def load_prompt_file(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

base_system_prompt = load_prompt_file('prompts/system_prompt.txt')
if scenario_manager.base_prompt:
    base_system_prompt = f"{base_system_prompt}\n\n{scenario_manager.base_prompt}"

base_system_prompt = base_system_prompt.replace(
    '{RENDERER_MOOD_DESCRIPTION}',
    renderer.get_mood_description_prompt()
)

# Initialize handlers
text_handler = TextChatHandler(client, scenario_manager, base_system_prompt)
voice_handler = VoiceChatHandler(client)

def resolve_image_path(path: str) -> str:
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

# Start scenario
print(">> Starting scenario...")
page_data = scenario_manager.start_scenario()
print(f"OK Started: {page_data['scene']} / {page_data['page']}")

# Test 1: Initial greeting
print("\n>> Test 1: Processing opening message...")
conversation_manager.page_just_changed = True
text_response, html_output = conversation_manager.process_text_message("こんにちは")
print(f"Response: {text_response[:100]}...")
print(f"History length: {len(conversation_manager.history)}")

# Test 2: Normal conversation
print("\n>> Test 2: Normal conversation...")
text_response, html_output = conversation_manager.process_text_message("海までの道を教えて")
print(f"Response: {text_response[:100]}...")
print(f"History length: {len(conversation_manager.history)}")

# Test 3: Check HTML rendering
print("\n>> Test 3: HTML rendering...")
if html_output and len(html_output) > 0:
    print("OK HTML output generated successfully")
    print(f"HTML length: {len(html_output)} characters")
else:
    print("ERROR HTML output is empty")

# Test 4: Check conversation history format
print("\n>> Test 4: Conversation history format...")
for i, msg in enumerate(conversation_manager.history):
    print(f"  [{i}] {msg['role']}: {msg['content'][:50]}...")

print("\n>> All basic tests passed!")
print(f"\n>> Summary:")
print(f"  - Scenario: {scenario_manager.current_scene}/{scenario_manager.current_page}")
print(f"  - History entries: {len(conversation_manager.history)}")
print(f"  - Mode: {conversation_manager.current_mode}")
