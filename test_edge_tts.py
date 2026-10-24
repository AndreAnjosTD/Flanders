#!/usr/bin/env python3
"""Test Edge-TTS voices"""
import edge_tts
import asyncio

async def test_voices():
    voices = await edge_tts.list_voices()
    print(f'Total Edge-TTS voices: {len(voices)}')
    # Show first 15 with available keys
    for i, voice in enumerate(voices[:15]):
        sn = voice.get('ShortName', 'N/A')
        g = voice.get('Gender', 'N/A')
        # VoiceAge may not exist
        va = voice.get('VoiceAge', 'N/A')
        print(f'{i}: {sn} - {g} - {va}')

asyncio.run(test_voices())