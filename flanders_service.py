#!/usr/bin/env python3
r"""Flanders Slack Watch - a real Windows service.

Replaces the scheduled task + PowerShell supervisor. The service owns the Slack
connection and never draws a window: it polls #firstmate, and for every new
message it drops a small job file into state/speech/.

A Windows service cannot reach the speakers (it lives in session 0, which has no
audio endpoint), so the service starts a tiny companion process inside the
logged-on session - flanders_speaker.py - and keeps it alive. That companion
owns the voice.

Commands (run from an elevated prompt for install/uninstall):

    python flanders_service.py install
    python flanders_service.py uninstall
    python flanders_service.py start
    python flanders_service.py stop
    python flanders_service.py status
    python flanders_service.py run        # foreground, for debugging

The service runs as LocalSystem so it can reach the logged-on session.
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

# The Windows service is launched by the base interpreter, not the venv stub,
# so teach this process where the venv's packages live before importing them.
# A bare site-packages entry is not enough: pywin32 normally adds win32/lib and
# its DLL directory through a .pth file that only runs for the venv interpreter.
_VENV_SITE = Path(__file__).resolve().parent / ".venv" / "Lib" / "site-packages"
if _VENV_SITE.is_dir():
    if str(_VENV_SITE) not in sys.path:
        sys.path.insert(0, str(_VENV_SITE))
    for _sub in ("win32", "win32\\lib", "pythonwin"):
        _extra = _VENV_SITE / _sub
        if _extra.is_dir() and str(_extra) not in sys.path:
            sys.path.append(str(_extra))
    _dll_dir = _VENV_SITE / "pywin32_system32"
    if _dll_dir.is_dir():
        try:
            os.add_dll_directory(str(_dll_dir))
        except (AttributeError, OSError):
            pass
    try:
        import pywin32_bootstrap  # noqa: F401
    except ImportError:
        pass


def _boot(step: str) -> None:
    """Breadcrumb trail for diagnosing service startup."""
    try:
        target = Path(__file__).resolve().parent / "state"
        target.mkdir(parents=True, exist_ok=True)
        with (target / "service-boot.log").open("a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now().isoformat(timespec='seconds')} {step}\n")
    except OSError:
        pass


_boot("module start")

import win32con  # noqa: E402

_boot("win32con")

import win32process  # noqa: E402

_boot("win32process")

import win32service  # noqa: E402

_boot("win32service")

import win32serviceutil  # noqa: E402

_boot("win32serviceutil")

import win32ts  # noqa: E402

_boot("win32ts")

import servicemanager  # noqa: E402

_boot("servicemanager")

import slack_bridge  # noqa: E402

_boot("slack_bridge imported")

HERE = Path(__file__).resolve().parent
STATE = HERE / "state"
QUEUE = STATE / "speech"
SERVICE_LOG = STATE / "flanders-service.log"
SPEAKER_HEARTBEAT = STATE / "speaker.heartbeat"
SPEAKER_STOP = STATE / "speaker.stop"
SPEAKER_SCRIPT = HERE / "flanders_speaker.py"
PYTHONW = HERE / ".venv" / "Scripts" / "pythonw.exe"

SERVICE_NAME = "FlandersSlackWatch"
DISPLAY_NAME = "Flanders Slack Watch"
DESCRIPTION = (
    "Reads #firstmate and speaks new messages in the captain's session. "
    "Started automatically at boot and restarted on failure."
)
POLL_SECONDS = 5.0
SPEAKER_STALE_SECONDS = 60.0
SPEAKER_CHECK_SECONDS = 10.0


# ---- logging -------------------------------------------------------------


def log(text: str) -> None:
    line = f"{datetime.now().isoformat(timespec='seconds')} {text}"
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        with SERVICE_LOG.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass
    if "--run-service" not in sys.argv:
        print(line, flush=True)


# ---- speech queue --------------------------------------------------------


def enqueue(text: str) -> None:
    """Drop one speech job for the in-session speaker."""
    clean = " ".join((text or "").split())
    if not clean:
        return
    QUEUE.mkdir(parents=True, exist_ok=True)
    epoch = time.time()
    name = f"{int(epoch * 1000):013d}-{uuid.uuid4().hex[:8]}.job"
    payload = {"text": clean, "epoch": epoch, "queued": datetime.now().isoformat()}
    temp = QUEUE / (name + ".tmp")
    temp.write_text(json.dumps(payload), encoding="utf-8")
    temp.replace(QUEUE / name)


def speaker_is_alive() -> bool:
    try:
        age = time.time() - SPEAKER_HEARTBEAT.stat().st_mtime
    except OSError:
        return False
    return age < SPEAKER_STALE_SECONDS


# ---- launching the in-session speaker ------------------------------------


def launch_speaker() -> bool:
    """Start flanders_speaker.py inside the logged-on session."""
    session_id = win32ts.WTSGetActiveConsoleSessionId()
    if session_id in (0, 0xFFFFFFFF):
        log("no interactive session; cannot start the speaker yet")
        return False

    try:
        token = win32ts.WTSQueryUserToken(session_id)
    except Exception as exc:  # noqa: BLE001
        log(f"WTSQueryUserToken failed for session {session_id}: {exc}")
        return False

    try:
        exe = str(PYTHONW if PYTHONW.exists() else sys.executable)
        command = f'"{exe}" "{SPEAKER_SCRIPT}"'
        startup = win32process.STARTUPINFO()
        startup.lpDesktop = "winsta0\\default"
        win32process.CreateProcessAsUser(
            token,
            exe,
            command,
            None,
            None,
            0,
            win32con.CREATE_UNICODE_ENVIRONMENT,
            None,
            str(HERE),
            startup,
        )
        log(f"speaker launched in session {session_id}")
        return True
    except Exception as exc:  # noqa: BLE001
        log(f"CreateProcessAsUser failed: {exc}")
        return False


# ---- the work ------------------------------------------------------------


class Watcher:
    def __init__(self) -> None:
        self.stop_event = threading.Event()
        self.config = None
        self.last_seen = "0"

    def start(self) -> None:
        # A previous run leaves a heartbeat behind. Clear it, or the supervisor
        # believes a speaker is alive and waits a full minute before starting one.
        try:
            SPEAKER_HEARTBEAT.unlink(missing_ok=True)
            SPEAKER_STOP.unlink(missing_ok=True)
        except OSError:
            pass

        self.config = slack_bridge.load_config()
        recent = slack_bridge.fetch_messages(self.config, limit=1)
        self.last_seen = recent[-1].get("ts", "0") if recent else "0"
        log(f"watching channel {self.config['channel']} from ts {self.last_seen}")

    def poll_once(self) -> None:
        messages = slack_bridge.fetch_messages(
            self.config, limit=20, oldest=self.last_seen
        )
        # Resolve ids to names before anything is spoken or logged.
        slack_bridge.resolve_names(self.config, messages)
        for message in messages:
            self.last_seen = message.get("ts") or self.last_seen
            if message.get("subtype") in ("message_changed", "message_deleted"):
                continue
            speech = slack_bridge._speech_for(message)
            if not speech:
                continue
            enqueue(speech)
            log(f"queued: {speech[:90]}")

    def supervise_speaker(self) -> None:
        if not speaker_is_alive():
            launch_speaker()

    def run(self) -> None:
        try:
            self.start()
        except BaseException as exc:  # noqa: BLE001 - never let startup kill the service
            log(f"startup failed: {exc}")
            return

        last_check = 0.0
        while not self.stop_event.is_set():
            try:
                self.poll_once()
            except BaseException as exc:  # noqa: BLE001 - keep polling after any error
                log(f"poll failed: {exc}")

            now = time.monotonic()
            if now - last_check >= SPEAKER_CHECK_SECONDS:
                last_check = now
                try:
                    self.supervise_speaker()
                except BaseException as exc:  # noqa: BLE001
                    log(f"speaker supervision failed: {exc}")

            self.stop_event.wait(POLL_SECONDS)

    def stop(self) -> None:
        self.stop_event.set()
        try:
            SPEAKER_STOP.write_text("stop", encoding="utf-8")
        except OSError:
            pass


# ---- the Windows service -------------------------------------------------


class FlandersService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = DISPLAY_NAME
    _svc_description_ = DESCRIPTION

    def __init__(self, args):
        super().__init__(args)
        self._watcher = Watcher()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        log("stop requested")
        self._watcher.stop()

    def SvcDoRun(self):
        servicemanager.LogInfoMsg(f"{SERVICE_NAME} starting")
        log("service starting")
        self._watcher.run()
        try:
            SPEAKER_STOP.unlink(missing_ok=True)
        except OSError:
            pass
        log("service stopped")
        servicemanager.LogInfoMsg(f"{SERVICE_NAME} stopped")


# ---- installation helpers ------------------------------------------------


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:  # noqa: BLE001
        return False


def sc(*args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["sc.exe", *args], capture_output=True, text=True, check=False
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def service_exists() -> bool:
    code, _ = sc("query", SERVICE_NAME)
    return code == 0


def install() -> int:
    if not is_admin():
        print(
            "Installing a Windows service needs administrator rights.\n"
            "Re-run this from an elevated PowerShell:\n\n"
            f'  cd "{HERE}"\n'
            f'  ".venv\\Scripts\\python.exe" flanders_service.py install\n'
        )
        return 1

    # The service must be launched by a real interpreter, not the venv stub,
    # so the image path points at the base Python and this script bootstraps
    # the venv's packages onto sys.path before importing pywin32.
    base_python = str(Path(sys.base_prefix) / "python.exe")
    script = str(Path(__file__).resolve())

    if service_exists():
        sc("stop", SERVICE_NAME)
        time.sleep(2)
        try:
            win32serviceutil.RemoveService(SERVICE_NAME)
        except Exception as exc:  # noqa: BLE001
            print(f"could not remove the old service: {exc}")
        time.sleep(1)

    try:
        win32serviceutil.InstallService(
            "flanders_service.FlandersService",
            SERVICE_NAME,
            DISPLAY_NAME,
            startType=win32service.SERVICE_AUTO_START,
            exeName=base_python,
            exeArgs=f'"{script}" --run-service',
            description=DESCRIPTION,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"service install failed: {exc}")
        return 1

    sc(
        "failure", SERVICE_NAME,
        "reset=", "86400",
        "actions=", "restart/5000/restart/10000/restart/30000",
    )
    sc("failureflag", SERVICE_NAME, "1")

    # The scheduled-task era is over; make sure the old one cannot double up.
    subprocess.run(
        ["schtasks", "/delete", "/tn", SERVICE_NAME, "/f"],
        capture_output=True, text=True, check=False,
    )

    code, output = sc("start", SERVICE_NAME)
    print("service installed and started" if code == 0 else f"start failed:\n{output}")
    return 0 if code == 0 else 1


def uninstall() -> int:
    if not is_admin():
        print("Removing a Windows service needs administrator rights.")
        return 1
    sc("stop", SERVICE_NAME)
    time.sleep(2)
    try:
        win32serviceutil.RemoveService(SERVICE_NAME)
        print("service removed")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"service removal failed: {exc}")
        return 1


def status() -> int:
    if not service_exists():
        print(f"{SERVICE_NAME}: not installed")
        return 3
    code, output = sc("query", SERVICE_NAME, "ex")
    print(output)
    if SPEAKER_HEARTBEAT.exists():
        age = time.time() - SPEAKER_HEARTBEAT.stat().st_mtime
        print(f"\nspeaker heartbeat: {int(age)}s ago")
    else:
        print("\nspeaker heartbeat: none")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0

    command = argv[0]
    if command == "install":
        return install()
    if command == "uninstall":
        return uninstall()
    if command == "start":
        code, output = sc("start", SERVICE_NAME)
        print(output)
        return code
    if command == "stop":
        code, output = sc("stop", SERVICE_NAME)
        print(output)
        return code
    if command == "status":
        return status()
    if command == "run":
        watcher = Watcher()
        try:
            watcher.run()
        except KeyboardInterrupt:
            watcher.stop()
        return 0
    if command == "--run-service":
        _boot("dispatching")
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(FlandersService)
        servicemanager.StartServiceCtrlDispatcher()
        _boot("dispatcher returned")
        return 0

    print(f"unknown command: {command}\n")
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
