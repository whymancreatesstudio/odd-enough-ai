#!/usr/bin/env python3
"""Step 1. List every video of a creator, then save thumbnail + info.json + audio
for each one inside the date range. Re-running skips what is already saved.

  python3 1_collect.py --channel https://www.youtube.com/@thinkschool/shorts --since 2024-11-21
"""
import argparse, concurrent.futures as cf, datetime as dt, json, random, subprocess, sys, threading, time
import yt_dlp
from common import *

REFUSAL_LIMIT = 5
REFUSAL_MARKERS = ("429", "403", "too many requests", "sign in to confirm", "not a bot",
                   "rate-limit", "rate limit", "login required", "checkpoint", "please wait")

ap = argparse.ArgumentParser()
ap.add_argument("--channel", help="YouTube Shorts URL or Instagram profile URL")
ap.add_argument("--since", help="oldest upload date to keep, YYYY-MM-DD")
ap.add_argument("--refresh", action="store_true", help="re-list the channel")
args = ap.parse_args()

cfg = read_json(CONFIG) if CONFIG.exists() else {}
cfg["channel"] = args.channel or cfg.get("channel")
cfg["since"] = args.since or cfg.get("since")
if not cfg["channel"] or not cfg["since"]:
    sys.exit("need --channel and --since the first time")
write_json(CONFIG, cfg)
since = dt.date.fromisoformat(cfg["since"]).strftime("%Y%m%d")
insta = "instagram.com" in cfg["channel"]
workers = 1 if insta else 2
DATA.mkdir(exist_ok=True)

# --- list every video (--flat-playlist -J) -------------------------------------------
listing = ROOT / "listing.json"
if args.refresh or not listing.exists():
    cmd = ["yt-dlp", "--flat-playlist", "-J", cfg["channel"]]
    if insta:
        cmd[1:1] = ["--cookies-from-browser", "chrome"]
    print("Listing videos ...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit("listing failed:\n" + r.stderr[-800:])
    listing.write_text(r.stdout)
entries = [e for e in json.loads(listing.read_text())["entries"] if e and e.get("id")]
print(f"{len(entries)} videos listed; keeping uploads on/after {cfg['since']}")

# --- per-video download --------------------------------------------------------------
state = {"refusals": 0, "stop": False}
lock = threading.Lock()


def is_refusal(msg):
    m = msg.lower()
    return any(k in m for k in REFUSAL_MARKERS)


def base_opts():
    o = {"quiet": True, "no_warnings": True, "noplaylist": True, "retries": 1, "extractor_retries": 1}
    if insta:
        o["cookiesfrombrowser"] = ("chrome",)
    return o


def collect(entry):
    vid = entry["id"]
    d = vid_dir(vid)
    if (d / "out_of_range").exists():
        return "skip"
    have = (d / "info.json").exists() and (d / "thumb.jpg").exists() and list(d.glob("audio.*"))
    if have:
        return "skip"
    with lock:
        if state["stop"]:
            return "stopped"
    time.sleep(random.uniform(1.0, 3.0))  # go slowly
    url = entry.get("url") or f"https://www.youtube.com/watch?v={vid}"
    try:
        with yt_dlp.YoutubeDL({**base_opts(), "skip_download": True}) as y:
            info = y.extract_info(url, download=False)
        up = info.get("upload_date")
        if up and up < since:
            (d / "out_of_range").write_text(up)
            return "old"
        opts = {**base_opts(), "format": "ba[ext=m4a]/ba/b", "outtmpl": str(d / "audio.%(ext)s"),
                "writethumbnail": True, "postprocessors": [{"key": "FFmpegThumbnailsConvertor", "format": "jpg"}]}
        opts["outtmpl"] = {"default": str(d / "audio.%(ext)s"), "thumbnail": str(d / "thumb")}
        with yt_dlp.YoutubeDL(opts) as y:
            y.process_ie_result(info, download=True)
        write_json(d / "info.json", {
            "id": vid, "url": url, "title": info.get("title"), "upload_date": up,
            "view_count": info.get("view_count"), "like_count": info.get("like_count"),
            "duration": info.get("duration"), "channel": info.get("channel") or info.get("uploader")})
        with lock:
            state["refusals"] = 0
        return "ok"
    except Exception as e:
        msg = str(e)
        with lock:
            if is_refusal(msg):
                state["refusals"] += 1
                if state["refusals"] >= REFUSAL_LIMIT:
                    state["stop"] = True
            else:
                state["refusals"] = 0
        return "refused" if is_refusal(msg) else "error: " + msg.splitlines()[-1][:160]


counts = {}
with cf.ThreadPoolExecutor(workers) as ex:
    futs = {ex.submit(collect, e): e for e in entries}
    for i, f in enumerate(cf.as_completed(futs), 1):
        r = f.result()
        k = r.split(":")[0]
        counts[k] = counts.get(k, 0) + 1
        if r not in ("skip", "ok", "old", "stopped"):
            print(f"  {futs[f]['id']}: {r}")
        if i % 25 == 0:
            print(f"  {i}/{len(entries)}  {counts}")
        if state["stop"] and not state.get("announced"):
            state["announced"] = True
            print(f"!! {REFUSAL_LIMIT} refusals in a row - stopping. Re-run later (or with cookies) to resume.")
print("done:", counts, "| videos in range with files:", len(all_videos()))
