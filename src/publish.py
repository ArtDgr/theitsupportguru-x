#!/usr/bin/env python3
"""
publish.py: X publisher via Ayrshare (headless, no Buffer) with AEST jitter + 30d Telegram gate
- Mirrors theitsupportguru-substack/src/publish.py but for X (twitter) via Ayrshare API
- Fixed AEST: daily 05:30 AEST build -> schedules 06:00/12:00/17:00/20:00 AEST via Ayrshare scheduleDate
- Gate: 30d human approve via Telegram, after AUTO_PUBLISH=1 -> auto
- Anti-bot: random jitter 06:12-06:27, User-Agent TheITSupportGuru-X/1.0, unique Message per post
"""
import os, random, time, json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

AEST = timezone(timedelta(hours=10))
DRAFT = Path(__file__).parent.parent / "out" / "draft.md"
TWEETS_JSON = Path(__file__).parent.parent / "out" / "tweets.json"
DRAFTS = Path(__file__).parent.parent / "drafts"
STATE = Path(__file__).parent.parent / "out" / "state.json"
# X posting times AEST (mirrors FacelessStudio config.x.postingTimes)
POSTING_TIMES = ["06:00", "12:00", "17:00", "20:00"]
FRIDAY_EXTRA = "18:00"  # gadget focus

def check_monthly_cap():
    now = datetime.now(AEST)
    yyyymm = now.strftime("%Y-%m")
    state = {}
    if STATE.exists():
        try: state = json.loads(STATE.read_text())
        except: state = {}
    # X is 4x/day Mon-Fri -> ~80/mo, but cap at 80 to avoid spam
    count = state.get(f"published_{yyyymm}", 0)
    if count >= 80:
        print(f"[CAP] SKIP - max 80 reached for {yyyymm} ({count}/80) AEST")
        return False
    return True

def record_publish(n=4):
    now = datetime.now(AEST)
    yyyymm = now.strftime("%Y-%m")
    state = {}
    if STATE.exists():
        try: state = json.loads(STATE.read_text())
        except: state = {}
    key = f"published_{yyyymm}"
    state[key] = state.get(key, 0) + n
    state["last_publish"] = now.isoformat()
    state["approved_count"] = state.get("approved_count", 0) + 1
    STATE.write_text(json.dumps(state, indent=2))

def aest_jitter_sleep():
    is_cron = os.environ.get("GITHUB_EVENT_NAME") == "schedule"
    is_ci = os.environ.get("CI") == "1"
    if is_cron and is_ci:
        j_hour = random.randint(2, 5)
        j_min = random.randint(12, 27)
        j_sec = random.randint(0, 59)
        if random.random() < 0.65:
            j_hour = random.randint(2, 3)
        sleep_s = j_hour*3600 + j_min*60 + j_sec
        # For X daily build 05:30 -> jitter to 06:12-06:27 is handled in workflow sleep; here cap to 2m for publish
        aest_target = datetime.now(AEST) + timedelta(seconds=sleep_s)
        print(f"[AEST] Cron jitter: sleeping {sleep_s}s -> target {aest_target.strftime('%H:%M:%S %a %d %b AEST')} (06:12-06:27 bias)")
        if os.environ.get("SKIP_SLEEP") != "1":
            time.sleep(sleep_s)
        return aest_target
    else:
        j_sec = random.randint(12, 27)
        j_ms = random.randint(0, 999)
        sleep_s = j_sec
        aest_target = datetime.now(AEST) + timedelta(seconds=sleep_s)
        print(f"[AEST] Dispatch jitter: sleeping {sleep_s}.{j_ms:03d}s -> target {aest_target.strftime('%H:%M:%S AEST')}")
        if os.environ.get("SKIP_SLEEP") != "1":
            time.sleep(sleep_s)
        return aest_target

def load_tweets():
    if TWEETS_JSON.exists():
        return json.loads(TWEETS_JSON.read_text(encoding="utf-8"))
    if DRAFT.exists():
        # fallback: single draft -> wrap as one tweet
        md = DRAFT.read_text(encoding="utf-8")
        return [{"slot": 0, "text": md[:280], "link": ""}]
    latest = sorted(DRAFTS.glob("*.json"), reverse=True)
    if latest:
        return json.loads(latest[0].read_text(encoding="utf-8"))
    latest_md = sorted(DRAFTS.glob("*.md"), reverse=True)
    if latest_md:
        md = latest_md[0].read_text(encoding="utf-8")
        return [{"slot": 0, "text": md[:280], "link": ""}]
    raise SystemExit("No tweets found - run synthesize.py first")

def should_auto_publish():
    if os.environ.get("AUTO_PUBLISH", "0") == "1":
        return True
    if STATE.exists():
        s = json.loads(STATE.read_text())
        if s.get("approved_count", 0) >= 12:
            return True
    return False

def send_via_telegram_gate(tweets):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("No Telegram config - saving to drafts/ for manual approve")
        return False
    try:
        aest_now = datetime.now(AEST).strftime("%Y-%m-%d %H:%M AEST")
        preview = "\n\n".join([f"[{t.get('slot',i)}] {t.get('text','')[:180]} ({len(t.get('text',''))} chars)" for i, t in enumerate(tweets[:4])])
        kb = {"inline_keyboard": [[{"text":"✅ APPROVE & PUBLISH","callback_data":"approve"},{"text":"❌ REJECT","callback_data":"reject"}]]}
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": f"🐦 X drafts {aest_now} ({len(tweets)} tweets)\n\n{preview}\n\nReply APPROVE to publish, REJECT to skip", "reply_markup": kb}, timeout=15)
        print(f"Telegram gate sent: {r.status_code}")
        return True
    except Exception as e:
        print(f"Telegram fail: {e}")
        return False

def publish_via_ayrshare(tweets):
    api_key = os.environ.get("AYRSHARE_API_KEY")
    if not api_key:
        # Dry run - save to out/email.eml equivalent
        out = Path("out/ayrshare_dryrun.json")
        out.write_text(json.dumps(tweets, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"DRY RUN - no AYRSHARE_API_KEY. Saved {out} ({len(tweets)} tweets) AEST {datetime.now(AEST).isoformat()}")
        for t in tweets:
            try:
                txt = t.get('text','')[:80].encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                print(f"  [{t.get('slot')}] {txt}... ({len(t.get('text',''))} chars)")
            except:
                print(f"  [{t.get('slot')}] ({len(t.get('text',''))} chars)")
        return False

    # Schedule each tweet at its AEST slot today
    today = datetime.now(AEST).strftime("%Y-%m-%d")
    times = POSTING_TIMES.copy()
    # Friday gadget focus 5th tweet?
    if len(tweets) > 4:
        times.append(FRIDAY_EXTRA)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    # Free tier check: scheduleDate requires Premium/Business; for free, publish 1 tweet immediately per run
    # Detect current AEST slot to pick single tweet (avoids 4-at-once spam on free)
    now_hm = datetime.now(AEST).strftime("%H:%M")
    # Map current time to nearest posting slot
    def nearest_slot(hm):
        try:
            cur = int(hm.replace(":",""))
            times_int = [int(t.replace(":","")) for t in POSTING_TIMES]
            # pick slot whose time <= cur < next, else last
            for i, t in enumerate(times_int):
                nxt = times_int[i+1] if i+1 < len(times_int) else 2400
                if t <= cur < nxt:
                    return i
            return len(times_int)-1
        except: return 0
    free_mode_single = False

    published = 0
    for idx, tweet in enumerate(tweets[:len(times)]):
        hm = times[idx] if idx < len(times) else POSTING_TIMES[idx % len(POSTING_TIMES)]
        # Ayrshare scheduleDate expects ISO UTC
        aest_dt = datetime.strptime(f"{today} {hm}", "%Y-%m-%d %H:%M").replace(tzinfo=AEST)
        utc_iso = aest_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        text = tweet.get("text", "")[:280]
        link = tweet.get("link", "")
        if link and link not in text and len(text) + len(link) + 1 <= 280:
            text = f"{text} {link}"
        payload = {
            "post": text,
            "platforms": ["twitter"],
            "scheduleDate": utc_iso,
            # human-like UA per Substack publish.py
        }
        # Optional media: if FacelessStudio rendered cards exist via raw github, add mediaUrls
        # Ayrshare supports mediaUrls for twitter (max 4)
        if tweet.get("mediaUrls"):
            payload["mediaUrls"] = tweet["mediaUrls"][:4]

        print(f"[AYRSHARE] Publishing slot {tweet.get('slot',idx)} @ {hm} AEST ({utc_iso}) -> {text[:60]}...")
        try:
            r = requests.post("https://api.ayrshare.com/api/post", headers=headers, json=payload, timeout=20)
            data = r.json() if r.headers.get("content-type","").startswith("application/json") else {"status": r.text[:200]}
            if r.status_code in (200, 201) and data.get("status") != "error":
                print(f"  -> OK {r.status_code} id={data.get('id') or data.get('postIds')}")
                published += 1
            else:
                # Free plan: scheduleDate requires Premium -> retry immediate publish (free tier, single tweet per run)
                if data.get("code") == 169 or "Premium" in str(data.get("message","")) or "Business Plan" in str(data.get("message","")):
                    print(f"  -> Schedule requires paid (code 169) -> retry immediate publish (free tier)")
                    # Free: publish only 1 tweet matching current slot immediately (avoid 4-at-once)
                    if not free_mode_single:
                        free_mode_single = True
                        # pick tweet for current slot
                        slot_idx = nearest_slot(now_hm)
                        tweet_single = tweets[slot_idx % len(tweets)] if tweets else tweet
                        text_single = tweet_single.get("text","")[:280]
                        link_single = tweet_single.get("link","")
                        if link_single and link_single not in text_single and len(text_single)+1+len(link_single) <= 280:
                            text_single = f"{text_single} {link_single}"
                        payload_immediate = {"post": text_single, "platforms": ["twitter"]}
                        if tweet_single.get("mediaUrls"):
                            payload_immediate["mediaUrls"] = tweet_single["mediaUrls"][:4]
                        print(f"  -> Free tier: publishing single slot {tweet_single.get('slot',slot_idx)} @ now {now_hm} AEST -> {text_single[:60]}...")
                        r2 = requests.post("https://api.ayrshare.com/api/post", headers=headers, json=payload_immediate, timeout=20)
                        data2 = r2.json() if r2.headers.get("content-type","").startswith("application/json") else {"status": r2.text[:200]}
                        if r2.status_code in (200, 201) and data2.get("status") != "error":
                            print(f"  -> OK immediate {r2.status_code} id={data2.get('id') or data2.get('postIds')}")
                            published += 1
                        else:
                            print(f"  -> FAIL immediate {r2.status_code}: {data2}")
                        # Free tier: only 1 post per run, break after first retry
                        break
                    else:
                        print(f"  -> Skipping remaining scheduled slots (free tier single per run)")
                        break
                else:
                    print(f"  -> FAIL {r.status_code}: {data}")
                # don't abort all, continue
            time.sleep(1.5)  # polite between posts
        except Exception as e:
            print(f"  -> exception: {e}")

    if published:
        record_publish(published)
        print(f"Published {published}/{len(tweets)} via Ayrshare AEST {datetime.now(AEST).isoformat()}")
        return True
    return False

if __name__ == "__main__":
    if Path("out/skip_gate").exists():
        print(f"Gate skip marker exists ({Path('out/skip_gate').read_text()}) - random AEST gate chose SKIP")
        raise SystemExit(0)
    if not check_monthly_cap():
        raise SystemExit(0)
    tweets = load_tweets()
    aest_jitter_sleep()
    if should_auto_publish():
        print(f"Gate PASSED (auto) - publishing {len(tweets)} X tweets via Ayrshare")
        ok = publish_via_ayrshare(tweets)
    else:
        print("Gate ACTIVE (human approve) - sending to Telegram")
        sent = send_via_telegram_gate(tweets)
        if not sent:
            print("Gate: tweets awaiting manual publish - check drafts/ folder AEST")
