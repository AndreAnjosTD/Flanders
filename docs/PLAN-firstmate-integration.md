# Plan: Firstmate Project "flanders" with Voice Integration

## Overview
Create a Firstmate project called "flanders" that integrates with the existing Flanders Python trading bot at C:\Users\abanj\Dev\Flanders\, and adds voice capabilities so the captain can talk to Flanders.

## Current State
- **Existing Flanders project**: C:\Users\abanj\Dev\Flanders\ - Python trading bot with:
  - Core trading engine (Alpaca/yfinance)
  - Database (PostgreSQL)
  - PyQt6 GUI dashboard
  - Flanders personality system (landers_personality.py)
  - API routes for trading operations
- **Firstmate Flanders skill**: C:\Users\abanj\Dev\firstmate\skills\flanders\SKILL.md - Task delegate skill with "Okily dokily!" phrasing
- **Firstmate repo**: C:\Users\abanj\Dev\firstmate\ - The supervisor framework

## Best Solution: Integrated Firstmate Project

Create a Firstmate project at C:\Users\abanj\Dev\firstmate\projects\flanders\ that:
1. References and integrates with the existing Flanders Python project
2. Moves the Flanders skill into the project structure
3. Adds voice integration libraries
4. Provides captain-Flanders voice interaction

## Project Structure

`
C:\Users\abanj\Dev\firstmate\projects\flanders\
├── AGENTS.md                  # Project-specific AGENTS.md
├── README.md                  # Project documentation
├── config.py                  # Project configuration
├── briefs/                    # Task briefs directory
│   └── fleece/               # Example briefs
├── data/                      # Project data records
├── skills/                    # Skills included in this project
│   └── flanders/             # The Flanders skill (moved from skills\flanders\)
│       └── SKILL.md
├── voice/                     # Voice integration directory
│   ├── recognition.py         # Speech recognition (speech_recognition library)
│   ├── synthesis.py           # Text-to-speech with Flanders personality
│   └── fd.py                 # Flanders voice definitions
├── integration/               # Integration with existing Flanders project
│   ├── pointer.py            # Pointer to C:\Users\abanj\Dev\Flanders\
│   └── bridge.py             # Bridge between Firstmate and Flanders bot
└── tasks/                     # Task tracking
    └── backlog.md            # Task backlog
`

## Voice Integration Design

### Libraries to Use
1. **speech_recognition** - For listening to captain's voice commands
2. **pyttsx3** - For text-to-speech output (offline, no internet needed)
3. **Custom Flanders voice** - Personality-layered responses

### Voice Flow
1. **Captain speaks**: speech_recognition captures audio → text
2. **Firstmate processes**: Interprets the task/ask
3. **Flanders responds**: pyttsx3 with Flanders personality filters
4. **Flanders actions**: May trigger Flanders bot operations

### Flanders Voice Personality
- "Okily dokily!" responses
- Religious-friendly tone ("Praise the Lord!")
- "Hi-diddly-ho, investorino!" greetings
- "Aw, hamburgers!" for errors
- Neighborino-style phrasing

## Skill Migration

Move C:\Users\abanj\Dev\firstmate\skills\flanders\SKILL.md to:
C:\Users\abanj\Dev\firstmate\projects\flanders\skills\flanders\SKILL.md

Updated skill to work within project context, referencing the Flanders bot and voice capabilities.

## Integration Bridge

Create integration/bridge.py that:
1. Listens for Firstmate task delegation events
2. Triggers Flanders bot operations as needed
3. Routes voice input to Flanders personality
4. Returns Flanders-style responses to captain

## Implementation Phases

### Phase 1: Project Scaffold
- [ ] Create C:\Users\abanj\Dev\firstmate\projects\flanders\ directory
- [ ] Write AGENTS.md, README.md, config.py
- [ ] Move Flanders skill into project structure
- [ ] Set up riefs/, data/, 	asks/ directories

### Phase 2: Voice Integration
- [ ] Install speech_recognition library
- [ ] Create oice/recognition.py - microphone capture
- [ ] Create oice/synthesis.py - TTS with Flanders filters
- [ ] Define Flanders voice phrases and responses

### Phase 3: Integration
- [ ] Create integration/pointer.py - Link to existing Flanders project
- [ ] Create integration/bridge.py - Event routing
- [ ] Test voice-Flanders interaction cycle

### Phase 4: Testing
- [ ] Voice command recognition tests
- [ ] Flanders personality response tests
- [ ] Integration with Flanders bot operations
- [ ] Captain-Flanders conversational flow

## Voice Library Choices

### Primary: speech_recognition
- Cross-platform (Windows, macOS, Linux)
- Supports microphone input
- Easy integration with Python
- Falls back to Sphinx (offline) or Google Web Speech API

### Secondary: pyttsx3
- Offline text-to-speech
- No internet dependency
- Supports voice properties (rate, volume, voice selection)
- Can apply Flanders personality filters to output

### Alternative: gTTS (Google Text-to-Speech)
- Online, higher quality
- Requires internet connection
- Could be used for initial implementation

## Safety & Compliance

Per AGENTS.md hard rules:
- **Never write to projects without captain approval** - This plan requires explicit approval
- **Project files remain gitignored** - projects/ directory is captain-private
- **Skill migration follows proper channels** - Skill moves only with captain's concrete approval
- **Voice data handling** - Audio captured stays within project scope

## Captain's Role

The captain will:
1. Approve the project creation at C:\Users\abanj\Dev\firstmate\projects\flanders\
2. Provide explicit approval for skill migration from skills\flanders\ to projects\flanders\skills\flanders\
3. Define voice interaction boundaries and preferences
4. Authorize any integration with the existing Flanders bot

## Next Steps

1. Present this plan to the captain for approval
2. Upon approval, implement Phase 1: Project scaffold
3. Proceed through phases iteratively
4. Test voice integration at each step

---
*Plan created for Firstmate "flanders" project integration with existing Flanders trading bot and voice capabilities.*
