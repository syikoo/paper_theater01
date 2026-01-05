"""Test that JSON is not displayed in chatbot."""
import os
from dotenv import load_dotenv
from openai import OpenAI
from core import TextChatHandler, VoiceChatHandler, ConversationManager
from scenario_manager import ScenarioManager
from renderers import PaperTheaterRenderer, DEFAULT_PAPER_THEATER_MOODS

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
scenario_manager = ScenarioManager('prompts/scenario.yaml')
renderer = PaperTheaterRenderer(DEFAULT_PAPER_THEATER_MOODS)

def load_prompt_file(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

base_system_prompt = load_prompt_file('prompts/system_prompt.txt')
base_system_prompt = base_system_prompt.replace(
    '{RENDERER_MOOD_DESCRIPTION}',
    renderer.get_mood_description_prompt()
)

text_handler = TextChatHandler(client, scenario_manager, base_system_prompt)
voice_handler = VoiceChatHandler(client)

def resolve_image_path(path: str):
    return path

manager = ConversationManager(
    client=client,
    text_handler=text_handler,
    voice_handler=voice_handler,
    scenario_manager=scenario_manager,
    renderer=renderer,
    resolve_image_path_func=resolve_image_path
)

# Start scenario
scenario_manager.start_scenario()

# Send a normal message
print("Sending message: 海までの道を教えて")
text_response, html_output = manager.process_text_message("海までの道を教えて")

print("\n=== Display History (shown in chatbot) ===")
for msg in manager.history:
    print(f"{msg['role']}: {msg['content'][:100]}")
    # Check if JSON present
    if '{' in msg['content'] and '"text"' in msg['content']:
        print("  ERROR: JSON found in display history!")

print("\n=== LLM History (used for API context) ===")
for msg in manager.llm_history:
    content_preview = msg['content'][:100]
    print(f"{msg['role']}: {content_preview}")
    # Check if JSON present
    if '{' in msg['content'] and '"text"' in msg['content']:
        print("  OK: JSON found in LLM history (expected)")

print("\n=== Test Result ===")
display_has_json = any('{' in msg['content'] and '"text"' in msg['content']
                       for msg in manager.history if msg['role'] == 'assistant')
llm_has_json = any('{' in msg['content'] and '"text"' in msg['content']
                   for msg in manager.llm_history if msg['role'] == 'assistant')

if display_has_json:
    print("FAIL: JSON still appears in display history")
else:
    print("PASS: No JSON in display history")

if llm_has_json:
    print("PASS: JSON present in LLM history")
else:
    print("FAIL: JSON missing from LLM history")
