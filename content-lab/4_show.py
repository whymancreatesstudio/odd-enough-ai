#!/usr/bin/env python3
"""Step 4. Build report.html (one static page, no server) and open it. Prints the headline numbers."""
import json, statistics, webbrowser
from common import *

MIN_N = 10
PRICE_PER_M = 0.042
cfg = load_config()
videos = []
for vid in all_videos():
    d = DATA / vid
    if not (d / "jev.json").exists():
        continue
    info, jev = read_json(d / "info.json"), read_json(d / "jev.json")
    a = jev["answers"]
    roles = []
    for i, s in enumerate(jev["sentences"], 1):
        r = a.get(f"role_{i}", {})
        roles.append({"t": s, "role": r.get("choice"), "p": round(max(r.get("probabilities", {0: 0}).values()), 2)})
    up = info.get("upload_date") or ""
    videos.append({
        "id": vid, "title": info["title"], "date": f"{up[:4]}-{up[4:6]}-{up[6:]}" if up else None,
        "views": info.get("view_count") or 0, "likes": info.get("like_count"), "url": info["url"],
        "style": a["style"]["choice"], "style_p": round(max(a["style"]["probabilities"].values()), 2),
        "hook": a["hook"]["choice"], "hook_p": round(max(a["hook"]["probabilities"].values()), 2),
        "cta": round(a["has_cta"]["noul"], 2), "roles": roles,
        "tokens": jev["usage"]["input_tokens"]})
videos = [v for v in videos if v["date"]]
if not videos:
    raise SystemExit("no videos with Jev answers yet - run steps 1-3")


def rank(key):
    groups = {}
    for v in videos:
        groups.setdefault(v[key], []).append(v["views"])
    rows = [{"name": k, "n": len(x), "median": statistics.median(x)} for k, x in groups.items()]
    rows.sort(key=lambda r: -r["median"])
    ok = [r for r in rows if r["n"] >= MIN_N]
    for r in rows:
        r["winner"] = bool(ok) and r is ok[0]
        r["small"] = r["n"] < MIN_N
    return rows


styles, hooks = rank("style"), rank("hook")
tokens = sum(v["tokens"] for v in videos)
cost = tokens * PRICE_PER_M / 1e6
payload = {"channel": cfg["channel"], "since": cfg["since"], "min_n": MIN_N, "videos": videos,
           "styles": styles, "hooks": hooks, "tokens": tokens, "cost": cost}
html = (ROOT / "report_template.html").read_text().replace("/*DATA*/null", json.dumps(payload, ensure_ascii=False))
out = ROOT / "report.html"
out.write_text(html)
write_json(ROOT / "summary.json", {k: payload[k] for k in ("styles", "hooks", "tokens", "cost")})

print(f"{len(videos)} videos -> {out}")
for label, rows in (("Styles", styles), ("Hooks", hooks)):
    print(f"\nTop {label.lower()} by median views (groups with n >= {MIN_N}):")
    for r in [r for r in rows if not r["small"]][:3]:
        print(f"  {r['name']:<14} median {r['median']:>10,.0f}  (n={r['n']})")
    small = [f"{r['name']} (n={r['n']})" for r in rows if r["small"]]
    if small:
        print("  ignored, fewer than 10:", ", ".join(small))
print(f"\nJev total: {tokens:,} input tokens -> ${cost:.4f}")
webbrowser.open(out.as_uri())
