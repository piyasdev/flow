#!/usr/bin/env python3
"""
Technocore Pulse - signed reporter
Posts the latest network summary to Technocore as a signed message,
using the existing flop-airdrop identity (agent_toolkit).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "scripts"))

from agent_toolkit import post_message  # noqa: E402


def main():
    summary = (HERE / "latest_summary.txt").read_text(encoding="utf-8").strip()
    if not summary:
        print("no summary to report", file=sys.stderr)
        sys.exit(1)
    msg = f"Technocore Pulse (network monitor): {summary}"
    res = post_message("technocore", msg)
    posted = res.get("posted", {})
    print("Pulse reported.")
    print(f"Sequence: {posted.get('seq')}")
    print(f"DID: {posted.get('from')}")


if __name__ == "__main__":
    main()
