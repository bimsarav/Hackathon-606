#!/usr/bin/env python3
"""Automatic, zero-token activity logging and resume context for Claude Code (see instructions/CHECKPOINT_PROTOCOL.md).

Modes (argv[1]):
  tool          PostToolUse:        append one line to execution/logs/tool-activity.log
  tool-fail     PostToolUseFailure: same, marked FAIL
  session-start SessionStart:       inject execution/RESUME.md + recent activity as additional context
  marker EVENT  Stop / PreCompact / SessionEnd: append a marker to execution/logs/sessions.log

Fail-safe by design: never raises, never blocks, always exits 0, writes nothing to stdout except for session-start.
Secrets are redacted before logging (tool-activity.log is committed with unfinished work, so redaction matters).
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOGS = os.path.join(ROOT, "execution", "logs")
ACTIVITY = os.path.join(LOGS, "tool-activity.log")
SESSIONS = os.path.join(LOGS, "sessions.log")
RESUME = os.path.join(ROOT, "execution", "RESUME.md")
MAX_ACTIVITY_BYTES = 2_000_000  # rotate at ~2 MB, keeping one previous file

SECRET = re.compile(
    r"(?i)((?:password|passwd|pwd|secret|token|api[_-]?key|authorization|bearer)[\"']?\s*[:=]?\s*[\"']?)([^\s\"',;&|]{4,})")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]+")
URL_CREDS = re.compile(r"(://[^/\s:@]+:)[^@\s/]+@")


def redact(s: str) -> str:
    s = BEARER.sub(lambda m: m.group(1) + " ***", s)
    s = URL_CREDS.sub(lambda m: m.group(1) + "***@", s)
    return SECRET.sub(lambda m: m.group(1) + ("***" if m.group(2) != "***" else m.group(2)), s)


def one_line(s, limit=160) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= limit else s[: limit - 1] + "…"


def rel(path: str) -> str:
    try:
        return os.path.relpath(path, ROOT) if path and os.path.isabs(path) else (path or "")
    except ValueError:
        return path or ""


def summarise(tool: str, inp: dict) -> str:
    if not isinstance(inp, dict):
        return ""
    if "file_path" in inp:
        extra = ""
        if tool == "Write":
            extra = f" ({len(inp.get('content') or '')} chars)"
        return rel(inp["file_path"]) + extra
    if tool == "Bash":
        bg = " [bg]" if inp.get("run_in_background") else ""
        return redact(one_line(inp.get("description") or "", 60)) + " :: " + redact(one_line(inp.get("command", ""), 150)) + bg
    if tool in ("Agent", "Task"):
        return one_line(inp.get("description", ""), 80)
    if tool == "Skill":
        return inp.get("skill", "")
    for k in ("pattern", "query", "url", "action"):
        if k in inp:
            return redact(one_line(f"{k}={inp[k]}", 150))
    return redact(one_line(json.dumps(inp)[:300], 150))


def append(path: str, line: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        if os.path.getsize(path) > MAX_ACTIVITY_BYTES:
            os.replace(path, path + ".1")
    except OSError:
        pass
    with open(path, "a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")


def tail(path: str, n: int) -> list[str]:
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 16384))
            return f.read().decode("utf-8", "replace").splitlines()[-n:]
    except OSError:
        return []


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        data = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        data = {}
    sid = str(data.get("session_id", ""))[:8]

    if mode in ("tool", "tool-fail"):
        tool = data.get("tool_name")
        if not tool:
            return
        status = "FAIL" if mode == "tool-fail" else "ok"
        resp = data.get("tool_response")
        if isinstance(resp, dict) and (resp.get("interrupted") or resp.get("is_error")):
            status = "FAIL"
        err = ""
        if mode == "tool-fail":
            err = " | err=" + redact(one_line(data.get("error") or "", 120))
        append(ACTIVITY, f"{now()} | {sid} | {status:4} | {tool} | {summarise(tool, data.get('tool_input') or {})}{err}")

    elif mode == "marker":
        event = sys.argv[2] if len(sys.argv) > 2 else "event"
        extra = data.get("trigger") or data.get("reason") or data.get("source") or ""
        append(SESSIONS, f"{now()} | {sid} | {event} {extra}".rstrip())

    elif mode == "session-start":
        source = data.get("source", "")
        append(SESSIONS, f"{now()} | {sid} | SessionStart {source}".rstrip())
        parts = ["## Automatic resume context (from .claude/hooks/checkpoint_hook.py)"]
        try:
            with open(RESUME, encoding="utf-8") as f:
                parts.append("### execution/RESUME.md\n" + f.read()[:6000])
        except OSError:
            parts.append("execution/RESUME.md not found: follow the full resume procedure in CLAUDE.md.")
        last = tail(ACTIVITY, 15)
        if last:
            parts.append("### Last tool activity (execution/logs/tool-activity.log, newest last)\n" + "\n".join(last))
        last_s = tail(SESSIONS, 5)
        if last_s:
            parts.append("### Recent session markers\n" + "\n".join(last_s))
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                                 "additionalContext": "\n\n".join(parts)}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - a logging hook must never disturb the session
        pass
    sys.exit(0)
