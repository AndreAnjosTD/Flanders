"""Flanders - a Ned Flanders-voiced task assistant.

Modules:

    settings            the one reader for voice_settings.json
    voice_integration   engine selection and the /flanders command tree
    fish_audio_tts      hosted Fish Audio voice
    flanders_local_tts  offline Fish Speech voice
    flanders_audio      playback with an explicit device
    flanders_speech     turns Slack text into speakable prose
    flanders_character  personality and task classification
    secret_store        Windows Credential Manager access, never a file
    slack_bridge        reads and posts to the Slack channel
    flanders_service    Windows service that owns the listener
    flanders_speaker    in-session speaker the service drives
    flanders_say        command-line bridge used by firstmate
"""

__version__ = "1.1.0"
