#!/usr/bin/env python3
from __future__ import annotations

import cmd
import json
import os
import secrets
import shutil
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from digest_pipeline import build_digest, canonical_json_bytes, report_from_digest, sha256_hex

APP_ROOT = Path("/app")
DATA_ROOT = APP_ROOT / "data"
RUNTIME_ROOT = APP_ROOT / "runtime"
OUTPUT_ROOT = APP_ROOT / "output"
STATE_FILE = RUNTIME_ROOT / "state" / "publisher_state.json"
DRAFT_FILE = RUNTIME_ROOT / "tmp" / "draft_digest.json"
PUBLISHED_FILE = RUNTIME_ROOT / "published" / "bookworm-security-digest.json"
RECEIPT_FILE = RUNTIME_ROOT / "published" / "publish_receipt.json"
AUDIT_FILE = RUNTIME_ROOT / "logs" / "console_audit.jsonl"
TRACKED_PACKAGES_FILE = DATA_ROOT / "incident" / "tracked_packages.json"
UPSTREAM_ROOT = DATA_ROOT / "upstream"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RecoveryConsole(cmd.Cmd):
    intro = (
        "Debian Security digest recovery console\n"
        "Type 'help' for commands. This console requires a live TTY.\n"
    )
    prompt = "recovery-console> "

    def __init__(self) -> None:
        super().__init__()
        self.session_id = str(uuid.uuid4())
        self.current_token: str | None = None
        self.current_draft_sha256: str | None = None
        self.current_report: dict | None = None
        self._capability_hash = os.environ.get("NANOBOT_RECOVERY_CAP_HASH", "")
        self._audit("session_start", {"session_id": self.session_id})

    def _owner_session_id(self, state: dict) -> str:
        return str(state.get("recovery_owner_session_id", "") or "")

    def _ensure_owner(self, state: dict, *, action: str) -> bool:
        owner = self._owner_session_id(state)
        if owner and owner != self.session_id:
            print("Another live recovery session already owns this publication. Reconnect to the existing console session.")
            self._audit(action, {"result": "blocked_wrong_session", "owner_session_id": owner})
            return False
        return True

    def _load_state(self) -> dict:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))

    def _save_state(self, state: dict) -> None:
        STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _audit(self, event: str, payload: dict) -> None:
        record = {
            "timestamp": utc_now(),
            "session_id": self.session_id,
            "event": event,
            **payload,
        }
        with AUDIT_FILE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")

    def _ensure_ready(self) -> dict | None:
        state = self._load_state()
        if state["pipeline_mode"] != "active":
            print("Pipeline is paused. Run: resume-pipeline")
            self._audit("blocked", {"reason": "pipeline_paused"})
            return None
        if state["stale_lock"]:
            print("A stale draft lock is still present. Run: clear-stale-lock")
            self._audit("blocked", {"reason": "stale_lock"})
            return None
        return state

    def do_status(self, _arg: str) -> None:
        state = self._load_state()
        print(f"session_id: {self.session_id}")
        print(f"snapshot_id: {state['snapshot_id']}")
        print(f"pipeline_mode: {state['pipeline_mode']}")
        print(f"stale_lock: {str(state['stale_lock']).lower()}")
        print(f"draft_ready: {str(state['draft_ready']).lower()}")
        print(f"published: {str(state['published']).lower()}")
        print(f"last_error: {state['last_error']}")
        self._audit("status", state)

    def do_resume_pipeline(self, _arg: str) -> None:
        state = self._load_state()
        if not self._ensure_owner(state, action="resume_pipeline"):
            return
        state["pipeline_mode"] = "active"
        state["last_error"] = "stale draft lock still blocks publication until it is cleared"
        self._save_state(state)
        print("Pipeline resumed.")
        self._audit("resume_pipeline", {"result": "ok"})

    def do_clear_stale_lock(self, _arg: str) -> None:
        state = self._load_state()
        if not self._ensure_owner(state, action="clear_stale_lock"):
            return
        state["stale_lock"] = False
        state["last_error"] = ""
        self._save_state(state)
        if DRAFT_FILE.exists():
            DRAFT_FILE.unlink()
        print("Stale draft lock cleared.")
        self._audit("clear_stale_lock", {"result": "ok"})

    def do_rebuild_digest(self, _arg: str) -> None:
        state = self._ensure_ready()
        if state is None:
            return
        if not self._ensure_owner(state, action="rebuild_digest"):
            return
        if state["draft_ready"]:
            print("A staged draft already exists. Continue the existing recovery session; do not rebuild in a new session.")
            self._audit("rebuild_digest", {"result": "blocked_existing_staged_draft"})
            return
        digest = build_digest(UPSTREAM_ROOT, TRACKED_PACKAGES_FILE)
        draft_bytes = canonical_json_bytes(digest)
        draft_sha256 = sha256_hex(draft_bytes)
        DRAFT_FILE.write_bytes(draft_bytes)
        state["draft_ready"] = True
        state["last_error"] = ""
        state["recovery_owner_session_id"] = self.session_id
        self._save_state(state)
        self.current_draft_sha256 = draft_sha256
        self.current_token = secrets.token_hex(6)
        self.current_report = report_from_digest(digest, draft_sha256)
        print("Draft digest rebuilt from upstream snapshot.")
        print(f"Draft SHA256: {draft_sha256}")
        print(f"Publish token: {self.current_token}")
        print("Keep this console session open. The publish token is only valid here.")
        self._audit(
            "rebuild_digest",
            {
                "result": "ok",
                "draft_sha256": draft_sha256,
                "tracked_packages": digest["tracked_packages"],
                "package_count": digest["package_count"],
            },
        )

    def do_publish_digest(self, arg: str) -> None:
        parts = arg.split()
        state = self._ensure_ready()
        if state is None:
            return
        if not self._ensure_owner(state, action="publish_digest"):
            return
        if not state["draft_ready"] or not DRAFT_FILE.exists():
            print("No draft is ready. Run: rebuild-digest")
            self._audit("publish_digest", {"result": "blocked_no_draft"})
            return
        if len(parts) != 2:
            print("Usage: publish-digest <token> <capability>")
            self._audit("publish_digest", {"result": "missing_token"})
            return
        token, capability = parts
        if token != self.current_token or self.current_draft_sha256 is None or self.current_report is None:
            print("Publish token invalid for this live console session.")
            self._audit("publish_digest", {"result": "invalid_token"})
            return
        if sha256_hex(capability.encode("utf-8")) != self._capability_hash:
            print("Recovery capability invalid for this live console session.")
            self._audit("publish_digest", {"result": "invalid_capability"})
            return

        print("Publishing digest", flush=True)
        for step in ("  - validating draft", "  - writing published artifact", "  - sealing receipt"):
            print(step, flush=True)
            time.sleep(1)

        shutil.copyfile(DRAFT_FILE, PUBLISHED_FILE)
        receipt = {
            **self.current_report,
            "published_artifact": str(PUBLISHED_FILE),
            "published_at": utc_now(),
            "session_id": self.session_id,
        }
        RECEIPT_FILE.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        state["published"] = True
        state["last_error"] = ""
        self._save_state(state)
        print("Publication complete.")
        print(f"Published artifact: {PUBLISHED_FILE}")
        self._audit("publish_digest", {"result": "ok", "published_artifact": str(PUBLISHED_FILE)})

    def do_write_report(self, arg: str) -> None:
        parts = arg.split()
        state = self._load_state()
        if not self._ensure_owner(state, action="write_report"):
            return
        if not RECEIPT_FILE.exists():
            print("No publish receipt found. Run: publish-digest <token> <capability>")
            self._audit("write_report", {"result": "blocked_no_receipt"})
            return
        if not parts:
            print("Usage: write-report [destination] <capability>")
            self._audit("write_report", {"result": "missing_capability"})
            return
        if len(parts) == 1:
            destination = Path("/app/output/recovery_report.json")
            capability = parts[0]
        else:
            destination = Path(" ".join(parts[:-1]))
            capability = parts[-1]
        if sha256_hex(capability.encode("utf-8")) != self._capability_hash:
            print("Recovery capability invalid for this live console session.")
            self._audit("write_report", {"result": "invalid_capability"})
            return

        receipt = json.loads(RECEIPT_FILE.read_text(encoding="utf-8"))
        report = {
            "snapshot_id": receipt["snapshot_id"],
            "suite": receipt["suite"],
            "component": receipt["component"],
            "architecture": receipt["architecture"],
            "published": receipt["published"],
            "package_count": receipt["package_count"],
            "tracked_packages": receipt["tracked_packages"],
            "digest_sha256": receipt["digest_sha256"],
        }
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Wrote report to {destination}")
        self._audit("write_report", {"result": "ok", "destination": str(destination)})

    def do_show_report(self, _arg: str) -> None:
        if not RECEIPT_FILE.exists():
            print("No publish receipt found.")
            self._audit("show_report", {"result": "missing_receipt"})
            return
        receipt = json.loads(RECEIPT_FILE.read_text(encoding="utf-8"))
        print(json.dumps(receipt, indent=2, sort_keys=True))
        self._audit("show_report", {"result": "ok"})

    def do_exit(self, _arg: str) -> bool:
        self._audit("session_end", {"result": "exit"})
        print("Bye.")
        return True

    def do_quit(self, arg: str) -> bool:
        return self.do_exit(arg)

    def parseline(self, line: str):
        translated = line.replace("-", "_")
        return super().parseline(translated)

    def emptyline(self) -> None:
        pass


def main() -> int:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("recovery-console requires a real TTY.", file=sys.stderr)
        return 2

    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    console = RecoveryConsole()
    console.cmdloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
