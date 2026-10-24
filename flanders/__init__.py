"""Flanders - a Ned Flanders-voiced task assistant.

Modules:

    voice_integration   engine selection and the /flanders command tree
    fish_audio_tts      hosted Fish Audio voice
    flanders_local_tts  offline Fish Speech voice
    flanders_audio      playback with an explicit device
    flanders_speech     turns Slack text into speakable prose
    flanders_character  personality and task classification
    slack_bridge        reads and posts to the Slack channel
    flanders_service    Windows service that owns the listener
    flanders_speaker    in-session speaker the service drives
    flanders_say        command-line bridge used by firstmate
"""

__version__ = "1.0.0"
