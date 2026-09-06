#!/usr/bin/env python3
"""ingest.py - RSS ingest for The IT Support Guru : 1:38 sources, AEST aware"""
import feedparser, yaml, hashlib, json, time, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

AEST = timezone(timedelta(hours=10))
CONFIG = Path(__file__).parent.parent / "config" / "sources.yaml"
OUT = Path(__file__).parent.parent / "out" / "ingest.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

def load_sources():
    with open(CONFIG) as f:
        return yaml.safe_load(f)

def ingest():
    cfg = load_sources()
    items = []
    seen = set()
    sources = []
    # X uses 7 IG niches (ai, gadgets, apple, hardware, security, it-support, cloud-devops) plus legacy substack keys
    for cat in ["ai","gadgets","apple","hardware","security","it-support","cloud-devops","windows_platform","cybersecurity","ai_applied","infra_specialist"]:
        sources.extend(cfg.get(cat,[]))
    # fallback: if no known cat, ingest all list values
    if not sources:
        for v in cfg.values():
            if isinstance(v, list):
                sources.extend(v)
    print(f"Ingesting {len(sources)} feeds (AEST {datetime.now(AEST).isoformat()})")
    for s in sources:
        url = s["url"]
        try:
            d = feedparser.parse(url)
            for e in d.entries[:15]:
                # dedupe by link hash
                lid = hashlib.md5(e.get("link","").encode()).hexdigest()
                if lid in seen: continue
                seen.add(lid)
                # filter last 7 days only
                pub = e.get("published_parsed") or e.get("updated_parsed")
                if pub:
                    dt = datetime.fromtimestamp(time.mktime(pub), tz=timezone.utc)
                    if (datetime.now(timezone.utc) - dt).days > 7:
                        continue
                items.append({
                    "title": e.get("title","").strip(),
                    "link": e.get("link",""),
                    "summary": re.sub("<[^>]+>","", e.get("summary",""))[:600],
                    "published": e.get("published",""),
                    "source_url": url,
                    "pillar": s.get("pillar","all"),
                    "weight": s.get("weight",1),
                    "id": lid
                })
            print(f"  {url[:60]} -> {len(d.entries)} entries")
            time.sleep(0.8) # polite delay, avoids rate flag
        except Exception as ex:
            print(f"  FAIL {url}: {ex}")
    # sort by weight desc
    items.sort(key=lambda x: x["weight"], reverse=True)
    print(f"Total items: {len(items)}")
    OUT.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    return items

if __name__ == "__main__":
    ingest()
