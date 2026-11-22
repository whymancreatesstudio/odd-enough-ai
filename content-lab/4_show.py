"""Step 4. Build report.html (one file, open it straight in the browser, no server) and print the headline numbers."""
import datetime as dt
import json
import statistics
import webbrowser

from common import DATA, ROOT, JEV_PRICE_PER_M_INPUT, load_json, video_ids

MIN_N = 10


def collect():
    rows = []
    for vid in video_ids():
        info, jev = load_json(DATA / "info" / f"{vid}.json"), load_json(DATA / "jev" / f"{vid}.json")
        if not info or not jev or "answers" not in jev or not info.get("in_range"):
            continue
        if not info.get("views") or not info.get("upload_date"):
            continue
        a = jev["answers"]
        style, hook, cta = a["style"], a["hook"], a["has_cta"]
        sents = []
        for i, text in enumerate(jev["sentences"]):
            r = a.get(f"role_{i}", {})
            sents.append({"t": text, "role": r.get("choice"), "p": (r.get("probabilities") or {}).get(r.get("choice"))})
        rows.append({"id": vid, "title": info["title"], "date": dt.datetime.strptime(info["upload_date"], "%Y%m%d").strftime("%Y-%m-%d"),
                     "views": info["views"], "likes": info.get("likes"), "url": info.get("url"),
                     "style": style["choice"], "style_p": style["probabilities"][style["choice"]],
                     "hook": hook["choice"], "hook_p": hook["probabilities"][hook["choice"]],
                     "cta": cta["noul"], "sents": sents})
    return rows


def ranking(rows, key):
    groups = {}
    for r in rows:
        groups.setdefault(r[key], []).append(r["views"])
    out = [{"name": k, "n": len(v), "median": statistics.median(v)} for k, v in groups.items()]
    return sorted(out, key=lambda g: (g["n"] < MIN_N, -g["median"]))


def main():
    rows = collect()
    if not rows:
        raise SystemExit("No finished videos yet. Run steps 1-3 first.")
    tokens = sum((load_json(p, {}).get("usage") or {}).get("input_tokens", 0) for p in (DATA / "jev").glob("*.json"))
    cost = tokens * JEV_PRICE_PER_M_INPUT / 1e6
    html = (ROOT / "template.html").read_text().replace(
        "__DATA__", json.dumps({"videos": rows, "cost": cost, "tokens": tokens, "min_n": MIN_N}, ensure_ascii=False).replace("</", "<\\/"))
    out = ROOT / "report.html"
    out.write_text(html)
    print(f"Wrote {out}  ({len(rows)} videos)")
    for label, key in (("STYLES", "style"), ("HOOKS", "hook")):
        print(f"\nTop {label} by median views (groups with fewer than {MIN_N} videos ignored):")
        for i, g in enumerate([g for g in ranking(rows, key) if g["n"] >= MIN_N][:3], 1):
            print(f"  {i}. {g['name']:<13} median {g['median']:>12,.0f} views   based on {g['n']} videos")
    print(f"\nTotal Jev cost: ${cost:.4f}  ({tokens:,} input tokens at ${JEV_PRICE_PER_M_INPUT}/M)")
    try:
        webbrowser.open(out.as_uri())
    except Exception:
        pass


if __name__ == "__main__":
    main()
