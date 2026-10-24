# The Flanders agent skill

The canonical skill definition lives at
[`.agents/skills/flanders/SKILL.md`](../.agents/skills/flanders/SKILL.md), where
agent harnesses can discover it. This page is a pointer so the two copies cannot
drift apart:

- **Persona and phrasing** — that file.
- **The command tree** — `flanders/voice_integration.py`.
- **How the voice is chosen** — `flanders/voice_integration.py` and
  `voice_settings.json`.
- **How firstmate calls it** — `flanders/flanders_say.py`, documented in the
  project `README.md`.
