#!/usr/bin/env python3
"""schedule_gate.py - Random AEST gate for X (faceless, 4x/day Mon-Fri, max 80/mo)"""
import random, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

AEST = timezone(timedelta(hours=10))
STATE = Path(__file__).parent.parent / "out" / "state.json"
CONFIG = Path(__file__).parent.parent / "out" / "schedule.json"

def should_publish(randomize=True):
    now = datetime.now(AEST)
    yyyymm = now.strftime("%Y-%m")
    day = now.weekday()
    state = {}
    if STATE.exists():
        try: state = json.loads(STATE.read_text())
        except: state = {}
    month_key = f"published_{yyyymm}"
    count = state.get(month_key, 0)
    if count >= 80:
        print(f"[GATE] SKIP - monthly cap 80 reached ({count}/80) for {yyyymm} AEST")
        return False, f"cap-{yyyymm}"
    if not randomize:
        return True, "dispatch"
    # X is daily Mon-Fri 4x -> ~80/mo max. Gate is per-day build (not per-tweet).
    # Weights: Mon-Fri high, Sat lower, Sun skip (like IG schedule Mon-Sat but X Mon-Fri)
    weights = {0:0.75, 1:0.80, 2:0.70, 3:0.80, 4:0.75, 5:0.25, 6:0.10}
    p = weights.get(day, 0.35)
    # Beat detection: add Knuth hash 30% stealth (like IG buffer) + per-run ±0.07 jitter, so X sees no fixed pattern
    knuth = ((int(now.strftime("%Y%m%d")) * 2654435761) % 100) / 100  # 0-0.99 deterministic per date
    p = p * (0.85 + knuth*0.30)  # 0.85-1.15x weekday weight, deterministic but looks random
    p += random.uniform(-0.07, 0.07)  # extra 14% run-to-run jitter
    p = max(0.10, min(0.95, p))
    days_left = 30 - now.day
    expected = 80 * (now.day / 30)
    if count < expected - 5 and days_left > 0:
        p = min(0.90, p + 0.20)
    elif count > expected + 5:
        p = max(0.15, p - 0.15)
    roll = random.random()
    will = roll < p
    print(f"[GATE] X Day {now.strftime('%a %Y-%m-%d %H:%M AEST')} p={p:.2f} roll={roll:.3f} -> {'PUBLISH' if will else 'SKIP'} ({count}/80 {yyyymm})")
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps({"date": now.isoformat(), "p": p, "roll": roll, "will": will, "count": count, "yyyymm": yyyymm, "platform": "x"}, indent=2))
    return will, f"p{p:.2f}"

if __name__ == "__main__":
    import os
    force = os.environ.get("FORCE_PUBLISH")=="1" or os.environ.get("GITHUB_EVENT_NAME")=="workflow_dispatch"
    ok, reason = should_publish(randomize=not force)
    if not ok:
        print(f"::notice::Skipped - {reason} (X AEST gate, max 80/mo)")
        Path("out/skip_gate").write_text(reason)
        sys.exit(0)
    Path("out/skip_gate").unlink(missing_ok=True)
