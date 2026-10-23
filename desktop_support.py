"""Versioned, allowlisted support reports. No credentials, paths or raw logs."""
# Desktop edition copyright (c) 2026 Abdallah22s; see LICENSE.
from __future__ import annotations

import datetime
import json
import os
import platform
import sys
import traceback
import uuid

APP_VERSION = "1.2.0"
APP_NAME = "Antigravity Desktop"
APP_ID = "Abdallah22s.AntigravityDesktop"
APP_AUTHOR = "Abdallah22s"
APP_URL = "https://github.com/Abdallah22s/antigravity-desktop"

# Only fixed descriptions can leave the diagnostic boundary. Raw output can
# contain user paths or exception contents and is never saved or displayed.
REASONS = (
    ("desktop-alias-backups", "Existing backups for aliases disagree. Restore a verified original before retrying."),
    ("desktop-discovery", "Some installation locations could not be inspected. Choose a location manually or retry."),
    ("desktop-empty", "No components were selected. Choose an installation location."),
    ("desktop-changed", "The selected file changed or became inaccessible. Retry Activate to select and inspect it again."),
    ("desktop-verification", "A component could not be verified after the operation. Review its result before retrying."),
    ("desktop-unsupported", "The installed build does not match a supported signature."),
    ("permission denied", "The installation is not writable by this Windows account."),
    ("is in use", "An application is still running and locking the target file."),
    ("signature is not unique", "More than one signature matched; no guess was made."),
    ("both patched and unpatched", "Mixed signatures were detected."),
    ("multiple architecture", "Ambiguous architecture signatures were detected."),
    ("unsupported version", "The installed build does not match a supported signature."),
    ("no architecture gate", "No verified signature matched this executable architecture."),
    ("target changed", "The file changed after checking; the operation was stopped."),
    ("backup verification failed", "The backup could not be verified."),
    ("cannot verify a pristine backup", "A clean backup for an existing patch could not be verified."),
    ("backup already contains", "The backup already contains a patch."),
    ("no backup for", "The original backup is missing."),
    ("not a recognized clean build", "The backup is not a recognized clean build."),
    ("post-write", "Verification after writing failed."),
    ("automatic rollback failed", "Automatic rollback failed. Restore from a verified backup before retrying."),
    ("state before this patch restored", "The state before this operation was restored."),
    ("original restored from backup", "The original was restored from backup."),
    ("library validation", "macOS Library Validation requires an explicit CLI signing option."),
    ("code signing failed", "macOS code signing failed."),
    ("not found (use", "The previously selected target is no longer present."),
)


def diagnostic_reasons(output):
    lowered = output.lower()
    return [description for pattern, description in REASONS if pattern in lowered]


def error_report(operation, apps=(), reasons=(), exception=None, qt_version=None):
    states = {"patched", "unpatched", "unknown", "error", "not found", "unchecked"}
    report = {
        "application": APP_NAME,
        "version": APP_VERSION,
        "report_id": uuid.uuid4().hex[:12],
        "time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "operation": operation if operation in ("check", "patch", "restore", "startup", "interface") else "unknown",
        "system": {"os": platform.system(), "release": platform.release(),
                   "machine": platform.machine(), "python": platform.python_version(),
                   "packaged": bool(getattr(sys, "frozen", False))},
        "components": [{"target": a["target"], "state": a["state"] if a["state"] in states else "unknown"}
                       for a in apps if a.get("target") in ("cli", "manager", "ide", "extension")],
        "reasons": [r for r in reasons if r in {description for _, description in REASONS}],
    }
    if qt_version:
        report["system"]["qt"] = qt_version
    if exception is not None:
        report["exception"] = {
            "type": type(exception).__name__,
            "errno": getattr(exception, "errno", None),
            "winerror": getattr(exception, "winerror", None),
            "frames": [{"file": os.path.basename(f.filename), "function": f.name, "line": f.lineno}
                       for f in traceback.extract_tb(exception.__traceback__)],
        }
    return json.dumps(report, indent=2, ensure_ascii=True)


def startup_error(exception):
    """Still works if importing Tk fails, including in a windowed EXE."""
    report = error_report("startup", exception=exception)
    message = ("Antigravity Desktop could not start.\n\n"
               "Press Ctrl+C to copy this window, then send it to the person who provided the app.\n"
               "No account data or access tokens are included.\n\n" + report)
    if os.name == "nt":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, APP_NAME + " - Startup error", 0x10)
    elif sys.stderr:
        sys.stderr.write(message + "\n")
