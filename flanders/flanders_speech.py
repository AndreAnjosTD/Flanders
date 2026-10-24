#!/usr/bin/env python3
r"""Turn a Slack message into something worth hearing.

Slack text is written for eyes: emoji shortcodes, bold markers, HTML-escaped
angle brackets, backticks, and link syntax. Read aloud verbatim, Flanders says
"colon wave colon" and "ampersand g t semicolon".

This module keeps the meaning and drops the decoration.

Usage:
    .\.venv\Scripts\python.exe flanders_speech.py --preview
    .\.venv\Scripts\python.exe flanders_speech.py "raw message text"
"""

from __future__ import annotations

import argparse
import html
import re
import sys

# Icons that carry meaning in this channel are spoken as a short word. Icons
# that are pure decoration are dropped, because hearing "wave" adds nothing.
EMOJI_WORDS = {
    "white_check_mark": "Done.",
    "heavy_check_mark": "Done.",
    "ballot_box_with_check": "Done.",
    "x": "Not done.",
    "negative_squared_cross_mark": "Not done.",
    "warning": "Warning.",
    "rotating_light": "Alert.",
    "red_circle": "Blocked.",
    "large_green_circle": "Green.",
    "green_circle": "Green.",
    "bulb": "Idea.",
    "speech_balloon": "",
    "question": "",
    "grey_question": "",
    "stopwatch": "",
    "hourglass": "",
    "hourglass_flowing_sand": "",
    "wave": "",
    "mailbox_with_mail": "",
    "writing_hand": "",
    "point_right": "",
    "arrow_right": "",
    "arrow_forward": "",
    "tada": "",
    "sparkles": "",
    "rocket": "",
    "fire": "",
    "memo": "",
    "pushpin": "",
    "link": "",
    "heavy_plus_sign": "",
}

_ENTITY = re.compile(r"<([^>]+)>")
_LINK_LABEL = re.compile(r"^https?://[^|]+\|(.+)$")
_LINK_BARE = re.compile(r"^https?://")
_USER_LABEL = re.compile(r"^@[^|]+\|(.+)$")
_USER_BARE = re.compile(r"^@")
_CHANNEL_LABEL = re.compile(r"^#[^|]+\|(.+)$")
_BROADCAST = re.compile(r"^!(here|channel|everyone)$")

_EMOJI_CODE = re.compile(r":([a-z0-9_+\-]+):")
# Emoji, dingbats, arrows, variation selectors and joiners.
_EMOJI_CHAR = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U0001F000-\U0001F2FF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\u2190-\u21FF"
    "\u2B00-\u2BFF"
    "\uFE0F\u200D\u20E3"
    "]+"
)

_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_MARKUP = re.compile(r"[*_~]")
_BLOCKQUOTE = re.compile(r"^\s*>\s?", re.MULTILINE)
_QUOTE_INLINE = re.compile(r"\s*>\s*")
_ARROW = re.compile(r"\s*-+>+\s*")
_PUNCT_COLON = re.compile(r"([.!?])\s*:\s*")
_LIST_MARKER = re.compile(r"^\s*(?:\d+\.|[-•*])\s+", re.MULTILINE)
_INLINE_LIST = re.compile(r"\s+\d+\.\s+")
_DASHES = re.compile(r"[\u2013\u2014]")

_UNIT = re.compile(r"(?<![\w.])(\d+)\s*(m|h|s|d)\b")
_UNIT_WORD = {"m": "minute", "h": "hour", "s": "second", "d": "day"}

_REPEAT_PUNCT = re.compile(r"([!?.,])\1{1,}")
_EMPTY_PAIRS = re.compile(r"[\(\[\{]\s*[\)\]\}]")
_OPEN_SPACE = re.compile(r"\(\s+")
_CLOSE_SPACE = re.compile(r"\s+\)")
_LEAD_JUNK = re.compile(r"^[\s\-–—,.;:|]+")
_SPACES = re.compile(r"[ \t\u00A0]+")
_BLANK_LINES = re.compile(r"\n{2,}")

# Sentences that are really command help, not something worth hearing.
_COMMAND_START = re.compile(r"^\s*`?/(?:flanders?|fm-[a-z-]+)\b", re.IGNORECASE)
_REPLY_HELP = re.compile(r"\s*Reply with\b[^.]*\.?", re.IGNORECASE)
_RUN_HELP = re.compile(
    r"\s*(?:Run|Use|Type)\b[^.]*?/(?:flanders?|fm-[a-z-]+)[^.]*\.?",
    re.IGNORECASE,
)
_BARE_COMMAND = re.compile(
    r"\s*[\(\[]?\s*/(?:flanders?|fm-[a-z-]+)[^.)\]]*[\)\]]?\.?",
    re.IGNORECASE,
)
# "(1 minute)" style metadata left behind after a clause is removed.
_DURATION_PAREN = re.compile(
    r"\(\s*\d+\s*(?:minute|hour|second|day)s?\s*\)", re.IGNORECASE
)

# Short, content-free replies. Anything with real words in it is not an
# acknowledgement and still gets spoken.
_ACK_PHRASES = {
    "ok", "okay", "k", "kk", "thanks", "thank you", "thx", "ty", "cheers",
    "nice", "cool", "great", "awesome", "perfect", "alright", "got it",
    "sounds good", "good", "np", "no problem", "all good", "lol", "haha",
    "yes", "yeah", "yep", "yup", "no", "nope", "sure", "amazing", "brilliant",
    "good job", "well done", "nice one", "much obliged", "okily dokily",
}
_ACK_WORDS = {
    "ok", "okay", "k", "kk", "thanks", "thank", "thx", "ty", "cheers", "nice",
    "cool", "great", "awesome", "perfect", "alright", "good", "np", "lol",
    "haha", "yes", "yeah", "yep", "yup", "no", "nope", "sure", "amazing",
    "brilliant", "captain", "flanders", "neighborino", "sir",
}
_PUNCT_ONLY = re.compile(r"[^\w\s']")


def _drop_command_help(text: str) -> str:
    """Remove instructions for typing a command, keep the sentence around them."""
    if _COMMAND_START.match(text):
        return ""

    cleaned = _REPLY_HELP.sub(" ", text)
    cleaned = _RUN_HELP.sub(" ", cleaned)
    cleaned = _BARE_COMMAND.sub(" ", cleaned)
    cleaned = _DURATION_PAREN.sub(" ", cleaned)
    cleaned = _SPACES.sub(" ", cleaned)
    cleaned = cleaned.strip()
    cleaned = _LEAD_JUNK.sub("", cleaned)
    return cleaned


def _is_acknowledgement(text: str) -> bool:
    normalised = _PUNCT_ONLY.sub("", text.lower())
    normalised = " ".join(normalised.split())
    if not normalised:
        return True
    if normalised in _ACK_PHRASES:
        return True
    words = normalised.split()
    return len(words) <= 4 and all(word in _ACK_WORDS for word in words)


def speakable(text: str, limit: int = 600) -> str:
    """Full pipeline: clean the text, drop noise, then cap the length.

    Returns an empty string when the message is not worth saying out loud.
    """
    cleaned = to_speech(text, limit=None)
    cleaned = _drop_command_help(cleaned)
    cleaned = " ".join(cleaned.split())
    if not cleaned or _is_acknowledgement(cleaned):
        return ""
    if len(cleaned) > limit:
        cut = cleaned[:limit].rsplit(" ", 1)[0]
        cleaned = f"{cut}. And more."
    return cleaned


def _unit(match: re.Match) -> str:
    number = int(match.group(1))
    word = _UNIT_WORD[match.group(2)]
    plural = "" if number == 1 else "s"
    return f"{number} {word}{plural}"


def _slack_entity(match: re.Match) -> str:
    """Decode one <...> Slack token into words."""
    token = match.group(1)

    label = _LINK_LABEL.match(token)
    if label:
        return label.group(1)
    if _LINK_BARE.match(token):
        return "a link"

    label = _USER_LABEL.match(token)
    if label:
        return label.group(1)
    if _USER_BARE.match(token):
        return "someone"

    label = _CHANNEL_LABEL.match(token)
    if label:
        return f"{label.group(1)} channel"
    if token.startswith("#"):
        return "a channel"

    if _BROADCAST.match(token):
        return "everyone"

    # Unknown token: treat the words inside as literal text (e.g. <number>).
    if token:
        return token.strip("<>")
    return ""


def to_speech(text: str, limit: int | None = 600) -> str:
    """Return the spoken form of a Slack message."""
    if not text:
        return ""

    spoken = html.unescape(text)

    spoken = _ENTITY.sub(_slack_entity, spoken)

    def emoji_word(match: re.Match) -> str:
        name = match.group(1).lower()
        if name.startswith("skin-tone"):
            return ""
        return EMOJI_WORDS.get(name, "")

    spoken = _EMOJI_CODE.sub(emoji_word, spoken)
    spoken = _EMOJI_CHAR.sub("", spoken)

    spoken = _CODE_FENCE.sub(" a code block ", spoken)
    spoken = _INLINE_CODE.sub(lambda m: m.group(1), spoken)
    spoken = spoken.replace("`", "")

    spoken = _BLOCKQUOTE.sub("", spoken)
    spoken = _ARROW.sub(" to ", spoken)
    spoken = _QUOTE_INLINE.sub(": ", spoken)
    spoken = _PUNCT_COLON.sub(r"\1 ", spoken)
    spoken = _LIST_MARKER.sub("", spoken)
    spoken = _INLINE_LIST.sub(" ", spoken)
    spoken = _MARKUP.sub("", spoken)
    spoken = _DASHES.sub(", ", spoken)

    spoken = _UNIT.sub(_unit, spoken)

    spoken = _REPEAT_PUNCT.sub(r"\1", spoken)
    spoken = _EMPTY_PAIRS.sub("", spoken)
    spoken = _OPEN_SPACE.sub("(", spoken)
    spoken = _CLOSE_SPACE.sub(")", spoken)
    spoken = _SPACES.sub(" ", spoken)
    spoken = _BLANK_LINES.sub("\n", spoken)

    # Join wrapped lines into one sentence-ish stream.
    spoken = " ".join(part.strip() for part in spoken.splitlines() if part.strip())

    spoken = spoken.strip()
    spoken = _LEAD_JUNK.sub("", spoken)
    if limit is not None and len(spoken) > limit:
        cut = spoken[:limit].rsplit(" ", 1)[0]
        spoken = f"{cut}. And more."
    return spoken


def preview(limit: int) -> int:
    from flanders import slack_bridge

    config = slack_bridge.load_config()
    messages = slack_bridge.fetch_messages(config, limit=limit)
    for message in messages:
        if message.get("subtype") in ("message_changed", "message_deleted"):
            continue
        raw = slack_bridge.body_text(message)
        print("\n--- raw ---")
        print(raw)
        print("--- spoken ---")
        result = speakable(raw)
        print(result if result else "(skipped: acknowledgement or command help)")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Make Slack text speakable.")
    parser.add_argument("text", nargs="*", help="text to convert")
    parser.add_argument("--preview", action="store_true", help="show recent channel messages")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--raw-form", action="store_true",
        help="show the cleaned text before noise filtering",
    )
    args = parser.parse_args(argv)

    if args.preview:
        return preview(args.limit)
    if args.text:
        joined = " ".join(args.text)
        print(to_speech(joined) if args.raw_form else speakable(joined))
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
