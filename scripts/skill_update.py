"""Check for updates quietly and apply fast-forwards to a Git installation."""

import os
import sqlite3
import subprocess
import sys
import time
from contextlib import closing, contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / ".git" / "swc-databank-update.sqlite3"
CHECK_INTERVAL = 24 * 60 * 60
REMOTE_BRANCH = "refs/remotes/origin/main"
OFFICIAL_REMOTES = {
    "https://github.com/LukeSONG2000/swc-databank-skill",
    "https://github.com/LukeSONG2000/swc-glossary-skill",
}


@contextmanager
def state():
    with closing(sqlite3.connect(STATE_FILE, timeout=0.05)) as db, db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS updates (
                id INTEGER PRIMARY KEY,
                checked_at INTEGER NOT NULL,
                pending_commit TEXT,
                notify_after INTEGER NOT NULL DEFAULT 0
            )
        """)
        yield db


def start_update_check():
    if not STATE_FILE.parent.is_dir():
        return
    now = int(time.time())
    due_before = now - CHECK_INTERVAL
    try:
        with state() as db:
            row = db.execute("SELECT checked_at FROM updates WHERE id = 1").fetchone()
            if row and due_before < row[0]:
                return
            claimed = db.execute("""
                INSERT INTO updates (id, checked_at) VALUES (1, ?)
                ON CONFLICT(id) DO UPDATE SET checked_at = excluded.checked_at
                WHERE updates.checked_at <= ?
            """, (now, due_before)).rowcount
        if not claimed:
            return
        if os.name == "nt":
            detach = {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
        else:
            detach = {"start_new_session": True}
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--background"],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, **detach,
        )
    except (OSError, sqlite3.Error):
        return


def take_update_notice():
    if not STATE_FILE.is_file():
        return {}
    try:
        with state() as db:
            row = db.execute("""
                SELECT pending_commit FROM updates
                WHERE id = 1 AND pending_commit IS NOT NULL AND notify_after <= ?
            """, (int(time.time()),)).fetchone()
            if row is None:
                return {}
            commit = row[0]
            taken = db.execute("""
                UPDATE updates SET pending_commit = NULL
                WHERE id = 1 AND pending_commit = ?
            """, (commit,)).rowcount
    except sqlite3.Error:
        return {}
    if taken:
        return {"skill_update": {"commit": commit[:12], "message": "星球大战中文网数据库 Skill 已更新"}}
    return {}


def git(*args, timeout=8):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    for name in ("GIT_ASKPASS", "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE", "GIT_NAMESPACE"):
        env.pop(name, None)
    result = subprocess.run(
        ["git", "-c", "credential.helper=", "-c", "core.askPass=",
         "-c", f"core.hooksPath={os.devnull}", *args],
        cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=True, timeout=timeout,
    )
    return result.stdout.strip()


def clean_main():
    return git("branch", "--show-current") == "main" and not git(
        "status", "--porcelain", "--untracked-files=no",
    )


def fast_forward():
    if Path(git("rev-parse", "--show-toplevel")).resolve() != ROOT or not clean_main():
        return None
    origin = git("remote", "get-url", "origin").rstrip("/")
    if origin.endswith(".git"):
        origin = origin[:-4]
    if origin not in OFFICIAL_REMOTES:
        return None

    previous = git("rev-parse", "HEAD")
    git("fetch", "--no-tags", "--no-recurse-submodules", "--no-write-fetch-head", "origin",
        f"refs/heads/main:{REMOTE_BRANCH}", timeout=35)
    target = git("rev-parse", REMOTE_BRANCH)
    if target == previous or git("rev-parse", "HEAD") != previous or not clean_main():
        return None
    git("merge", "--ff-only", "--no-edit", "--no-autostash", "--no-overwrite-ignore", target)
    current = git("rev-parse", "HEAD")
    return current if current != previous else None


def notify_macos():
    if sys.platform != "darwin":
        return False
    try:
        subprocess.run(
            ["/usr/bin/osascript", "-e",
             'display notification "Skill 已更新" with title "星球大战中文网数据库"'],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=4, check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def background_update():
    try:
        commit = fast_forward()
        if not commit:
            return
        with state() as db:
            db.execute("""
                UPDATE updates SET pending_commit = ?, notify_after = ? WHERE id = 1
            """, (commit, int(time.time()) + 5))
        notified = notify_macos()
        with state() as db:
            db.execute("""
                UPDATE updates SET pending_commit = ?, notify_after = 0
                WHERE id = 1 AND pending_commit = ?
            """, (None if notified else commit, commit))
    except (OSError, sqlite3.Error, subprocess.SubprocessError):
        return


if __name__ == "__main__" and sys.argv[1:] == ["--background"]:
    background_update()
