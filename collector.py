#!/usr/bin/env python3
"""
Technocore Pulse - network health collector
Reads public Technocore endpoints and stores network stats locally.
No API key needed: all endpoints are public GETs.
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://technocore.chat"
DB = Path(__file__).parent / "pulse.db"
UA = "TechnocorePulse/0.1 (open-source network monitor)"

ROOMS_TO_WATCH = ["lobby", "technocore", "events"]


def fetch_json(path: str, timeout: float = 15.0):
    req = Request(BASE + path, headers={"Accept": "application/json", "User-Agent": UA})
    with urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8"))


def snapshot_room(room: str) -> dict:
    """Grab the newest page of a room and compute simple stats."""
    try:
        data = fetch_json(f"/r/{room}?format=json&limit=100")
    except Exception as e:
        return {"room": room, "error": str(e)}

    msgs = data.get("messages", []) if isinstance(data, dict) else data
    if isinstance(data, dict) and not msgs:
        msgs = []
    verified = 0
    dids = set()
    for m in msgs:
        sender = str(m.get("from", ""))
        if sender.startswith("did:key:"):
            verified += 1
            dids.add(sender)
    seqs = [m.get("seq") for m in msgs if isinstance(m.get("seq"), int)]
    return {
        "room": room,
        "messages_in_window": len(msgs),
        "verified_signed": verified,
        "unique_dids": len(dids),
        "first_seq": min(seqs) if seqs else None,
        "last_seq": max(seqs) if seqs else None,
        "raw": None,
    }


def snapshot_network() -> dict:
    out = {"ts": datetime.now(timezone.utc).isoformat(), "rooms": []}
    # public room list (rooms, note counts)
    try:
        rooms_raw = fetch_json("/rooms")
        # /rooms returns text lines; keep first 30 lines raw
        if isinstance(rooms_raw, dict):
            rooms_text = rooms_raw.get("body", json.dumps(rooms_raw)[:2000])
        else:
            rooms_text = str(rooms_raw)
        out["public_rooms_lines"] = rooms_text[:2000]
    except Exception as e:
        out["public_rooms_lines"] = f"ERROR: {e}"
    for r in ROOMS_TO_WATCH:
        out["rooms"].append(snapshot_room(r))
        time.sleep(1)  # be polite to rate limits
    return out


def save(db: sqlite3.Connection, snap: dict):
    db.execute(
        """CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            room TEXT,
            messages_in_window INTEGER,
            verified_signed INTEGER,
            unique_dids INTEGER,
            first_seq INTEGER,
            last_seq INTEGER,
            error TEXT
        )"""
    )
    for r in snap.get("rooms", []):
        db.execute(
            "INSERT INTO snapshots (ts, room, messages_in_window, verified_signed, unique_dids, first_seq, last_seq, error) VALUES (?,?,?,?,?,?,?,?)",
            (
                snap["ts"], r.get("room"), r.get("messages_in_window"),
                r.get("verified_signed"), r.get("unique_dids"),
                r.get("first_seq"), r.get("last_seq"), r.get("error"),
            ),
        )
    db.commit()


def summarize(snap: dict) -> str:
    parts = []
    total_verified = 0
    total_dids = set()
    for r in snap.get("rooms", []):
        if r.get("error"):
            parts.append(f"{r['room']}: ERROR")
            continue
        total_verified += r.get("verified_signed", 0)
        parts.append(
            f"{r['room']}: {r.get('messages_in_window',0)} msgs, {r.get('verified_signed',0)} signed, {r.get('unique_dids',0)} unique DIDs"
        )
    return " | ".join(parts) + f" | signed msgs in window: {total_verified}"


def main():
    snap = snapshot_network()
    db = sqlite3.connect(DB)
    save(db, snap)
    s = summarize(snap)
    print(s)
    # save latest summary for the reporter
    (Path(__file__).parent / "latest_summary.txt").write_text(s, encoding="utf-8")
    db.close()


if __name__ == "__main__":
    main()
