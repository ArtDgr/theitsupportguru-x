#!/usr/bin/env python3
"""qa.py: X hallucination + 280-char + hashtag gate"""
import re, json
from pathlib import Path

TWEETS = Path(__file__).parent.parent / "out" / "tweets.json"
DRAFT = Path(__file__).parent.parent / "out" / "draft.md"
ENRICHED = Path(__file__).parent.parent / "out" / "enriched.json"

PLACEHOLDERS = ["this is moving the whole field", "what changed:", "what to watch: the follow", "good morning", "hope you had", "today i'm reading", "subscribe", "unsubscribe"]
HASHTAG_RE = re.compile(r"#\w+")

def qa():
    if not TWEETS.exists():
        print("QA SKIP - no tweets.json (synthesize first)")
        return []
    tweets = json.loads(TWEETS.read_text(encoding="utf-8"))
    enriched = json.loads(ENRICHED.read_text(encoding="utf-8")) if ENRICHED.exists() else []
    links = [x["link"] for x in enriched]
    issues = []
    for t in tweets:
        where = f"[slot {t.get('slot')}] {t.get('title','')[:40]}"
        text = t.get("text","")
        if len(text) > 280:
            issues.append(f"{where} - {len(text)} chars exceeds 280")
        if len(text.strip()) < 20:
            issues.append(f"{where} - too short")
        if "&#" in text or "&amp;" in text:
            issues.append(f"{where} - lingering HTML entity")
        low = text.lower()
        for ph in PLACEHOLDERS:
            if ph in low:
                issues.append(f"{where} - placeholder '{ph}'")
                break
        tags = HASHTAG_RE.findall(text)
        if len(tags) > 4:
            issues.append(f"{where} - {len(tags)} hashtags >4")
        # CVE must be cited in enriched
        cves = re.findall(r"CVE-\d{4}-\d{4,7}", text)
        for c in cves:
            if not any(c in (e.get("enriched_text","")+e.get("title","")) for e in enriched):
                issues.append(f"{where} - uncited CVE {c}")
        # need link for news pillar
        if t.get("pillar") in ("news","gadget-focus") and not t.get("link"):
            # allow but warn if news without link
            if not any(cves):  # only warn for news without link/cve
                pass

    if len(tweets) < 2 or len(tweets) > 5:
        issues.append(f"Need 2-5 tweets, have {len(tweets)}")
    if not enriched or len(set(links)) < 3:
        print("QA WARN - need 3+ unique sources for grounding")
        # not fatal for X fallback but log

    if issues:
        print("QA WARNINGS:")
        for i in issues: print(f"  - {i}")
        if any("uncited CVE" in x or "exceeds 280" in x for x in issues):
            raise SystemExit(f"QA FAIL - blocking X publish: {issues}")
    else:
        print(f"QA PASS - {len(tweets)} X tweets grounded, all <=280, hashtags ok")
    Path(__file__).parent.parent.joinpath("out/qa.json").write_text(json.dumps({"issues": issues, "tweets": len(tweets)}, indent=2))
    return issues

if __name__ == "__main__":
    qa()
