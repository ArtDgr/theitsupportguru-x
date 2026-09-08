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
    if count >= 40:
        print(f"[GATE] SKIP - monthly cap 40 reached ({count}/40) for {yyyymm} AEST — warm-up 10/week")
        return False, f"cap-{yyyymm}"
    if not randomize:
        return True, "dispatch"
    # Warm-up Month 1: 10/week = 40/mo. Gate is per-slot run (4x/day Mon-Fri) -> need p~0.36 to hit 10/week (4*5*0.36=7.2) + catch-up to 10
    # Lower weights vs 80/mo to stay under X radar in month 1
    weights = {0:0.50, 1:0.55, 2:0.40, 3:0.55, 4:0.50, 5:0.15, 6:0.05}
    p = weights.get(day, 0.30)
    # Beat detection: Knuth hash + per-run jitter, so X sees no fixed pattern (like IG 30%)
    knuth = ((int(now.strftime("%Y%m%d%H")) * 2654435761) % 100) / 100  # per-hour deterministic
    p = p * (0.85 + knuth*0.30)
    p += random.uniform(-0.07, 0.07)
    p = max(0.10, min(0.85, p))
    days_left = 30 - now.day
    expected = 40 * (now.day / 30)
    if count < expected - 3 and days_left > 0:
        p = min(0.75, p + 0.15)
    elif count > expected + 3:
        p = max(0.10, p - 0.15)
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
