#!/usr/bin/env python3
"""Test Flanders TTS with Edge-TTS voices"""
import edge_tts
import asyncio

# Flanders phrases to test
flanders_phrases = [
    "Okily dokily Welcome to Flanders task delegation",
    "Praise the Lord Let me help you with your task",
    "Hi diddly ho investorino I am your faithful delegate",
    "Okily dokily I have noted your task and will help you delegate it properly"
]

# Test voices - pick some good ones for Flanders
test_voices = [
    "en-US-AvaNeural",     # Female, standard
    "en-US-AndrewNeural",  # Male, standard
    "en-GB-LibbyNeural",   # British female
    "en-IE-ConnorNeural",  # Irish male
]

async def test_voice(voice_id, phrase_idx=0):
    """Test a specific voice with a Flanders phrase"""
    try:
        communicate = edge_tts.Communicate(
            flanders_phrases[phrase_idx % len(flanders_phrases)],
            voice_id
        )
        # Save to file so we can play it
        output_file = f"flanders_{voice_id.replace('/', '_')}.mp3"
        communicate.save(output_file)
        return (voice_id, output_file, True)
    except Exception as e:
        return (voice_id, str(e), False)

async def main():
    print("Flanders TTS Voice Test - Edge-TTS")
    print("Testing voices with Flanders phrases")
    print()
    
    results = []
    for i, voice_id in enumerate(test_voices):
        print(f"Testing {voice_id}...")
        result = await test_voice(voice_id)
        results.append(result)
        voice_id_short = voice_id.split('.')[-1] if '.' in voice_id else voice_id
        print(f"  Saved: {result[1]} - Success: {result[2]}")
        print()
    
    print("=" * 50)
    print(f"Results: {sum(1 for r in results if r[2])}/{len(results)} voices successful")
    print("=" * 50)
    
    # List successful files
    for r in results:
        if r[2]:
            print(f"  Audio file: {r[1]}")

asyncio.run(main())