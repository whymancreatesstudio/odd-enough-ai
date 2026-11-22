#!/usr/bin/env python3
"""Rebuild creator_playbooks/INDEX.md from whatever shorts_full.json files exist."""
import json, pathlib
H = pathlib.Path(__file__).resolve().parent; OUT = H.parent
rows = []
for c in json.loads((H / "creators.json").read_text()):
    f = OUT / c["folder"] / "shorts_full.json"
    if f.exists():
        r = json.loads(f.read_text()); d = r["distribution"]; pdf = next((OUT / c["folder"]).glob("CONTENT_PLAYBOOK_*.pdf"), None)
        rows.append(f"| {c['n']} | [{c['name']}]({c['folder']}/) | {c['platform']} | {r['n_videos']} | {d['median']:,.0f} | {d['top10pct_share']:.0%} | {r['funnel']['jev_cost_usd']} | {'yes' if pdf else 'no'} |")
    else:
        rows.append(f"| {c['n']} | {c['name']} | {c['platform']} | not run | | | | |")
(OUT / "INDEX.md").write_text("# Creator playbooks\n\nOne folder per creator; creators are never merged.\n\n| # | Creator | Platform | Analysed | Median views | Top-10% share | Jev cost $ | PDF |\n|---|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n")
print("INDEX.md written")
