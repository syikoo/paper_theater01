"""
Voice chat handler - manages Realtime API audio streaming and transcription.
"""

import base64
import logging
import numpy as np
from scipy import signal
from typing import Generator, Tuple
from openai import OpenAI


logger = logging.getLogger(__name__)


class VoiceChatHandler:
    """Handles voice-based chat interactions using OpenAI Realtime API."""

    SAMPLE_RATE = 24000  # Required by Realtime API
    CHUNK_SIZE = 480  # 20ms @ 24000Hz

    def __init__(self, client: OpenAI):
        """
        Initialize voice chat handler.

        Args:
            client: OpenAI client instance
        """
        self.client = client

    def _generate_silence(self, duration_ms: int = 100) -> Tuple[int, np.ndarray]:
        """
        Generate silence data (for Stream connection maintenance).

        Args:
            duration_ms: Duration in milliseconds

        Returns:
            Tuple of (sample_rate, audio_array)
        """
        samples = int(self.SAMPLE_RATE * duration_ms / 1000)
        silence = np.zeros(samples, dtype=np.int16)
        return (self.SAMPLE_RATE, silence)

    def _preprocess_audio(
        self,
        audio_data: np.ndarray,
        sample_rate: int
    ) -> np.ndarray:
        """
        Preprocess audio data for Realtime API.

        - Flatten 2D arrays to 1D
        - Convert float32 to int16
        - Resample to 24kHz if needed

        Args:
            audio_data: Input audio array
            sample_rate: Input sample rate

        Returns:
            Preprocessed audio as int16 @ 24kHz
        """
        logger.debug(
            "Audio preprocessing: dtype=%s, shape=%s, rate=%dHz",
            audio_data.dtype,
            audio_data.shape,
            sample_rate
        )

        # Flatten 2D to 1D
        if len(audio_data.shape) == 2:
            logger.debug("Flattening 2D array: %s", audio_data.shape)
            audio_data = audio_data.flatten()

        # Convert float32 → int16
        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32767).astype(np.int16)
            logger.debug("Converted to int16")

        # Resample if needed
        if sample_rate != self.SAMPLE_RATE:
            target_length = int(len(audio_data) * self.SAMPLE_RATE / sample_rate)
            audio_data = signal.resample(audio_data, target_length).astype(np.int16)
            logger.debug("Resampled %dHz → %dHz", sample_rate, self.SAMPLE_RATE)

        return audio_data

    def process_audio(
        self,
        audio: Tuple[int, np.ndarray],
        system_instructions: str = "あなたは親切なドライブナビゲーターです。簡潔に日本語で応答してください。"
    ) -> Generator[Tuple[int, np.ndarray], None, Tuple[str, str]]:
        """
        Process audio through Realtime API with streaming response.

        Args:
            audio: Tuple of (sample_rate, audio_data)
            system_instructions: System instructions for the session

        Yields:
            Tuple of (sample_rate, audio_array) for audio output

        Returns:
            Tuple of (user_transcript, assistant_transcript)
        """
        sample_rate, audio_data = audio

        logger.info("Voice chat started: %d samples @ %dHz", len(audio_data), sample_rate)

        # Validate audio length
        if len(audio_data) < 100:
            logger.warning("Audio too short: %d samples", len(audio_data))
            yield self._generate_silence(100)
            return "", ""

        # Preprocess audio
        try:
            audio_24k = self._preprocess_audio(audio_data, sample_rate)
        except Exception as e:
            logger.error("Audio preprocessing error: %s", e)
            yield self._generate_silence(100)
            return "", ""

        # Initialize transcripts
        user_transcript = ""
        assistant_transcript = ""
        response_count = 0
        user_message_added = False

        # Realtime API streaming
        try:
            with self.client.beta.realtime.connect(model="gpt-4o-realtime-preview") as conn:
                logger.debug("Realtime API connected")

                # Configure session
                conn.session.update(session={
                    "instructions": system_instructions,
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    },
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    }
                })
                logger.debug("Session configured (Server VAD enabled)")

                # Send audio in chunks
                logger.debug(
                    "Sending audio: %d chunks",
                    len(audio_24k) // self.CHUNK_SIZE
                )
                for i in range(0, len(audio_24k), self.CHUNK_SIZE):
                    chunk = audio_24k[i:i+self.CHUNK_SIZE]
                    chunk_b64 = base64.b64encode(chunk.tobytes()).decode()
                    conn.input_audio_buffer.append(audio=chunk_b64)

                logger.debug("All chunks sent")

                # Commit and request response
                conn.input_audio_buffer.commit()
                logger.debug("Buffer committed")

                conn.response.create()
                logger.debug("Response creation requested")

                # Process event stream
                for event in conn:
                    logger.debug("Event: %s", event.type)

                    # Audio buffer events
                    if event.type == "input_audio_buffer.committed":
                        logger.debug("Audio buffer commit confirmed")

                    elif event.type == "input_audio_buffer.speech_started":
                        logger.debug("Speech detected")

                    elif event.type == "input_audio_buffer.speech_stopped":
                        logger.debug("Speech ended")

                    # Transcription events
                    elif event.type == "conversation.item.input_audio_transcription.completed":
                        user_transcript = event.transcript
                        logger.info("[USER] %s", user_transcript)
                        user_message_added = True

                    elif event.type == "conversation.item.input_audio_transcription.failed":
                        logger.error("Transcription failed: %s", event)

                    # Response audio
                    elif event.type == "response.audio.delta":
                        audio_chunk = base64.b64decode(event.delta)
                        audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
                        response_count += len(audio_array)
                        yield (self.SAMPLE_RATE, audio_array)

                    elif event.type == "response.audio.done":
                        logger.debug("Audio response complete: %d samples", response_count)

                    # Response text
                    elif event.type == "response.audio_transcript.delta":
                        assistant_transcript += event.delta

                    elif event.type == "response.audio_transcript.done":
                        logger.info("[ASSISTANT] %s", assistant_transcript)

                    # Response complete
                    elif event.type == "response.done":
                        logger.debug("Response complete")
                        if response_count == 0:
                            logger.warning("No audio response received")
                            yield self._generate_silence(100)
                        break

                    # Errors
                    elif event.type == "error":
                        logger.error("API error: %s", event)

        except Exception as e:
            logger.error("Realtime API error: %s: %s", type(e).__name__, str(e))
            import traceback
            traceback.print_exc()
            yield self._generate_silence(100)
            return "", ""

        return user_transcript, assistant_transcript
