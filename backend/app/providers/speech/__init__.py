"""Speech providers package."""

from backend.app.providers.speech.base import SpeechProvider, SpeechSpec, SpeechResult
from backend.app.providers.speech.mock import MockSpeechProvider
from backend.app.providers.speech.piper import PiperSpeechProvider

__all__ = [
    "SpeechProvider",
    "SpeechSpec",
    "SpeechResult",
    "MockSpeechProvider",
    "PiperSpeechProvider",
]