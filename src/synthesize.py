#!/usr/bin/env python3
"""synthesize.py: Neutral analyst synthesis -> tweets.json : 4: X 280-char pillars + IG logic"""
import json, os, random, hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from openai import OpenAI

AEST = timezone(timedelta(hours=10))
ENRICHED = Path(__file__).parent.parent / "out" / "enriched.json"
PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "analyst_system.md"
DRAFTS = Path(__file__).parent.parent / "drafts"
OUT = Path(__file__).parent.parent / "out" / "draft.md"
TWEETS_OUT = Path(__file__).parent.parent / "out" / "tweets.json"

PILLARS = ["redflag", "myth", "secrets", "guide"]
NICHE_TAGS = {
    "ai": "#AI #ChatGPT",
    "gadgets": "#gadgets #smartphone",
    "apple": "#Apple #iPhone",
    "hardware": "#hardware #PC",
    "security": "#cybersecurity #infosec",
    "it-support": "#itsupport #Windows11",
    "cloud-devops": "#cloud #DevOps",
}

def shorten(s, n):
    v = " ".join(str(s).split())
    if len(v) <= n: return v
    cut = v[:n-1]
    sp = cut.rfind(" ")
    if sp > n*0.6: cut = cut[:sp]
    return cut.rstrip() + "…"

def fit_280(text, link=""):
    # ensure <=280 incl link + tags
    if link and link not in text:
        if len(text) + 1 + len(link) <= 280:
            return f"{text} {link}"
    if len(text) <= 280:
        return text
    return text[:279].rstrip() + "…"

def synthesize_fallback(enriched):
    aest_now = datetime.now(AEST)
    top = enriched[:8]
    # deterministic per date like FacelessStudio mulberry32
    seed = int(hashlib.md5(aest_now.strftime("%Y-%m-%d").encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    niche_order = rng.sample(["ai","gadgets","apple","hardware","security","it-support","cloud-devops"][:5], 4)
    # pick deepest per niche (mirrors FacelessStudio pickDeepest: prefer link + fresh + non-promo)
    tweets = []
    for slot, pillar in enumerate(PILLARS):
        niche = niche_order[slot % len(niche_order)]
        # find best item for niche (by score)
        candidates = [t for t in enriched if niche in (t.get("pillar","")+t.get("source_url","")).lower() or t.get("weight",0)>=2]
        if not candidates: candidates = top
        item = sorted(candidates, key=lambda x: x.get("score",0), reverse=True)[slot % len(candidates)] if candidates else top[slot % len(top)]
        title = item.get("title","Tech update").strip()
        link = item.get("link","")
        # Build pillar-specific 280-char text (mirrors FacelessStudio x-generator captionFor)
        if pillar == "redflag":
            text = f"🚩 {shorten(title, 80)} — silent risk. Why & fix inside. {NICHE_TAGS.get(niche,'#tech')}"
        elif pillar == "myth":
            text = f"🛑 Myth: {shorten(title, 60)}\nTruth: Check the thread — it’s not what you think. {NICHE_TAGS.get(niche,'#tech')}"
        elif pillar == "secrets":
            text = f"🔓 {shorten(title, 70)} — IT pro shortcut you’ll wish you knew sooner. {NICHE_TAGS.get(niche,'#tech')}"
        else:  # guide
            text = f"🛠️ {shorten(title, 70)} — 4-step fix you can do now. {NICHE_TAGS.get(niche,'#tech')}"
        text = fit_280(text, link if pillar=="redflag" else "")
        tweets.append({"slot": slot, "pillar": pillar, "niche": niche, "text": text, "link": link, "title": title, "score": item.get("score",0)})

    # Friday gadget focus 5th?
    if aest_now.weekday() == 4 and len(enriched) > 4:  # Friday
        item = sorted([t for t in enriched if "gadget" in t.get("title","").lower() or "pixel" in t.get("title","").lower()], key=lambda x: x.get("score",0), reverse=True)
        item = item[0] if item else top[0]
        tweets.append({"slot": 4, "pillar": "gadget-focus", "niche": "gadgets", "text": fit_280(f"📱 Friday Gadget: {shorten(item['title'],65)} {NICHE_TAGS['gadgets']}", item.get("link","")), "link": item.get("link",""), "title": item["title"]})

    # also write draft.md for compat (concatenated)
    md = f"# X Draft — {aest_now.strftime('%Y-%m-%d %A AEST')}\n\n" + "\n\n---\n\n".join([f"**Slot {t['slot']} [{t['pillar']}/{t['niche']}]**\n{t['text']}\n{t['link']}" for t in tweets])
    DRAFTS.mkdir(parents=True, exist_ok=True)
    fname = f"{aest_now.strftime('%Y-%m-%d')}-x.json"
    (DRAFTS / fname).write_text(json.dumps(tweets, indent=2, ensure_ascii=False), encoding="utf-8")
    (DRAFTS / fname.replace(".json",".md")).write_text(md, encoding="utf-8")
    OUT.write_text(md, encoding="utf-8")
    TWEETS_OUT.write_text(json.dumps(tweets, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Fallback X draft -> {fname} ({len(tweets)} tweets) AEST {aest_now.isoformat()}")
    return tweets

def synthesize():
    if not ENRICHED.exists():
        raise SystemExit("Run enrich.py first")
    enriched = json.loads(ENRICHED.read_text(encoding="utf-8"))
    system = PROMPT_FILE.read_text(encoding="utf-8")
    aest_now = datetime.now(AEST)
    top = enriched[:7]
    context = "\n\n".join([f"[{i+1}] {t['title']} ({t['link']}) Score {t['score']}\n{t.get('enriched_text','')[:1000]}" for i,t in enumerate(top)])
    user = f"""Date AEST: {aest_now.strftime('%Y-%m-%d %A %H:%M AEST')}
Slots: 4 (0:redflag,1:myth,2:secrets,3:guide) + Friday slot4 gadget if Friday
Context sources (cite each):
{context}
Output JSON array of 4 objects with slot/pillar/niche/text(<=280)/link per system prompt. Max 4 hashtags per tweet.
"""

    gem_key = os.environ.get("GEMINI_API_KEY","")
    if gem_key and not gem_key.startswith("dummy") and gem_key!="":
        try:
            try:
                from google import genai as genai2
                client = genai2.Client(api_key=gem_key)
                for m in ["gemini-flash-latest","gemini-2.0-flash","gemini-pro-latest"]:
                    try:
                        resp = client.models.generate_content(model=m, contents=system + "\n\n" + user)
                        draft = resp.text.strip()
                        break
                    except Exception as e:
                        if "404" in str(e) or "503" in str(e) or "429" in str(e): continue
                        raise
                else: raise ValueError("No Gemini model")
            except ImportError:
                import google.generativeai as genai
                genai.configure(api_key=gem_key)
                for m in ["gemini-flash-latest","gemini-1.5-flash"]:
                    try:
                        model = genai.GenerativeModel(m)
                        resp = model.generate_content(system + "\n\n" + user)
                        draft = resp.text.strip()
                        break
                    except: continue
                else: raise ValueError("No model")
            # parse JSON from response
            import re
            m = re.search(r'\[.*\]', draft, re.S)
            tweets = json.loads(m.group(0)) if m else json.loads(draft)
            # validate
            for t in tweets:
                if len(t.get("text","")) > 280:
                    t["text"] = t["text"][:279]+"…"
            DRAFTS.mkdir(parents=True, exist_ok=True)
            fname = f"{aest_now.strftime('%Y-%m-%d')}-x.json"
            (DRAFTS / fname).write_text(json.dumps(tweets, indent=2, ensure_ascii=False), encoding="utf-8")
            TWEETS_OUT.write_text(json.dumps(tweets, indent=2, ensure_ascii=False), encoding="utf-8")
            # also md
            md = f"# X Draft — {aest_now.strftime('%Y-%m-%d %A AEST')}\n\n" + json.dumps(tweets, indent=2)
            OUT.write_text(md, encoding="utf-8")
            print(f"Gemini X draft -> drafts/{fname} ({len(tweets)} tweets) AEST {aest_now.isoformat()}")
            return tweets
        except Exception as e:
            print(f"Gemini synthesize failed ({e}) -> try OpenAI")

    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        if not os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY","").startswith("sk-dummy"):
            raise ValueError("No valid OPENAI_API_KEY")
        resp = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL","gpt-4o"),
            messages=[{"role":"system","content": system},{"role":"user","content": user}],
            temperature=0.6, max_tokens=2500
        )
        draft = resp.choices[0].message.content.strip()
        import re
        m = re.search(r'\[.*\]', draft, re.S)
        tweets = json.loads(m.group(0)) if m else json.loads(draft)
        for t in tweets:
            if len(t.get("text","")) > 280: t["text"] = t["text"][:279]+"…"
        DRAFTS.mkdir(parents=True, exist_ok=True)
        fname = f"{aest_now.strftime('%Y-%m-%d')}-x.json"
        (DRAFTS / fname).write_text(json.dumps(tweets, indent=2, ensure_ascii=False), encoding="utf-8")
        TWEETS_OUT.write_text(json.dumps(tweets, indent=2, ensure_ascii=False), encoding="utf-8")
        OUT.write_text(draft, encoding="utf-8")
        print(f"OpenAI X draft -> drafts/{fname} ({len(tweets)} tweets)")
        return tweets
    except Exception as e:
        print(f"OpenAI synthesize failed ({e}) -> fallback heuristic")
        return synthesize_fallback(enriched)

if __name__ == "__main__":
    synthesize()
