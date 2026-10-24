#!/usr/bin/env python3
"""
Flanders <-> Slack bridge.

Flanders becomes your local mouth and ears for the firstmate Slack channel:
you talk to him here, he posts to #firstmate, and he reads or speaks back
whatever arrives there. This file is additive - it imports Flanders' existing
voice engine and changes none of it.

Usage:
    py slack_bridge.py say <text> [--plain]
        Post text to the channel in Flanders' voice. --plain skips the
        persona flavour and sends exactly what you typed.

    py slack_bridge.py read [--limit N] [--speak]
        Print the most recent messages; --speak reads them in Flanders' voice.

    py slack_bridge.py watch [--speak] [--interval SECONDS] [--headless]
        Announce new messages as they arrive, optionally aloud. Without
        --headless it also sends anything you type at the prompt; with
        --headless it only listens, which is what the background supervisor runs.

    py slack_bridge.py help
        This text.

Configuration:
    Slack credentials are read from the firstmate home's config/slack.env, so
    there is exactly one copy of the tokens. Resolution order:

        1. --config <path>
        2. $FM_HOME/config/slack.env
        3. ../firstmate/config/slack.env beside this folder

    The bot token needs chat:write to post and groups:history to read a private
    channel. Nothing here stores, prints, or transmits the token anywhere except
    to Slack itself.

Safety:
    Read and send only. No merge, approval, deletion, or other mutating action
    exists in this bridge.
"""

import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import redirect_stderr
from datetime import datetime
from io import StringIO
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flanders import flanders_speech

HERE = Path(__file__).resolve().parent.parent
API_BASE = "https://slack.com/api"
USER_AGENT = "flanders-slack-bridge/1.0"
_print_lock = threading.Lock()


# ---- configuration -------------------------------------------------------


def resolve_config_path(explicit=None):
    if explicit:
        return Path(explicit).expanduser()
    home = Path.home()
    env_home = __import__("os").environ.get("FM_HOME")
    if env_home:
        return Path(env_home).expanduser() / "config" / "slack.env"
    return HERE.parent / "firstmate" / "config" / "slack.env"


def parse_env_file(path):
    values = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_config(explicit=None):
    path = resolve_config_path(explicit)
    if not path.is_file():
        fail(f"I can't find the Slack settings at {path}.\n"
             "Point me at them with --config <path> or set FM_HOME.")
    values = parse_env_file(path)
    bot = values.get("SLACK_BOT_TOKEN", "")
    channel = values.get("SLACK_CHANNEL_ID", "")
    if not bot.startswith("xoxb-"):
        fail(f"{path} has no usable bot token.")
    if not channel.startswith("C"):
        fail(f"{path} has no usable channel id.")
    return {
        "bot_token": bot,
        "channel": channel,
        "owner": values.get("SLACK_OWNER_USER_ID", ""),
        "watchdog": values.get("SLACK_WATCHDOG_URL", ""),
        "path": path,
    }


def fail(message, code=1):
    sys.stderr.write(f"Flanders: {message}\n")
    raise SystemExit(code)


# ---- slack api -----------------------------------------------------------


def call_api(method, payload, token):
    """Call one Slack method with form-encoded parameters.

    Form encoding is used for every method because several read methods ignore
    a JSON body and then report the parameter as missing.
    """
    body = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{API_BASE}/{method}",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as error:
        fail(f"Slack is unreachable right now ({error.reason}).", 2)
    except json.JSONDecodeError:
        fail("Slack answered with something I could not read.", 2)

    if not result.get("ok"):
        error = result.get("error", "unknown_error")
        if error == "missing_scope":
            needed = result.get("needed", "")
            detail = f": {needed}" if needed else ""
            fail(f"The Slack app is missing a scope it needs{detail}.", 2)
        if error == "not_in_channel":
            fail("The bot is not in #firstmate. Invite it in the channel.", 2)
        fail(f"Slack refused that: {error}.", 2)
    return result


def post_message(config, text, plain=False):
    # The Slack app itself is named flanders, so every message here is already
    # attributed to him; a per-message label would only add noise.
    body = text if plain else flavor(text)
    result = call_api(
        "chat.postMessage",
        {
            "channel": config["channel"],
            "text": body,
            "unfurl_links": "false",
        },
        config["bot_token"],
    )
    return result.get("ts", "")


def fetch_messages(config, limit=10, oldest=None):
    payload = {"channel": config["channel"], "limit": str(limit)}
    if oldest:
        payload["oldest"] = oldest
        payload["inclusive"] = "false"
    result = call_api("conversations.history", payload, config["bot_token"])
    messages = result.get("messages", [])
    return list(reversed(messages))


# ---- flanders voice -----------------------------------------------------


# Ned Flanders' speech, in the pieces that carry the character without
# mangling the meaning: a greeting interjection, the odd "neighborino", and a
# closing exclamation. The captain's own words are never reworded, only framed.
OPENERS_GOOD = ("Okily dokily!", "Hi-diddly-ho!", "Howdily-doodily!")
OPENERS_BAD = ("Aw, hamburgers!", "Son of a diddly!", "Good gravy!")
ALREADY_OPEN = re.compile(
    r"^(okily|hi-diddly|howdily|praise the lord|aw, hamburgers|son of a diddly|good gravy|well, shucks|much obliged)",
    re.IGNORECASE,
)
GOOD_NEWS = ("ready", "works", "working", "done", "green", "passed", "landed", "fixed", "connected")
BAD_NEWS = ("failed", "broken", "broke", "error", "stopped", "stuck", "blocked", "refused", "expired")
NEIGHBOR = re.compile(r"\b(captain|neighbor|neighbour)\b", re.IGNORECASE)


def flavor(text):
    """Frame a message in Flanders' voice without changing what it says."""
    body = " ".join(text.split()).strip()
    if not body:
        return body

    lowered = body.lower()
    good = any(word in lowered for word in GOOD_NEWS)
    bad = any(word in lowered for word in BAD_NEWS)
    if bad:
        opener = OPENERS_BAD[0]
    elif good:
        opener = OPENERS_GOOD[0]
    else:
        opener = OPENERS_GOOD[1]

    if ALREADY_OPEN.match(body):
        opener = ""

    body = body[0].upper() + body[1:]
    if not body.endswith((".", "!", "?")):
        body += "!"

    parts = [part for part in (opener, body) if part]
    if not bad and not NEIGHBOR.search(body) and len(body) < 80:
        parts.append("Much obliged, neighborino!")
    return " ".join(parts)


_voice = None
_speak_lock = threading.Lock()


def speak(text):
    """Speak text aloud through Flanders' own voice.

    Prefers the tuned hosted/local voice in voice_integration, and keeps the
    Windows SAPI voice only as a last resort. Audio failures never break the
    bridge.
    """
    global _voice
    cleaned = " ".join(text.split())
    if not cleaned:
        return

    try:
        from flanders.voice_integration import FlandersVoice

        with _speak_lock:
            if _voice is None:
                _voice = FlandersVoice()
            used = _voice.speak(cleaned)
        if used in ("failed", "nothing"):
            raise RuntimeError(f"voice engine {used}")
        return
    except Exception as error:  # audio must never break the bridge
        with _print_lock:
            print(f"  (Flanders voice unavailable: {error})", flush=True)

    try:
        import pyttsx3

        with _speak_lock:
            engine = pyttsx3.init()
            engine.setProperty("rate", 155)
            engine.setProperty("volume", 0.95)
            engine.say(cleaned)
            engine.runAndWait()
    except Exception as error:  # audio must never break the bridge
        with _print_lock:
            print(f"  (voice unavailable: {error})", flush=True)


# ---- formatting ---------------------------------------------------------


_SLACK_ID = re.compile(r"^[UWB][A-Z0-9]{6,}$")
NAME_CACHE_PATH = HERE / "state" / "user-names.json"
_name_cache = None
_users_scope_missing = False


def is_slack_id(value) -> bool:
    return bool(value and _SLACK_ID.match(str(value)))


def _name_cache_load() -> dict:
    global _name_cache
    if _name_cache is None:
        try:
            _name_cache = json.loads(NAME_CACHE_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _name_cache = {}
    return _name_cache


def _name_cache_save() -> None:
    try:
        NAME_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        NAME_CACHE_PATH.write_text(
            json.dumps(_name_cache or {}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def resolve_user_name(config, user_id) -> str:
    """Turn a Slack user id into something worth saying out loud.

    Names are cached on disk so a user is looked up once, not on every message.
    Without the users:read scope Slack refuses the lookup; the caller then falls
    back to a neutral phrase rather than reading an id aloud.
    """
    global _users_scope_missing
    if not user_id:
        return ""

    cache = _name_cache_load()
    if cache.get(user_id):
        return cache[user_id]

    # Ask Slack for the real profile first, so the spoken name is the person's
    # own. The lookup is quiet: a missing scope is expected, not an error.
    if not _users_scope_missing:
        try:
            with redirect_stderr(StringIO()):
                result = call_api("users.info", {"user": user_id}, config["bot_token"])
        except SystemExit:
            _users_scope_missing = True
        else:
            user = result.get("user") or {}
            profile = user.get("profile") or {}
            name = (
                profile.get("display_name")
                or profile.get("real_name")
                or user.get("real_name")
                or user.get("name")
                or ""
            ).strip()
            if name:
                cache[user_id] = name
                _name_cache_save()
                return name

    owner = config.get("owner") or ""
    if owner and user_id == owner:
        return "the captain"
    return ""


def resolve_names(config, messages):
    """Attach a readable name to each message, in place."""
    for message in messages:
        user = message.get("user")
        if message.get("username") or not user:
            continue
        resolved = resolve_user_name(config, user)
        if resolved:
            message["username"] = resolved
    return messages


def who(message):
    profile = message.get("user_profile") or {}
    for candidate in (
        message.get("username"),
        profile.get("display_name"),
        profile.get("real_name"),
    ):
        if candidate:
            return candidate
    bot_profile = message.get("bot_profile") or {}
    if bot_profile.get("name"):
        return bot_profile["name"]
    if message.get("bot_id"):
        return "bot"
    user = message.get("user") or ""
    # Slack only sends a profile when it has one to hand; a bare "U0CB9HSSHJR"
    # is not something anyone wants read aloud.
    if _SLACK_ID.match(user):
        return "a teammate"
    return user or "unknown"


def stamp(message):
    try:
        return datetime.fromtimestamp(float(message.get("ts", "0"))).strftime("%H:%M")
    except (TypeError, ValueError):
        return "--:--"


def body_text(message):
    text = (message.get("text") or "").replace("\n", " ").strip()
    if not text and message.get("attachments"):
        text = " (attachment)"
    if not text and message.get("blocks"):
        text = " (rich message)"
    return text[:500]


def render(message):
    return f"{stamp(message)}  {who(message)}: {body_text(message)}"


def emit(line, say_it=False, speech=None):
    with _print_lock:
        print(line, flush=True)
    if say_it:
        speak(speech if speech is not None else line)


# ---- commands -----------------------------------------------------------


def cmd_say(config, argv):
    plain = "--plain" in argv
    words = [item for item in argv if not item.startswith("--")]
    if not words:
        fail('tell me what to say, for example: py slack_bridge.py say "staging is green"')
    text = " ".join(words)
    ts = post_message(config, text, plain=plain)
    print(f"sent to #firstmate ({ts})")


def cmd_read(config, argv):
    limit = 10
    say_it = "--speak" in argv
    if "--limit" in argv:
        index = argv.index("--limit")
        try:
            limit = max(1, int(argv[index + 1]))
        except (IndexError, ValueError):
            fail("--limit needs a number.")
    messages = fetch_messages(config, limit=limit)
    if not messages:
        print("Nothing in the channel yet.")
        return
    for message in messages:
        if message.get("subtype") in ("message_changed", "message_deleted"):
            continue
        emit(render(message), say_it=say_it)


def _heartbeat(text=""):
    try:
        path = HERE / "state" / "slack-watch.heartbeat"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{datetime.now().isoformat(timespec='seconds')} {text}\n", encoding="utf-8")
    except OSError:
        pass


def _ping(watchdog):
    if not watchdog:
        return
    try:
        with urllib.request.urlopen(watchdog, timeout=10) as response:
            response.read(64)
    except Exception:  # a watchdog ping must never stop the listener
        pass


def _speech_for(message):
    """What Flanders says out loud: cleaned, noise-filtered, never raw markup."""
    body = flanders_speech.speakable(body_text(message))
    if not body:
        return ""
    return f"New message from {who(message)}. {body}"


def cmd_watch(config, argv):
    say_it = "--speak" in argv
    headless = "--headless" in argv
    interval = 5.0
    if "--interval" in argv:
        index = argv.index("--interval")
        try:
            interval = max(1.0, float(argv[index + 1]))
        except (IndexError, ValueError):
            fail("--interval needs a number of seconds.")

    recent = fetch_messages(config, limit=1)
    last_seen = recent[-1].get("ts") if recent else "0"
    if not last_seen:
        last_seen = "0"

    # Everything in #firstmate is posted by this same bot app, including
    # firstmate's own notifications, so no self-filter here: filtering would
    # silence the whole channel.
    last_ping = 0.0

    def poll_once():
        nonlocal last_seen, last_ping
        messages = fetch_messages(config, limit=20, oldest=last_seen)
        resolve_names(config, messages)
        for message in messages:
            last_seen = message.get("ts", last_seen)
            if message.get("subtype") in ("message_changed", "message_deleted"):
                continue
            emit(render(message), say_it=say_it, speech=_speech_for(message))
        if config.get("watchdog") and time.monotonic() - last_ping > 60:
            _ping(config["watchdog"])
            last_ping = time.monotonic()
        _heartbeat("ok")

    if headless:
        print(
            f"watching #firstmate every {interval:g}s (headless, speak={say_it})",
            flush=True,
        )
        _heartbeat("starting")
        try:
            while True:
                try:
                    poll_once()
                except SystemExit:
                    raise
                except Exception as error:
                    with _print_lock:
                        print(f"  (poll failed: {error})", flush=True)
                    _heartbeat(f"poll failed: {error}")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nleft the channel. Okily dokily!", flush=True)
        return

    print(f"watching #firstmate every {interval:g}s - type to send, /quit to leave")
    stop = threading.Event()

    def poll():
        while not stop.is_set():
            time.sleep(interval)
            try:
                poll_once()
            except SystemExit:
                stop.set()
            except Exception as error:
                with _print_lock:
                    print(f"  (poll failed: {error})", flush=True)

    worker = threading.Thread(target=poll, daemon=True)
    worker.start()

    try:
        while True:
            try:
                typed = input("flanders> ").strip()
            except EOFError:
                break
            if not typed:
                continue
            if typed.lower() in ("/quit", "/exit", "q"):
                break
            if typed.startswith("/say "):
                typed = typed[len("/say "):]
            post_message(config, typed)
            with _print_lock:
                print("  sent", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        print("\nleft the channel. Okily dokily!")


def cmd_help():
    print(__doc__.strip())


def main(argv):
    if not argv or argv[0] in ("help", "--help", "-h"):
        cmd_help()
        return
    command, rest = argv[0], argv[1:]
    config_path = None
    if "--config" in rest:
        index = rest.index("--config")
        try:
            config_path = rest[index + 1]
        except IndexError:
            fail("--config needs a path.")
        rest = rest[:index] + rest[index + 2:]

    handlers = {"say": cmd_say, "read": cmd_read, "watch": cmd_watch}
    handler = handlers.get(command)
    if not handler:
        fail(f"I don't know '{command}'. Try: say, read, watch, help.")
    config = load_config(config_path)
    handler(config, rest)


if __name__ == "__main__":
    main(sys.argv[1:])
