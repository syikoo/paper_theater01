# Voice Mode Implementation - Dual-Mode Chat

## Overview

The conversation app now supports both **Text** and **Voice** chat modes with intelligent transcript analysis.

## Features

### Text Mode (Default)
- Type messages in the text input
- LLM responds with JSON format (mood, transition)
- Full scenario navigation support
- Mood/background rendering

### Voice Mode
- Speak into microphone
- OpenAI Realtime API with Server-side VAD
- AI responds with voice
- Automatic transcript analysis
- Mood/transition detection from voice conversation
- Transcripts appear in chat history

## Architecture

```
Text Mode:  User types → gpt-4o-mini → JSON → Display update
Voice Mode: User speaks → Realtime API → Transcript →
            gpt-4o-mini analysis → JSON → Display update
```

## How to Use

### Starting the Application

```bash
# Install dependencies (if not already done)
uv sync

# Run the application
uv run python conversation_app.py
```

The app will launch at: http://127.0.0.1:7862

### Switching Modes

1. **Text Mode** (default):
   - Use the text input box to type messages
   - Click "Send" or press Enter
   - Works exactly as before

2. **Voice Mode**:
   - Click the "Voice" radio button
   - Grant microphone permissions when prompted
   - Speak into your microphone
   - The AI will respond with voice
   - Transcripts automatically appear in the chatbot

### Voice Mode Features

- **Automatic Transcription**: User speech is transcribed via Whisper
- **Voice Response**: AI responds with natural speech
- **Mood Detection**: Conversation is analyzed to determine appropriate mood
- **Scenario Transitions**: Voice conversations can trigger page transitions
- **Shared History**: Both text and voice messages appear in the same chat

## Technical Details

### New Modules

- `core/text_handler.py`: Text chat processing
- `core/voice_handler.py`: Realtime API audio streaming
- `core/transcript_analyzer.py`: Voice transcript → JSON conversion
- `core/conversation_manager.py`: Unified state management

### Dependencies Added

- `fastrtc[vad]>=0.0.30`: Audio streaming with voice activity detection
- `scipy>=1.0.0`: Audio resampling
- `numpy>=1.20.0`: Audio processing
- `gradio>=5.0.0,<6.0.0`: Compatible with fastrtc

### Audio Processing

- Input: 48kHz → Downsampled to 24kHz
- Format: float32 → int16 conversion
- Chunking: 480 samples (20ms)
- VAD: Server-side voice activity detection

## Testing

### Basic Functionality Test

```bash
uv run python test_basic_functionality.py
```

This tests:
- Scenario initialization
- Text message processing
- HTML rendering
- Conversation history management

### Manual Testing

1. **Text Mode**:
   - Send a message
   - Verify JSON parsing
   - Check mood/background rendering
   - Try `/move` command

2. **Voice Mode**:
   - Switch to voice mode
   - Speak into microphone
   - Verify audio response
   - Check transcript in chatbot
   - Verify mood/background update

3. **Mode Switching**:
   - Switch between text and voice
   - Verify history is preserved
   - Check display persistence

## Known Issues

- Deprecation warnings for Gradio 6.0 (safe to ignore, works on Gradio 5.x)
- First voice interaction downloads VAD model (~3MB)
- Console output may show character encoding issues on Windows (display is fine)

## Environment Variables

```bash
# Required
OPENAI_API_KEY=your_api_key_here

# Optional
LOG_LEVEL=INFO  # Set to DEBUG for detailed logs
GRADIO_SERVER_PORT=7862  # Default port
```

## Cost Considerations

- **Text Mode**: ~$0.0001 per message (gpt-4o-mini)
- **Voice Mode**: ~$0.06 per minute (Realtime API) + ~$0.0001 for transcript analysis
- Voice mode makes 2 API calls: Realtime API + gpt-4o-mini analysis

## Future Enhancements

- [ ] Voice command shortcuts (e.g., "Jump to cafe")
- [ ] Audio quality settings
- [ ] Voice mode status indicators
- [ ] Interrupt/pause functionality
- [ ] Multi-language support

## Troubleshooting

### Microphone Access
- Grant browser permission when prompted
- Check browser settings if voice not working

### VAD Model Download
- First launch downloads ~3MB model
- Requires internet connection
- Cached for subsequent use

### Audio Quality Issues
- Check microphone settings
- Ensure quiet environment
- Adjust VAD threshold if needed

## Files Modified

- `conversation_app.py`: Refactored with dual-mode support
- `pyproject.toml`: Added audio dependencies
- `core/*`: New modular architecture

## Backup

Original file backed up as: `conversation_app_original_backup.py`
